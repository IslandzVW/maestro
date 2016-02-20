#============================================================================
# This library is free software; you can redistribute it and/or
# modify it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#============================================================================
# Copyright (C) 2006 XenSource Ltd.
#============================================================================

import time

import win32security
import win32api
import inworldz.maestro.uuid as genuuid
from inworldz.maestro.MaestroError import ServiceError

AUTH_NONE = 'none'
AUTH_WINDOWS = 'windows'

class MaestroAuth:
    """Keeps track of Maestro API Login Sessions.
    Note: Login sessions are not valid across instances of Zookeeper.
    """
    def __init__(self):
        self.sessions = {}

    def init(self):
        pass

    def login_unconditionally(self, username, password, handle):
        """Returns a session UUID if valid.

        @rtype: string
        @return: Session UUID
        """
        new_session = genuuid.createString()
        self.sessions[new_session] = (username, password, time.time(), handle)
        return new_session


    def login_with_password(self, username, password):
        """Returns a session UUID if valid, otherwise raises an error.

        @raises ServiceError: If login fails.
        @rtype: string
        @return: Session UUID
        """
        authInfo = self.try_authorize(username, password)
        
        if authInfo[0]:
            return self.login_unconditionally(username, password, authInfo[1])

        raise ServiceError("Login failed")


    def logout(self, session):
        """Delete session of it exists."""
        if self.is_session_valid(session):
            sessionInfo = self.sessions[session]
            win32api.CloseHandle(sessionInfo[3])
            del self.sessions[session]


    def is_session_valid(self, session):
        """Returns true is session is valid."""
        if type(session) == type(str()):
            return (session in self.sessions)
        return False


    def try_authorize(self, username, password):
        """Returns true is a user is authorised via PAM.
       @rtype: boolean
        """
        try:
            htoken = win32security.LogonUser(
                username, "", password, win32security.LOGON32_LOGON_NETWORK,
                win32security.LOGON32_PROVIDER_DEFAULT)
        except win32security.error, err:
            return (False, None)
        else:
            if htoken: 
                return (True, htoken)
            else:
                return (False, None)
    

    def get_user(self, session):
        try:
            return self.sessions[session][0]
        except (KeyError, IndexError):
            return None

    def get_first_session(self):
        if len(self.sessions) == 0:
            return None
        
        firstItem = self.sessions.itervalues().next()
        
        return firstItem

def instance():
    """Singleton constructor. Use this instead of the class constructor.
    """
    global inst
    try:
        inst
    except:
        inst = MaestroAuth()
        inst.init()
    return inst
