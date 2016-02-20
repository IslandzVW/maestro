'''
Created on Jan 16, 2014

@author: David Daeschler
'''

import string

from tasklets.TaskletBase import TaskletBase

class UpdateTasklet(TaskletBase):
    '''
    Tasklet to update regions, services, or both
    '''

    
    def execute(self):
        # UpdateTasklet
        # {
        #    "target": "All", "AllRegions", "Region", "Services"
        #    "revision": "latest or [R####]"
        #    "regionId": "[uuid of region]"
        # }
        target = string.lower(self.args['target'])
        revision = string.upper(self.args['revision'])
        
        host = self.session.api.RegionHost.get_all()[0]
        
        regions = self.session.api.RegionHost.get_Regions(host)
        
        if target == "all" or target == "services":
            if revision == "LATEST":
                self.session.api.RegionHost.UpdateGridServicesToLatest(host)
            else:
                self.session.api.RegionHost.UpdateGridServicesToRevision(host, revision)
        
        if target == "all" or target == "allregions":
            for region in regions:
                if revision == "LATEST":
                    self.session.api.Region.UpdateToLatest(region)
                else:
                    self.session.api.Region.UpdateToRevision(region, revision)
                
        elif target == "region":
            region = self.args['regionId']
            if revision == "LATEST":
                self.session.api.Region.UpdateToLatest(region)
            else:
                self.session.api.Region.UpdateToRevision(region, revision)
