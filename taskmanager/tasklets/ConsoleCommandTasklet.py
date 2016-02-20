'''
Created on Jan 13, 2014

@author: David Daeschler
'''

import string

from tasklets.TaskletBase import TaskletBase
from inworldz.maestro.environment.RegionEntry import RegionState
import inworldz.maestro.environment.ComputeResource as ComputeResource

class ConsoleCommandTasklet(TaskletBase):
    '''
    Tasklet to run a console command on a region, a service, all services, or all regions
    '''
    
    def execute(self):
        # ConsoleCommandTasklet
        # {
        #    "target": "All" or "AllRegions" or "Services" or "SingleRegion" or 
        #        "MessagingService" or "GridService" or "UserService"
        #    "regionId": "[region_uuid]"
        #    "command": "[command]"
        # }
        
        target = string.lower(self.args['target'])
        command = self.args['command']
        
        host = self.session.api.RegionHost.get_all()[0]
        
        regions = self.session.api.RegionHost.get_Regions(host)
        
        msid = self.session.api.RegionHost.get_MessagingService(host)
        usid = self.session.api.RegionHost.get_UserService(host)
        gsid = None
        
        if int(self.session.api.RegionHost.get_Flags(host)) & ComputeResource.Flags.GridServiceHost == ComputeResource.Flags.GridServiceHost:
            gsid = self.session.api.RegionHost.get_GridService(host)
        
        if target == "all" or target == "services" or target == "messagingservice":
            self.session.api.MessagingService.ConsoleCommand(msid, command)
            
        if target == "all" or target == "services" or target == "gridservice":
            if gsid != None:
                self.session.api.GridService.ConsoleCommand(gsid, command)
                
        if target == "all" or target == "services" or target == "userservice":
            self.session.api.UserService.ConsoleCommand(usid, command)
        
        if target == "all" or target == "allregions":
            for region in regions:
                if int(self.session.api.Region.get_State(region)) == RegionState.DeployedRunning:
                    self.session.api.Region.ConsoleCommand(region, command)
                
        elif target == "singleregion":
            region = self.args['regionId']
            self.session.api.Region.ConsoleCommand(region, command)
    