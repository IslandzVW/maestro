'''
Created on Jan 11, 2014

@author: David Daeschler
'''

import time

from tasklets.TaskletBase import TaskletBase
from inworldz.maestro.environment.RegionEntry import RegionState
import inworldz.maestro.environment.ComputeResource as ComputeResource


class StartupTasklet(TaskletBase):
    '''
    Tasklet that starts up sims, services or both. Will only start regions 
    that are in the DeployedStopped state
    '''
    
    SERVICE_STARTUP_WAIT_TIME = 10
    '''
    The amount of time to wait for the services to load before starting the region
    '''
    
        
    def execute(self):
        # StartupTasklet
        # {
        #    "startupType": "full" or "region"  
        #    "regionId": "[regionUUID]"
        # }
        if self.args['startupType'] == "full":
            self.doFullStartup()
        else:
            self.doSingleStartup(self.args['regionId'])
    
    def doFullStartup(self):
        host = self.session.api.RegionHost.get_all()[0]
        
        #time to stop the services
        msid = self.session.api.RegionHost.get_MessagingService(host)
        usid = self.session.api.RegionHost.get_UserService(host)
        asid = self.session.api.RegionHost.get_ApertureService(host)
        gsid = None
        
        if int(self.session.api.RegionHost.get_Flags(host)) & ComputeResource.Flags.GridServiceHost == ComputeResource.Flags.GridServiceHost:
            gsid = self.session.api.RegionHost.get_GridService(host)
        
        self.session.api.ApertureService.Start(asid)
        self.session.api.UserService.Start(usid)
        
        if gsid != None:
            self.session.api.GridService.Start(gsid)
        
        self.session.api.MessagingService.Start(msid)
        
        #we're doing a full startup. give the services some time to load
        #up before launching the regions
        time.sleep(self.SERVICE_STARTUP_WAIT_TIME)
        
        regions = self.session.api.RegionHost.get_Regions(host)
        
        regionsToStartUp = []
        
        for region in regions:
            #only regions that are deployed and stopped
            if int(self.session.api.Region.get_State(region)) == RegionState.DeployedStopped:
                regionsToStartUp.append(region)
        
        
        for region in regionsToStartUp:
            self.doSingleStartup(region)
        
        #no need to update the region status to DeployedRunning, they do this themselves.
        
    def doSingleStartup(self, region):
        self.session.api.Region.ChangeState(region, RegionState.DeployedStarting)
        self.session.api.Region.Start(region)
