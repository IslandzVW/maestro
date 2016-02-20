'''
Created on Jan 11, 2014

@author: David Daeschler    
'''

from tasklets.TaskletBase import TaskletBase

class CompositeTasklet(TaskletBase):
    '''
    Tasklet that executes a list of other tasklets w/their parameters serially
    '''
    
    def execute(self):
        # CompositeTasklet
        # args
        # {
        #    "1": 
        #    {
        #        "taskletName": "name",
        #        "arg1": "value",
        #        "arg2": "value"
        #    },
        #    "2":
        #    {
        #        "taskletName": "name",
        #        "arg1": "value",
        #        "arg2": "Value"
        #    }
        # }
        
        for taskletParams in self.args:
            taskletClass = TaskletBase.resolveTaskletClass(taskletParams["taskletName"])
            tasklet = taskletClass(taskletParams, self.session)
            
            tasklet.execute()
            