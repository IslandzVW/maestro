#===========================================================================
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
# Copyright (C) 2007 XenSource Ltd
#============================================================================

"""
Task Manager for Maestro API asynchronous tasks.

Stores all tasks in a simple dictionary in module's own local storage to
avoid the 'instance()' methods.

Tasks are indexed by UUID.

"""

from inworldz.maestro.MaestroTask import MaestroTask
from inworldz.maestro import uuid
import threading

tasks = {}
tasks_lock = threading.Lock()

def create_task(func, args, func_name, return_type, label, session):
    """Creates a new Task and registers it with the MaestroTaskManager.

    @param func: callable object XMLRPC method
    @type func: callable object
    @param args: tuple or list of arguments
    @type args: tuple or list
    @param func_name: XMLRPC method name, so we can estimate the progress
    @type func_name: string
    
    @return: Task UUID
    @rtype: string.
    """
    task_uuid = uuid.createString()
    try:
        tasks_lock.acquire()
        task = MaestroTask(task_uuid, func, args, func_name, return_type, label,
                        '', session)
        tasks[task_uuid] = task
    finally:
        tasks_lock.release()

    task.start()

    return task_uuid

def destroy_task(task_uuid):
    """Destroys a task.

    @param task_uuid: Task UUID
    @type task_uuid: string.
    """
    try:
        tasks_lock.acquire()
        if task_uuid in tasks:
            del tasks[task_uuid]
    finally:
        tasks_lock.release()

def get_all_tasks():
    """ Returns all the UUID of tracked tasks, completed or pending.

    @returns: list of UUIDs
    @rtype: list of strings
    """
    try:
        tasks_lock.acquire()
        return tasks.keys()
    finally:
        tasks_lock.release()

def get_task(task_uuid):
    """ Retrieves a task by UUID.

    @rtype: MaestroTask or None
    @return: Task denoted by UUID.
    """
    try:
        tasks_lock.acquire()
        return tasks.get(task_uuid)
    finally:
        tasks_lock.release()

def get_tasks_by_name(task_name):
    """ Retrieves a task by UUID.

    @rtype: MaestroTask or None
    @return: Task denoted by UUID.
    """
    try:
        tasks_lock.acquire()
        return [t.uuid for t in tasks if t.name_label == task_name]
    finally:
        tasks_lock.release()        


