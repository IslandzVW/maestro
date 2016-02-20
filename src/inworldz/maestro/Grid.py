'''
Created on Jan 24, 2013
@author: mdickson

The main "Grid" instance.  This will initialize the rest of the objects.
We use stable id's for RegionHost's and Regions so that we can take a 
Maestro server down and restart it and still resolve entries in other
server instances correctly.
'''
import inworldz.util.properties as DefaultProperties
import inworldz.maestro.uuid as genuuid
import inworldz.maestro.MaestroStore as store

from inworldz.maestro.ServiceBase import ServiceBase
from inworldz.maestro.RegionHost import RegionHost
from inworldz.maestro.Region import Region
from inworldz.maestro.GridServices import GridService


class Grid(ServiceBase):
    """The 'Grid' instance """

    @classmethod
    def getClass(cls):
        return "Grid"
     
    @classmethod
    def getAttrRO(cls):
        attrs = [
           "this_host",
            ]
        return ServiceBase.getAttrRO() + attrs
    
    def __init__(self, uuid, record={}):
        ServiceBase.__init__(self, uuid, record) 
        self.props = DefaultProperties.instance()
        self.thisHost = RegionHost.instance()
        """ Should lookup and init a proxy for other hosts here also """
       
    @classmethod
    def create(cls, record={}):          
        uuid = genuuid.createString()
        return (cls.recreate(record, uuid))     

    @classmethod
    def recreate(cls, record, uuid):          
        service = Grid(uuid, record)
        return (service.get_uuid())
    
    def get_this_host(self):
        return self.thisHost.get_uuid()
    
