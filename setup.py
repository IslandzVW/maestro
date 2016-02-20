# ...
# ModuleFinder can't handle runtime changes to __path__, but win32com uses them
# This works around our use of the win32com.shell call so that we find the needed modules.

try:
    # py2exe 0.6.4 introduced a replacement modulefinder.
    # This means we have to add package paths there, not to the built-in
    # one.  If this new modulefinder gets integrated into Python, then
    # we might be able to revert this some day.
    # if this doesn't work, try import modulefinder
    try:
        import py2exe.mf as modulefinder
    except ImportError:
        import modulefinder
    import win32com, sys
    for p in win32com.__path__[1:]:
        modulefinder.AddPackagePath("win32com", p)
    for extra in ["win32com.shell"]: #,"win32com.mapi"
        __import__(extra)
        m = sys.modules[extra]
        for p in m.__path__[1:]:
            modulefinder.AddPackagePath(extra, p)
except ImportError:
    # no build path setup, no worries.
    pass

import os, sys, time
import glob, fnmatch
from distutils.core import setup
import py2exe

from distutils.cmd import Command
from distutils.command.clean import clean
from distutils.sysconfig import get_python_lib, PREFIX

# If we are run without args build executables in quiet mode
if (len(sys.argv) == 1):
    sys.argv.append("py2exe")
    sys.argv.append("-q")


def opj(*args):

    path = os.path.join(*args)

    return os.path.normpath(path)


def find_data_files(srcdir, *wildcards, **kw):
    # get a list of all files under the srcdir matching wildcards,
    # returned in a format to be used for install_data
    def walk_helper(arg, dirname, files):
        if '.svn' in dirname:
            return
        names = []
        lst, wildcards, emptydir = arg
        for wc in wildcards:
            wc_name = opj(dirname, wc)
            for f in files:
                filename = opj(dirname, f)

                if fnmatch.fnmatch(filename, wc_name) and not os.path.isdir(filename):
                    names.append(filename)

        if names:
            lst.append( (dirname, names ) )
        elif emptydir:
            lst.append( (dirname, []) )

    file_list = []
    recursive = kw.get('recursive', True)
    emptydir = kw.get('include_empty_dir', False)
    if recursive:
        os.path.walk(srcdir, walk_helper, (file_list, wildcards, emptydir))
    else:
        walk_helper((file_list, wildcards, emptydir),
                    srcdir,
                    [os.path.basename(f) for f in glob.glob(opj(srcdir, '*'))])
        
    return file_list


def find_special_dlls(dlls, recursive=False):
    ret = []
    # Technically, we should search the entire path, but the files we
    # want are installed in the python install directory (where python.exe
    # lives).  So, for now, just search that directory.
    #dirs = [os.path.dirname(sys.executable)] + os.getenv('PATH').split(os.pathsep)
    dirs = [os.path.dirname(sys.executable)]
    for d in dirs:
        files = find_data_files(d, *dlls, recursive=recursive)
        for xdir, flist in files:
            for f in flist:
                if f not in ret:
                    ret.append(f)

    return ret


maestro_version = \
    os.path.join(os.path.abspath(os.path.dirname(__file__)), 'src', 'inworldz', 'maestro', 'version.py')

maestro_reqs = \
    os.path.join(os.path.abspath(os.path.dirname(__file__)), 'requirements.txt')

exec(compile(open(maestro_version).read(), maestro_version, 'exec'))

if 'SYSCONFDIR' in os.environ:
    etc_path = os.environ['SYSCONFDIR']
else:
    etc_path = os.path.join(os.path.dirname(PREFIX), 'etc')

with open(maestro_reqs) as f:
    lines = f.read().split('\n')
    requirements = [line for line in lines if line] 


# explicit includes
# Sometimes the auto module traversal doesn't find everything, so we
# explicitly add it. The auto dependency tracking especially does not work for
# imports occurring in salt.modules, as they are loaded at salt runtime.
# Specifying includes that don't exist doesn't appear to cause a freezing
# error.
includes = [
    'win32api', 'win32file', 'win32con',  'win32com', 'win32com.shell', 'win32net', 'win32netcon',
    'win32gui', 'win32security', 'ntsecuritycon', 'pywintypes', 'pythoncom',
    '_winreg', 'ast', 'difflib', 'distutils', 'distutils.version', 'json',
    'maestro', "mysql", "mysql.connector.locales.eng.client_error",
    ]

# excludes: anything we specifically dont want to pull in
excludes = [
    'pywin', 'pywin.debugger', 'pywin.debugger.dbgcon', 'pywin.dialogs', 
    'pywin.dialogs.list', 'util.soap', 'tcl', 'Tkinter', 'salt'
    ]

# datafiles
datafiles = find_data_files("data", "*")

# The packages in our application
pkgs = [
    'inworldz',
    'inworldz.maestro',
    'inworldz.maestro.environment',
    'inworldz.util',
    'inworldz.win32',
    ]

manifest_template = '''
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity
    version="5.0.0.0"
    processorArchitecture="x86"
    name="%(prog)s"
    type="win32"
/>
<description>%(prog)s Program</description>
<dependency>
    <dependentAssembly>
        <assemblyIdentity 
            type="win32" 
            name="Microsoft.VC90.CRT" 
            version="9.0.21022.8" 
            processorArchitecture="x86" 
            publicKeyToken="1fc8b3b9a1e18e3b"
            language="*"
        />
    </dependentAssembly>
</dependency>
</assembly>
'''

RT_MANIFEST = 24


class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        self.version = __version__
        self.company_name = "InWorldz LLC"
        self.url = "http://www.inworldz.com"
        self.copyright =  "Copyright 2013, All Rights Reserved"
        self.classifiers = [    'Programming Language :: Python',
                                'Programming Language :: Cython',
                                'Programming Language :: Python :: 2.7',
                                'Development Status :: 5 - Production/Stable',
                                'Environment :: Console',
                                'Intended Audience :: Developers',
                                'Intended Audience :: Information Technology',
                                'Intended Audience :: System Administrators',
                                ]
        self.install_requires = requirements
        self.icon=os.path.join(sys.prefix,"DLLs","py.ico"),
        

# The things we produce
server = Target(
    name = "maestro",
    dest_base = "maestro",
    description = "Inworldz Maestro Standalone Server",
    gui_only = False,
    script = opj("src", "server.py"),
    )

shell = Target(
    name = "shell",
    dest_base = "maestro_shell",
    description = "Inworldz Maestro Shell Client",
    gui_only = False,
    script = opj("src", "shell.py"), 
    )

remote_console = Target(
    name = "remote_console",
    dest_base = "remote_console",
    description = "Inworldz Remote Service Console",
    gui_only = False,
    script = opj("src", "console.py"), 
    )

service = Target(
    name = "maestro_service",
    dest_base = "maestro_service",
    description = "InWorldz Maestro Windows Service",
    modules = [ "service" ],
    cmdline_style = "pywin32",
    )

if __name__ == '__main__':
    setup(
        name = "InWorldz.Maestro",
        version = __version__,
        package_dir = { '' : 'src'},
        packages = pkgs,
        data_files = datafiles,
        options = {"py2exe" : {
                        "compressed" : 1,
                        "optimize" : 2,
                        "includes" : includes,
                        "excludes" : excludes}},
        zipfile = "lib/shared.zip",
        service = [service],
        console = [server, shell, remote_console],  
          )