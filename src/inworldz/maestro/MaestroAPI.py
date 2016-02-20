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
# Copyright (C) 2006-2007 XenSource Ltd.
#============================================================================

import inspect
import Queue
import sets
import sys
import traceback
import threading
import time
import xmlrpclib

import inworldz.maestro.MaestroStore as MaestroStore

from inworldz.maestro.MaestroAuth import instance as auth_manager
from inworldz.maestro.MaestroAuth import AUTH_NONE, AUTH_WINDOWS
from inworldz.maestro.MaestroError import MAESTRO_ERROR_TODO
from inworldz.maestro.MaestroError import ServiceError, ServiceAPIError

import inworldz.maestro.MaestroTaskManager as MaestroTaskManager 
from inworldz.maestro.MaestroTask import MaestroTask

from inworldz.maestro.System import Memory, Disk, Cpu, Process
from inworldz.maestro.Region import Region
from inworldz.maestro.RegionHost import RegionHost
from inworldz.maestro.Estate import Estate
from inworldz.maestro.User import User
from inworldz.maestro.GridServices import GridService, UserService, MessagingService, ApertureService

import logging
log = logging.getLogger("zookeeper")

argcounts = {}

# ------------------------------------------
# Utility Methods for ZooKeeper API Implementation
# ------------------------------------------

#
# Convert all integers to strings as described in the API
#

def stringify(value):
    if isinstance(value, long) or \
       (isinstance(value, int) and not isinstance(value, bool)):
        return str(value)
    elif isinstance(value, dict):
        new_value = {}
        for k, v in value.items():
            new_value[stringify(k)] = stringify(v)
        return new_value
    elif isinstance(value, (tuple, list)):
        return [stringify(v) for v in value]
    else:
        return value

def maestro_api_success(value):
    """Wraps a return value in zkAPI format."""
    if value is None:
        s = ''
    else:
        s = stringify(value)
    return {"Status": "Success", "Value": s}

def maestro_api_success_void():
    """Return success, but caller expects no return value."""
    return maestro_api_success("")

def maestro_api_error(error):
    """Wraps an error value in zkAPI format."""
    if type(error) == tuple:
        error = list(error)
    if type(error) != list:
        error = [error]
    if len(error) == 0:
        error = ['INTERNAL_ERROR', 'Empty list given to maestro_api_error']

    return { "Status": "Failure",
             "ErrorDescription": [str(x) for x in error] }

def maestro_api_todo():
    """Temporary method to make sure we track down all the TODOs"""
    return {"Status": "Error", "ErrorDescription": MAESTRO_ERROR_TODO}

def now():
    return datetime()

def datetime(when = None):
    """Marshall the given time as a zk-API DateTime.

    @param when The time in question, given as seconds since the epoch, UTC.
                May be None, in which case the current time is used.
    """
    if when is None:
        return xmlrpclib.DateTime(time.gmtime())
    else:
        return xmlrpclib.DateTime(time.gmtime(when))


# ---------------------------------------------------
# Event dispatch
# ---------------------------------------------------

EVENT_QUEUE_LENGTH = 50
event_registrations = {}

def event_register(session, reg_classes):
    if session not in event_registrations:
        event_registrations[session] = {
            'classes' : set(),
            'queue'   : Queue.Queue(EVENT_QUEUE_LENGTH),
            'next-id' : 1
            }
    if not reg_classes:
        reg_classes = classes
    sessionclasses = event_registrations[session]['classes']
    if hasattr(sessionclasses, 'union_update'):
        sessionclasses.union_update(reg_classes)
    else:
        sessionclasses.update(reg_classes)



def event_unregister(session, unreg_classes):
    if session not in event_registrations:
        return

    if unreg_classes:
        event_registrations[session]['classes'].intersection_update(
            unreg_classes)
        if len(event_registrations[session]['classes']) == 0:
            del event_registrations[session]
    else:
        del event_registrations[session]


def event_next(session):
    if session not in event_registrations:
        return maestro_api_error(['SESSION_NOT_REGISTERED', session])
    queue = event_registrations[session]['queue']
    events = [queue.get()]
    try:
        while True:
            events.append(queue.get(False))
    except Queue.Empty:
        pass

    return maestro_api_success(events)


def _ctor_event_dispatch(maestro_api, ctor, api_cls, session, args):
    result = ctor(maestro_api, session, *args)
    if result['Status'] == 'Success':
        ref = result['Value']
        event_dispatch('add', api_cls, ref, '')
    return result


def _dtor_event_dispatch(maestro_api, dtor, api_cls, session, ref, args):
    result = dtor(maestro_api, session, ref, *args)
    if result['Status'] == 'Success':
        event_dispatch('del', api_cls, ref, '')
    return result


def _setter_event_dispatch(maestro_api, setter, api_cls, attr_name, session, ref, args):
    result = setter(maestro_api, session, ref, *args)
    if result['Status'] == 'Success':
        event_dispatch('mod', api_cls, ref, attr_name)
    return result


def event_dispatch(operation, api_cls, ref, attr_name):
    assert operation in ['add', 'del', 'mod']
    event = {
        'timestamp' : now(),
        'class'     : api_cls,
        'operation' : operation,
        'ref'       : ref,
        'obj_uuid'  : ref,
        'field'     : attr_name,
        }
    for reg in event_registrations.values():
        if api_cls in reg['classes']:
            event['id'] = reg['next-id']
            reg['next-id'] += 1
            reg['queue'].put(event)


# ---------------------------------------------------
# Python Method Decorators for input value validation
# ---------------------------------------------------

def trace(func, api_name = ''):
    """Decorator to trace XMLRPC API methods.

    @param func: function with any parameters
    @param api_name: name of the api call for debugging.
    """
    if hasattr(func, 'api'):
        api_name = func.api
    def trace_func(self, *args, **kwargs):
        log.debug('%s: %s' % (api_name, args))
        return func(self, *args, **kwargs)
    trace_func.api = api_name
    return trace_func


def catch_typeerror(func):
    """Decorator to catch any TypeErrors and translate them into the ZooKeeper-API
    errors.

    @param func: function with params: (self, ...)
    @rtype: callable object
    """
    def f(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except TypeError, exn:
            #log.exception('catch_typeerror')
            if hasattr(func, 'api') and func.api in argcounts:
                # Assume that if the argument count was wrong and if the
                # exception was thrown inside this file, then it is due to an
                # invalid call from the client, otherwise it's an internal
                # error (which will be handled further up).
                expected = argcounts[func.api]
                actual = len(args) + len(kwargs)
                if expected != actual:
                    tb = sys.exc_info()[2]
                    try:
                        sourcefile = traceback.extract_tb(tb)[-1][0]
                        if sourcefile == inspect.getsourcefile(MaestroAPI):
                            return maestro_api_error(['MESSAGE_PARAMETER_COUNT_MISMATCH', func.api, expected, actual])
                    finally:
                        del tb
            raise
        except ServiceAPIError, exn:
            return maestro_api_error(exn.get_api_error())

    return f


def session_required(func):
    """Decorator to verify if session is valid before calling method.

    @param func: function with params: (self, session, ...)
    @rtype: callable object
    """    
    def check_session(self, session, *args, **kwargs):
        if auth_manager().is_session_valid(session):
            return func(self, session, *args, **kwargs)
        else:
            return maestro_api_error(['SESSION_INVALID', session])

    return check_session


def _is_valid_ref(ref, validator):
    return type(ref) == str and validator(ref)

def _check_ref(validator, clas, func, api, session, ref, *args, **kwargs):
    if _is_valid_ref(ref, validator):
        return func(api, session, ref, *args, **kwargs)
    else:
        return maestro_api_error(['HANDLE_INVALID', clas, ref])


def valid_host(func):
    """Decorator to verify if host_ref is valid before calling method.

    @param func: function with params: (self, session, host_ref, ...)
    @rtype: callable object
    """
    return lambda *args, **kwargs: \
           _check_ref(RegionHost.instance().is_valid_host,
                      'RegionHost', func, *args, **kwargs)



def valid_object(class_name):
    """Decorator to verify if object is valid before calling
    method.

    @param func: function with params: (self, session, pif_ref)
    @rtype: callable object
    """
    return lambda func: \
           lambda *args, **kwargs: \
           _check_ref(lambda r: \
                          MaestroStore.get(r, class_name) is not None,
                      class_name, func, *args, **kwargs)

def valid_task(func):
    """Decorator to verify if task_ref is valid before calling
    method.

    @param func: function with params: (self, session, task_ref)
    @rtype: callable object
    """
    return lambda *args, **kwargs: \
           _check_ref(MaestroTaskManager.get_task,
                      'task', func, *args, **kwargs)

classes = {
    'session'       : None,
    'event'         : None,
    "task"          : valid_task,
    'Memory'        : valid_object("Memory"),
    "Disk"          : valid_object("Disk"),
    "Cpu"           : valid_object("Cpu"),
    "Process"       : valid_object("Process"),
    "RegionHost"    : valid_object("RegionHost"),
    "Region"        : valid_object("Region"),
    "Estate"        : valid_object("Estate"),
    "User"          : valid_object("User"),
    "GridService"   : valid_object("GridService"),
    "UserService"   : valid_object("UserService"),
    "MessagingService" : valid_object("MessagingService"),
    "ApertureService" : valid_object("ApertureService"),
}

autoplug_classes = {
    'Memory'        : Memory,
    'Disk'          : Disk,
    'Cpu'           : Cpu,
    'Process'       : Process,
    'RegionHost'    : RegionHost,
    'Region'        : Region,
    'Estate'        : Estate,
    'User'          : User,
    'GridService'   : GridService,
    'UserService'   : UserService,
    'MessagingService' : MessagingService,
    'ApertureService' : ApertureService,
}

class MaestroAPI(object):
    """Implementation of the Zookeeper API. Expects to be
    used via XMLRPCServer.

    All methods that need a valid session are marked with
    a L{session_required} decorator that will
    transparently perform the required session authentication.

    We need to support Python <2.4, so we use the old decorator syntax.

    All XMLRPC accessible methods require an 'api' attribute and
    is set to the XMLRPC function name which the method implements.
    """

    __decorated__ = False
    __init_lock__ = threading.Lock()
    _debug = {}
    
    def __new__(cls, *args, **kwds):
        """ Override __new__ to decorate the class only once.

        Lock to make sure the classes are not decorated twice.
        """
        cls.__init_lock__.acquire()
        try:
            if not cls.__decorated__:
                cls._decorate()
                cls.__decorated__ = True
                
            return object.__new__(cls, *args, **kwds)
        finally:
            cls.__init_lock__.release()
            
    def _decorate(cls):
        """ Decorate all the object methods to have validators
        and appropriate function attributes.

        This should only be executed once for the duration of the
        server.
        """
        global_validators = [session_required, catch_typeerror]


        # Cheat methods
        # -------------
        # Methods that have a trivial implementation for all classes.
        # 1. get_by_uuid == getting by ref, so just return uuid for
        #    all get_by_uuid() methods.
        
        for api_cls in classes.keys():
            # We'll let the autoplug classes implement these functions
            # themselves - its much cleaner to do it in the base class
            if api_cls == 'session' or api_cls in autoplug_classes.keys():
                continue
            
            get_by_uuid = '%s_get_by_uuid' % api_cls
            get_uuid = '%s_get_uuid' % api_cls
            get_all_records = '%s_get_all_records' % api_cls    

            def _get_by_uuid(_1, _2, ref):
                return maestro_api_success(ref)

            def _get_uuid(_1, _2, ref):
                return maestro_api_success(ref)

            def unpack(v):
                return v.get('Value')

            def _get_all_records(_api_cls):
                return lambda s, session: \
                    maestro_api_success(dict([(ref, unpack(getattr(cls, '%s_get_record' % _api_cls)(s, session, ref)))\
                                          for ref in unpack(getattr(cls, '%s_get_all' % _api_cls)(s, session))]))

            setattr(cls, get_by_uuid, _get_by_uuid)
            setattr(cls, get_uuid,    _get_uuid)
            setattr(cls, get_all_records, _get_all_records(api_cls))

        # Autoplugging classes
        # --------------------
        # These have all of their methods grabbed out from the implementation
        # class, and wrapped up to be compatible with the zk-API.

        def getter(ref, type):
            return MaestroStore.get(ref, type)
        
        for api_cls, impl_cls in autoplug_classes.items():
            def doit(n):           
                dot_n = '%s.%s' % (api_cls, n)
                full_n = '%s_%s' % (api_cls, n)
                if not hasattr(cls, full_n):
                    f = getattr(impl_cls, n)
                    argcounts[dot_n] = f.func_code.co_argcount + 1
                    g = lambda api_cls: \
                    setattr(cls, full_n, \
                            lambda s, session, ref, *args: \
                               maestro_api_success( \
                                   f(getter(ref, api_cls), *args)))
                    g(api_cls) # Force api_cls to be captured
                    
            def doit_func(n):           
                dot_n = '%s.%s' % (api_cls, n)
                full_n = '%s_%s' % (api_cls, n)
                if not hasattr(cls, full_n):
                    f = getattr(impl_cls, n)
                    argcounts[dot_n] = f.func_code.co_argcount
                    setattr(cls, full_n, \
                            lambda s, session, *args: \
                               maestro_api_success( \
                                   f(*args)))

            ro_attrs = impl_cls.getAttrRO()
            rw_attrs = impl_cls.getAttrRW()
            methods  = impl_cls.getMethods()
            funcs    = impl_cls.getFuncs()
            
            for attr_name in ro_attrs + rw_attrs:
                doit('get_%s' % attr_name)
            for attr_name in rw_attrs:
                doit('set_%s' % attr_name)
            for method in methods:
                doit('%s' % method)
            for func in funcs:
                doit_func('%s' % func)

        def wrap_method(name, new_f):
            try:
                f = getattr(cls, name)
                wrapped_f = (lambda *args: new_f(f, *args))
                wrapped_f.api = f.api
                wrapped_f.async = f.async
                setattr(cls, name, wrapped_f)
            except AttributeError:
                # Logged below (API call: %s not found)
                pass


        def setter_event_wrapper(api_cls, attr_name):
            setter_name = '%s_set_%s' % (api_cls, attr_name)
            wrap_method(
                setter_name,
                lambda setter, s, session, ref, *args:
                _setter_event_dispatch(s, setter, api_cls, attr_name,
                                       session, ref, args))


        def ctor_event_wrapper(api_cls):
            ctor_name = '%s_create' % api_cls
            wrap_method(
                ctor_name,
                lambda ctor, s, session, *args:
                _ctor_event_dispatch(s, ctor, api_cls, session, args))


        def dtor_event_wrapper(api_cls):
            dtor_name = '%s_destroy' % api_cls
            wrap_method(
                dtor_name,
                lambda dtor, s, session, ref, *args:
                _dtor_event_dispatch(s, dtor, api_cls, session, ref, args))


        # Wrapping validators around XMLRPC calls
        # ---------------------------------------

        for api_cls, validator in classes.items():
            def doit(n, takes_instance, async_support = False,
                     return_type = None):
                n_ = n.replace('.', '_')
                try:
                    f = getattr(cls, n_)
                    if n not in argcounts:
                        argcounts[n] = f.func_code.co_argcount - 1
                    
                    validators = takes_instance and validator and \
                                 [validator] or []

                    validators += global_validators
                    for v in validators:
                        f = v(f)
                        f.api = n
                        f.async = async_support
                        if return_type:
                            f.return_type = return_type
                    
                    setattr(cls, n_, f)
                except AttributeError:
                    log.warn("API call: %s not found" % n)

            if api_cls in autoplug_classes.keys():
                impl_cls = autoplug_classes[api_cls]
                ro_attrs = impl_cls.getAttrRO()
                rw_attrs = impl_cls.getAttrRW()
                methods  = map(lambda x: (x, ""), impl_cls.getMethods())
                funcs    = map(lambda x: (x, ""), impl_cls.getFuncs())
            else:
                ro_attrs = getattr(cls, '%s_attr_ro' % api_cls, []) \
                           + cls.Base_attr_ro
                rw_attrs = getattr(cls, '%s_attr_rw' % api_cls, []) \
                           + cls.Base_attr_rw
                methods  = getattr(cls, '%s_methods' % api_cls, []) \
                           + cls.Base_methods
                funcs    = getattr(cls, '%s_funcs'   % api_cls, []) \
                           + cls.Base_funcs

            # wrap validators around readable class attributes
            for attr_name in ro_attrs + rw_attrs:
                doit('%s.get_%s' % (api_cls, attr_name), True,
                     async_support = False)

            # wrap validators around writable class attrributes
            for attr_name in rw_attrs:
                doit('%s.set_%s' % (api_cls, attr_name), True,
                     async_support = False)
                setter_event_wrapper(api_cls, attr_name)

            # wrap validators around methods
            for method_name, return_type in methods:
                doit('%s.%s' % (api_cls, method_name), True,
                     async_support = True)

            # wrap validators around class functions
            for func_name, return_type in funcs:
                doit('%s.%s' % (api_cls, func_name), False,
                     async_support = True,
                     return_type = return_type)

            ctor_event_wrapper(api_cls)
            dtor_event_wrapper(api_cls)


    _decorate = classmethod(_decorate)

    def __init__(self, auth):
        self.auth = auth

    Base_attr_ro = ['uuid']
    Base_attr_rw = []
    Base_methods = [('get_record', 'Struct')]
    Base_funcs   = [('get_all', 'Set'), ('get_by_uuid', None), ('get_all_records', 'Set')]
    

    # zk API: Class Session
    # ----------------------------------------------------------------
    # NOTE: Left unwrapped by __init__

    session_attr_ro = ['this_host', 'this_user', 'last_active']
    session_methods = [('logout', None)]

    def session_get_all(self, session):
        return maestro_api_success([session])

    def session_login_with_password(self, *args):
        if len(args) != 2:
            return maestro_api_error(
                 ['MESSAGE_PARAMETER_COUNT_MISMATCH',
                 'session.login_with_password', 2, len(args)])
        username = args[0]
        password = args[1]
        try:
            session = ((self.auth == AUTH_NONE and
                        auth_manager().login_unconditionally(username)) or
                       auth_manager().login_with_password(username, password))
            return maestro_api_success(session)
        except ServiceError, e:
            return maestro_api_error(['SESSION_AUTHENTICATION_FAILED'])

    session_login_with_password.api = 'session.login_with_password'

    # object methods
    def session_logout(self, session):
        auth_manager().logout(session)
        return maestro_api_success_void()

    def session_get_record(self, session, self_session):
        if self_session != session:
            return maestro_api_error(['PERMISSION_DENIED'])

        record = {'uuid'       : session,
                  'this_host'  : RegionHost.instance().get_uuid(),
                  'this_user'  : auth_manager().get_user(session),
                  'last_active': now()}
        return maestro_api_success(record)

    def session_get_uuid(self, session, self_session):
        return maestro_api_success(self_session)

    def session_get_by_uuid(self, session, self_session):
        return maestro_api_success(self_session)

    # attributes (ro)
    def session_get_this_host(self, session, self_session):
        if self_session != session:
            return maestro_api_error(['PERMISSION_DENIED'])
        return maestro_api_success(RegionHost.instance().get_uuid())

    def session_get_this_user(self, session, self_session):
        if self_session != session:
            return maestro_api_error(['PERMISSION_DENIED'])
        user = auth_manager().get_user(session)
        if user is not None:
            return maestro_api_success(user)
        return maestro_api_error(['SESSION_INVALID', session])

    def session_get_last_active(self, session, self_session):
        if self_session != session:
            return maestro_api_error(['PERMISSION_DENIED'])
        return maestro_api_success(now())


    # Maestro API: Class event
    # ----------------------------------------------------------------

    event_attr_ro = []
    event_attr_rw = []
    event_funcs = [('register', None),
                   ('unregister', None),
                   ('next', None)]

    def event_register(self, session, reg_classes):
        event_register(session, reg_classes)
        return maestro_api_success_void()

    def event_unregister(self, session, unreg_classes):
        event_unregister(session, unreg_classes)
        return maestro_api_success_void()

    def event_next(self, session):
        return event_next(session)

    # ----------------------------------------------------------------
    # Maestro API: Class Tasks
    # ----------------------------------------------------------------

    task_attr_ro = ['name_label',
                    'name_description',
                    'status',
                    'progress',
                    'type',
                    'result',
                    'error_info',
                    'allowed_operations',
                    'session'
                    ]

    task_attr_rw = []

    task_funcs = [('get_by_name_label', 'Set(task)'), ('cancel', None)]

    def task_get_name_label(self, session, task_ref):
        task = MaestroTaskManager.get_task(task_ref)
        return maestro_api_success(task.name_label)

    def task_get_name_description(self, session, task_ref):
        task = MaestroTaskManager.get_task(task_ref)
        return maestro_api_success(task.name_description)

    def task_get_status(self, session, task_ref):
        task = MaestroTaskManager.get_task(task_ref)
        return maestro_api_success(task.get_status())

    def task_get_progress(self, session, task_ref):
        task = MaestroTaskManager.get_task(task_ref)
        return maestro_api_success(task.progress)

    def task_get_type(self, session, task_ref):
        task = MaestroTaskManager.get_task(task_ref)
        return maestro_api_success(task.type)

    def task_get_result(self, session, task_ref):
        task = MaestroTaskManager.get_task(task_ref)
        return maestro_api_success(task.result)

    def task_get_error_info(self, session, task_ref):
        task = MaestroTaskManager.get_task(task_ref)
        return maestro_api_success(task.error_info)

    def task_get_allowed_operations(self, session, task_ref):
        return maestro_api_success({})

    def task_get_session(self, session, task_ref):
        task = MaestroTaskManager.get_task(task_ref)
        return maestro_api_success(task.session)

    def task_get_all(self, session):
        tasks = MaestroTaskManager.get_all_tasks()
        return maestro_api_success(tasks)

    def task_get_record(self, session, task_ref):
        task = MaestroTaskManager.get_task(task_ref)
        return maestro_api_success(task.get_record())

    def task_cancel(self, session, task_ref):
        return maestro_api_error('OPERATION_NOT_ALLOWED')

    def task_get_by_name_label(self, session, name):
        return maestro_api_success(MaestroTaskManager.get_tasks_by_name(name))



class MaestroAPIAsyncProxy:
    """ A redirector for Async.Class.function calls to MaestroAPI
    but wraps the call for use with the MaestroTaskManager.

    @ivar maestroapi: Maesto API instance
    @ivar method_map: Mapping from XMLRPC method name to callable objects.
    """

    method_prefix = 'Async.'

    def __init__(self, api):
        """Initialises the Async Proxy by making a map of all
        implemented Maesto API methods for use with MaestroTaskManager.

        @param api: MaestroAPI instance
        """
        self.api = api
        self.method_map = {}
        for method_name in dir(self.api):
            method = getattr(self.api, method_name)            
            if (method_name[0] != '_') and hasattr(method, 'async') and method.async == True:
                self.method_map[method.api] = method

    def _dispatch(self, method, args):
        """Overridden method so that SimpleXMLRPCServer will
        resolve methods through this method rather than through
        inspection.

        @param method: marshalled method name from XMLRPC.
        @param args: marshalled arguments from XMLRPC.
        """

        # Only deal with method names that start with "Async."
        if not method.startswith(self.method_prefix):
            return maestro_api_error(['MESSAGE_METHOD_UNKNOWN', method])

        # Lookup synchronous version of the method
        synchronous_method_name = method[len(self.method_prefix):]
        if synchronous_method_name not in self.method_map:
            return maestro_api_error(['MESSAGE_METHOD_UNKNOWN', method])
        
        method = self.method_map[synchronous_method_name]

        # Check that we've got enough arguments before issuing a task ID.
        needed = argcounts[method.api]
        if len(args) != needed:
            return maestro_api_error(['MESSAGE_PARAMETER_COUNT_MISMATCH',
                                  self.method_prefix + method.api, needed,
                                  len(args)])

        # Validate the session before proceeding
        session = args[0]
        if not auth_manager().is_session_valid(session):
            return maestro_api_error(['SESSION_INVALID', session])

        # create and execute the task, and return task_uuid
        return_type = getattr(method, 'return_type', None)
        task_uuid = MaestroTaskManager.create_task(method, args,
                                                synchronous_method_name,
                                                return_type,
                                                synchronous_method_name,
                                                session)
        return maestro_api_success(task_uuid)
