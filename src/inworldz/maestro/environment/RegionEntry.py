'''
Created on Dec 25, 2013

@author: ddaeschler
'''

import mysql.connector

class RegionState(object):
    Invalid, DeployedRunning, DeployedStopped, DeployedStopping, DeployedMaintenance, \
    TakedownWait, SetupInProgress, DeployedStarting = range(8)

class RegionEntry(object):
    '''
    Represents a region entry in the maestro environment database. The presence of this
    information means that maestro expects to manage the region 
    '''

    def __init__(self,dbid,name,owner,estateId,productType,xloc,yloc,hostResource,state):
        '''
        Constructor
        '''
        self.dbid = dbid
        self.name = name
        self.owner = owner
        self.estateId = estateId
        self.productType = productType
        self.xloc = xloc
        self.yloc = yloc
        self.hostResource = hostResource
        self.state = state
        self.dbConfig = None
        
    @staticmethod
    def findRegionsAssignedToResource(dbconfig, resourceId):
        '''
        Uses the given resource ID to find all regions associated with it
        '''
        cnx = mysql.connector.connect(**dbconfig)
        cursor = cnx.cursor()
        
        findHostedRegionsSql = \
            "SELECT id, name, owner, estate_id, product_type, grid_loc_x, grid_loc_y, host_resource, state " + \
            "FROM deployedregions " + \
            "WHERE host_resource = %s"
        
        args = (resourceId,)
        
        regions = []
        
        cursor.execute(findHostedRegionsSql, args)
        for (dbid,name,owner,estate_id,productType,locX,locY,hostResource,state) in cursor:
            ent = RegionEntry(dbid,name,owner,estate_id,int(productType),int(locX),int(locY),hostResource,int(state))
            ent.dbConfig = dbconfig
            regions.append(ent)
        
        cursor.close()
        cnx.close()
        
        return regions
    
    def updateState(self, newState):
        '''
        Updates the state of this region in the environment database
        '''
        
        self.state = newState
        
        cnx = mysql.connector.connect(**self.dbConfig)
        cursor = cnx.cursor()
        
        try:
            updateRegionSql = \
                "UPDATE deployedregions SET state = %s WHERE id = %s;"
            
            args = (self.state, self.dbid)
            cursor.execute(updateRegionSql, args)
            
            cnx.commit()
            
        finally:
            cursor.close()
            cnx.close()
            
    def unprovision(self):
        '''
        Removes the region from the provisioning database
        '''

        
        cnx = mysql.connector.connect(**self.dbConfig)
        cursor = cnx.cursor()
        
        try:
            removeRegionSql = \
                "DELETE FROM deployedregions WHERE id = %s;"
            
            args = (self.dbid,)
            cursor.execute(removeRegionSql, args)
            
            cnx.commit()
            
        finally:
            cursor.close()
            cnx.close()
            
    def saveChanges(self):
        '''
        Saves any changes to this region entry back to the environment database
        '''
        
        cnx = mysql.connector.connect(**self.dbConfig)
        cursor = cnx.cursor()
        
        try:
            updateRegionSql = \
                "UPDATE deployedregions SET " +\
                    "name=%s, owner=%s, estate_id=%s, product_type=%s, grid_loc_x=%s, "+\
                    "grid_loc_y=%s, host_resource=%s, state=%s " +\
                "WHERE id=%s";
                
            
            args = (self.name, self.owner, self.estateId, self.productType, self.xloc,
                    self.yloc, self.hostResource, self.state, self.dbid)
            
            cursor.execute(updateRegionSql, args)
            
            cnx.commit()
            
        finally:
            cursor.close()
            cnx.close()