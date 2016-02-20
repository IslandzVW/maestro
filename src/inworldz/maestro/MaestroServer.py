'''
@author:     Michael Dickson
@copyright:  2012 InWorldz. All rights reserved.
@license:    Unreleased Source
@contact:    mike.chase@alternatemetaverse.com
@deffield    updated: 2013-1-25
'''

import sys
import traceback
import socket
import SocketServer

from SimpleXMLRPCServer import SimpleXMLRPCServer

from inworldz.maestro.MaestroAPI import MaestroAPI, MaestroAPIAsyncProxy
from inworldz.maestro.Grid import Grid

import inworldz.util.properties as DefaultProperties

# Set up logging
import logging    
logging.basicConfig(level=logging.DEBUG)

MAESTRO_CONFIG_FILE = "Maestro.exe.config";
DEFAULT_PORT = 12089

class MaestroServer(SocketServer.ThreadingMixIn, SimpleXMLRPCServer): 
    def __init__(self, auth, host = "localhost", port = DEFAULT_PORT, hosts_allowed = None):
        SimpleXMLRPCServer.__init__(self, (host, port), logRequests=False)

        self.auth = auth
        self.port = port
        self.host = host
        self.hosts_allowed = hosts_allowed
        
        self.ready = False        
        self.running = True

        self.api = MaestroAPI(auth) or None
        self.props = DefaultProperties.instance()

            
    def run(self):
        # Register API Functions
        # -------------------------------------------------------------------
        # exportable functions are ones that do not begin with '_'
        # and has the 'api' attribute.

        for meth_name in dir(self.api):
            if meth_name[0] != '_':
                meth = getattr(self.api, meth_name)
                if callable(meth) and hasattr(meth, 'api'):
                    self.register_function(meth, getattr(meth, 'api'))
        
        # Install Async support
        self.register_instance(MaestroAPIAsyncProxy(self.api))
        
        self.register_introspection_functions()
        self.ready = True
        
        # Initialize the local "Host" object
        # -----------------------------------------------------------------
        self.grid = Grid.create()
        
        # Custom runloop so we can cleanup when exiting.
        # -----------------------------------------------------------------
        while self.running:
            try:
                self.handle_request()
            except KeyboardInterrupt:
                self.running = False
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_traceback)           
                pass
                
        self.shutdown() 
        
    def cleanup(self):
        if hasattr(self, 'server'):
            try:
                self.socket.shutdown(2)
            except socket.error, e:
                pass # ignore any socket errors
            try:
                self.socket.close()
            except socket.error, e:
                pass

    def shutdown(self):
        self.running = False
        if self.ready:
            self.ready = False
            self.cleanup()

