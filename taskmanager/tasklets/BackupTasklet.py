'''
Created on Jan 17, 2014

@author: David Daeschler
'''

import os.path
import shutil
import string

from tasklets.TaskletBase import TaskletBase
from inworldz.maestro.environment.RegionEntry import RegionState
from config import Configuration


class BackupTasklet(TaskletBase):
    '''
    Backs up a region to an OAR file and copies it to the backup server
    '''

    
    def backupRegion(self, region):
        #only regions that are deployed and running
        if int(self.session.api.Region.get_State(region)) == RegionState.DeployedRunning:
            regionName = self.session.api.Region.get_sim_name(region)
            regionOwner = self.session.api.Region.get_master_avatar_uuid(region)
            oarFileName = Configuration.instance().generateOarFileName(regionName)
            
            if not self.session.api.Region.Backup(region, regionName, oarFileName, False):
                raise Exception("Region backup for {0} '{1}' failed".format(region, regionName))
            
            transferFileName = self.session.api.Region.CopyFileToTransferLocation(region, oarFileName, True)
            transferLocation = os.path.join(Configuration.instance().transferSharePath, transferFileName)
            
            #copy the file to the backup server location
            backupDir = Configuration.instance().generateFullOarBackupPath(regionOwner, region)
            if not os.path.exists(backupDir):
                os.makedirs(backupDir)
            destinationPath = os.path.join(backupDir, transferFileName[0:-7])
            shutil.copy(transferLocation, destinationPath)
            os.unlink(transferLocation)

    def execute(self):
        # BackupTasklet
        # {
        #    "type": "full" or "singleRegion"
        #    "regionId": "[region uuid]"
        # }
        
        host = self.session.api.RegionHost.get_all()[0]
        regions = self.session.api.RegionHost.get_Regions(host)
        
        if string.lower(self.args['type']) == 'full':
            #perform a backup on all regions that are running
            for region in regions:
                self.backupRegion(region)
        else:
            self.backupRegion(self.args['regionId'])
                