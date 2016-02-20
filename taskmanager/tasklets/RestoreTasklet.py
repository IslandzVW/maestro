'''
Created on Jan 20, 2014

@author: David Daeschler
'''

import os.path
import shutil

import inworldz.util.general

from tasklets.TaskletBase import TaskletBase
from config import Configuration

class RestoreTasklet(TaskletBase):
    '''
    Tasklet to restore a region from a backup
    '''

    def execute(self):
        # RestoreTasklet
        # {
        #    "regionId": "[region uuid]"
        #    "fileName": "[oar filename]"
        # }
        
        self.restoreRegionBackup(self.args['regionId'], self.args['fileName'])
        
    def restoreRegionBackup(self, region, fileName):
        regionName = self.session.api.Region.get_sim_name(region)
        regionOwner = self.session.api.Region.get_master_avatar_uuid(region)
        
        backupStoragePath = os.path.join(Configuration.instance().generateFullOarBackupPath(regionOwner, region), fileName)
        
        #try to copy the OAR to the transfer location
        transferFileName = fileName + "_" + inworldz.util.general.id_generator()
        transferPath = os.path.join(Configuration.instance().transferSharePath, transferFileName)
        
        shutil.copy(backupStoragePath, transferPath)
        
        self.session.api.Region.CopyFileFromTransferLocation(region, transferFileName, True)
        
        if not self.session.api.Region.Restore(region, regionName, fileName, False, False):
            raise Exception("Restore failed for region {0} '{1}'".format(region, regionName))
        