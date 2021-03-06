#!/usr/bin/env python2.6

# $Id$

import struct

import ipaddr
from option_def import *
from optionset import *
from rpcc import *
from shared_network import *


g_write = AnyGrants(AllowUserWithPriv("write_all_subnetworks"), AdHocSuperuserGuard)
g_read = AnyGrants(g_write, AllowUserWithPriv("read_all_subnetworks"))


class ExtNoSuchSubnetworkError(ExtLookupError):
    desc = "No such subnetwork exists."


class ExtSubnetworkAlreadyExistsError(ExtLookupError):
    desc = "The subnetwork ID is already in use"

    
class ExtSubnetworkOverlapsExisting(ExtValueError):
    desc = "The given subnetwork overlaps an already existing subnetwork"

    
class ExtSubnetworkInUseError(ExtValueError):
    desc = "The subnetwork is referred to by other objects. It cannot be destroyed"  
    
       
class ExtSubnetworkInvalidError(ExtValueError):
    desc = "the subnetwork specifcation is invalid"
    
    
class ExtSubnetworkInUseByDHCPServerError(ExtSubnetworkInUseError):
    desc = "The operation would leave a DHCP server without a defined subnetwork. This is not allowed"
    
    
class ExtSubnetInUseByPoolRanges(ExtSubnetworkInUseError):
    desc = "The operation would leave one or more pool ranges without a defined subnetwork. This is not allowed"


class ExtSubnetworkID(ExtString):
    name = "subnetwork-id"
    desc = "ID of a subnetwork in CIDR notation. [ipaddress/bitcount]"
    regexp = r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/(\d|[1-2]\d|3[0-2]))$"

    def lookup(self, fun, cval):
        (_ip, n) = cval.split("/", 1)
        n = int(n)
        if n < 1 or n > 31:
            raise ExtSubnetworkInvalidError("The bitcount of the subnetwork specification is out of range, should be between 1 and 31")
        return cval


class ExtSubnetworkInfo(ExtOrNull):
    name = "subnetwork-info"
    desc = "Information about a subnetwork"
    typ = ExtString
    
    
class ExtSubnetwork(ExtSubnetworkID):
    name = "subnetwork"
    desc = "A defined subnetwork in CIDR notation. [ipaddress/bitcount]"

    def lookup(self, fun, cval):
        return fun.subnetwork_manager.get_subnetwork(str(cval))

    def output(self, fun, obj):
        return obj.oid
    
    
class SubnetworkFunBase(SessionedFunction):  
    params = [("subnetwork", ExtSubnetwork, "Subnetwork ID")]
    
    
class SubnetworkCreate(SessionedFunction):
    extname = "subnetwork_create"
    params = [("subnetwork", ExtSubnetworkID, "ID of new subnetwork"),
              ("network", ExtNetwork, "Shared network that the subnetwork belongs to"),
              ("info", ExtString, "Subnetwork description")]
    desc = "Creates a subnetwork"
    returns = (ExtNull)

    def do(self):
        self.subnetwork_manager.create_subnetwork(self, self.subnetwork, self.network.oid, self.info)
        

class SubnetworkDestroy(SubnetworkFunBase):
    extname = "subnetwork_destroy"
    desc = "Destroys a subnetwork"
    returns = (ExtNull)

    def do(self):
        self.subnetwork_manager.destroy_subnetwork(self, self.subnetwork)
        
        
class SubnetworkOptionsUpdate(SubnetworkFunBase):
    extname = "subnetwork_option_update"
    desc = "Update option value(s) on a subnetwork"
    returns = (ExtNull)
    
    @classmethod
    def get_parameters(cls):
        pars = super(SubnetworkOptionsUpdate, cls).get_parameters()
        ptype = Optionset._update_type(0)
        ptype.name = "subnetwork-" + ptype.name
        pars.append(("updates", ptype, "Fields and updates"))
        return pars
    
    def do(self):
        self.subnetwork_manager.update_options(self, self.subnetwork, self.updates)
            
            
class Subnetwork(AdHocModel):
    name = "subnetwork"
    exttype = ExtSubnetwork
    id_type = str

    def init(self, *args, **kwargs):
        a = list(args)
        self.oid = a.pop(0)
        self.network = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)
        self.optionset = a.pop(0)

    @template("subnetwork", ExtSubnetwork, desc="The subnetwork")
    @entry(g_read)
    def get_subnetwork(self):
        return self

    @template("network", ExtNetworkName, desc="Which shared network the subnetwork belongs to")
    @entry(g_read)
    def get_network(self):
        return self.network
    
    @template("netmask", ExtIpV4Address, desc="The netmask corresponding to bit count of the subnetwork")
    @entry(g_read)
    def get_netmask(self):
        (_ip, n) = self.oid.split('/', 1)
        bits = 0xffffffff ^ (1 << 32 - n) - 1
        return socket.inet_ntoa(struct.pack('>I', bits))
    
    @template("start_ip", ExtIpV4Address, desc="The start IP address of the subnetwork")
    @entry(g_read)
    def get_start_ip(self):
        (ip, _n) = self.oid.split('/', 1)
        return ip
    
    @template("size", ExtInteger, desc="The number of IP addresses covered by the subnetwork")
    @entry(g_read)
    def get_size(self):
        (_ip, n) = self.oid.split('/', 1)
        n = int(n)
        self.logger.debug("Subnetwork get_size: n=%s, _ip=%s" % (str(n), str(_ip)))
        if n >= 32:
            return 0
        return (1 << 32 - n)
        
    @template("info", ExtString, desc="Subnetwork description")
    @entry(g_read)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime, desc="Time of last change")
    @entry(g_read)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString, desc="User who did the last change")
    @entry(g_read)
    def get_changed_by(self):
        return self.changed_by
    
    @template("options", ExtOptionKeyList, desc="List of options defined for this subnetwork")
    @entry(g_read)
    def list_options(self):
        return self.get_optionset().list_options()
    
    @template("optionset", ExtOptionset, model=Optionset)
    @entry(g_read)
    def get_optionset(self):
        return self.optionset_manager.get_optionset(self.optionset)
    
    @update("subnetwork", ExtSubnetworkID)
    @entry(g_write)
    def set_id(self, value):
        """ Changing the ID means changing the range of IP addresses for the subnetwork.
                This may result in two bad things. A subnetwork overlap or that we leave
                one or more of our DHCP servers in the cold"""
        self.manager.checkoverlap(value, self.oid)
        if self.manager.dhcp_servers(self.oid) != self.manager.dhcp_servers(value):
                    raise ExtSubnetworkInUseByDHCPServerError()
        
        # Check which pool ranges we are hosting
        n1 = ipaddr.IPv4Network(self.oid)
        current_pool_ranges = self.pool_range_manager.getoverlaps(str(n1.network), str(n1.broadcast))
        
        n2 = ipaddr.IPv4Network(value)
        future_pool_ranges = self.pool_range_manager.getoverlaps(str(n2.network), str(n2.broadcast))
        
        if cmp(current_pool_ranges, future_pool_ranges) != 0:
            raise ExtSubnetInUseByPoolRanges()
        
        for range in current_pool_ranges:
            if ipaddr.IPv4Address(range[0]) not in n2 or ipaddr.IPAddress(range[1]) not in n2:
                raise ExtSubnetInUseByPoolRanges("The pool range (%s, %s) will not fit within the redefined subnetwork" % range)
                
        q = "UPDATE subnetworks SET id=:value WHERE id=:id"
        self.db.put(q, id=self.oid, value=value)
        self.manager.rename_object(self, value)
        self.event_manager.add("rename", subnetwork=self.oid, newstr=value, authuser=self.function.session.authuser)
        
    @update("network", ExtNetworkName)
    @entry(g_write)
    def set_network(self, value):
        q = "UPDATE subnetworks SET network=:value WHERE id=:id"
        self.db.put(q, id=self.oid, value=value)
        self.event_manager.add("update", subnetwork=self.oid, network=value, authuser=self.function.session.authuser)
              
    @update("info", ExtSubnetworkInfo)
    @entry(g_write)
    def set_info(self, value):
        q = "UPDATE subnetworks SET info=:value WHERE id=:id"
        self.db.put(q, id=self.oid, value=value)
        self.event_manager.add("update", subnetwork=self.oid, info=value, authuser=self.function.session.authuser)


class IPV4Match(Match):
    @suffix("covers", ExtIpV4Address)
    def covers(self, fun, q, expr, val):
        q1 = "INET_ATON("
        q1 += q.var(val)
        q1 += ") >= INET_ATON(SUBSTRING_INDEX(id,'/',1)) AND INET_ATON("
        q1 += q.var(val)
        q1 += ") <= INET_ATON(SUBSTRING_INDEX(id,'/',1)) + ((1 << (32 - CONVERT(SUBSTRING_INDEX(id,'/',-1), UNSIGNED) ))-1)"
        q.where(q1)

        
class SubnetworkManager(AdHocManager):
    name = "subnetwork_manager"
    manages = Subnetwork

    model_lookup_error = ExtNoSuchSubnetworkError
    
    def init(self):
        self._model_cache = {}
        
    @classmethod
    def base_query(cls, dq):
        dq.table("subnetworks nw")
        dq.select("nw.id", "nw.network", "nw.info", "nw.mtime", "nw.changed_by", "nw.optionset")
        return dq

    def get_subnetwork(self, id):
        return self.model(id)

    def search_select(self, dq):
        dq.table("subnetworks nw")
        dq.select("nw.id")

    @search("subnetwork", StringMatch)
    def s_snet(self, dq):
        dq.table("subnetworks nw")
        return "nw.id"
    
    @search("subnetwork", IPV4Match, desc="Subnetworks covering a given IP address")
    def s_anet(self, dq):
        dq.table("subnetworks nw")
        return "nw.id"
    
    @search("network", NullableStringMatch)
    def s_net(self, dq):
        dq.table("subnetworks nw")
        return "nw.network"
    
    @search("info", NullableStringMatch)
    def s_info(self, dq):
        dq.table("subnetworks nw")
        return "nw.info"
    
    @entry(g_write)
    def create_subnetwork(self, fun, id, network, info):
        
        optionset = self.optionset_manager.create_optionset(fun)
        
        self.checkoverlap(id)
        
        q = """INSERT INTO subnetworks (id, network, info, changed_by, optionset) 
               VALUES (:id, :network, :info, :changed_by, :optionset)"""
        try:
            self.db.put(q, id=id, network=network, info=info, 
                        changed_by=fun.session.authuser, optionset=optionset)
        except IntegrityError:
            raise ExtSubnetworkAlreadyExistsError()
        self.event_manager.add("create", subnetwork=id, parent_object=network, info=info, 
                               authuser=fun.session.authuser, optionset=optionset)
        
    @entry(g_write)
    def destroy_subnetwork(self, fun, subnetwork):
        self.approve_config = True
        
        if self.dhcp_servers(subnetwork.oid):
            raise ExtSubnetworkInUseByDHCPServerError()
        
        subnetwork.get_optionset().destroy()
        
        try:
            q = "DELETE FROM subnetworks WHERE id=:id LIMIT 1"
            self.db.put(q, id=subnetwork.oid)
        except IntegrityError:
            raise ExtSubnetworkInUseError()
        
        self.event_manager.add("destroy", subnetwork=subnetwork.oid, authuser=fun.session.authuser)
        
        # print "Subnetwork destroyed, id=", id
     
    def checkoverlap(self, cidr, from_cidr=None):
        """ Check if the given CIDR overlaps any of the existing subnetworks"""
        try:
            n1 = ipaddr.IPNetwork(cidr, strict=True)
        except ValueError, e:
            raise ExtSubnetworkInvalidError("The subnetwork CIDR is invalid: %s " % str(e))
        #print "n1=",cidr
        
        for row in self.db.get("SELECT id FROM subnetworks"):
            #print "n2=", row[0]
            if from_cidr and from_cidr == row[0]:  # This allows an existing subnetwork to be changed
                continue
            n2 = ipaddr.IPNetwork(row[0])
            if n1.overlaps(n2) or n2.overlaps(n1):
                raise ExtSubnetworkOverlapsExisting()
            
    def dhcp_servers(self, cidr): 
        """ Return the set of dhcp servers contained within the cidr"""
        nw = ipaddr.IPNetwork(cidr)   
        q = """SELECT name FROM dhcp_servers"""
        
        servers = set()
        
        for row in self.db.get(q):
            dhcp_server_name = row[0]
            try:
                dhcp_server_ip = socket.gethostbyname(dhcp_server_name)
            except socket.gaierror:
                continue
            if nw.Contains(ipaddr.IPv4Address(dhcp_server_ip)):
                servers.add(dhcp_server_name)
                
        return servers
    
    def rename_object(self, obj, new_name):
        self.approve_config = True
        oid = obj.oid
        obj.oid = new_name
        del(self._model_cache[oid])
        self._model_cache[new_name] = obj
                     
    @entry(g_write)
    def update_options(self, fun, subnetwork, updates):
        
        # print "Subnetwork update, subnetwork==",subnetwork, "updates=", updates
        omgr = fun.optionset_manager
        optionset = omgr.get_optionset(subnetwork.optionset)
            
        for (key, value) in updates.iteritems():
            optionset.set_option_by_name(key, value)
            self.event_manager.add("update", subnetwork=subnetwork.oid, option=key, option_value=unicode(value), authuser=fun.session.authuser)
