'''
Created on Jan 17, 2014

@author: David Daeschler
'''

from tasklets.TaskletBase import TaskletBase
import inworldz.maestro.environment.ComputeResource as ComputeResource

class TerminateAllTasklet(TaskletBase):
    '''
    This tasklet forcibly terminates all services and sims on a host.
    This can be used in an emergency situation where all services and sims failed
    to properly configure and you must terminate to force a reconfiguration
    '''

    def execute(self):
        # TerminateAllTasklet
        #    no arguments
        
        host = self.session.api.RegionHost.get_all()[0]
        
        regions = self.session.api.RegionHost.get_Regions(host)
        
        for region in regions:
            self.session.api.Region.Terminate(region)
        
        msid = self.session.api.RegionHost.get_MessagingService(host)
        usid = self.session.api.RegionHost.get_UserService(host)
        asid = self.session.api.RegionHost.get_ApertureService(host)
        gsid = None
        
        if int(self.session.api.RegionHost.get_Flags(host)) & ComputeResource.Flags.GridServiceHost == ComputeResource.Flags.GridServiceHost:
            gsid = self.session.api.RegionHost.get_GridService(host)
        
        self.session.api.MessagingService.Terminate(msid)
        if gsid != None:
            self.session.api.GridService.Terminate(gsid)
        
        self.session.api.UserService.Terminate(usid)
        self.session.api.ApertureService.Terminate(asid)
        
        