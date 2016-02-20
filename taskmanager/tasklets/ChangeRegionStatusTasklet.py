'''
Created on Jan 21, 2014

@author: David Daeschler
'''

import string

from tasklets.TaskletBase import TaskletBase

class ChangeRegionStatusTasklet(TaskletBase):
    '''
    Changes the run status of one or more regions on a host
    '''

        
    def execute(self):
        # ChangeRegionStatusTasklet
        # {
        #    "target" : "all" or "region"
        #    "regionId": "[uuid of target region]"
        #    "newStatus": "[id of new run status]"
        # }
        if string.lower(self.args['target']) == "all":
            self.changeAllRegionStatus()
        else:
            self.changeSingleRegionStatus(self.args['regionId'], self.args['newStatus'])
            
    def changeSingleRegionStatus(self, regionId, newStatus):
        self.session.api.Region.ChangeState(regionId, newStatus)
        
    def changeAllRegionStatus(self):
        host = self.session.api.RegionHost.get_all()[0]
        regions = self.session.api.RegionHost.get_Regions(host)
        
        for region in regions:
            self.changeSingleRegionStatus(region, self.args['newStatus'])
            
