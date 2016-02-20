'''
Created on Jan 23, 2014

@author: David Daeschler
'''

import string

from tasklets.TaskletBase import TaskletBase
import inworldz.maestro.environment.ComputeResource as ComputeResource

class DumpThreadStacksTasklet(TaskletBase):
    '''
    Dumps the thread stacks of the given region or service into the task result field
    '''

    
    def execute(self):
        # DumpThreadStacksTasklet
        # {
        #    "target": "region" or "UserService" or "MessagingService" or "GridService"
        #    "regionId": "[uuid of region to dump]"
        # }
        target = string.lower(self.args['target'])
        
        host = self.session.api.RegionHost.get_all()[0]
        
        msid = self.session.api.RegionHost.get_MessagingService(host)
        usid = self.session.api.RegionHost.get_UserService(host)
        gsid = None
        
        if int(self.session.api.RegionHost.get_Flags(host)) & ComputeResource.Flags.GridServiceHost == ComputeResource.Flags.GridServiceHost:
            gsid = self.session.api.RegionHost.get_GridService(host)
            
        stacks = None
        
        if target == 'region':
            stacks = self.session.api.Region.DumpThreadStacks(self.args['regionId'])
        elif target == 'userservice':
            stacks = self.session.api.UserService.DumpThreadStacks(usid)
        elif target == 'messagingservice':
            stacks = self.session.api.MessagingService.DumpThreadStacks(msid)
        elif target == 'gridservice':
            if gsid != None:
                stacks = self.session.api.GridService.DumpThreadStacks(gsid)
                
        return stacks

            