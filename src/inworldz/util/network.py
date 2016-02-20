import os
import sys
import socket
import win32com.client

from inworldz.win32.Registry import RegistryDict, _winreg


INetFwMgr = win32com.client.Dispatch('HNetCfg.FwMgr')

NET_FW_ACTION_BLOCK = 0
NET_FW_ACTION_ALLOW = 1
NET_FW_ACTION_MAX = 2

NET_FW_RULE_DIR_IN = 1
NET_FW_RULE_DIR_OUT = 2
NET_FW_RULE_DIR_MAX = 3

NET_FW_IP_PROTOCOL_TCP = 6
NET_FW_IP_PROTOCOL_UDP = 17
NET_FW_IP_PROTOCOL_ANY = 256

NET_FW_SCOPE_ALL = 0
NET_FW_SCOPE_LOCAL_SUBNET = 1
NET_FW_SCOPE_CUSTOM = 2
NET_FW_SCOPE_MAX = 3

NET_FW_IP_VERSION_V4 = 0
NET_FW_IP_VERSION_V6 = 1
NET_FW_IP_VERSION_ANY = 2
NET_FW_IP_VERSION_MAX = 3


def AuthorizeProgram(title, path,  scope, ipver):
    global INetFwMgr

    authapp = win32com.client.Dispatch('HNetCfg.FwAuthorizedApplication')
    authapp.Name = title;
    authapp.ProcessImageFileName = path;
    authapp.Scope = scope;
    authapp.IpVersion = ipver;
    authapp.Enabled = True;

    try:
        INetFwMgr.LocalPolicy.CurrentProfile.AuthorizedApplications.Add(authapp)
    except Exception, e:
        print "Failed to add an Authorized Application to the Firewall:", e
        return False
    else:
        return True


def FWOpenSubnet(name, subNet):
    global INetFwMgr

    firewallRule = win32com.client.Dispatch('HNetCfg.FWRule')

    firewallRule.Enabled = True;
    firewallRule.Action = NET_FW_ACTION_ALLOW;
    firewallRule.Description = "Opens all ports on the subnet";
    firewallRule.Direction = NET_FW_RULE_DIR_IN;
    firewallRule.InterfaceTypes = "All";
    firewallRule.Name = name;
    firewallRule.RemoteAddresses = subNet;

    firewallPolicy = win32com.client.Dispatch('HNetCfg.FWPolicy2')

    try:
        firewallPolicy.Rules.Add(firewallRule); 
    except Exception, e:
        print "Failed to open a subnet to the Firewall:", e
        return False
    else:
        return True


def FWOpenPort(name, port, proto, scope, ipver):
    global INetFwMgr

    openPort = win32com.client.Dispatch('HNetCfg.FwOpenPort')

    openPort.Enabled = True;
    openPort.IpVersion = ipver;
    openPort.Name = name;
    openPort.Port = port;
    openPort.Protocol = proto;
    openPort.Scope = scope;

    try:
        INetFwMgr.LocalPolicy.CurrentProfile.GloballyOpenPorts.Add(openPort);
    except Exception, e:
        print "Failed to add a Globally Open Port to the firewall:", e
        return False
    else:
        return True


def OpenPort(proto, port):
    if (proto == "tcp"):
        return FWOpenPort("Provtool TCP {0}".format(port), port,
                NET_FW_IP_PROTOCOL_TCP, NET_FW_SCOPE_ALL, NET_FW_IP_VERSION_ANY)
    elif (proto == "udp"):
        return FWOpenPort("Provtool UDP {0}".format(port), port,
                NET_FW_IP_PROTOCOL_UDP, NET_FW_SCOPE_ALL, NET_FW_IP_VERSION_ANY)
    else:
        print "OpenPort: Invalid protocol/port specified {0} {1}".format(proto, port)
        return False


def TCPTweaks():
    """ This is the LocalMachine registry key containing the TCP/IP parameters """
    TcpIpParamsKey = "System\CurrentControlSet\Services\Tcpip\Parameters"

    """ Value for adjusting the maximum port assigned to client connections. """
    maxPort = 32768;

    """ Value for adjusting the time a closed socket remains in the TIME_WAIT state. """
    waitDelay = 60;

    reg = RegistryDict(_winreg.HKEY_LOCAL_MACHINE, TcpIpParamsKey, flags=None)

    try:
        reg["MaxUserPort"] = maxPort
        reg["TCPTimedWaitDelay"] = waitDelay
    except Exception, e:
        print "Exception setting TCP registry settings", e
        return


def OpenAllFirewallPorts(
        maxRegionSlots=16, 
        startingUdpPort=9020, 
        startingHttpPort=9500, 
        backendSubnet="10.0.0.0/20"):
    print "Opening TCP port {0} on firewall (Aperture)".format(8000)
    FWOpenPort("Aperture", 8000, NET_FW_IP_PROTOCOL_TCP, NET_FW_SCOPE_ALL, NET_FW_IP_VERSION_ANY);

    for i in range(maxRegionSlots):
        print "Opening UDP port {0} on firewall".format(startingUdpPort + i);
        FWOpenPort("OpenSim UDP {0}".format(i), startingUdpPort + i, 
                   NET_FW_IP_PROTOCOL_UDP, NET_FW_SCOPE_ALL, NET_FW_IP_VERSION_ANY)

        print "Opening TCP port {0} on firewall".format(startingHttpPort + i)
        FWOpenPort("OpenSim TCP {0}".format(i), startingHttpPort + i,
                   NET_FW_IP_PROTOCOL_TCP, NET_FW_SCOPE_ALL, NET_FW_IP_VERSION_ANY)

    FWOpenSubnet("Backend Subnet", backendSubnet);


def GetOpenPorts():
    global INetFwMgr

    policy = INetFwMgr.LocalPolicy.CurrentProfile
    ports = policy.GloballyOpenPorts
    values = []

    for objPort in ports:
        values.append({
            "Name "             : objPort.Name,
            "Port"              : objPort.Port,
            "IpVersion"         : objPort.IpVersion,
            "Protocol"          : objPort.Protocol,
            "Scope"             : objPort.Scope,
            "RemoteAddresses"   : objPort.RemoteAddresses,
            "Enabled"           : objPort.Enabled,
            "BuiltIn"           : objPort.BuiltIn
            })

    return values

def GetAuthorizedApplications():
    global INetFwMgr

    apps = INetFwMgr.LocalPolicy.CurrentProfile.AuthorizedApplications
    values = []

    for app in apps:
        values.append({
            "Name"                  : app.Name, 
            "ProcessImageFileName"  : app.ProcessImageFileName
            })

    return values


class NatEntry(object):
    publicIp = None
    privateIp = None
    netMask = None
    
    def __init__(self, publicIp=None, privateIp=None, netMask=None):
        self.publicIp = publicIp
        self.privateIp = privateIp
        self.netMask = netMask

    def GetResultantIPs(self):
        # to determine the resultant IPs, we take the netmask and determine
        # how many bits are remaining for the host portion. Using this, we 
        # then begin counting upwards until we have exhausted the maximum
        # number of hosts that the host portion allows

        # this only works for /24 blocks and smaller
        hostCount = 256 - int(self.netMask.split('.')[3])
        privateIpParts = self.privateIp.split('.')
        publicIpParts = self.publicIp.split('.')

        currInside = int(privateIpParts[3])
        currOutside = int(publicIpParts[3])

        addressmap = {}
        for i in range(0, hostCount):
            if ((currInside > 255) or (currOutside > 255)):
                break;
            private = privateIpParts[0] + "." + privateIpParts[1] + "." + privateIpParts[2] + "." + str(currInside)
            public = publicIpParts[0] + "." + publicIpParts[1] + "." + publicIpParts[2] + "." + str(currOutside)
            currInside += 1
            currOutside += 1
            addressmap[private] = public
            
        return addressmap

class StaticNatFile(object):

    _ipMap = {}
    _revMap = {}
    
    def __init__(self, filename):
        self.filename = filename

    def ExtractMappingsFromFile(self):
        try:
            fileStream = open(self.filename, 'r')
        except IOError as e:
            import errno
            if e.errno == errno.EACCES:
                return
            # Not a permission error.
            raise
       
        natEntries = []        
        for line in fileStream:
            # 0            1               2           3           4           5
            #static (inside,outside) 198.61.240.123 10.0.0.123 netmask 255.255.255.255[ dns] 
            parts = line.split(" ")
            natEntry = NatEntry(parts[2], parts[3], parts[5])
            natEntries.append(natEntry)
            
        for natEntry in natEntries:
            mappings = natEntry.GetResultantIPs()
            for key in mappings:
                self._ipMap[key] = mappings[key]
                self._revMap[mappings[key]] = key


    def GetPublicIp(self, privateIp):
        return self._ipMap[privateIp] if privateIp in self._ipMap else None

    def GetPrivateIp(self, publicIp):
        return self._revMap[publicIp] if publicIp in self._revMap else None


def IsLocal(address):
    if address == None:
        raise ValueError("IsLocal: Null Address Argument")
        
    addr = address.split(".")
    if ((int(addr[0]) == 10) or
        ((int(addr[0]) == 192) and (int(addr[1]) == 168)) or
        ((int(addr[0]) == 169) and (int(addr[1]) == 254)) or
        ((int(addr[0]) == 172) and (int(addr[2]) == 16) and (int(addr[3]) == 31))):
        return True
    else:
        return False

def GetPrivateIP():
    (hostname, aliaslist, ipaddrlist) = socket.gethostbyname_ex(socket.gethostname())
    for address in ipaddrlist:
        # Don't return and IPv6 address if we get one (shouldn't happen)
        if (IsLocal(address) and not ":" in address):
            return address
    # Nothing found we can use
    return None

def GetPrivateIPs():
    '''
    Returns a list of all private IPs associated with this host
    '''
    privateIps = []
    (hostname, aliaslist, ipaddrlist) = socket.gethostbyname_ex(socket.gethostname())
    for address in ipaddrlist:
        # Don't return and IPv6 address if we get one (shouldn't happen)
        if (IsLocal(address) and not ":" in address):
            privateIps.append(address)
            
    # Nothing found we can use
    return privateIps

def GetPublicIP():
    (hostname, aliaslist, ipaddrlist) = socket.gethostbyname_ex(socket.gethostname())
    for address in ipaddrlist:
        # Don't return an IPv6 address if we get one (shouldn't happen)
        if (not IsLocal(address) and not ":" in address):
            return address
    # Nothing found we can use
    return None

def GetPublicIPFromPrivate(natmapping, priv):
    natFile = StaticNatFile(natmapping)
    natFile.ExtractMappingsFromFile()
    return natFile.GetPublicIp(priv)

def GetPrivateIPFromPublic(natmapping, pub):
    natFile = StaticNatFile(natmapping)
    natFile.ExtractMappingsFromFile()
    return natFile.GetPrivateIp(pub)

def TryGetPublicIpFromNatFile(natmapping):
    natFile = StaticNatFile(natmapping)
    natFile.ExtractMappingsFromFile()
    privateIp = GetPrivateIP()
    return natFile.GetPublicIp(privateIp)

if __name__ == "__main__":
    print "Private IP is ",GetPrivateIP()
    print "Public IP is ", GetPublicIP()
    natFile = StaticNatFile("natmapping.txt")
    natFile.ExtractMappingsFromFile()
    print natFile._ipMap
    print natFile._revMap
    print natFile._ipMap["10.0.5.2"]