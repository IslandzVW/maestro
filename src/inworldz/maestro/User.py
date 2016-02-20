'''
Created on Jan 24, 2013

@author: mdickson
'''
import inworldz.util.user as user
import inworldz.util.properties as DefaultProperties

import inworldz.maestro.MaestroStore as store
from inworldz.maestro.ServiceBase import ServiceBase
from inworldz.maestro.MaestroError import ServiceError


class User(ServiceBase):
    """An User Instance"""

    def getClass(self):
        return "User"

    def getMethods(self):
        methods = [
            ]
        return ServiceBase.getMethods() + methods
     
    def getAttrRO(self):
        attrs = [
           "user_id",
           "first_name",
           "last_name", 
            ]
        return ServiceBase.getAttrRO() + attrs         

    def getFuncs(self):
        funcs = [
            "FindByUserID",
            "FindByName"
            ]
        return ServiceBase.getFuncs() + funcs    
    
    getClass = classmethod(getClass)
    getAttrRO = classmethod(getAttrRO)
    getMethods = classmethod(getMethods)
    getFuncs = classmethod(getFuncs)
    
    def __init__(self, uuid, record={}):
        ServiceBase.__init__(self, uuid, record)
        self.props = DefaultProperties.instance()
        if ('user_id' in record):
            self.user_id = str(record.get('user_id'))
        else:
            raise ServiceError("Create failed. No user id specified")

        self.first_name = str(record['first_name'] if 'first_name' in record else "")
        self.last_name = str(record['last_name'] if 'last_name' in record else "")


    @classmethod
    def recreate(cls, record, uuid):
        if (not 'user_id' in record):
            raise ServiceError("Recreate: user_id not provided")
        
        result = user.LookupUserNameById(record['user_id'])
        if (result == None):
            raise ServiceError("Recreate failed. user id not found '"+record['user_id']+"'")
        record['first_name'] = result[0]
        record['last_name'] = result[1]
           
        userobj = User(uuid, record)
        return userobj.get_uuid()
    
    @classmethod
    def FindByUserID(cls, user_id):
        # First Look in active Estates
        for instance in store.get_all("User"):
            if (instance.get_user_id() == user_id):
                return (instance.get_uuid())
        return (cls.recreate({'user_id' : user_id}, user_id))
    
    @classmethod
    def FindByName(cls, firstname, lastname):
        user_id = user.LookupUserIdByName(firstname, lastname)
        return cls.FindByUserID(user_id)        
    
    def get_user_id(self):
        return self.user_id
    
    def get_first_name(self):
        return self.first_name

    def get_last_name(self):
        return self.last_name
    
        