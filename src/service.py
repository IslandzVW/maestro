'''
Created on Nov 8, 2012

@author: mdickson
'''
### Run Python scripts as a service example (ryrobes.com)
### Usage : python aservice.py install (or / then start, stop, remove)

import os
import sys
from threading import Thread

import win32service
import win32serviceutil
import win32event

from inworldz.util.filesystem import getCurrentUsersAppDataPath
from inworldz.maestro.version import product_name
from inworldz.maestro.MaestroServer import MaestroServer
from inworldz.maestro.MaestroAuth import AUTH_WINDOWS
import inworldz.util.properties as DefaultProperties     

    
class MaestroService(win32serviceutil.ServiceFramework):
    _svc_name_ = "InWorldz.Maestro"
    _svc_display_name_ = _svc_name_
    _svc_description_ = "InWorldz Maestro Management Agent"
    _svc_deps = [ "EventLog" ]
    
    def __init__(self, args):
        
        win32serviceutil.ServiceFramework.__init__(self, args)
        # Create an event which we will use to wait on.
        # The "service stop" request will set this event.
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        # Register servicemanager.pyd with with our service so eventlog messages
        # from our service are logged and rendered in the event viewer)
    

    def SvcStop(self):        
        # Before we do anything, tell the SCM we are starting the stop process.
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        # And set my event.
        win32event.SetEvent(self.hWaitStop)
        

    def SvcDoRun(self):
        # Starting up
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        if (self.starting() == True):
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)        
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        # Shutting Down
        self.stopping()
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)


    def starting(self):
        try:
            self.appdata = getCurrentUsersAppDataPath()
            self.propfile = os.path.join(self.appdata, product_name(), "maestro.config") 
            self.address = "0.0.0.0"
            self.port = 12089
            self.props = DefaultProperties.instance()
            self.props.loadConfiguration(self.propfile)
            self.server = MaestroServer(AUTH_WINDOWS, self.address, self.port, self.propfile)
            self.thread = Thread(target = self.server.run, args = ())
            self.thread.start()
            return True
        except Exception, e:
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)   
            return False
        
    def stopping(self):
        self.server.shutdown()
        return True  
        

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(MaestroService)