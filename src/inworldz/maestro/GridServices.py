'''
Created on Jan 24, 2013

@author: mdickson
'''
import subprocess
import os.path
import time

import inworldz.util.provision as provision
import inworldz.util.properties as DefaultProperties
import inworldz.maestro.uuid as genuuid

from inworldz.maestro.ServiceBase import ServiceBase
from inworldz.maestro.MaestroError import ServiceError
from maestro.rpcclient import Session

import inworldz.util.process

class GridServiceBase(ServiceBase):
    """ Base Class for Grid Services"""
    
    STARTUP_WAIT = 5
    '''
    The amount of time to sleep and wait while a grid service is started
    '''

    def getMethods(self):
        methods = [
            "IsRunning",
            "Start",
            "Shutdown",
            "Terminate",
            "ConsoleCommand",
            "DumpThreadStacks"
            ]
        return ServiceBase.getMethods() + methods
     
    def getAttrRO(self):
        attrs = [
            "RegionHost",
            "remoteadmin_url"
            ]    
        return ServiceBase.getAttrRO() + attrs
     
    def getAttrRW(self):
        attrs = [
            ]
        return ServiceBase.getAttrRW() + attrs

    def getFuncs(self):
        funcs = [
            ]
        return ServiceBase.getFuncs() + funcs

    getAttrRO = classmethod(getAttrRO)
    getAttrRW = classmethod(getAttrRW)
    getMethods = classmethod(getMethods)
    getFuncs = classmethod(getFuncs)
   
    def __init__(self, uuid, record={}):
        ServiceBase.__init__(self, uuid, record)
        self.props = DefaultProperties.instance()
        self.exe_name = "unknown"
        self.exe_args = ""
        self.remoteadmin_url = None
        self.remoteadmin_session = None
        self.remoteadmin_sessionid = None
             
        from inworldz.maestro.RegionHost import RegionHost
        self.regionHost = RegionHost.instance()
        self.service_basedir = provision.GetServiceBaseDir()
        self.shouldBeRunning = True
            
    def get_remoteadmin_url(self):
        return self.remoteadmin_url
        
    def get_RegionHost(self):
        return (self.regionHost.get_uuid())
    
    def IsRunning(self):
        """ Is this service currently running? """
        p = provision._findServiceProcess(self.exe_name)
        return p != None
    
    def ShouldBeRunning(self):
        return self.shouldBeRunning
    
    def Start(self, restart=False, delay=60):
        """ Requests a start/restart of the managed sim node with an alert and a delay.
            If restart is False nothing is done if we are already running.  If True and the
            region is running an alert is sent and the region restarted after the delay. """
        self.shouldBeRunning = True
        
        if self.IsRunning() and restart == True:
            self.Shutdown(delay)
            
        if self.IsRunning() and restart == False:
            return True

        bindir = os.path.join(self.service_basedir, "bin")
        exename = os.path.join(bindir, self.exe_name)
        exeargs = self.exe_args
        p = self.regionHost.RunCommandEx(bindir, exename, exeargs)
        
        #give the service some time to start up before launching anything further
        time.sleep(self.STARTUP_WAIT)
        
        if p != None:
            return True
        else:
            return False

            
    def Terminate(self):
        self.shouldBeRunning = False
        
        """ Shutdown the region after sending an Alert and delaying for a specified interval """
        p = provision._findServiceProcess(self.exe_name)
        if (p == None):
            return (True)
        p.terminate()
        p = provision._findServiceProcess(self.exe_name)
        return (p == None)


    def ConsoleCommand(self, command):
        """ Runs the given console command """
        if (not self.IsRunning()):
            raise ServiceError("ConsoleCommand: Process Not Running")
        
        ServiceBase.ConsoleCommand(self, command)
        
    def findApi(self):
        '''
        Finds the API that corresponds to the given class name
        '''
        apimap = {
                  'MessagingService': self.remoteadmin_session.api.MessagingService,
                  'GridService': self.remoteadmin_session.api.GridService,
                  'UserService': self.remoteadmin_session.api.UserService
                  }
        
        return apimap[self.getClass()]
    
    def Shutdown(self, delay=0, wait=60):
        self.shouldBeRunning = False
        
        """ Shutdown the service after sending an Alert and delaying for a specified interval """
        p = provision._findServiceProcess(self.exe_name)
        if p == None:
            return True
        
        self.establishRemoteAdminApiCredentials()
        self.findApi().Shutdown(delay)
    
        p = provision._findServiceProcess(self.exe_name)
        return inworldz.util.process.WaitForProcessTermination(p, wait)
    
    def DumpThreadStacks(self):
        p = provision._findServiceProcess(self.exe_name)
        
        return inworldz.util.process.DumpThreadStacks(p.pid)


class GridService(GridServiceBase):
    """ The GridService Instance """

    def getClass(self):
        return "GridService"

    @classmethod     
    def getAttrRO(cls):
        attrs = [
            "grid_server_uri",
            "grid_server_port",
            ]    
        return GridServiceBase.getAttrRO() + attrs
           
    def __init__(self, uuid, record={}):
        GridServiceBase.__init__(self, uuid, record)
        self.grid_server_port = self.props.getInteger("grid_server_port")
        self.grid_server_uri = self.props.getValue("grid_server_uri")
        self.exe_name = "OpenSim.Grid.GridServer.exe"
#        self.exe_args = "--console rest"
        self.exe_args = ""
        self.set_remoteadmin_url(record.get("remoteadmin_url"))
        self.remoteadmin_session = Session(self.get_remoteadmin_url())
        self.remoteadmin_sessionid = None
            
    @classmethod
    def create(cls, record):          
        uuid = genuuid.createString()     
        service = GridService(uuid, record)
        return service.get_uuid()

    @classmethod
    def recreate(cls, record, uuid):          
        service = GridService(uuid, record)
        return service.get_uuid()
    
    def set_remoteadmin_url(self, url):
        self.remoteadmin_url = str(url if url != None else 'http://127.0.0.1:{}/xmlrpc/RemoteAdmin/'.format(self.get_grid_server_port()))
               
    def get_grid_server_port(self):
        return (self.grid_server_port)
    
    def get_grid_server_uri(self):
        return (self.grid_server_uri)
    
    


class UserService(GridServiceBase):
    """ The Local UserService Instance On the RegionHost"""

    def getClass(self):
        return "UserService"

    @classmethod     
    def getAttrRO(cls):
        attrs = [
            "user_server_uri",
            "user_server_port",
            ]    
        return GridServiceBase.getAttrRO() + attrs
           
    def __init__(self, uuid, record={}):
        GridServiceBase.__init__(self, uuid, record)
        self.user_server_port = self.props.getInteger("user_server_port")
        self.user_server_uri = self.props.getValue("user_server_uri")
        self.exe_name = "OpenSim.Grid.UserServer.exe"
#        self.exe_args = "--console rest"
        self.exe_args = ""
        self.set_remoteadmin_url(record.get("remoteadmin_url"))
        self.remoteadmin_session = Session(self.get_remoteadmin_url())
        self.remoteadmin_sessionid = None
                   
    @classmethod
    def create(cls, record):          
        uuid = genuuid.createString()     
        user_service = UserService(uuid, record)
        return user_service.get_uuid()

    @classmethod
    def recreate(cls, record, uuid):          
        user_service = UserService(uuid, record)
        return user_service.get_uuid()
    
    def set_remoteadmin_url(self, url):
        self.remoteadmin_url = str(url if url != None else 'http://127.0.0.1:{}/xmlrpc/RemoteAdmin/'.format(self.get_user_server_port()))
        
    def get_user_server_port(self):
        return (self.user_server_port)
    
    def get_user_server_uri(self):
        return (self.user_server_uri)


class MessagingService(GridServiceBase):
    """ The Local MessagingService Instance On the RegionHost"""

    def getClass(self):
        return "MessagingService"

    @classmethod     
    def getAttrRO(cls):
        attrs = [
            "messaging_server_uri",
            "messaging_server_port",
            ]    
        return GridServiceBase.getAttrRO() + attrs
           
    def __init__(self, uuid, record={}):
        GridServiceBase.__init__(self, uuid, record)
        self.messaging_server_port = self.props.getInteger("messaging_server_port")
        self.messaging_server_uri = self.props.getValue("messaging_server_uri")
        self.exe_name = "OpenSim.Grid.MessagingServer.exe"
#        self.exe_args = "--console rest"
        self.exe_args = ""
        self.set_remoteadmin_url(record.get("remoteadmin_url"))
        self.remoteadmin_session = Session(self.get_remoteadmin_url())
        self.remoteadmin_sessionid = None
                    
    @classmethod
    def create(cls, record):          
        uuid = genuuid.createString()     
        service = MessagingService(uuid, record)
        return service.get_uuid()

    @classmethod
    def recreate(cls, record, uuid):          
        service = MessagingService(uuid, record)
        return service.get_uuid()
    
    def set_remoteadmin_url(self, url):
        self.remoteadmin_url = str(url if url != None else 'http://127.0.0.1:{}/xmlrpc/RemoteAdmin/'.format(self.get_messaging_server_port()))
               
    def get_messaging_server_port(self):
        return (self.messaging_server_port)
    
    def get_messaging_server_uri(self):
        return (self.messaging_server_uri)



class ApertureService(GridServiceBase):
    """ The Local Aperture Instance On the RegionHost"""

    def getClass(self):
        return "ApertureService"
           
    def __init__(self, uuid, record={}):
        GridServiceBase.__init__(self, uuid, record)
        self.exe_name = "aperture.exe"
            
    @classmethod
    def create(cls, record):          
        uuid = genuuid.createString()     
        service = ApertureService(uuid, record)
        return service.get_uuid()

    @classmethod
    def recreate(cls, record, uuid):          
        service = ApertureService(uuid, record)
        return service.get_uuid()

    def Shutdown(self, delay=0):
        self.shouldBeRunning = False
        
        """ Shutdown the service after sending an Alert and delaying for a specified interval """
        p = provision._findServiceProcess(self.exe_name)
        if (p == None):
            return True
        
        p.terminate()
        return True

