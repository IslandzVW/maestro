'''
Created on Jan 1, 2014

@author: David Daeschler
'''

import os
import inworldz.util.general

from ConfigParser import SafeConfigParser

class Configuration(object):
    '''
    Stores configuration information for the maestro task manager
    '''


    def __init__(self):
        defaults = \
        {
            "worker_process_count"  : "8",

            "oar_backup_basedir"    : "",
            "transfer_share_path"   : ""
        }

        self.configParser = SafeConfigParser(defaults)


    def loadFromFile(self, configFilePath):
        '''
        Loads the configuration information from the given config file
        '''
        if (os.path.exists(configFilePath)):
            self.configParser.read(configFilePath)

    @property
    def envDbHost(self):
        return self.configParser.get("maestro", "env_db_host")

    @property
    def envDbDatabase(self):
        return self.configParser.get("maestro", "env_db_database")

    @property
    def envDbUserId(self):
        return self.configParser.get("maestro", "env_db_userid")

    @property
    def envDbPassword(self):
        return self.configParser.get("maestro", "env_db_password")

    @property
    def workerProcessCount(self):
        return self.configParser.getint("maestro", "worker_process_count")

    @property
    def oarBackupBasedir(self):
        return self.configParser.get("maestro", "oar_backup_basedir")

    @property
    def transferSharePath(self):
        return self.configParser.get("maestro", "transfer_share_path")

    def getEnvironmentDbConfig(self):
        section = "maestro"
        config = {
          'user': self.configParser.get(section, "env_db_userid"),
          'password': self.configParser.get(section, "env_db_password"),
          'host': self.configParser.get(section, "env_db_host"),
          'database': self.configParser.get(section, "env_db_database"),
          'raise_on_warnings': False,
          }
        return config

    def getValue(self, name, section="maestro"):
        return self.configParser.get(section, name)

    def generateFullOarBackupPath(self, regionOwner, regionId):
        backupBasedir = self.oarBackupBasedir
        userPathParts = os.path.join(regionOwner[0:2], regionOwner, "regions", regionId)
        backupFullPath = os.path.join(backupBasedir, userPathParts)

        return backupFullPath

    def generateOarFileName(self, regionName):
        return regionName.replace(' ', '_').replace("'", "") + '-' + inworldz.util.general.dateTimeString() + '.oar'

def instance():
    global inst
    try:
        inst
    except:
        inst = Configuration()
    return inst
