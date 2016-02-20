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
# Copyright (C) 2007 Tom Wilkie <tom.wilkie@gmail.com>
#============================================================================
"""
This is a place to put instances of Service objects,
instead of just holding them in arbitrary places.

All objects which subclass ApiBase should use this
mechanism.

You must register both the uuid and type, and get objects
by type, to ensure safety
"""

__classes = {}

def register(uuid, stype, inst):
    __classes[(uuid, stype)] = inst
    return inst

def deregister(uuid, stype):
    old = get(uuid, stype)
    del __classes[(uuid, stype)]
    return old

def get(uuid, stype):
    """
    Get the instances by uuid and type
    """
    return __classes.get((uuid, stype), None)

def get_all(all_type):
    """
    Get all instances by type
    """
    return [inst
            for ((uuid, t), inst) in __classes.items()
            if t == all_type]        

def get_all_uuid(all_type):
    """
    Get all uuids by type
    """
    return [uuid
            for (uuid, t) in __classes.keys()
            if t == all_type]
