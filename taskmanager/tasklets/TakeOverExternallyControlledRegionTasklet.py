'''
Created on Jan 14, 2014

@author: David Daeschler
'''

from tasklets.TaskletBase import TaskletBase
from inworldz.maestro.environment.RegionEntry import RegionState

import time

class TakeOverExternallyControlledSimulatorTasklet(TaskletBase):
    '''
    Tasklet for taking a simulator away from the control system currently running it and moving it to Maestro.
    Procedure:
    1. Log into the VM and disable ZooKeeper, or whatever is managing the simulator process.
    2. Execute this tasklet against every simulator on that VM.
    '''

    def execute(self):
        # TakeOverExternallyControlledRegionTasklet
        # {
        #    "zkRegionPath": "[path to simulator bin folder]",
        # }
        host = self.session.api.RegionHost.get_all()[0]
        
        if self.args['zkRegionPath'] == None:
            raise Exception("zkRegionPath not specified")
        if self.args['zkRegionPath'] == '':
            raise Exception("zkRegionPath was blank")

        regions = self.session.api.RegionHost.TakePossessionOfRegion(host, self.args['zkRegionPath'])
        
        # Power off the simulator and wait for it to be finished.
        while not self.session.api.RegionHost.ShutdownUncontrolledSimulatorByPath(self.args['zkRegionPath']):
            time.sleep(0.1)

        for region in regions:
            # Tell the new copy to power up.
            self.session.api.Region.ChangeState(region, RegionState.DeployedStarting)
            self.session.api.Region.Start(region)
