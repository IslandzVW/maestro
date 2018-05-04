'''
Created on Jan 14, 2014

@author: David Daeschler
'''

from tasklets.TaskletBase import TaskletBase
from inworldz.maestro.environment.RegionEntry import RegionState

import time

class TakeOverExternallyControlledSimulatorTasklet(TaskletBase):
    '''
    Tasklet for taking a simulator away from the control system currently running it, moving it to Maestro, and optionally starting it back up again.
    Procedure:
    1. Using your current grid manager send alerts to all regions in the VM about a pending restart.
    2. Wait for the time you specified in the alert.
    3. Disable the existing grid manager on that VM.
    4. Execute this tasklet against every simulator "bin" folder path on that VM.

    If the old simulator process fails to shut down, consequently preventing this tasklet from continuing, simply manually terminate the simulator and this tasklet will continue automatically.
    '''

    def execute(self):
        # TakeOverExternallyControlledRegionTasklet
        # {
        #    "simulatorPath": "[path to simulator bin folder]",
        #    "startRegions": true/false,
        # }
        host = self.session.api.RegionHost.get_all()[0]
        
        if self.args['regionsimulatorPathPath'] == None:
            raise Exception("simulatorPath not specified")
        if self.args['simulatorPath'] == '':
            raise Exception("simulatorPath was blank")

        regions = self.session.api.RegionHost.TakePossessionOfRegion(host, self.args['simulatorPath'])
        
        # Power off the simulator and wait for it to be finished.
        while not self.session.api.RegionHost.ShutdownUncontrolledSimulatorByPath(self.args['simulatorPath']):
            time.sleep(0.1)

        if self.args['startRegions']:
            for region in regions:
                # Tell the new copy to power up.
                self.session.api.Region.ChangeState(region, RegionState.DeployedStarting)
                self.session.api.Region.Start(region)
