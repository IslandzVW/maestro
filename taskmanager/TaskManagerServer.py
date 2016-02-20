'''
Created on Jan 1, 2014

@author: david_000
'''

import time
import multiprocessing
import traceback

from Task import Task

def TaskManagerServerWorker(workQueue, activeWorkers):
    '''
    Worker process loop 
    '''
    print "TaskManagerServerWorker started."
    while True:
        task = workQueue.get()
        if task == None:
            #signal to stop
            return
        
        #we have a task, increment the activeworkers count and execute the task
        with activeWorkers.get_lock():
            activeWorkers.value += 1
        
        try:
            task.errorInfo='no error'
            task.execute()
        except Exception:
            tb = traceback.format_exc()
            task.recordFault(tb)
            
            print "Fault outside of tasklet: " + tb
            
        finally:
            with activeWorkers.get_lock():
                activeWorkers.value -= 1
        
        continue

class TaskManagerServer(object):
    '''
    The actual task manager process
    '''
    

    def __init__(self,configuration):
        '''
        Constructor
        '''
        self.config = configuration
        self.dbConfig = configuration.getEnvironmentDbConfig()
        self.running = False
        self.numProcesses = self.config.workerProcessCount
        self.workerProcesses = []
        self.workQueue = multiprocessing.Queue()
        self.activeWorkers = multiprocessing.Value('i', 0)
        
    def run(self):
        self.running = True
        
        #start up our worker processes
        for i in xrange(self.numProcesses):
            process = multiprocessing.Process(target=TaskManagerServerWorker, args=(self.workQueue, self.activeWorkers))
            process.start()
            self.workerProcesses.append(process)
            time.sleep(0.25)
            
        while self.running:
            #if the queue is full, don't look for any more jobs for now
            with self.activeWorkers.get_lock():
                if self.activeWorkers.value >= self.numProcesses:
                    time.sleep(1)
                    continue
            
            nextTask = Task.findNextUnclaimedNoConflictTask(self.dbConfig)
            
            if nextTask == None:
                time.sleep(1)
                continue
            else:
                #queue the work
                self.workQueue.put(nextTask)
            
