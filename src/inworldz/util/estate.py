'''
Created on Feb 16, 2013
@author: mdickson
'''

import mysql.connector
import inworldz.util.properties as DefaultProperties


def CreateNewEstate(estate_name, owner_uuid):
    props = DefaultProperties.instance()
    cnx = mysql.connector.connect(**props.getCoreDbConfig())
    
    # starting at ParentEstateID
    cursor = cnx.cursor()
    query = \
        "INSERT INTO estate_settings " + \
            "(EstateName, AbuseEmailToEstateOwner, DenyAnonymous, ResetHomeOnTeleport, " + \
             "FixedSun, DenyTransacted, BlockDwell, DenyIdentified, AllowVoice, " + \
             "UseGlobalTime, PricePerMeter, TaxFree, AllowDirectTeleport, RedirectGridX, " + \
             "RedirectGridY, ParentEstateID, SunPosition, EstateSkipScripts, BillableFactor, " + \
             "PublicAccess, AbuseEmail, EstateOwner, DenyMinors) " + \
         "VALUES " + \
            "(%s, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, " + \
             "100, 0, 0, 0, 1, '', %s, 0)"
    cursor.execute(query, (estate_name, owner_uuid))
    estate_id = cursor.lastrowid
    cursor.close()
    
    cursor = cnx.cursor()
    
    #also set the parent of the new estate to itself
    query = \
        "UPDATE estate_settings SET ParentEstateID = %s WHERE EstateID = %s;"
    
    cursor.execute(query, (estate_id, estate_id))
    
    cnx.commit()
    cnx.close()
    
    return estate_id


def LookupEstateIds():
    props = DefaultProperties.instance()
    cnx = mysql.connector.connect(**props.getCoreDbConfig())
    cursor = cnx.cursor()
    sql = "SELECT EstateID FROM estate_settings"
    cursor.execute(sql)
    result = []
    for (EstateID, ) in cursor:
        result.append(str(EstateID))
    cursor.close()
    return result


def LookupEstateById(estate_id):
    props = DefaultProperties.instance()
    cnx = mysql.connector.connect(**props.getCoreDbConfig())
    cursor = cnx.cursor()
    sql = \
        "SELECT estate_settings.EstateID, estate_settings.EstateName, estate_settings.EstateOwner, estate_settings.ParentEstateID " + \
        "FROM estate_settings " + \
        "WHERE estate_settings.EstateID = %s"
    cursor.execute(sql, (estate_id,))
    result = None
    for (EstateID, EstateName, EstateOwner, ParentEstateID) in cursor:
        result = (str(EstateID), str(EstateName), str(EstateOwner), str(ParentEstateID))
    cursor.close()
    return result


def LinkRegionToExistingEstate(sim_uuid, estate_id):
    props = DefaultProperties.instance()
    cnx = mysql.connector.connect(**props.getCoreDbConfig())
    cursor = cnx.cursor()
    sql = "INSERT INTO estate_map(RegionID, EstateID) VALUES(%s, %s)"
    args = (sim_uuid, estate_id)
    cursor.execute(sql, args)
    cnx.commit()
    cursor.close()
    cnx.close()
    
def FindEstateIDForRegion(sim_uuid):
    props = DefaultProperties.instance()
    cnx = mysql.connector.connect(**props.getCoreDbConfig())
    cursor = cnx.cursor()
    sql = \
        "SELECT estate_map.RegionID, estate_map.EstateID FROM estate_map " + \
        "WHERE estate_map.RegionID = %s"
    cursor.execute(sql, (sim_uuid,))
    estate_id = None
    for (RegionID, EstateID) in cursor:
        estate_id = str(EstateID)
    cursor.close()
    return estate_id
    
    
if __name__ == "__main__":
    import os
    from inworldz.util.filesystem import getCurrentUsersAppDataPath
    from inworldz.util.user import LookupUserIdByName
    from inworldz.maestro.version import product_name
    appdata = getCurrentUsersAppDataPath()
    props = DefaultProperties.instance()
    props.loadConfiguration()
    
    userid = LookupUserIdByName("Mike", "Chase")
    print userid
    estate_id = CreateNewEstate("The Rift", userid)
    print estate_id
    print LookupEstateById(estate_id)
    print LookupEstateIds()

