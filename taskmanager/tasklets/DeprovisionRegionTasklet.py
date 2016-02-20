'''
Created on Jan 22, 2014

@author: David Daeschler
'''

from tasklets.TaskletBase import TaskletBase
from inworldz.maestro.environment.RegionEntry import RegionState

class DeprovisionRegionTasklet(TaskletBase):
    '''
    Tasklet to deprovision a region. This is a permanent takedown
    '''

    def execute(self):
        # DeprovisionRegionTasklet
        # {
        #    "regionId": "[uuid]"
        # }
        
        region = self.args['regionId']
        state = self.session.api.Region.get_State(region)
        
        if int(state) != RegionState.TakedownWait:
            raise Exception("Region {0} can not be deprovisioned. It must first be taken down.")
        else:
            self.session.api.Region.destroy(region)

        
        