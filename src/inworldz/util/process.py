'''
Created on Dec 30, 2013

@author: David Daeschler
'''

import time
import os
import psutil
import sys
import subprocess

def WaitForProcessTermination(process, timeout):
    '''
    Waits the specified amount of time for a process to terminate. Returns
    true if the process terminated within the timeout, false if not
    '''
    
    if process == None:
        return True
    
    start = time.time()

    while (process.is_running() and ((time.time() - start) < timeout)):
        time.sleep(1);
        
    if process.is_running():
        return False
    else:
        return True

def TerminateAndWaitForConfirmation(process, timeout):
    process.terminate() # This sends CTRL-C, which will cause an immediate shutdown.
    return WaitForProcessTermination(process, timeout)

def DumpThreadStacks(pid):
    sddir = os.path.dirname(sys.argv[0])
    p = psutil.Popen([os.path.join(sddir, "stackdump.exe"), str(pid)], 
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE)
    
    # wait for the process to terminate
    out = p.communicate()[0]
    
    return out