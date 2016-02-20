'''
Created on Jan 15, 2014

@author: David Daeschler
'''

import string

from tasklets.TaskletBase import TaskletBase

class ReconfigureTasklet(TaskletBase):
    '''
    Tasklet for reconfiguring regions or services
    '''

        
    def execute(self):
        # ReconfigureTasklet
        # {
        #    "target": "All", "AllRegions", "Region", "Services"
        #    "regionId": "[uuid of region]"
        # }
        target = string.lower(self.args['target'])
        
        host = self.session.api.RegionHost.get_all()[0]
        
        regions = self.session.api.RegionHost.get_Regions(host)
        
        if target == "all" or target == "services":
            self.session.api.RegionHost.ReconfigureGridServices(host)
        
        if target == "all" or target == "allregions":
            for region in regions:
                self.session.api.Region.Reconfigure(region)
                
        elif target == "region":
            region = self.args['regionId']
            self.session.api.Region.Reconfigure(region)
            