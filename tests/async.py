'''
Created on Mar 2, 2013

@author: mdickson
'''

# Simple example using the asynchronous version of the VM start method
# Assumes the presence of a VM called 'new'
import pprint, time, sys
from maestro.rpcclient import Session

def main(session):

    host = session.api.session.get_this_host(session._session)
    record = session.api.RegionHost.get_record(host)
    print "RegionHost: "
    pprint.pprint(record)
    
    print "Attempting to fetch regions asynchronously"       
    regions = record['Regions']
            
    for region in regions:
        taskid = session.api.Async.Region.Start(region, False, 120)
        pprint.pprint(taskid)
    
        print "Waiting for the task to complete"
        while session.api.task.get_status(taskid) == "pending": 
            print "poll"
            time.sleep(1)

        task_record = session.api.task.get_record(taskid)
        print "The contents of the task record:"
        pprint.pprint(task_record)
    
if __name__ == "__main__":
    if len(sys.argv) <> 4:
        print "Usage:"
        print sys.argv[0], " <url> <username> <password>"
        sys.exit(1)
    url = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    # First acquire a valid session by logging in:
    session = Session(url)    
    session.api.login_with_password(username, password)
    main(session)
 