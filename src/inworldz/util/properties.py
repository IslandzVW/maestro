'''
Created on Feb 10, 2013

@author: mdickson
'''
import os.path

from ConfigParser import SafeConfigParser

from inworldz.util.network import GetPrivateIPs
from inworldz.util.filesystem import getCurrentUsersDesktopPath, getCurrentUsersAppDataPath
from inworldz.maestro.version import product_name
from inworldz.maestro.environment.ComputeResource import ComputeResource

class DefaultProperties():

    def __init__(self):
        self.currentDesktop = getCurrentUsersDesktopPath()
        self.appdata = getCurrentUsersAppDataPath()
        self.templatebase = os.path.join(self.appdata, "maestro", "data")


        defaults = {
            "basedir"            : self.currentDesktop,
            "region_leaf_base"   : "IzR1.09",

            "starting_udp_port"  : 9020,
            "starting_http_port" : 9500,
            "template_basedir"   : os.path.join(self.templatebase, "templates"),
            "backend_subnet"     : "10.0.0.0/20",
            "max_region_slots"   : 16,
            }

        self.configParser = SafeConfigParser(defaults)

    @property
    def backend_ip(self):
        return self.hostingResource.internalIp

    @property
    def frontend_ip(self):
        return self.hostingResource.externalIp

    @property
    def hostName(self):
        return self.hostingResource.hostName

    def loadConfiguration(self, filePath=None):
        if (filePath == None):
            filePath = os.path.join(self.appdata, product_name(), "maestro.config")
        if (os.path.exists(filePath)):
            self.configParser.read(filePath)

        #after configuration loading, grab our hosting compute resource info
        self.loadHostInformationFromEnvDB()

        #set the appropriate values in the config
        self.configParser.set("maestro", "frontend_ip", self.frontend_ip)
        self.configParser.set("maestro", "backend_ip", self.backend_ip)
        self.configParser.set("maestro", "hostname", self.hostName)


    def loadHostInformationFromEnvDB(self):
        envDbConfig = self.getEnvironmentDbConfig()
        resource = None
        for ip in GetPrivateIPs():
            resource = ComputeResource.findByInternalIp(envDbConfig, ip)
            if resource != None:
                break

        if resource == None:
            raise RuntimeError("No hosting resource entry found matching any assigned private IP")

        self.hostingResource = resource

    def getValue(self, name, section="maestro"):
        return self.configParser.get(section, name)

    def getInteger(self, name, section="maestro"):
        return self.configParser.getint(section, name)

    def getBoolean(self, name, section="maestro"):
        return self.configParser.getboolean(section, name)

    def getFloat(self, name, section="maestro"):
        return self.configParser.getfloat(section, name)

    def getCoreDbConfig(self):
        section = "maestro"
        config = {
          'user': self.configParser.get(section, "core_db_userid"),
          'password': self.configParser.get(section, "core_db_password"),
          'host': self.configParser.get(section, "core_db_host"),
          'database': self.configParser.get(section, "core_db_database"),
          'raise_on_warnings': False,
          }
        return config

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

    def getGridShareCredentials(self):
        section = "maestro"
        username = self.configParser.get(section, "gridshare_user")
        password = self.configParser.get(section, "gridshare_pass")
        return (username, password)

    def getTransferShareCredentials(self):
        section = "maestro"
        username = self.configParser.get(section, "transfer_share_user")
        password = self.configParser.get(section, "transfer_share_pass")
        return (username, password)

    def getItems(self, section="maestro", vars={}):
        replacements={}
        for key in vars.keys():
            replacements[str(key)] = str(vars[key])
        keys = self.configParser.items(section, False, replacements)
        return keys


def instance():
    global inst
    try:
        inst
    except:
        inst = DefaultProperties()
    return inst
