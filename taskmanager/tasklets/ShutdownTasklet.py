'''
Created on Jan 1, 2014

@author: David Daeschler
'''

import threading

from tasklets.TaskletBase import TaskletBase
from inworldz.maestro.environment.RegionEntry import RegionState
import inworldz.maestro.environment.ComputeResource as ComputeResource
import inworldz.util.general as Util

class ShutdownTasklet(TaskletBase):
    '''
    Tasklet that shuts down sims, services, or both
    '''

        
    def execute(self):
        # ShutdownTasklet
        # {
        #    "shutdownType": "full" or "region"  
        #    "regionId": "[regionUUID]"
        #    "regionDelay": [delay]
        #    [optional] "postShutdownState": "[state id for regions after a successful shutdown]"
        # }
        
        if self.args['shutdownType'] == "full":
            self.doFullShutdown()
        else:
            self.trySingleShutdown(self.args['regionId'])
    
    def doFullShutdown(self):
        host = self.session.api.RegionHost.get_all()[0]
        
        regions = self.session.api.RegionHost.get_Regions(host)
        
        regionsToShutDown = []
        
        for region in regions:
            #only regions that are running
            if int(self.session.api.Region.get_State(region)) == RegionState.DeployedRunning:
                regionsToShutDown.append(region)
        
        
        #shut down the regions in parallel
        self.parallelShutdown(regionsToShutDown)
        
        #no need to update the region status to Stopped, they do this themselves.
        
        #time to stop the services
        msid = self.session.api.RegionHost.get_MessagingService(host)
        usid = self.session.api.RegionHost.get_UserService(host)
        asid = self.session.api.RegionHost.get_ApertureService(host)
        gsid = None
        
        if int(self.session.api.RegionHost.get_Flags(host)) & ComputeResource.Flags.GridServiceHost == ComputeResource.Flags.GridServiceHost:
            gsid = self.session.api.RegionHost.get_GridService(host)
        
        Util.throwIfFalse(self.session.api.MessagingService.Shutdown(msid), "Unable to shut down MessagingService")
        
        if gsid != None:
            Util.throwIfFalse(self.session.api.GridService.Shutdown(gsid), "Unable to shut down GridService")
        
        Util.throwIfFalse(self.session.api.UserService.Shutdown(usid), "Unable to shut down UserService")
        Util.throwIfFalse(self.session.api.ApertureService.Shutdown(asid), "Unable to shut down ApertureService")
        
            
    def parallelShutdown(self, regions):
        '''
        Shuts down the given list of regions in parallel using threads
        '''
        
        threads = []
        
        self.parallelErrors = []
        self.parallelErrorLock = threading.Lock()
        
        for region in regions:
            t = threading.Thread(target=self.doRegionShutdown, args=(region,))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
        
        #errors?
        if len(self.parallelErrors) > 0:
            errorStr = ''
            for error in self.parallelErrors:
                errorStr = errorStr + "[{0}: {1}] ".format(error[0], error[1])
            raise Exception(errorStr)
 

    def trySingleShutdown(self, regionId):
        self.session.api.Region.ChangeState(regionId, RegionState.DeployedStopping)
        if not self.session.api.Region.Shutdown(regionId, self.args['regionDelay']):
            if not self.session.api.Region.Terminate(regionId):
                raise Exception("Timeout waiting for process to go down")
        
        if 'postShutdownState' in self.args:
            self.session.api.Region.ChangeState(regionId, self.args['postShutdownState'])
                

    def doRegionShutdown(self, regionId):
        try:
            self.trySingleShutdown(regionId)
            
        except Exception, e:
            with self.parallelErrorLock:
                self.parallelErrors.append((regionId, e))
        