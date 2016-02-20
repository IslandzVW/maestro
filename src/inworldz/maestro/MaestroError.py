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
# Copyright (C) 2004, 2005 Mike Wray <mike.wray@hp.com>
# Copyright (c) 2006, 2007 XenSource Inc.
#============================================================================

from xmlrpclib import Fault

ERROR_INTERNAL = 1
ERROR_GENERIC = 2

class ServiceError(Fault):
    
    def __init__(self, value):
        Fault.__init__(self, ERROR_GENERIC, value)
        self.value = value

    def __str__(self):
        return self.value

class ServiceAPIError(ServiceError):
    """Extend this class for all error thrown by autoplugged classes"""
    def __init__(self):
        ServiceError.__init__(self, 'ServiceAPI Error: You should never see this'
                           ' message; this class need to be overidden')

    def get_api_error(self):
        return ['INTERNAL_ERROR', 'You should never see this message; '
                'this method needs to be overidden']

class CreateUnspecifiedAttributeError(ServiceAPIError):
    def __init__(self, attr_name, class_name):
        ServiceAPIError.__init__(self)
        self.attr_name = attr_name
        self.class_name = class_name

    def get_api_error(self):
        return ['CREATE_UNSPECIFIED_ATTRIBUTE', self.attr_name,
                self.class_name]

    def __str__(self):
        return "CREATE_UNSPECIFIED_ATTRIBUTE: %s, %s" % (self.attr_name,
                 self.class_name)

class UniqueNameError(ServiceAPIError):
    def __init__(self, name, class_name):
        ServiceAPIError.__init__(self)
        self.name = name
        self.class_name = class_name
        
    def get_api_error(self):
        return ['UNIQUE_NAME_ERROR', self.name, self.class_name]        

    def __str__(self):
        return 'UNIQUE_NAME_ERROR: %s, %s' % (self.name, self.class_name)

class InvalidHandleError(ServiceAPIError):
    def __init__(self, klass, handle):
        ServiceAPIError.__init__(self)
        self.klass = klass
        self.handle = handle
        
    def get_api_error(self):
        return ['HANDLE_INVALID', self.klass, self.handle]        

    def __str__(self):
        return 'HANDLE_INVALID: %s %s' % (self.klass, self.handle)

class ImplementationError(ServiceAPIError):
    def __init__(self, klass, func):
        ServiceAPIError.__init__(self)
        self.klass = klass
        self.func = func

    def get_api_error(self):
        return ['IMPLEMENTATION_ERROR', self.klass, self.func]        

    def __str__(self):
        return 'IMPLEMENTATION_ERROR: %s %s' % (self.klass, self.func)
    

class SecurityError(ServiceAPIError):
    def __init__(self, error, message=None):
        ServiceAPIError.__init__(self)
        self.error = error
        if not message:
            self.message = "Unknown Error"
        else:
            self.message = message

    def get_api_error(self):
        return ['SECURITY_ERROR', self.error, self.message]

    def __str__(self):
        return 'SECURITY_ERROR: %s:%s' % (self.error, self.message)

class ServiceRuntimeError(ServiceAPIError):
    def __init__(self, error, message=None):
        ServiceAPIError.__init__(self)
        self.error = error
        if not message:
            self.message = "Unknown Error"
        else:
            self.message = message

    def get_api_error(self):
        return ['SERVICE_RUNTIME_ERROR', self.error, self.message]

    def __str__(self):
        return 'SERVICE_RUNTIME_ERROR: %s:%s' % (self.error, self.message)
    
    
MAESTRO_ERROR_AUTHENTICATION_FAILED = ('ELUSER', 'Authentication Failed')
MAESTRO_ERROR_SESSION_INVALID       = ('EPERMDENIED', 'Session Invalid')
MAESTRO_ERROR_TODO                  = ('ETODO', 'Lazy Programmer Error')
