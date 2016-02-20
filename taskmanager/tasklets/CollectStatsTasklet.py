'''
Created on Jan 24, 2014

@author: David Daeschler
'''

import string
import json
import mysql.connector

from tasklets.TaskletBase import TaskletBase
from inworldz.maestro.environment.RegionEntry import RegionState

from config import Configuration

class CollectStatsTasklet(TaskletBase):
    '''
    Tasklet that collects compute resource and region performance stats from the given resource
    '''
    MONITOR_DISK = "C:\\"
    
        
    def execute(self):
        # CollectStatsTasklet
        # {
        #    "result": "store" or "return"
        # }
        
        #
        # {
        #    "computeResourceStats": 
        #    {
        #        "cpu_used_percentage": "0.0", 
        #        "memory_used_percentage": "0.0", 
        #        "disk_used_percentage": "0.0"
        #    },
        #    "regionStats": 
        #    [
        #        {"region_id": "[uuid]", "cpu_used_percentage": "0.0", 
        #        "memory_used": [bytes], "thread_count": 0, "handle_count": 0}, 
        #        ...
        #    ]
        # }       
        
        resultAction = string.lower(self.args['result'])
        
        stats = {}
        
        host = self.session.api.RegionHost.get_all()[0]
        regions = self.session.api.RegionHost.get_Regions(host)
        
        hostMemory = self.session.api.RegionHost.get_Memory(host)
        hostDisk = self.session.api.RegionHost.get_Disk(host)
        hostCPU = self.session.api.RegionHost.get_Cpu(host)
        
        hostStats = {}
        
        hostStats['cpu_used_percentage'] = self.session.api.Cpu.cpu_percent(hostCPU)
        hostStats['memory_used_percentage'] = self.session.api.Memory.virtual_memory(hostMemory)[2]
        hostStats['disk_used_percentage'] = self.session.api.Disk.disk_usage(hostDisk, self.MONITOR_DISK)[3]
        
        stats['computeResourceStats'] = hostStats
        
        regionStats = []
        
        #collect stats for all running regions
        for region in regions:
            if int(self.session.api.Region.get_State(region)) == RegionState.DeployedRunning:
                cpuUsed = self.session.api.Region.get_cpu_used_percentage(region)
                memUsed = self.session.api.Region.get_memory_used(region)
                threadCount = self.session.api.Region.get_thread_count(region)
                handleCount = self.session.api.Region.get_handle_count(region)
                
                regionStats.append({"region_id": region, "cpu_used_percentage": cpuUsed, "memory_used": memUsed,
                                    "thread_count": threadCount, "handle_count": handleCount})
        
        stats['regionStats'] = regionStats
        
        if resultAction == 'return':
            return json.dumps(stats)
        else:
            #store the results to the DB
            self.storeResultsToDb(stats)
    
    def storeResultsToDb(self, stats):
        dbConfig = Configuration.instance().getEnvironmentDbConfig()
        
        cnx = mysql.connector.connect(**dbConfig)
        
        try:
            insertResourceStatSql = \
                "INSERT INTO computeresourcestats(collected_on, computeresource_id, cpu_used_percentage, " +\
                    "memory_used_percentage, disk_used_percentage) VALUES(NOW(),%s,%s,%s,%s)"
                    
            args = (self.task.resourceId, 
                    stats['computeResourceStats']['cpu_used_percentage'],
                    stats['computeResourceStats']['memory_used_percentage'],
                    stats['computeResourceStats']['disk_used_percentage']
                    )
            
            cursor = cnx.cursor()
            cursor.execute(insertResourceStatSql, args)
            cnx.commit()
            cursor.close()
            
            insertRegionStatSql = \
                "INSERT INTO deployedregionstats(collected_on, region_id, cpu_used_percentage, " +\
                    "memory_used, thread_count, handle_count) VALUES(NOW(),%s,%s,%s,%s,%s)"
            
            for regionData in stats['regionStats']:
                args = (regionData['region_id'], 
                        regionData['cpu_used_percentage'],
                        regionData['memory_used'],
                        regionData['thread_count'],
                        regionData['handle_count']
                        )
                
                cursor = cnx.cursor()
                cursor.execute(insertRegionStatSql, args)
                cnx.commit()
            
            
        finally:
            cnx.close()
        
        
        