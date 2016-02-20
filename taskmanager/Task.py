'''
Created on Dec 31, 2013

@author: David Daeschler
'''

import mysql.connector
import json
import traceback

from datetime import datetime

from maestro.rpcclient import Session
from inworldz.maestro.environment.ComputeResource import ComputeResource
from tasklets.TaskletBase import TaskletBase


class Status(object):
    New, Claimed, Running, Complete, Error = range(5) 
    
class Exclusivity(object):
    Free, Region, ComputeResource = range(3)

class Task(object):
    '''
    A task that can be executed by the taskmanager
    '''
    
    SQL_SELECT_LIST = "SELECT id, friendly_name, task_group_id, status, resource_id, region_id, exclusivity, tasklet, parameters, submitted_on, " +\
                        "started_on, progress, error_info, completed_on, return_value "

    def __init__(self, dbid, friendlyName, taskGroupId, status, resourceId, regionId, exclusivity,
                 tasklet, parameters, submittedOn, startedOn, progress, errorInfo,
                 completedOn, returnValue, dbConfig):
        '''
        Constructor
        '''
        self.dbid = dbid
        self.friendlyName = friendlyName
        self.taskGroupId = taskGroupId
        self.status = status
        self.resourceId = resourceId
        self.regionId = regionId
        self.exclusivity = exclusivity
        self.tasklet = tasklet
        self.parameters = parameters
        self.submittedOn = submittedOn
        self.startedOn = startedOn
        self.progress = progress
        self.errorInfo = errorInfo
        self.completedOn = completedOn
        self.returnValue = returnValue
        
        self.dbConfig = dbConfig
    
    def claim(self):
        cnx = mysql.connector.connect(**self.dbConfig)
        cursor = cnx.cursor()
        
        try:
            setTaskClaimed = \
                "UPDATE tasks SET status = %s WHERE id = %s AND status = %s";
            
            args = (Status.Claimed,self.dbid,Status.New)
            
            cursor.execute(setTaskClaimed, args)
            
            cnx.commit()
            
            if cursor.rowcount == 1:
                return True
            else:
                return False
            
        finally:
            cursor.close()
            cnx.close()
    
    def unclaim(self):
        cnx = mysql.connector.connect(**self.dbConfig)
        cursor = cnx.cursor()
        
        try:
            setTaskUnclaimed = \
                "UPDATE tasks SET status = %s WHERE id = %s;";
            
            args = (Status.New, self.dbid)
            
            cursor.execute(setTaskUnclaimed, args)
            
            cnx.commit()
            
        finally:
            cursor.close()
            cnx.close()
    
    def conflictsWith(self,otherTask):
        #check for resource conflicts
        if self.exclusivity == Exclusivity.ComputeResource or otherTask.exclusivity == Exclusivity.ComputeResource:
            if self.resourceId == otherTask.resourceId:
                return True
            
        #check for region conflicts
        if self.exclusivity == Exclusivity.Region or otherTask.exclusivity == Exclusivity.Region:
            if self.regionId == otherTask.regionId:
                return True
            
        return False
    
    def recordFault(self,errorInfo):
        if self.status == Status.Error:
            #we've already faulted once. don't overwrite the error
            return
        
        self.status = Status.Error
        self.errorInfo = errorInfo
        self.completedOn = datetime.now()
        
        cnx = mysql.connector.connect(**self.dbConfig)
        cursor = cnx.cursor()
        
        try:
            setTaskErrorSql = \
                "UPDATE tasks SET status = %s, error_info = %s, completed_on = NOW() WHERE id = %s;"
            
            args = (self.status,self.errorInfo,self.dbid)
            
            cursor.execute(setTaskErrorSql, args)
            
            cnx.commit()
            
            
        finally:
            cursor.close()
            cnx.close()
    
    def recordSuccess(self, returnValue=None):
        self.status = Status.Complete
        self.completedOn = datetime.now()
        
        cnx = mysql.connector.connect(**self.dbConfig)
        cursor = cnx.cursor()
        
        try:
            setTaskSuccessSql = \
                "UPDATE tasks SET status = %s, return_value = %s, completed_on = NOW() WHERE id = %s;"
            
            args = (self.status,self.returnValue,self.dbid)
            
            cursor.execute(setTaskSuccessSql, args)
            
            cnx.commit()
            
            
        finally:
            cursor.close()
            cnx.close()
            
    def recordTaskBegin(self):
        self.status = Status.Running
        self.startedOn= datetime.now()
        
        cnx = mysql.connector.connect(**self.dbConfig)
        cursor = cnx.cursor()
        
        try:
            setTaskErrorSql = \
                "UPDATE tasks SET status = %s, started_on = NOW();"
            
            args = (self.status,)
            
            cursor.execute(setTaskErrorSql, args)
            
            cnx.commit()
            
            
        finally:
            cursor.close()
            cnx.close()
    
    def execute(self):
        '''
        Actually runs the specified tasklet
        '''
        
        session = None
        try:
            #first parse the args which are packed in json
            args = None
            if self.parameters == None:
                args = None
            else:
                args = json.loads(self.parameters)
            
            #find the environment
            resource = ComputeResource.findById(self.dbConfig, self.resourceId)
            
            #find authentication information
            auth = ComputeResource.findAuth(self.dbConfig, self.resourceId)
            
            if auth == None:
                raise Exception("Could not find authorization info for {0}".format(resource.internalIp))
            
            #next grab an API instance to use for this tasklet
            session = Session("http://{0}:12089".format(resource.internalIp))
            
            #attempt a login
            session.api.login_with_password(*auth)
            
            taskletClass = TaskletBase.resolveTaskletClass(self.tasklet)
            tasklet = taskletClass(args, session, self)
            
            retVal = tasklet.execute() 
            if retVal != None:
                self.returnValue = retVal
            
            self.recordSuccess()
            
        except Exception:
            self.recordFault(traceback.format_exc())
            
        finally:
            if session != None:
                session.api.session.logout()
    
    @staticmethod
    def findNextUnclaimedNoConflictTask(dbconfig):
        '''
        Finds the next task that is ready for execution
        '''
        
        attemptedTasks = []
        task = None
        while True:
            task = Task.findNextUnclaimedTask(dbconfig,attemptedTasks)
            if task == None:
                #there are no tasks remaining
                return None
            
            #we have a task, now we need to make sure its exclusivity does not compete with any
            #running task. First, claim it to avoid race conditions
            if not task.claim():
                #we were unable to claim the task, someone else beat us to it. Bail out
                continue
            
            #we've claimed this task, now check that we're not in conflict with any other task
            potentialConflictList = Task.findRunningOrClaimedTasksForResource(dbconfig,task.resourceId)
            
            wasConflict = False
            
            #first check for other tasks we'll bump heads with
            for otherTask in potentialConflictList:
                if otherTask.dbid != task.dbid and task.conflictsWith(otherTask):
                    wasConflict = True
                    #since we've gotten this far that only thing that can stop us is if we have a conflict 
                    #with another task. track this task to use later for the next task search if
                    # we do happen to conflict
                    attemptedTasks.append(task.dbid)
            
            if not wasConflict:
                #also make sure we're not at our execution limit for the given task group
                if task.taskGroupId != None:
                    limit = Task.findTaskGroupConcurrencyLimit(dbconfig,task.taskGroupId)
                    otherTasks = Task.findRunningOrClaimedTasksForGroup(dbconfig,task.taskGroupId,task.dbid)
                    
                    if len(otherTasks) >= limit:
                        wasConflict = True
                        for groupTask in otherTasks:
                            attemptedTasks.append(groupTask.dbid)
            
            if wasConflict:
                task.unclaim()
                continue
            else:
                break
            
        #nothing.. awesome, we can run
        return task
    
    @staticmethod
    def mapTasksFromCursor(dbconfig, cursor):
        tasks = []
        for (dbid, friendly_name, task_group_id, status, resource_id, region_id, exclusivity, tasklet, parameters, submitted_on, \
            started_on, progress, error_info, completed_on, return_value) in cursor:
            
            task = Task(dbid, friendly_name, task_group_id, status, resource_id, region_id, exclusivity, tasklet, 
                parameters, submitted_on, started_on, progress, error_info, completed_on, return_value, dbconfig)
            tasks.append(task)
        
        return tasks
    
    @staticmethod
    def findNextUnclaimedTask(dbconfig,avoidIds):
        cnx = mysql.connector.connect(**dbconfig)
        cursor = cnx.cursor()
        
        try:
            findUnclaimedTaskSql = \
                Task.SQL_SELECT_LIST +\
                "FROM tasks " +\
                "WHERE status = %s "
            
            args = (Status.New,)
            
            if avoidIds != None and len(avoidIds) > 0:
                format_strings = ','.join(['%s'] * len(avoidIds))
                findUnclaimedTaskSql += " AND id NOT IN (%s) " % format_strings
                args = args + tuple(avoidIds)
                
            findUnclaimedTaskSql += " ORDER BY submitted_on ASC LIMIT 1"
            
            cursor.execute(findUnclaimedTaskSql, args) 
            
            tasks = Task.mapTasksFromCursor(dbconfig, cursor)
            
            if len(tasks) == 0:
                return None
            else:
                return tasks[0]
            
        finally:
            cursor.close()
            cnx.close()
    
    @staticmethod
    def findRunningOrClaimedTasksForResource(dbconfig,resourceId):
        cnx = mysql.connector.connect(**dbconfig)
        cursor = cnx.cursor()
        
        try:
            findRunningOrClaimedTasksForResourceSql = \
                Task.SQL_SELECT_LIST +\
                "FROM tasks " +\
                "WHERE (status = %s OR status = %s) AND resource_id = %s ";
            
            args = (Status.Claimed,Status.Running,resourceId)
            
            cursor.execute(findRunningOrClaimedTasksForResourceSql, args)     
            
            tasks = Task.mapTasksFromCursor(dbconfig, cursor)
                
            return tasks
            
        finally:
            cursor.close()
            cnx.close()
            
    @staticmethod
    def findTaskGroupConcurrencyLimit(dbconfig,taskGroupId):
        cnx = mysql.connector.connect(**dbconfig)
        cursor = cnx.cursor()
        
        try:
            findTaskGroupConcurrencyLimitSql = "SELECT concurrency_limit FROM taskgroups WHERE id = %s"
            args = (taskGroupId,)
            cursor.execute(findTaskGroupConcurrencyLimitSql, args)     
            
            limit = None
            for (concurrency_limit,) in cursor:
                limit = concurrency_limit
                
            return limit
            
        finally:
            cursor.close()
            cnx.close()

    @staticmethod
    def findRunningOrClaimedTasksForGroup(dbconfig,taskGroupId,excludeId):
        cnx = mysql.connector.connect(**dbconfig)
        cursor = cnx.cursor()
        
        try:
            findRunningOrClaimedTasksForGroupSql = \
                Task.SQL_SELECT_LIST +\
                "FROM tasks " +\
                "WHERE (status = %s OR status = %s) AND task_group_id = %s AND id != %s";
            
            args = (Status.Claimed,Status.Running,taskGroupId,excludeId)
            
            cursor.execute(findRunningOrClaimedTasksForGroupSql, args)     
            
            tasks = Task.mapTasksFromCursor(dbconfig, cursor)
                
            return tasks
            
        finally:
            cursor.close()
            cnx.close()
