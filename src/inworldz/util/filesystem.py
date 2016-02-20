import os.path

import pywintypes

from win32net import NetUseAdd, NetUseDel
from win32com.shell import shell, shellcon

def strip_suffix(text, suffix):
    if not text.endswith(suffix):
        return text
    return text[:-len(suffix)]

def getCurrentUsersDesktopPath():
    """ Return the path to the users desktop. Usually C:/Users/<user>/Desktop """
    return (shell.SHGetFolderPath (0, shellcon.CSIDL_DESKTOP, None, 0))

def getCurrentUsersHomePath():
    """ Return the path to the users home directory. Usually C:/Users/<user> """
    return (shell.SHGetFolderPath (0, shellcon.CSIDL_PROFILE, None, 0))

def getCurrentUsersAppDataPath():
    """ Return the path to the users home directory. Usually C:/Users/<user>/AppData/Roaming """
    return (shell.SHGetFolderPath (0, shellcon.CSIDL_APPDATA, None, 0))

def ConnectUNCShare(path, userName=None, password=None):
    (unc, path) = os.path.splitunc(path)
    if (unc and unc != ""):
        data = {'remote' : unc, 'local' : None, 'password' : password, 'username' : userName } 
        
        try:
            NetUseAdd(None, 2, data)
        except pywintypes.error, details:
            if details[0] == 1219:
                pass #already connected
            else:
                raise
        
        
"""
Could use this for ConnectUNCShare above if the .NET call doesnt work

def network_share_auth(share, username=None, password=None):

    cmd_parts = ["NET USE %s" % share]
    
    if password:
        cmd_parts.append(password)
    
    if username:
        cmd_parts.append("/USER:%s" % username)
        
    os.system(" ".join(cmd_parts))
    #try:
    #    yield
    #finally:
    #    os.system("NET USE %s: /DELETE" % drive_letter)
"""

if __name__ == "__main__":
    print getCurrentUsersAppDataPath()
    print getCurrentUsersDesktopPath()
    print getCurrentUsersHomePath()
