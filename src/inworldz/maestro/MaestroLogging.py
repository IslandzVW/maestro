#============================================================================
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
# Copyright (C) 2004, 2005 Mike Wray <mike.wray@hp.com>
# Copyright (C) 2005, 2006 XenSource Ltd.
#============================================================================

import os.path
import tempfile
import types
import logging.handlers


__all__ = [ 'log', 'init', 'getLogFilename' ]

log = logging.getLogger("zookeeper")


MAX_BYTES = 1 << 20  # 1MB
BACKUP_COUNT = 5

STDERR_FORMAT = "[%(name)s] %(levelname)s (%(module)s:%(lineno)d) %(message)s"
LOGFILE_FORMAT = "[%(asctime)s %(process)d] %(levelname)s (%(module)s:%(lineno)d) %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


logfilename = None

class MaestroRotatingFileHandler(logging.handlers.RotatingFileHandler):

    def __init__(self, fname, mode, maxBytes, backupCount):
        logging.handlers.RotatingFileHandler.__init__(self, fname, mode, maxBytes, backupCount)
        self.setCloseOnExec()

    def doRollover(self):
        logging.handlers.RotatingFileHandler.doRollover(self)

      
def _mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            _mkdir(head)
        #print "_mkdir %s" % repr(newdir)
        if tail:
            os.mkdir(newdir)
            

def init(filename, level):
    """Initialise logging.  Logs to the given filename, and logs to stderr if DEBUG is set.
    """

    global logfilename

    def openFileHandler(fname):
        _mkdir.parents(os.path.dirname(fname))
        return MaestroRotatingFileHandler(fname, mode = 'a',
                                       maxBytes = MAX_BYTES,
                                       backupCount = BACKUP_COUNT)

    # Rather unintuitively, getLevelName will get the number corresponding to
    # a level name, as well as getting the name corresponding to a level
    # number.  setLevel seems to take the number only though, so convert if we
    # are given a string.
    if isinstance(level, types.StringType):
        level = logging.getLevelName(level)

    log.setLevel(level)

    try:
        fileHandler = openFileHandler(filename)
        logfilename = filename
    except IOError:
        logfilename = tempfile.mkstemp("-maestro.log")[1]
        fileHandler = openFileHandler(logfilename)

    fileHandler.setFormatter(logging.Formatter(LOGFILE_FORMAT, DATE_FORMAT))
    log.addHandler(fileHandler)
    

def getLogFilename():
    return logfilename
