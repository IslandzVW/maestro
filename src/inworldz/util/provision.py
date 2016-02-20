import os.path
import fnmatch
import psutil
import glob

from ConfigParser import SafeConfigParser

import inworldz.util.properties as DefaultProperties
from inworldz.util.filesystem import strip_suffix

import xml.etree.ElementTree as ET
from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateError
from distutils.dir_util import copy_tree

# ------------------------------------------------------------------------------
# Manage slots and slot directories
# ------------------------------------------------------------------------------
            
def GetMaxRegionSlots():
    global maxRegionSlots
    try:
        maxRegionSlots
    except:
        maxRegionSlots = DefaultProperties.instance().getInteger("max_region_slots")
    return maxRegionSlots


def GetSlotBaseDir():
    global slotBaseDir
    try:
        slotBaseDir
    except:
        slotBaseDir = DefaultProperties.instance().getValue("basedir")
    return slotBaseDir

def GetServiceBaseDir():
    global serviceBaseDir
    try:
        serviceBaseDir
    except:
        baseDir = GetSlotBaseDir()
        serviceBaseDir = os.path.join(baseDir, "GridServices")
    return serviceBaseDir

def GetSlotDirectory(slotnum):
    global regionLeafBase
    try:
        regionLeafBase
    except:
        regionLeafBase = DefaultProperties.instance().getValue("region_leaf_base")
    # Calculate the base directory
    if ((slotnum < 0) or (slotnum > GetMaxRegionSlots())):
        raise Exception("GetSlotDirectory: Invalid Slot specified - {0}".format(slotnum))
    elif (slotnum == 0):
        return (os.path.join(GetSlotBaseDir(), regionLeafBase))
    else:
        return (os.path.join(GetSlotBaseDir(), regionLeafBase + " - " + str(slotnum)))                

def IsSlotProvisioned(slotnum):
    slotDirectory  = GetSlotDirectory(slotnum)
    regionDir = os.path.join(slotDirectory, "bin", "Regions")
    files = glob.glob(os.path.join(regionDir, "*.xml"))
    return (len(files) > 0)
    
def IsSlotFree(slotnum):
    return (IsSlotProvisioned(slotnum) == False)

def GetSlotConfiguration(slotnum):
    """ Return all of the configurations we find in this slot.  Can be more 
        than one.  We use this on startup to build the regions list. """
    slotDirectory  = GetSlotDirectory(slotnum)
    regionDir = os.path.join(slotDirectory, "bin", "Regions")
    configFiles = glob.glob(os.path.join(regionDir,"*.xml"))
    result = {}
    for config in configFiles:
        if (os.access(config, os.O_RDONLY) == False):
            continue
        tree = ET.parse(config)
        root = tree.getroot()
        record = {}
        for child in root.iter('Config'):
            for entry in child.attrib:
                record[str.lower(entry)] = child.attrib[entry]
        sim_uuid = record['sim_uuid']
        result[sim_uuid] = record
    return result


def _findRegionProcess(slotnum):
    bindir = os.path.join(GetSlotDirectory(slotnum), "bin")
    for p in psutil.process_iter():
        if (len(p.cmdline()) <= 0):
            continue
        cmdline = p.cmdline()[0]
        if ((os.path.dirname(cmdline) == bindir) and
            (os.path.basename(cmdline) == "OpenSim.exe")):
            return (p)
    return None

def _findServiceProcess(servicename):
    bindir = os.path.join(GetServiceBaseDir(), "bin")
    for p in psutil.process_iter():
        if (len(p.cmdline()) <= 0):
            continue
        cmdline = p.cmdline()[0]
        if ((os.path.dirname(cmdline) == bindir) and
            (os.path.basename(cmdline) == servicename)):
            return (p)
    return None
        
def _findRevision(path, revision):
    # Install whatever they send us.
    curdir = os.path.realpath(os.path.join(path, "R"+str(revision)))      
    if (not (curdir and os.path.isdir(curdir))):
        return(None)
    else:
        return (curdir)
    

def _findLatestRevision(path):
    result = None
    # only revs that are RNNNNN will be considered
    dirs = fnmatch.filter(os.listdir(path), "R*[0-9]")      
    for curdir in dirs:
        curpath = os.path.join(path, curdir)
        if (not os.path.isdir(curpath)):
            continue
        if not result:
            result = curdir
        elif int(result[1:]) < int(curdir[1:]):
            result = curdir
            
    # return what we found
    if (result):
        return (os.path.join(path, result))  
    else:
        return None

def _copyTemplate(sourceBase, destination):
    """ Copy the Revision at revPath to destination, symlinks are expanded and
        we handle any files to ignore here as well """
    source = os.path.normpath(os.path.join(sourceBase, "_New_Region", "Template"))
    copy_tree(source, destination, preserve_mode=1, preserve_times=1, preserve_symlinks=1)
        
def _copyRevision(revPath, destination, ignore=None):
    """ Copy the Revision at revPath to destination, symlinks are expanded and
        we handle any files to ignore here as well """
    source = os.path.normpath(revPath)
    copy_tree(source, destination, preserve_mode=1, preserve_times=1, preserve_symlinks=1)

def _prepForUpdate(destdir):
    if (not os.path.exists(destdir)):
        os.makedirs(destdir)
    names = [".exe", ".dll", ".pdb", ".log"]
    for (path, subdirs, files) in os.walk(destdir):
        for filename in files:
            (name, ext) = os.path.splitext(filename)
            if ext in names:
                os.remove(os.path.join(path, filename))
                
def GetRevisions(basedir):
    path = os.path.join(basedir, "Grid")
    revisions = []
    dirs = fnmatch.filter(os.listdir(path), "R*[0-9]")         
    for curdir in dirs:
        curpath = os.path.join(path, curdir)
        if (not os.path.isdir(curpath)):
            continue
        revisions.append(curdir)
    return (revisions)

def ProvisionFromLatest(source, destBase):
    revision = _findLatestRevision(os.path.join(source, "Grid"))
    destination = os.path.normpath(os.path.join(destBase, "bin"))    
    if (revision):
        _copyTemplate(source, destination)
        _prepForUpdate(destination)
        _copyRevision(revision, destination)
        return True
    else:
        return False


def ProvisionFromRevision(source, destBase, rev):
    revision = _findRevision(os.path.join(source, "Grid"), rev)
    destination = os.path.normpath(os.path.join(destBase, "bin"))
    if revision:
        _copyTemplate(source, destination)
        _prepForUpdate(destination)
        _copyRevision(revision, destination)
        return True
    else:
        return False

""" Load the configuration file named filename and use settings from "section".  
    default values come from "vars".  Returns the dictionary of values. """
def GetConfiguration(templateBasedir, filename, section, vars):
    filename = os.path.join(templateBasedir, filename)
    
    configParser = SafeConfigParser(vars)
    if (os.path.exists(filename)):
        configParser.read(filename)
    replacements={}
    for key in vars.keys():
        replacements[str(key)] = str(vars[key])
    if (configParser.has_section(section)):
        return dict(configParser.items(section, False, replacements))
    else:
        return (replacements)

 
def ReconfigureRegion(templateBaseDir, regionDir, fileName, keys):
    regionTemplateDir = os.path.join(templateBaseDir, "region")
    if (not os.path.isdir(regionTemplateDir)):
        raise Exception("Region Template Directory " + regionTemplateDir + " doesn't exist")
    
    """ Update the Region Configuration First """
    # Write the new Region Config, We dont handle more than one region.xml
    configFiles = glob.glob(os.path.join(regionDir,"*.xml"))
    for path in configFiles:
        os.remove(path)

    regionEnvironment = Environment(loader=FileSystemLoader(regionTemplateDir))
    template=regionEnvironment.get_template("region-default.xml")
    config = template.render(keys)
    configFile = open(os.path.join(regionDir,fileName), "w")
    configFile.write(config)
    configFile.close()


def ReconfigureSimulator(templateBaseDir, regionBinDir, keys):     
    configTemplateDir = os.path.join(templateBaseDir, "configs")
    if (not os.path.isdir(configTemplateDir)):
        raise Exception("Simulator Configuration Template Directory " + configTemplateDir + " doesn't exist")
    
    """ Now do the Simulator Configuration Files """
    configEnvironment = Environment(loader=FileSystemLoader(configTemplateDir))
    templates = configEnvironment.list_templates(".tmpl")
    for template in templates: 
        try:
            template_object = configEnvironment.get_template(template)
            config = template_object.render(keys)            
            filename = strip_suffix(template, ".tmpl")
            configFile = open(os.path.join(regionBinDir, filename), "w")
            configFile.write(config)
            configFile.close()
        except TemplateError, e:
            print e, " processing ", template
            pass
            
                
# basedir = os.path.join(props.BaseDir, props.RegionLeafBase)
# regionSlot = RegionSlotInfo.FindOrCreateRegionSlot(basedir)    
# AssignValuesFromLocalNode(regionInfo, regionSlot)                # replace invalid entries in the region info with the correct slot data
#     
# # get region to latest revision for binaries, unless this is the primary
# # region slot and it already has files. In this case, services are already
# # running from the folder and we need to use the files already in place
# # which should be up to date
# BuildAndUpdateNonServiceSlot(regionSlot)
# AssignBestRdbHost(props.getCoreDbConfig(), regionInfo)
# UpdateSlotConfiguration(regionSlot, regionInfo)                 # build out general configuration
# regionsDir = os.path.join(regionSlot.SlotDir, "Regions")
# regionInfo.GenerateConfigFile(regionsDir)                       # set region configuration
# ConfigureNewRegionEstate(regionInfo)                            # set up estate




# def DoCopyVM(ip, user, adminPassword):
    # SHARE_BASE = "\\\\{0}\\c$"
    # USER_DESKTOP_DIR_BASE = "\\Users\\{0}\\Desktop"
    # share = SHARE_BASE.format(ip)
    # desktop = USER_DESKTOP_DIR_BASE.format(user)
#     
    # fullRemotePath = os.path.join(share, desktop)
    # filesystem.ConnectUNCShare(share, "Administrator", adminPassword);
#  
    # subdirs = [name for name in os.listdir(fullRemotePath) if os.path.isdir(os.path.join(dir, name))]
    # print "Found {0} regions to duplicate".format(len(subdirs))
# 
    # for curdir in subdirs:
        # # read the first xml file in the directory and use that information to spin up a sim
        # topdir = os.path.join(fullRemotePath, curdir)
        # bindir = os.path.join(topdir, "bin")
        # regionFileDir = os.path.join(bindir, "Regions")
#         
        # xmlFiles = [name for name in os.listdir(regionFileDir) if fnmatch.fnmatch(name, '*.xml')]
        # for filename in xmlFiles:
            # regionFile = os.path.join(regionFileDir, filename)
            # regionInfo = RegionInfo()
            # regionInfo.RegionInfoFromXML(regionFile)
# 
            # print "Copying region {0}..".format(regionInfo.SimUuid)
            # slotInfo = MoveGivenRegionHere(regionInfo, regionInfo);
# 
            # # copy script states
            # STATE_FILE_SUBPATH = "bin\\ScriptEngines\\Phlox\\states"
            # STATE_FILE_SUBPATH_NO_BIN = "ScriptEngines\\Phlox\\states"
            # stateFile = os.path.join(os.path.join(fullRemotePath, STATE_FILE_SUBPATH), "script_states.db3")
# 
            # print "About to look for script states in {0}".format(stateFile)
# 
            # if os.path.exists(stateFile):
                # state_dir = os.path.join(slotInfo.SlotDir, STATE_FILE_SUBPATH_NO_BIN)
                # if (not os.path.exists(state_dir)):
                    # os.mkdir(state_dir)
                # shutil.copy(stateFile, state_dir)
# 
# 
# def ProvisionSingleRegionFromXMLFileData(sourceRegion):
    # props = DefaultProperties.instance()
    # dbconfig = props.getCoreDbConfig()
    # rdbHost = GetRdbHost(dbconfig, sourceRegion)
#     
    # if (rdbHost != None):
        # print "RDB server {0} found for {1}".format(rdbHost, sourceRegion.SimUuid)
    # else:
        # # no info? that's ok in this case we assign
        # print "RDB server not assigned for {0}, allocating new slot".format(sourceRegion.SimUuid)
        # AssignBestRdbHost(dbconfig, sourceRegion)
#     
    # # XXX Check this.
    # basedir = os.path.join(props.getValue('BaseDir'), props.getValue('RegionLeafBase'))
    # regionSlot = RegionSlotInfo.FindOrCreateRegionSlot(basedir) 
    # AssignValuesFromLocalNode(sourceRegion, regionSlot)             # replace invalid entries in the region info
    # BuildSlotFromTemplate(regionSlot)                               # get region to latest revision for binaries
    # UpdateRegionToLatest(regionSlot)
    # UpdateSlotConfiguration(regionSlot, sourceRegion)               # build out general configuration
    # regionDir = os.path.join(regionSlot.SlotDir, "Regions")
    # sourceRegion.RegionInfoToXML(regionDir)                         # set region configuration
# 
# 
# def BuildAndUpdateNonServiceSlot(regionSlotInfo):
    # if ((regionSlotInfo.SlotIndex != 0) and regionSlotInfo.DirIsEmpty()):
        # BuildSlotFromTemplate(regionSlotInfo)
        # UpdateRegionToLatest(regionSlotInfo);
# 
# 
# def MoveRegionHere(sourceRegionId):
    # # find the region info in the database
    # sourceRegion = RegionInfo.RegionInfoFromDb(sourceRegionId.sim_uuid);    
    # MoveGivenRegionHere(sourceRegion);
# 
# 
# def MoveGivenRegionHere(sourceRegion):
    # """ Returns RegionSlotInfo """
    # if (sourceRegion == None):
        # raise Exception("Can not move region to this server: Region data not found in DB/file for {0}".format(sourceRegion.sim_uuid))
#     
    # regionSlot = RegionSlotInfo.FindOrCreateRegionSlot()        # Find a Slot to put it in
    # AssignValuesFromLocalNode(sourceRegion, regionSlot)         # replace invalid entries in the region info
    # BuildAndUpdateNonServiceSlot(regionSlot)                    # get region to latest revision for binaries
    # UpdateSlotConfiguration(regionSlot, sourceRegion)           # build out general configuration
    # regionsDir = os.path.join(regionSlot.SlotDir, "Regions")
    # sourceRegion.GenerateConfigFile(regionsDir)                 # set region configuration
    # return regionSlot;
