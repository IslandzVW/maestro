'''
Created on May 9, 2013
@author: mdickson
'''

import mysql.connector

import inworldz.util.properties as DefaultProperties

def LookupUserIdByName(firstname, lastname):
    props = DefaultProperties.instance()
    cnx = mysql.connector.connect(**props.getCoreDbConfig())
    cursor = cnx.cursor()
    sql = "SELECT UUID from users WHERE userName = %s AND lastName = %s"
    args = (firstname, lastname)
    cursor.execute(sql, args)
    
    userid = None
    for (user_uuid,) in cursor:
        userid = user_uuid
    cursor.close()
    return str(userid)

def LookupUserNameById(userid):
    props = DefaultProperties.instance()
    cnx = mysql.connector.connect(**props.getCoreDbConfig())
    cursor = cnx.cursor()
    sql = \
        "SELECT users.userName, users.lastName FROM users " + \
        "WHERE users.UUID = '" + str(userid) + "'"
    cursor.execute(sql, ())
    
    result = None
    for (userName, lastName) in cursor:
        result = (str(userName), str(lastName))
    cursor.close()
    return result


if __name__ == "__main__":
    import os
    from inworldz.util.filesystem import getCurrentUsersAppDataPath
    from inworldz.maestro.version import product_name
    appdata = getCurrentUsersAppDataPath()
    props = DefaultProperties.instance()
    props.loadConfiguration()
    
    userid = LookupUserIdByName("Mike", "Chase")
    print userid
    print LookupUserNameById(userid)


