'''
Created on Jan 24, 2013

@author: mdickson
'''
import inworldz.maestro.uuid as genuuid
import inworldz.util.user as user
import inworldz.util.estate as estate
import inworldz.util.properties as DefaultProperties

import inworldz.maestro.MaestroStore as store
from inworldz.maestro.ServiceBase import ServiceBase
from inworldz.maestro.MaestroError import ServiceError


class Estate(ServiceBase):
    """An Estate Instance"""

    def getClass(self):
        return "Estate"

    def getMethods(self):
        methods = [
            "AssignRegion",
            ]
        return ServiceBase.getMethods() + methods
     
    def getAttrRO(self):
        attrs = [
           "estate_id",
           "estate_name",
           "estate_owner", 
           "parent_estate_id"
            ]
        return ServiceBase.getAttrRO() + attrs         

    def getFuncs(self):
        funcs = [
            "create",
            "FindByEstateID",
            "FindBySimUUID"
            ]
        return ServiceBase.getFuncs() + funcs    
    
    getClass = classmethod(getClass)
    getAttrRO = classmethod(getAttrRO)
    getMethods = classmethod(getMethods)
    getFuncs = classmethod(getFuncs)
    
    def __init__(self, uuid, record={}):
        ServiceBase.__init__(self, uuid, record)
        self.props = DefaultProperties.instance()
        self.estate_owner = record.get('estate_owner')
        self.estate_name = record.get('estate_name')
        self.estate_id = record.get('estate_id')
        self.parent_estate_id = record.get('parent_estate_id')
        
    @classmethod
    def initialize(cls):
        estate_ids = estate.LookupEstateIds()
        for estate_id in estate_ids:
            cls.recreate({ 'estate_id' : estate_id }, genuuid.createString())
            
    @classmethod
    def create(cls, record):
        if ((not 'estate_name' in record) or
            (not 'estate_owner' in record)):
            raise ServiceError("Create: Invalid Estate Information provided")
        
        # make sure the estate owner is valid
        if (user.LookupUserNameById(record['estate_owner']) == None):
            raise ServiceError("Create failed. Invalid estate owner specified")
               
        record['estate_id'] = estate.CreateNewEstate(record['estate_name'], record['estate_owner'])
        if (record['estate_id'] == None):
            raise ServiceError("Create: Cannot create new Estate")            
        
        record['parent_estate_id'] = record['estate_id']
        
        uuid = genuuid.createString()
        new_estate = Estate(uuid, record)
        return new_estate.get_uuid()
    
    @classmethod
    def recreate(cls, record, uuid):
        if (not 'estate_id' in record):
            raise ServiceError("Recreate: Invalid Estate Information provided")
        
        # make sure the estate owner is valid
        estate_entry = estate.LookupEstateById(record['estate_id'])
        if (estate_entry == None):
            raise ServiceError("Recreate: Invalid Estate Information provided")
        
        record['estate_name'] = estate_entry[1]
        record['estate_owner'] = estate_entry[2]
        record['parent_estate_id'] = estate_entry[3]       
        uuid = genuuid.createString()     
        new_estate = Estate(uuid, record)
        return new_estate.get_uuid()
    
    @classmethod
    def FindByEstateID(cls, estate_id):
        # First Look in active Estates
        for instance in store.get_all("Estate"):
            if (instance.get_estate_id() == estate_id):
                return (instance.get_uuid())
        return (cls.recreate({'estate_id' : estate_id}, genuuid.createString()))
    
    @classmethod
    def FindBySimUUID(cls, sim_uuid):
        estate_id = estate.FindEstateIDForRegion(sim_uuid)
        return cls.FindByEstateID(estate_id)        
    
    def get_estate_id(self):
        return self.estate_id
    
    def get_estate_name(self):
        return self.estate_name

    def get_estate_owner(self):
        return self.estate_owner
    
    def get_parent_estate_id(self):
        return self.parent_estate_id
    
    def AssignRegion(self, region):
        region_id = region.get_sim_uuid()
        estate.LinkRegionToExistingEstate(region_id, self.estate_id)
        