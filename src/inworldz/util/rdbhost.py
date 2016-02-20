'''
Created on Feb 14, 2013

@author: mdickson
'''
import mysql.connector
import inworldz.util.properties as properties


# ------------------------------------------------------------------------------------------
# RBD Host Sharding
# ------------------------------------------------------------------------------------------

def GetRdbHost(dbconfig, regionUuid):
    destination = None
    cnx = mysql.connector.connect(**dbconfig)
    cursor = cnx.cursor()
    
    findCurrentHostSql = \
        "SELECT host_name FROM RegionRdbMapping " + \
        "INNER JOIN RdbHosts ON RegionRdbMapping.rdb_host_id = RdbHosts.id " + \
        "WHERE RegionRdbMapping.region_id = '" + regionUuid + "'";
    cursor.execute(findCurrentHostSql, ())            
    for (host_name,) in cursor:
        destination = host_name
    
    cursor.close()
    cnx.close()
    return destination


def FindBestRdbHost(dbconfig):
    destination = None
    cnx = mysql.connector.connect(**dbconfig)
    cursor = cnx.cursor()
    
    findBestHostSql = \
        "SELECT RdbHosts.id, RdbHosts.host_name, COUNT(*) as cnt " + \
        "FROM RdbHosts " + \
        "LEFT JOIN RegionRdbMapping ON RegionRdbMapping.rdb_host_id = RdbHosts.id " + \
        "GROUP BY RdbHosts.id, RdbHosts.host_name " + \
        "ORDER BY cnt ASC LIMIT 1;";

    cursor.execute(findBestHostSql, ())            
    for (hostid, host_name, cnt) in cursor:
        destination = host_name
    
    cursor.close()
    cnx.close()
    return destination


def RecordAssignedServer(dbconfig, regionId, dstServerHost):
    cnx = mysql.connector.connect(**dbconfig)
    cursor = cnx.cursor()
    
    insertMappingSql = \
        "REPLACE INTO RegionRdbMapping " + \
        "SELECT %s AS region_id, (SELECT id FROM RdbHosts WHERE host_name=%s LIMIT 1) AS region_host "
    args = (regionId, dstServerHost)
    cursor.execute(insertMappingSql, args)
    cnx.commit()
    
    cursor.close()
    cnx.close()
    
    
def AssignBestRdbHost(dbconfig, sourceRegion):
    # Look up source host if one already exists
    if (GetRdbHost(dbconfig, sourceRegion) != None):
        raise Exception("Can not assign an RDB host, region already assigned")
    bestHost = FindBestRdbHost(dbconfig)
    if (bestHost == None):
        raise Exception("Could not find available RDB host")
    RecordAssignedServer(dbconfig, sourceRegion, bestHost)
    return bestHost
