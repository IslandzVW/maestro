'''
Created on Dec 24, 2013

@author: David Daeschler
'''

import mysql.connector
from RegionEntry import RegionEntry
from inworldz.maestro.environment import CredentialCrypt

class Flags(object):
    Empty = 0
    GridServiceHost = (1 << 0)

class State(object):
    Invalid, WaitingSetup, Active, Inactive, Maintenance = range(5)

class ComputeResource(object):
    '''
    Represents a compute resource as defined in the maestro environment database. Compute resources
    each host a single instance of maestro and zero or more simulators
    '''


    def __init__(self, dbConfig, dbid, dbtype, containerId, hostName, internalIp, externalIp, 
                 state, flags, totalComputeUnits):
        
        self.dbConfig = dbConfig
        self.dbid = dbid
        self.dbtype = dbtype
        self.containerId = containerId
        self.hostName = hostName
        self.internalIp = internalIp
        self.externalIp = externalIp
        self.state = state
        self.flags = flags
        self.totalComputeUnits = totalComputeUnits
        self.regionEntries = None
    
    @staticmethod
    def findAuth(dbconfig,resourceId):
        '''
        Finds, decrypts, and returns authentication information for the given compute resource
        '''
        cnx = mysql.connector.connect(**dbconfig)
        cursor = cnx.cursor()
        
        try:
            findAuthInfoSql = \
                "SELECT username_enc, password_enc FROM computeresourceauth WHERE resource_id = %s;"
            
            args = (resourceId,)
            
            uAndPass = None
            
            cursor.execute(findAuthInfoSql, args)            
            for (username_enc,password_enc) in cursor:
                uAndPass = (username_enc, password_enc)
                break
            
            if uAndPass != None:
                uAndPass = (CredentialCrypt.Decode(uAndPass[0]), CredentialCrypt.Decode(uAndPass[1]))
            
            return uAndPass
        
        finally:
            cursor.close()
            cnx.close()
            
    @staticmethod
    def setAuth(dbconfig,resourceId,userName,passWord):
        '''
        Creates and writes credential information for the given resource
        '''
        cnx = mysql.connector.connect(**dbconfig)
        cursor = cnx.cursor()
        
        try:
            setAuthInfoSql = \
                "REPLACE INTO computeresourceauth(resource_id, username_enc, password_enc) VALUES(%s,%s,%s);"
            
            args = (resourceId, CredentialCrypt.Encode(userName), CredentialCrypt.Encode(passWord))
            
            
            cursor.execute(setAuthInfoSql, args)     
            cnx.commit()
        
        finally:
            cursor.close()
            cnx.close()
        
    @staticmethod
    def findByInternalIp(dbconfig,vmInternalIp):
        '''
        Uses the given internal IP to find the compute resource associated with it
        '''
        cnx = mysql.connector.connect(**dbconfig)
        cursor = cnx.cursor()
        
        try:
            findHostingResourceSql = \
                "SELECT computeresources.id as dbid, type, container_id, hostname, internal_ip, external_ip, state, flags, total_compute_units " + \
                "FROM computeresources " + \
                "INNER JOIN computeresourcetypes ON computeresources.type = computeresourcetypes.id " + \
                "WHERE internal_ip = %s"
            
            args = (vmInternalIp,)
            
            resource = None
            
            cursor.execute(findHostingResourceSql, args)            
            for (dbid,dbtype,containerId,hostName,internalIp,externalIp,state,flags,totalComputeUnits) in cursor:
                resource = ComputeResource(dbconfig,dbid,dbtype,containerId,hostName,internalIp,externalIp,state,flags,totalComputeUnits)
                break
            
            if resource != None:
                resource.regionEntries = RegionEntry.findRegionsAssignedToResource(dbconfig,resource.dbid)
            
            return resource
        
        finally:
            cursor.close()
            cnx.close()
    
    @staticmethod
    def findById(dbconfig,dbid):
        cnx = mysql.connector.connect(**dbconfig)
        cursor = cnx.cursor()
        
        try:
            findHostingResourceSql = \
                "SELECT computeresources.id as dbid, type, container_id, hostname, internal_ip, external_ip, state, flags, total_compute_units " + \
                "FROM computeresources " + \
                    "INNER JOIN computeresourcetypes ON computeresources.type = computeresourcetypes.id " + \
                "WHERE computeresources.id = %s"
            
            args = (dbid,)
            
            resource = None
            
            cursor.execute(findHostingResourceSql, args)            
            for (dbid,dbtype,containerId,hostName,internalIp,externalIp,state,flags,totalComputeUnits) in cursor:
                resource = ComputeResource(dbconfig,dbid,dbtype,containerId,hostName,internalIp,externalIp,state,flags,totalComputeUnits)
                break
            
            if resource != None:
                resource.regionEntries = RegionEntry.findRegionsAssignedToResource(dbconfig,resource.dbid)
            
            return resource
        
        finally:
            cursor.close()
            cnx.close()
    
    def findHostedRegionByUUID(self, dbid):
        try:
            return next(x for x in self.regionEntries if x.dbid == dbid)
        except StopIteration:
            return None
    
    
    def registerNewRegion(self, regionEntry):
        '''
        Registers a new region with this compute resource in the environment database
        and validates that there is not another region registered that this one will conflict
        with
        '''
        
        cnx = mysql.connector.connect(**self.dbConfig)
        cursor = cnx.cursor()
        
        try:
            findConflictingRegionSql = \
                "SELECT COUNT(*) AS cnt FROM deployedregions WHERE name = %s OR " +\
                "(grid_loc_x = %s AND grid_loc_y = %s);"
                
            args = (regionEntry.name, regionEntry.xloc, regionEntry.yloc)
            
            cursor.execute(findConflictingRegionSql, args)            
            for (count,) in cursor:
                if count != 0:
                    raise Exception("New region conflicts with an already provisioned region")
            
            cursor.close()
            cursor = cnx.cursor()
            
            insertRegionSql = \
                "INSERT INTO deployedregions(id, name, owner, estate_id, product_type, grid_loc_x, " +\
                    "grid_loc_y, host_resource, state) " + \
                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s);"
            
            args = (regionEntry.dbid, regionEntry.name, regionEntry.owner, regionEntry.estateId, \
                    regionEntry.productType, regionEntry.xloc, regionEntry.yloc, \
                    regionEntry.hostResource, regionEntry.state)
            
            cursor.execute(insertRegionSql, args)
            
            cnx.commit()
            
            regionEntry.dbConfig = self.dbConfig
            self.regionEntries.append(regionEntry)
            
        finally:
            cursor.close()
            cnx.close()
    