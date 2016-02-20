'''
Created on Jan 2, 2013

@author: mdickson
'''
import sys
import win32ui
import time

import SendKeys

def FindConsole(windowTitle):
    try:
        return win32ui.FindWindow("ConsoleWindowClass", windowTitle)
    except win32ui.error:
        return None

def SendKeysToWindow(window, keys):
    if (window == None):
        return (False)

    try:
        window.SetForegroundWindow()
        SendKeys.SendKeys(keys)
    except Exception:
        return False
    
    return True


def WaitForWindowClose(window, timeout):
    if (window == None):
        return
    
    start = time.time()

    while (window.IsWindow() and ((time.time() - start) < timeout)):
        time.sleep(1);

    if (window.IsWindow()):
        return False;
    else:
        return True;


def WaitForWindowOpen(windowTitle, timeout):
    start = time.time()
    while ((time.time() - start) < timeout):
        if (FindConsole(windowTitle) != None):
            return True 
        time.sleep(1)
    
    return False


def usage():
    """
    Writes help message to `stderr` and exits.
    """
    print >> sys.stderr, """\
%(name)s [-h] [-d seconds] [-p seconds] [-f filename] or [string of keys]

    -dN    or --delay=N   : N is seconds before starting
    -pN    or --pause=N   : N is seconds between each key
    -wNAME or --window=NAME : NAME is the windowTitle to receive focus
    -h     or --help      : show help message
""" % {'name': 'SendKeys.py'}
    sys.exit(1)

def error(msg):
    """
    Writes `msg` to `stderr`, displays usage
    information, and exits.
    """
    print >> sys.stderr, '\nERROR: %s\n' % msg
    usage()

def main(args=None):
    import getopt

    if args is None:
        args = sys.argv[1:]

    try:
        opts,args = getopt.getopt(args, "hp:d:w:", ["help","pause","delay","window"])
    except getopt.GetoptError:
        usage()

    pause=0
    delay=0
    windowTitle=None

    for o, a in opts:
        if o in ('-h','--help'):
            usage()
        elif o in ('-w','--window'):
            windowTitle = a
        elif o in ('-p','--pause'):
            try:
                pause = float(a)
                assert pause >= 0
            except (ValueError,AssertionError):
                error('`pause` must be >= 0.0')
        elif o in ('-d','--delay'):
            try:
                delay = float(a)
                assert delay >= 0
            except (ValueError,AssertionError):
                error('`delay` must be >= 0.0')

    time.sleep(delay)
    window = FindConsole(windowTitle)
    for a in args:
        SendKeysToWindow(window, a)

if __name__ == '__main__':
    main(sys.argv[1:])

# :indentSize=4:lineSeparator=\r\n:maxLineLen=80:noTabs=true:tabSize=4: