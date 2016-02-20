'''
Created on Jan 24, 2013

@author: mdickson
'''
import psutil
import json

from inworldz.maestro.ServiceBase import ServiceBase

class Memory(ServiceBase):
    """Physical and Virtual Memory."""

    def getClass(self):
        return "Memory"

    def getMethods(self):
        methods = [
            "virtual_memory",
            "swap_memory"
            ]
        return ServiceBase.getMethods() + methods
     
    def getAttrRO(self):
        attrs = [
            ]
        return ServiceBase.getAttrRO() + attrs         
    
    getClass = classmethod(getClass)
    getAttrRO = classmethod(getAttrRO)
    getMethods = classmethod(getMethods)
    
    def __init__(self, uuid, record={}):
        ServiceBase.__init__(self, uuid, record)

    def virtual_memory(self):
        return psutil.virtual_memory()

    def swap_memory(self):
        return psutil.swap_memory()


class Disk(ServiceBase):
    """Disk Subsytems."""

    def getClass(self):
        return "Disk"
    
    def getMethods(self):
        methods = [
            "disk_usage",
            "disk_io_counters"
            ]
        return ServiceBase.getMethods() + methods

    def getAttrRO(self):
        attrs = [
           'disk_partitions'
            ]
        return ServiceBase.getAttrRO() + attrs

    getClass = classmethod(getClass)
    getMethods = classmethod(getMethods)
    getAttrRO = classmethod(getAttrRO)
    
    def __init__(self, uuid, record={}):
        ServiceBase.__init__(self, uuid, record)

    def get_disk_partitions(self):
        return psutil.disk_partitions()

    def disk_usage(self, path):
        return psutil.disk_usage(path)

    def disk_io_counters(self, perfdisk):
        return psutil.disk_io_counters(perfdisk)


class Cpu(ServiceBase):
    """Processor Subsytems."""

    def getClass(self):
        return "Cpu"
    
    def getMethods(self):
        methods = [
            "cpu_percent",
            "cpu_times"
            ]
        return ServiceBase.getMethods() + methods

    getClass = classmethod(getClass)
    getMethods = classmethod(getMethods)
    
    def __init__(self, uuid, record={}):
        ServiceBase.__init__(self, uuid, record)

    def cpu_percent(self, interval=0.1, percpu=False):
        return psutil.cpu_percent(interval, percpu)

    def cpu_times(self, percpu=False):
        return psutil.cpu_times(percpu)
    
    
class Process(ServiceBase):
    """Process Subsytem."""

    def getClass(self):
        return "Process"
    
    def getMethods(self):
        methods = [
            "process_list",
            ]
        return ServiceBase.getMethods() + methods

    getClass = classmethod(getClass)
    getMethods = classmethod(getMethods)
    
    def __init__(self, uuid, record={}):
        ServiceBase.__init__(self, uuid, record)

    def process_list(self):
        pass

#import os.path
#for p in psutil.process_iter():
#    if (len(p.cmdline()) <= 0):
#        continue
#    cmdline = p.cmdline()[0]
#    if os.path.basename(cmdline) == "OpenSim.exe":
#        print cmdline
#        print os.path.dirname(cmdline)
#        print p.pid
