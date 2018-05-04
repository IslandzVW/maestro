'''
Created on Jan 24, 2013

@author: mdickson
'''
import sys
import errno
import time
import os.path
import threading
import shlex
import shutil
import subprocess
import psutil
import Queue

import inworldz.util.provision as provision
import inworldz.util.properties as DefaultProperties

from inworldz.util.filesystem import ConnectUNCShare
from inworldz.util.rdbhost import GetRdbHost, AssignBestRdbHost

import inworldz.util.general

import inworldz.maestro.uuid as genuuid
import inworldz.maestro.MaestroStore as store

from inworldz.maestro.ServiceBase import ServiceBase
from inworldz.maestro.MaestroError import ServiceError

from inworldz.maestro.System import Cpu, Disk, Memory, Process
from inworldz.maestro.Region import Region
from inworldz.maestro.GridServices import UserService, MessagingService, ApertureService,\
    GridService
import inworldz.maestro.environment.ComputeResource as ComputeResource
from inworldz.maestro.environment.RegionEntry import RegionState, RegionEntry
from inworldz.maestro.Estate import Estate
from inworldz.maestro import User

class RegionHost(ServiceBase):
    """Region Host Server"""
    
    @classmethod
    def instance(cls):
        global inst
        try:
            inst
        except:
            hostid = RegionHost.create({})
            inst = store.get(hostid, RegionHost.getClass())
            inst.start()
        return inst

    @classmethod
    def getClass(cls):
        return "RegionHost"

    @classmethod
    def getMethods(cls):
        methods = [
            "IsSlotProvisioned",
            "IsSlotFree",
            "GetSlotDirectory",
            "GetSlotConfiguration",
            "ProvisionRegion",
            "Shutdown",
            "UpdateRegionToRevision",
            "UpdateRegionToLatest",
            "UpdateGridServicesToRevision",
            "UpdateGridServicesToLatest",
            "ReconfigureRegion",
            "ReconfigureGridServices",
            "RunCommand",
            "RunCommandAs"
            ]
        return ServiceBase.getMethods() + methods
     
    @classmethod
    def getAttrRO(cls):
        attrs = [
           "Regions",
           "Memory",
           "Disk",
           "Cpu",
           "Process",
           "UserService",
           "MessagingService",
           "ApertureService",
           "GridService",
           "service_base_dir",
           "slot_base_dir",
           "max_slots",
           "Flags"
            ]
        return ServiceBase.getAttrRO() + attrs
    
    @classmethod
    def getAttrRW(cls):
        attrs = [
           "maintenance_mode",  
            ]
        return ServiceBase.getAttrRW() + attrs
        
    @classmethod
    def getFuncs(cls):
        funcs = [
            "GetAvailableReleases"
            ]
        return ServiceBase.getFuncs() + funcs
    
    
    def __init__(self, uuid, record={}):
        ServiceBase.__init__(self, uuid, record) 
        self.props = DefaultProperties.instance()
        
        self.set_maintenance_mode(record.get('maintenance_mode'))
            
        self.host_memory = Memory(genuuid.createString())
        self.host_disk = Disk(genuuid.createString())
        self.host_cpu = Cpu(genuuid.createString())
        self.process = Process(genuuid.createString())
        self.maxRegionSlots = provision.GetMaxRegionSlots()
        self.slotBaseDir = provision.GetSlotBaseDir()
        self.serviceBaseDir = provision.GetServiceBaseDir()
        self.regions = []
        self.regions_lock = threading.RLock()
        
    @classmethod
    def create(cls, record):          
        uuid = genuuid.createString()
        return (cls.recreate(record, uuid))     

    @classmethod
    def recreate(cls, record, uuid):          
        service = RegionHost(uuid, record)
        return (service.get_uuid())
    
    @classmethod
    def GetAvailableReleases(cls):
        try:
            props = DefaultProperties.instance()
            gridshare_path = props.getValue("gridshare_path")
            (username, password) = props.getGridShareCredentials()   
            
            ConnectUNCShare(gridshare_path, username, password)
            return (provision.GetRevisions(gridshare_path))              
        except:
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            raise ServiceError(exc_value) 


    def start(self):
        # Initialize grid services
        self.user_service_id = UserService.create({})
        self.user_service = store.get(self.user_service_id, "UserService") 
        self.messaging_service_id = MessagingService.create({})
        self.messaging_service = store.get(self.messaging_service_id, "MessagingService")
        self.aperture_service_id = ApertureService.create({})
        self.aperture_service = store.get(self.aperture_service_id, "ApertureService")
        
        #if we should be hosting a grid service, fire that up too
        if self.props.hostingResource.flags & ComputeResource.Flags.GridServiceHost == ComputeResource.Flags.GridServiceHost:
            self.grid_service_id = GridService.create({})
            self.grid_service = store.get(self.grid_service_id, "GridService")
        else:
            self.grid_service = None
            
        # Initialize regions
        for slot in range(self.maxRegionSlots):
            if not provision.IsSlotProvisioned(slot):
                continue
            regionInfo = provision.GetSlotConfiguration(slot)
            for region_uuid in regionInfo.keys():
                record = regionInfo[region_uuid]
                record['slot_number'] = slot
                record['master_avatar_uuid'] = User.User.FindByName(record["master_avatar_first"], 
                                                                    record["master_avatar_last"])
                try:
                    region = Region.recreate(record, region_uuid)
                    self.region_add(region)
                except:
                    import traceback
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_exception(exc_type, exc_value, exc_traceback)           
                    pass
        
        self.work_queue = Queue.Queue()
        self.queue_runner = threading.Thread(target=self._processQueue, name="QueueRunner")
        self.queue_runner.start()
                
        self.poll_interval = 10.0;
        self.monitor = threading.Thread(target=self._regionMonitor, name="RegionMonitor")
        self.monitor.start()       
        

    def _processQueue(self):
        print "QueueRunner Starting"
        while True:
            try:
                objid = self.work_queue.get()
                
                service = None
                for classname in ["ApertureService", "UserService", "MessagingService", "GridService", "Region"]:
                    service = store.get(objid, classname)
                    if (service != None):
                        break
                    
                if service:
                    if service.ShouldBeRunning():
                        service.Start()
                        time.sleep(2) #prevents mono addins problems when services rapid-fire start
                    
                else:
                    print "QueueRunner: Unknown object type queued for service"
            except:
                import traceback
                exc_type, exc_value, exc_traceback = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_traceback)           
                pass
            finally:
                self.work_queue.task_done()
                    
    def _regionMonitor(self):
        print "RegionMonitor Starting"
        while True:
            try:
                if (self.maintenance_mode == True):
                    continue
                
                if (self.aperture_service.IsRunning() == False and self.aperture_service.ShouldBeRunning()):
                    self.work_queue.put(self.aperture_service_id)
                
                if (self.user_service.IsRunning() == False and self.user_service.ShouldBeRunning()):
                    self.work_queue.put_nowait(self.user_service_id)
                    
                if (self.grid_service != None and self.grid_service.IsRunning() == False and self.grid_service.ShouldBeRunning()):
                    self.work_queue.put_nowait(self.grid_service_id)
  
                if (self.messaging_service.IsRunning() == False and self.messaging_service.ShouldBeRunning()):
                    self.work_queue.put_nowait(self.messaging_service_id)
                    
                with self.regions_lock:
                    for region_uuid in self.regions:
                        region = store.get(region_uuid, "Region")
                        regionEntry = self.props.hostingResource.findHostedRegionByUUID(region_uuid)
                        
                        if region == None or regionEntry == None:
                            continue
                        
                        if regionEntry.state != RegionState.DeployedRunning:
                            continue
                        
                        if (region.IsRunning() == False):
                            self.work_queue.put(region_uuid)
            except:
                import traceback
                exc_type, exc_value, exc_traceback = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_traceback)           
                pass
            finally:
                time.sleep(self.poll_interval)
        
    def Shutdown(self):
        pass
    
    def get_maintenance_mode(self):
        return self.maintenance_mode
    
    def set_maintenance_mode(self, mode):
        self.maintenance_mode = bool(mode if mode != None else False)
        return self.maintenance_mode
    
    def region_add(self, region):
        with self.regions_lock:
            self.regions.append(region)
        
    def region_del(self, region):
        with self.regions_lock:
            self.regions.remove(region)

    def get_Memory(self):
        return self.host_memory.get_uuid()
    
    def get_Disk(self):
        return self.host_disk.get_uuid()    
    
    def get_Cpu(self):
        return self.host_cpu.get_uuid()
    
    def get_Process(self):
        return self.process.get_uuid()
    
    def get_Regions(self):
        with self.regions_lock:
            return self.regions

    def get_UserService(self):
        return self.user_service_id

    def get_MessagingService(self):
        return self.messaging_service_id 

    def get_ApertureService(self):
        return self.aperture_service_id
    
    def get_GridService(self):
        return self.grid_service_id
    
    def get_service_base_dir(self):
        return self.serviceBaseDir
    
    def get_slot_base_dir(self):
        return self.slotBaseDir
    
    def get_max_slots(self):
        return self.maxRegionSlots
    
    def get_Flags(self):
        return self.props.hostingResource.flags;
               
    def IsSlotProvisioned(self, slotnum):
        return (provision.IsSlotProvisioned(slotnum))
    
    def IsSlotFree(self, slotnum):
        return (provision.IsSlotFree(slotnum))
    
    def GetSlotDirectory(self, slotnum):
        return (provision.GetSlotDirectory(slotnum))
        
    def GetSlotConfiguration(self, slotnum):
        return (provision.GetSlotConfiguration(slotnum))
    
    def ProvisionRegion(self, record):
        """ Set up a new region in the resource pool provided by this host
                sim_name       - The name of the new region to provision
                sim_location_x - The x location on the map for the new region
                sim_location_y - The y location on the map for the new region
                master_avatar_uuid - The user that owns this new region
                
        """
        for slotnum in range(self.maxRegionSlots):
            if (self.IsSlotFree(slotnum)):
                record['slot_number'] = slotnum
                
                regions = self.RecordSimulatorRegions([record])
                return regions[0].get_uuid()

        """ No slots found available. tell them """
        raise ServiceError("No region slot is available")
    
    def RecordSimulatorRegions(self, region_records):
        regions = []
        for record in region_records:
            try:
                region = Region.create(record)
                
                #also record this provisioning to the environment
                regEntry = RegionEntry(region.sim_uuid, region.sim_name, region.master_avatar_uuid, \
                                        region.estate_id, region.get_region_product(), \
                                        region.sim_location_x, region.sim_location_y, \
                                        self.props.hostingResource.dbid, \
                                        RegionState.SetupInProgress)

                self.props.hostingResource.registerNewRegion(regEntry)
                region.associateWithRegionEntry()
                
                self.region_add(region.get_uuid()) 
                
                regions.append(region)
            
            except:
                import traceback
                exc_type, exc_value, exc_traceback = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_traceback)
                raise ServiceError(exc_value)
        return regions

    def UpdateRegionToRevision(self, region_uuid, revision):
        """ Update the region to the revision specified. """
        region = store.get(region_uuid, Region.getClass())
        if (region == None):
            raise ServiceError("Invalid Region Specified")
        
        if (region.IsRunning()):
            raise ServiceError("Cannot update a running region.")

        try:
            target = region.get_slot_directory()
            gridshare_path = self.props.getValue("gridshare_path")
            (username, password) = self.props.getGridShareCredentials()   
             
            ConnectUNCShare(gridshare_path, username, password)
            return (provision.ProvisionFromRevision(gridshare_path, target, revision))               
        except:
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            raise ServiceError(exc_value)
        

    def UpdateRegionToLatest(self, region_uuid):
        """ Update the region to the latest revision. """
        region = store.get(region_uuid, Region.getClass())
        if (region == None):
            raise ServiceError("Invalid Region Specified")
        
        if (region.IsRunning()):
            raise ServiceError("Cannot update a running region.")
        
        try:
            target = region.get_slot_directory()
            gridshare_path = self.props.getValue("gridshare_path")
            (username, password) = self.props.getGridShareCredentials()   
             
            ConnectUNCShare(gridshare_path, username, password)
            return (provision.ProvisionFromLatest(gridshare_path, target))     
        except:
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            raise ServiceError(exc_value)
        
        
    def UpdateGridServicesToRevision(self, revision):
        """ Update the target to the revision specified. """
        
        if (self.aperture_service.IsRunning()):
            raise ServiceError("Update: Cannot update, aperture is running.")
        if (self.messaging_service.IsRunning()):
            raise ServiceError("Update: Cannot update, messaging service is running.")
        if (self.user_service.IsRunning()):
            raise ServiceError("Update: Cannot update, user service is running.")
        
        try:
            target = provision.GetServiceBaseDir()
            gridshare_path = self.props.getValue("gridshare_path")
            (username, password) = self.props.getGridShareCredentials()   
             
            ConnectUNCShare(gridshare_path, username, password)
            return (provision.ProvisionFromRevision(gridshare_path, target, revision))             
        except:
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            raise ServiceError(exc_value)
        

    def UpdateGridServicesToLatest(self):
        """ Update the grid services to the latest revision. """
        
        if (self.aperture_service.IsRunning()):
            raise ServiceError("Update: Cannot update, aperture is running.")
        if (self.messaging_service.IsRunning()):
            raise ServiceError("Update: Cannot update, messaging service is running.")
        if (self.user_service.IsRunning()):
            raise ServiceError("Update: Cannot update, user service is running.")
        
        try:
            target = provision.GetServiceBaseDir()
            gridshare_path = self.props.getValue("gridshare_path")
            (username, password) = self.props.getGridShareCredentials()   
             
            ConnectUNCShare(gridshare_path, username, password)
            return (provision.ProvisionFromLatest(gridshare_path, target))     
        except:
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            raise ServiceError(exc_value)


    def ReconfigureRegion(self, region_uuid):
        """ Retrieves the most up to date configuration templates, and regenerates 
            configuration files.  The region must be down for this to succeed. """
        region = store.get(region_uuid, Region.getClass())
        if (region == None):
            raise ServiceError("Invalid Region Specified")
        
        if (region.IsRunning()):
            raise ServiceError("Cannot reconfigure a running region.")
        
        region_record = region.get_record()
        slotnum = region.get_slot_number()
       
        regionBaseDir = os.path.join(region.get_slot_directory(), "bin")
        regionConfigDir = os.path.join(region.get_slot_directory(), "bin", "Regions")
        
        try:
            os.makedirs(regionConfigDir)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(regionConfigDir):
                pass
            else: 
                raise ServiceError("Region destination directory doesn't exist")        
        
        dbconfig = self.props.getCoreDbConfig()
        region_uuid = region.get_sim_uuid()
        
        rdbHost = GetRdbHost(dbconfig, region_uuid)
        if (rdbHost == None):
            # no info? that's ok in this case we assign
            print "RDB server not assigned for {0}, assigning new slot".format(region_uuid)
            rdbHost = AssignBestRdbHost(dbconfig, region_uuid)

        if ((not 'http_listener_port' in region_record) or (region_record['http_listener_port'] == "{REQUIRE}")):
            region_record['http_listener_port'] = str(self.props.getInteger('starting_http_port') + slotnum)
        if ((not 'internal_ip_port' in region_record) or (region_record['internal_ip_port'] == "{REQUIRE}")):
            region_record['internal_ip_port'] = str(self.props.getInteger('starting_udp_port') + slotnum)
        if ((not 'rdb_host' in region_record) or (region_record['rdb_host'] == "{REQUIRE}")):
            region_record['rdb_host'] = rdbHost
                            
        # Check for REQUIRE items and do the replacements if needed
        keys = dict(self.props.getItems(vars=region_record))

        # Map the source drive and figure out if its on GridShare
        regionConfigName = region.get_name_label() + ".xml"
        (username, password) = self.props.getGridShareCredentials()   
        templateBaseDir = self.props.getValue("template_basedir")
        
        try:
            ConnectUNCShare(templateBaseDir, username, password)

            """ Read in Region Config Settings """
            keys = provision.GetConfiguration(templateBaseDir, "simulation.config", "simulation", keys)
            
            """ Update the Region Configuration First """                
            provision.ReconfigureRegion(templateBaseDir, regionConfigDir, regionConfigName, keys)
            """ Now do the Simulator Configuration Files """
            provision.ReconfigureSimulator(templateBaseDir, regionBaseDir, keys)

            """ Done"""
            return True
        
        except Exception, e:
            raise ServiceError("Reconfiguration failed: " + str(e))
        
        
    def ReconfigureGridServices(self):
        """ Retrieves the most up to date configuration templates, and regenerates 
            configuration files.  The grid services must be down for this to succeed. """

        if (self.aperture_service.IsRunning()):
            raise ServiceError("Reconfigure: Cannot reconfigure, aperture is running.")
        if (self.messaging_service.IsRunning()):
            raise ServiceError("Reconfigure: Cannot reconfigure, messaging service is running.")
        if (self.user_service.IsRunning()):
            raise ServiceError("Reconfigure: Cannot reconfigure, user service is running.")
        if (self.grid_service != None and self.grid_service.IsRunning()):
            raise ServiceError("Reconfigure: Cannot reconfigure, grid service is running.")
        
        serviceBaseDir = os.path.join(provision.GetServiceBaseDir(), "bin")
        try:
            os.makedirs(serviceBaseDir)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(serviceBaseDir):
                pass
            else: 
                raise ServiceError("Grid Services destination directory doesn't exist")        

        defaults = {}
        defaults['http_listener_port'] = str(self.props.getInteger('starting_http_port'))
        defaults['internal_ip_port'] = str(self.props.getInteger('starting_udp_port'))
        keys = dict(self.props.getItems(vars=defaults))

        # Map the source drive and figure out if its on GridShare
        (username, password) = self.props.getGridShareCredentials()   
        templateBaseDir = self.props.getValue("template_basedir")
        
        try:
            ConnectUNCShare(templateBaseDir, username, password)
           
            """ Read in Region Config Settings """  
            keys = provision.GetConfiguration(templateBaseDir, "simulation.config", "simulation", keys)    
            provision.ReconfigureSimulator(templateBaseDir, serviceBaseDir, keys)

            """ Done"""
            return True
        
        except Exception:
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)       
            return False
        
    """ Returns a process object for when one is neeeded """
    def RunCommandEx(self, cwd, cmd, cmdargs):
        try:
            cmdline = "{0} {1}".format(cmd, cmdargs)    
            p = psutil.Popen(cmdline, close_fds=True, cwd=cwd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            return p
        except Exception: 
            return None
        
    def RunCommand(self, cwd, cmd, cmdargs):
        self.RunCommandEx(cwd, cmd, cmdargs)
    
    """ Use PsExec to run the command """
    def RunCommandAsEx(self, username, password, cwd, cmd, cmdargs):
        try:
            cmdline = "PsExec -u {0} -p {1} {2} {3}".format(username, password, cwd, cmd, cmdargs)
            p = psutil.Popen(cmdline, close_fds=True, cwd=cwd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            return p
        except Exception: 
            return None   
        
    def RunCommandAs(self, username, password, cwd, cmd, cmdargs):
        self.RunCommandAsEx(username, password, cwd, cmd, cmdargs)


    def ShutdownUncontrolledSimulatorByPath(self, path_to_bin):
        """
        Tells the simulator to die, based on where in the filesystem it is run from.
        DO NOT USE for Maestro-controlled regions.
        """
        p = provision._findRegionProcessByBin(path_to_bin)
        if p == None:
            return True
        p.terminate() # This sends CTRL-C, which will cause an immediate clean shutdown, which is perfect.
        
        if inworldz.util.process.WaitForProcessTermination(p, 30):
            return True
        else:
            return False

    def TakePossessionOfSimulator(self, path_to_bin):
        """
        Copies the bin folder to a Maestro slot, getting region data from config files located in the bin folder.
        Also records each region in the simulator in Maestro.
        """
        # Read region configs from bin/Regions/*.xml
        region_records = provision.ReadRegionConfigs(path_to_bin)
        
        for record in region_records:
            estate_id = Estate.FindEstateIDForRegion(record["sim_uuid"])
            if not estate_id:
                continue
            record["estate_id"] = estate_id

            slot_found = False

            for slotnum in range(self.maxRegionSlots):
                if (self.IsSlotFree(slotnum)):
                    slotDir = provision.GetSlotDirectory(slotnum)
                    try:
                        shutil.copytree(path_to_bin, slotDir)
                    except:
                        continue
                    record['slot_number'] = slotnum
                    slot_found = True
                    break

        if not slot_found:
            return None

        active_region_records = [record for record in region_records if "estate_id" in record and "slot_number" in record]

        return self.RecordSimulatorRegions(active_region_records)


