
import gettext
import xmlrpclib

translation = gettext.translation("inworldz-api", fallback = True)

class Failure(Exception):
    def __init__(self, details):
        try:
            # If this failure is MESSAGE_PARAMETER_COUNT_MISMATCH, then we
            # correct the return values here, to account for the fact that we
            # transparently add the session handle as the first argument.
            if details[0] == 'MESSAGE_PARAMETER_COUNT_MISMATCH':
                details[2] = str(int(details[2]) - 1)
                details[3] = str(int(details[3]) - 1)

            self.details = details
        except Exception, exn:
            self.details = ['INTERNAL_ERROR', 'Client-side: ' + str(exn)]

    def __str__(self):
        try:
            return translation.ugettext(self.details[0]) % self._details_map()
        except TypeError, exn:
            return "Message database broken: %s.\ninworldz-api failure: %s" % \
                   (exn, str(self.details))
        except Exception, exn:
            import sys
            print >>sys.stderr, exn
            return "inworldz-api failure: %s" % str(self.details)

    def _details_map(self):
        return dict([(str(i), self.details[i])
                     for i in range(len(self.details))])


_RECONNECT_AND_RETRY = (lambda _ : ())

class Session(xmlrpclib.ServerProxy):
    """A server proxy and session manager for communicating with XmlRPC Backends
    using the InWorldz ZooKeeper and Simulator API.

    Example:

    session = Session('http://localhost:9363/')
    session.login_with_password('me', 'mypassword')
    session.api.VM.start(vm_uuid)
    session.api.session.logout()
    """

    def __init__(self, uri, transport=None, encoding=None, verbose=0,
                 allow_none=1):
        xmlrpclib.ServerProxy.__init__(self, uri, transport, encoding,
                                       verbose, allow_none)
        self._session = None
        self.last_login_method = None
        self.last_login_params = None


    def api_request(self, methodname, params):
        print "api_request: "+methodname
        if methodname.startswith('login'):
            self._login(methodname, params)
            return None
        else:
            retry_count = 0
            while retry_count < 3:
                full_params = (self._session,) + params
                result = _parse_result(getattr(self, methodname)(*full_params))
                if result == _RECONNECT_AND_RETRY:
                    retry_count += 1
                    if self.last_login_method:
                        self._login(self.last_login_method,
                                    self.last_login_params)
                    else:
                        if methodname == 'session.logout':
                            return None
                        else:
                            raise xmlrpclib.Fault(401, 'You must log in')
                else:
                    return result
            raise xmlrpclib.Fault(
                500, 'Tried 3 times to get a valid session, but failed')


    def _login(self, method, params):
        result = _parse_result(getattr(self, 'session.%s' % method)(*params))
        if result == _RECONNECT_AND_RETRY:
            raise xmlrpclib.Fault(
                500, 'Received SESSION_INVALID when logging in')
        self._session = result
        self.last_login_method = method
        self.last_login_params = params


    def __getattr__(self, name):
        if name == 'api':
            return _Dispatcher(self.api_request, None)
        elif name.startswith('login'):
            return lambda *params: self._login(name, params)
        else:
            return xmlrpclib.ServerProxy.__getattr__(self, name)

def _parse_result(result):
    if type(result) != dict or 'Status' not in result:
        raise xmlrpclib.Fault(500, 'Missing Status in response from server' + result)
    if result['Status'] == 'Success':
        if 'Value' in result:
            return result['Value']
        else:
            raise xmlrpclib.Fault(500, 'Missing Value in response from server')
    else:
        if 'ErrorDescription' in result:
            if result['ErrorDescription'][0] == 'SESSION_INVALID':
                return _RECONNECT_AND_RETRY
            else:
                raise Failure(result['ErrorDescription'])
        else:
            raise xmlrpclib.Fault(
                500, 'Missing ErrorDescription in response from server')


# Based upon _Method from xmlrpclib.
class _Dispatcher:
    def __init__(self, send, name):
        self.__send = send
        self.__name = name

    def __repr__(self):
        if self.__name:
            return '<RemoteAdminAPI._Dispatcher for %s>' % self.__name
        else:
            return '<RemoteAdminAPI._Dispatcher>'

    def __getattr__(self, name):
        if self.__name is None:
            return _Dispatcher(self.__send, name)
        else:
            return _Dispatcher(self.__send, "%s.%s" % (self.__name, name))

    def __call__(self, *args):
        return self.__send(self.__name, args)
