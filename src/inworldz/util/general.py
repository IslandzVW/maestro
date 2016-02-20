'''
Created on Jan 13, 2014

@author: David Daeschler
'''

import string
import random
import datetime

def throwIfFalse(result, message):
    if not result:
        raise Exception(message)
    
def id_generator(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

def dateTimeString():
    now = datetime.datetime.now()
    return now.strftime("%Y%m%d%H%M%S")