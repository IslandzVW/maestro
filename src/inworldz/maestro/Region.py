'''
Created on Jan 24, 2013

@author: mdickson
'''
import subprocess
import os.path
import shutil
import sys

from inworldz.util.rdbhost import GetRdbHost, AssignBestRdbHost
import inworldz.util.provision as provision
import inworldz.util.estate as estate
import inworldz.util.properties as DefaultProperties

import inworldz.maestro.uuid as genuuid
import inworldz.maestro.MaestroStore as store

from inworldz.maestro.ServiceBase import ServiceBase
from inworldz.maestro.MaestroError import ServiceError
from inworldz.maestro.Estate import Estate
from inworldz.maestro.User import User

from maestro.rpcclient import Session

import inworldz.util.process

from inworldz.maestro.environment.RegionEntry import RegionState
from inworldz.util.filesystem import ConnectUNCShare
import inworldz.util.general

class Region(ServiceBase):
    """A Region On the RegionHost"""
    
    def __init__(self, uuid, record={}):
        ServiceBase.__init__(self, uuid, record)
        self.props = DefaultProperties.instance()
        dbconfig = self.props.getCoreDbConfig()
        self.exe_name = "OpenSim.exe"
#        self.exe_args = "--console rest"
        self.exe_args = ""
                        
        if ((not 'sim_name' in record) or 
            (not 'sim_location_x' in record) or
            (not 'sim_location_y' in record) or
            (not 'estate_id' in record) or
            (not 'master_avatar_uuid' in record)):
            raise ServiceError("Region: Invalid Region Information provided")
        
        self.regionEntry = None   
        
        self.sim_uuid = uuid
        
        self.estate_id = record['estate_id']
        self.syncEstateInfoToEstateId()
        
        self.master_avatar_uuid = record['master_avatar_uuid']
        self.syncOwnerInfoToMasterAvatarId()
     
        self.sim_name = record.get("sim_name")
        self.set_sim_location(record.get("sim_location_x"), record.get("sim_location_y"))                        
                
        if ('slot_number' in record):
            self.slot_number = int(record.get('slot_number'))
            self.slot_directory = provision.GetSlotDirectory(self.slot_number)
        else:
            raise ServiceError("Create failed. No Slot Number Specified")
          
        rdbHost = GetRdbHost(dbconfig, uuid)
        if not rdbHost:
            # no info? that's ok in this case we assign
            print "RDB server not assigned for {0}, assigning new slot".format(uuid)
            rdbHost = AssignBestRdbHost(dbconfig, uuid)

        from inworldz.maestro.RegionHost import RegionHost
        self.regionHost = RegionHost.instance()
                     
        self.set_external_host_name(record.get('external_host_name'))  
        self.set_outside_ip(record.get('outside_ip'))          
        self.set_internal_ip_address(record.get('internal_ip_address'))
        self.set_internal_ip_port(record.get('internal_ip_port'))
        self.set_allow_alternate_ports(record.get('allow_alternate_ports'))
        self.set_lastmap_uuid(record.get("lastmap_uuid"))
        self.set_lastmap_refresh(record.get("lastmap_refresh"))
        self.set_nonphysical_prim_max(record.get("nonphysical_prim_max"))
        self.set_physical_prim_max(record.get("physical_prim_max"))
        self.set_clamp_prim_size(record.get("clamp_prim_size"))
        self.set_object_capacity(record.get("object_capacity"))
        self.set_region_product(record.get("region_product"))

        self.set_remoteadmin_url(record.get("remoteadmin_url"))
        self.remoteadmin_session = Session(self.get_remoteadmin_url())
        self.remoteadmin_sessionid = None
            
    def syncOwnerInfoToMasterAvatarId(self):
        self.owner_uuid = User.FindByUserID(self.master_avatar_uuid)
        self.owner = store.get(self.owner_uuid, 'User')
        self.master_avatar_first = self.owner.get_first_name()
        self.master_avatar_last = self.owner.get_last_name()
        
    def syncEstateInfoToEstateId(self):
        estate_uuid = Estate.FindByEstateID(self.estate_id)  
        self.estate = store.get(estate_uuid, 'Estate')
        
    @classmethod
    def getClass(cls):
        return "Region"

    @classmethod
    def getMethods(cls):
        methods = [
            "destroy",
            "IsRunning",
            "Start",
            "Shutdown",
            "Terminate",
            "AssignEstate",
            "UpdateToRevision",
            "UpdateToLatest",
            "Reconfigure",
            "ConsoleCommand",
            "RestoreOarBackup",
            "SaveOarBackup",
            "Backup",
            "Restore",
            "ChangeState",
            "CopyFileToTransferLocation",
            "CopyFileFromTransferLocation",
            "DumpThreadStacks"
            ]
        return ServiceBase.getMethods() + methods
     
    @classmethod
    def getAttrRO(cls):
        attrs = [
            "sim_uuid",
            "owner_uuid",
            "master_avatar_first",
            "master_avatar_last",
            "sim_location_x",
            "sim_location_y",
            "slot_number",
            "slot_directory",
            "name_label",
            "internal_ip_address",
            "internal_ip_port",
            "allow_alternate_ports",
            "external_host_name",
            "outside_ip",
            "lastmap_uuid",
            "lastmap_refresh",
            "nonphysical_prim_max",
            "physical_prim_max",
            "clamp_prim_size",
            "object_capacity",
            "region_product",
            "remoteadmin_url",
            "RegionHost",
            "Estate",
            "State",
            "cpu_used_percentage",
            "memory_used",
            "thread_count",
            "handle_count"
            ]    
        return ServiceBase.getAttrRO() + attrs
     
    @classmethod
    def getAttrRW(cls):
        attrs = [
            "sim_name",
            "sim_location",
            "master_avatar_uuid",
            "estate_id"
            ]
        return ServiceBase.getAttrRW() + attrs

    @classmethod
    def getFuncs(cls):
        funcs = [
            "create",
            "FindByName",
            ]
        return ServiceBase.getFuncs() + funcs

    @classmethod
    def verifyRecord(cls, record, verifyEstate=True):
        if ((not 'sim_name' in record) or 
            (not 'sim_location_x' in record) or
            (not 'sim_location_y' in record) or
            (verifyEstate and not 'estate_id' in record) or 
            (not 'region_product' in record) or
            (not 'master_avatar_uuid' in record)):
            raise ServiceError("Create: Invalid Region Information provided")
        
    @classmethod
    def create(cls, record):    
        cls.verifyRecord(record)
        
        uuid = genuuid.createString()
        record['sim_uuid'] = uuid        
        region = Region(uuid, record)
        estate.LinkRegionToExistingEstate(region.get_sim_uuid(), region.get_estate_id())
        
        return region
    

    @classmethod
    def recreate(cls, record, uuid):
        if ('estate_id' not in record):
            estate_id = estate.FindEstateIDForRegion(uuid)
            if (estate_id == None):
                raise ServiceError("Recreate: No estate assigned for region " + uuid)
            record['estate_id'] = estate_id
        
        cls.verifyRecord(record,False)
        
        region = Region(uuid, record)
        region.associateWithRegionEntry()
        
        return region.get_uuid()


    @classmethod
    def FindByName(cls, name):
        instances = cls.get_all()
        for instance in instances:
            if (instance.get_sim_name() == name):
                return instance.get_uuid()      
        return None


    def destroy(self):
        p = provision._findRegionProcess(self.slot_number)
        if p:
            raise ServiceError("Cannot destroy a running region")
        
        """ Zap the config file """
        regionDir = os.path.join(provision.GetSlotDirectory(self.slot_number), "bin", "Regions")
        configFile = os.path.join(regionDir, self.get_name_label() + ".xml")
        if (os.path.exists(configFile)):
            os.remove(configFile)
        
        self.regionEntry.unprovision()
        
        """ Remove our Entry in the Host """
        self.regionHost.region_del(self.get_uuid())
        ServiceBase.destroy(self)
        
    def set_sim_name(self, name):
        self.sim_name = name
        self.regionEntry.name = name
        self.regionEntry.saveChanges()

    def set_master_avatar_uuid(self, uuid):
        self.master_avatar_uuid = uuid
        self.syncOwnerInfoToMasterAvatarId()
        self.regionEntry.owner = uuid
        self.regionEntry.saveChanges()
        
    def set_estate_id(self, estateId):
        self.estate_id = estateId
        self.syncEstateInfoToEstateId()
    
    def set_sim_location(self, x, y):
        self.sim_location_x = int(x)
        self.sim_location_y = int(y)
        
        if self.regionEntry != None: #handles initial bootstrap
            self.regionEntry.xloc = int(x)
            self.regionEntry.yloc = int(y)
            self.regionEntry.saveChanges()
        
    def set_external_host_name(self, hostname):
        self.external_host_name = str(hostname if hostname else self.props.getValue("hostname"))

    def set_outside_ip(self, ipaddress):
        self.outside_ip = str(ipaddress if ipaddress else self.props.getValue("frontend_ip"))
        
    def set_internal_ip_address(self, ipaddress):
        self.internal_ip_address = str(ipaddress if ipaddress else self.props.getValue("backend_ip"))
    
    def set_internal_ip_port(self, port):
        self.internal_ip_port = int(port if port else (self.props.getInteger('starting_udp_port') + self.slot_number))
 
    def set_allow_alternate_ports(self, allow):
        self.allow_alternate_ports = "true" if (allow and str.lower(str(allow)) == "true") else "false"

    def set_lastmap_uuid(self, uuid):
        self.lastmap_uuid = str(uuid if uuid != None else genuuid.uuidZero())
 
    def set_lastmap_refresh(self, refresh):
        self.lastmap_refresh = int(refresh if refresh != None else 0)
   
    def set_nonphysical_prim_max(self, prim_max):
        self.nonphysical_prim_max = int(prim_max if prim_max != None else 0)
 
    def set_physical_prim_max(self, prim_max):
        self.physical_prim_max = int(prim_max if prim_max != None else 0)

    def set_clamp_prim_size(self, clamp_size):
        self.clamp_prim_size = "true" if (clamp_size and str.lower(str(clamp_size)) == "true") else "false"

    def set_object_capacity(self, capacity):
        self.object_capacity = int(capacity if capacity != None else 0)

    def set_region_product(self, product):
        self.region_product = int (product if product != None else 0)

    def set_remoteadmin_url(self, url):
        self.remoteadmin_url = str(url if url != None else 'http://127.0.0.1:{}/xmlrpc/RemoteAdmin/'.format(self.get_internal_ip_port()))

    """ External API functions """
    def get_slot_number(self):
        return (self.slot_number)

    def get_slot_directory(self):
        return (self.slot_directory)
    
    def get_name_label(self):
        # Build the name label (alphanumeric chars only
        return(''.join(ch for ch in self.sim_name if ch.isalnum()))

    def get_RegionHost(self):
        return (self.regionHost.get_uuid())
    
    def get_Estate(self):
        return (str(self.estate.get_uuid() if self.estate != None else genuuid.uuidZero()))
    
    def get_sim_uuid(self):
        return self.sim_uuid
        
    def get_sim_name(self):
        return self.sim_name
    
    def get_sim_location(self):
        return (self.sim_location_x, self.sim_location_y)
     
    def get_sim_location_x(self):
        return self.sim_location_x

    def get_sim_location_y(self):
        return self.sim_location_y

    def get_internal_ip_address(self):
        return self.internal_ip_address
        
    def get_internal_ip_port(self):
        return self.internal_ip_port
        
    def get_allow_alternate_ports(self):
        return self.allow_alternate_ports

    def get_external_host_name(self):
        return self.external_host_name
    
    def get_outside_ip(self):
        return self.outside_ip

    def get_master_avatar_uuid(self):
        return self.master_avatar_uuid

    def get_master_avatar_first(self):
        return self.master_avatar_first

    def get_master_avatar_last(self):
        return self.master_avatar_last

    def get_lastmap_uuid(self):
        return self.lastmap_uuid

    def get_lastmap_refresh(self):
        return self.lastmap_refresh

    def get_nonphysical_prim_max(self):
        return self.nonphysical_prim_max

    def get_physical_prim_max(self):
        return self.physical_prim_max

    def get_clamp_prim_size(self):
        return self.clamp_prim_size

    def get_object_capacity(self):
        return self.object_capacity
     
    def get_region_product(self):
        return self.region_product
    
    def get_remoteadmin_url(self):
        return self.remoteadmin_url
      
    def get_estate_id(self):
        return self.estate_id
         
    def get_owner_uuid(self):
        return self.owner_uuid
    
    def get_State(self):
        return self.regionEntry.state
    
    def get_cpu_used_percentage(self):
        p = provision._findRegionProcess(self.slot_number)
        if p != None:
            return p.get_cpu_percent()
        else:
            return 0.0
        
    def get_memory_used(self):
        p = provision._findRegionProcess(self.slot_number)
        if p != None:
            return p.get_memory_info()[1]
        else:
            return 0
    
    def get_thread_count(self):
        p = provision._findRegionProcess(self.slot_number)
        if p != None:
            return p.get_num_threads()
        else:
            return 0
    
    def get_handle_count(self):
        p = provision._findRegionProcess(self.slot_number)
        if p != None:
            return p.get_num_handles()
        else:
            return 0

    def IsRunning(self):
        """ Is this simulator currently running? """
        p = provision._findRegionProcess(self.slot_number)
        return p != None
    
    def ShouldBeRunning(self):
        return self.regionEntry.state == RegionState.DeployedRunning
        
    def Start(self, restart=False, delay=60):
        """ Requests a start/restart of the managed sim node with an alert and a delay.
            If restart is False nothing is done if we are already running.  If True and the
            region is running an alert is sent and the region restarted after the delay. """
        p = provision._findRegionProcess(self.slot_number)
        if p != None:
            if (restart == False):
                return (True)
            else:
                self.Shutdown(delay)
        
        """" Make sure there is a region config here... """
        
        bindir = os.path.join(self.slot_directory, "bin")
        exename = os.path.join(bindir, self.exe_name)
        exeargs = self.exe_args
        p = self.regionHost.RunCommandEx(bindir, exename, exeargs)
        
        if p != None:
            self.ChangeState(RegionState.DeployedRunning)
            return True
        else:
            return False
 
    def Terminate(self):
        """ Shutdown the region immediately but safely. """
        p = provision._findRegionProcess(self.slot_number)
        if p == None:
            return True

        if inworldz.util.process.TerminateAndWaitForConfirmation(p, 30):
            self.ChangeState(RegionState.DeployedStopped)
            return True
        else:
            return False
        
    def AssignEstate(self, estate_uuid):
        estate = store.get(estate_uuid, "Estate")
        if (estate == None):
            ServiceError("AssignEstate: Invalid Estate Reference")
            
        estate.AssignRegion(self.get_sim_uuid())
        self.estate = estate
        self.estate_id = self.estate.get_estate_id()
        

    def UpdateToRevision(self, revision):
        """ Update the region to the revision specified. Calls through RegionHost"""
        return (self.regionHost.UpdateRegionToRevision(self.get_uuid(), revision))        


    def UpdateToLatest(self):
        """ Update the region to the latest revision.  Calls through the the RegionHost """
        return (self.regionHost.UpdateRegionToLatest(self.get_uuid()))

        
    def Reconfigure(self):
        """ Reconfigure the current region.  Calls through the the RegionHost """
        return (self.regionHost.ReconfigureRegion(self.get_uuid()))

        
    def Shutdown(self, delay=60, terminateWait=60):
        """ Shutdown the region after sending an Alert and delaying for a specified interval """
        if (not self.IsRunning()):
            #not an error. this is perfectly fine. the region is already down so we have nothing to do
            return True
        
        self.establishRemoteAdminApiCredentials()

        self.remoteadmin_session.api.Region.Shutdown(self.get_uuid(), delay)
    
        p = provision._findRegionProcess(self.slot_number)
        if inworldz.util.process.WaitForProcessTermination(p, terminateWait):
            self.ChangeState(RegionState.DeployedStopped)
            return True
        else:
            return False
    

    def ConsoleCommand(self, command):
        """ Runs the given console command """
        if (not self.IsRunning()):
            raise ServiceError("ConsoleCommand: Region Process Not Running")
        
        ServiceBase.ConsoleCommand(self, command)
    
           
    def RestoreOarBackup(self, owner_id, filename):
        """ Restores a region backup from disk """
        if (not self.IsRunning()):
            raise ServiceError("RestoreOar: Region Process Not Running")
        
        self.establishRemoteAdminApiCredentials()
        
        return self.remoteadmin_session.api.Region.RestoreOAR(owner_id, filename)
    
    def SaveOarBackup(self, owner_id):
        """ Saves a region to disk """
        if (not self.IsRunning()):
            raise ServiceError("SaveOar: Region Process Not Running")
        
        self.establishRemoteAdminApiCredentials()
        
        return self.remoteadmin_session.api.Region.SaveOAR(owner_id)
    
    def Restore(self, regionName, filename, allowUserReassignment, skipErrorGroups):
        """ Restores a region backup from disk """
        if (not self.IsRunning()):
            raise ServiceError("RestoreOar: Region Process Not Running")
        
        self.establishRemoteAdminApiCredentials()
        
        return self.remoteadmin_session.api.Region.Restore(regionName, filename, allowUserReassignment, skipErrorGroups)
    
    def Backup(self, regionName, fileName, storeAssets):
        """ Saves a region to disk """
        if (not self.IsRunning()):
            raise ServiceError("SaveOar: Region Process Not Running")
        
        self.establishRemoteAdminApiCredentials()
        
        return self.remoteadmin_session.api.Region.Backup(regionName, fileName, storeAssets)

    def ChangeState(self, newState):
        self.regionEntry.updateState(newState)

    def associateWithRegionEntry(self):
        self.regionEntry = self.props.hostingResource.findHostedRegionByUUID(self.sim_uuid)
        
        if self.regionEntry == None:
            raise Exception("Region improperly provisioned! No deployed region entry found for {0}".format(self.sim_uuid))

    def connectTransferShare(self):
        share_path = self.props.getValue("transfer_share_path")
        (username, password) = self.props.getTransferShareCredentials()   
        
        ConnectUNCShare(share_path, username, password)
        
        return share_path
    
    def CopyFileToTransferLocation(self, fileName, deleteOriginalAfterTransfer):
        share_path = self.connectTransferShare()
        
        srcPath = os.path.join(self.slot_directory, "bin", fileName)
        newFileName = fileName + "_" + inworldz.util.general.id_generator()
        dstPath = os.path.join(share_path, newFileName)
        
        shutil.copy(srcPath, dstPath)
        
        if deleteOriginalAfterTransfer:
            os.unlink(srcPath)
            
        return newFileName
        
    def CopyFileFromTransferLocation(self, fileName, deleteOriginalAfterTransfer):
        share_path = self.connectTransferShare()
        
        srcPath = os.path.join(share_path, fileName)
        dstPath = os.path.join(self.slot_directory, "bin", fileName[0:-7]) #strip the randomness
        
        shutil.copy(srcPath, dstPath)
        
        if deleteOriginalAfterTransfer:
            os.unlink(srcPath)
            
    def DumpThreadStacks(self):
        p = provision._findRegionProcess(self.slot_number)
        
        return inworldz.util.process.DumpThreadStacks(p.pid)
        