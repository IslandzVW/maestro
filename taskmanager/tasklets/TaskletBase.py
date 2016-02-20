'''
Created on Jan 2, 2014

@author: David Daeschler
'''

class TaskletBase(object):
    '''
    The base class for all tasklets
    '''

    def __init__(self,args,session,task):
        '''
        Constructor
        '''
        self.args = args
        self.session = session
        self.task = task
        
    @staticmethod
    def resolveTaskletClass(name):
        module = __import__("tasklets." + name) #this returns the general tasklets module
        module = getattr(module, name) #this returns the actual tasklet module
        
        return getattr(module, name)