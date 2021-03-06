#!/usr/bin/env python2.6

# $Id$

from option_def import *
from optionset import *
from rpcc.access import *
from rpcc.exttype import *
from rpcc.model import *


g_write = AnyGrants(AllowUserWithPriv("write_all_networks"), AdHocSuperuserGuard)
g_read = AnyGrants(g_write, AllowUserWithPriv("read_all_networks"))


class ExtNoSuchNetworkError(ExtLookupError):
    desc = "No such network exists."
    
    
class ExtNetworkAlreadyExistsError(ExtLookupError):
    desc = "The network name is already in use"
    
    
class ExtNetworkInUseError(ExtValueError):
    desc = "The network is referred to by other objects. It cannot be destroyed"    


class ExtNetworkName(ExtString):
    name = "network-name"
    desc = "Name of a DHCP shared network"
    regexp = "^[A-Za-z0-9_][-A-Za-z0-9_]*$"


class ExtNetworkInfo(ExtOrNull):
    name = "network-info"
    desc = "Information about a network"
    typ = ExtString


class ExtNetwork(ExtNetworkName):
    name = "network"
    desc = "A DHCP shared network"

    def lookup(self, fun, cval):
        return fun.network_manager.get_network(cval)

    def output(self, fun, obj):
        return obj.oid
    
    
class NetworkFunBase(SessionedFunction):  
    params = [("network", ExtNetwork, "Shared network name")]
   

class NetworkCreate(SessionedFunction):
    extname = "network_create"
    params = [("network_name", ExtNetworkName, "Network ID to create"),
              ("authoritative", ExtBoolean, "Whether the DHCP servers should claim to be authoritative for the network or not"),
              ("info", ExtString, "Network description")]
    desc = "Creates a shared network"
    returns = (ExtNull)

    def do(self):
        self.network_manager.create_network(self, self.network_name, self.authoritative, self.info)
        

class NetworkDestroy(NetworkFunBase):
    extname = "network_destroy"
    desc = "Destroys a shared network"
    returns = (ExtNull)

    def do(self):
        self.network_manager.destroy_network(self, self.network)


class NetworkOptionsUpdate(NetworkFunBase):
    extname = "network_option_update"
    desc = "Update option value(s) on a shared network"
    returns = (ExtNull)
    
    @classmethod
    def get_parameters(cls):
        pars = super(NetworkOptionsUpdate, cls).get_parameters()
        ptype = Optionset._update_type(0)
        ptype.name = "network-" + ptype.name
        pars.append(("updates", ptype, "Fields and updates"))
        return pars
    
    def do(self):
        self.network_manager.update_options(self, self.network, self.updates)


class Network(AdHocModel):
    name = "network"
    exttype = ExtNetwork
    id_type = unicode

    def init(self, *args, **kwargs):
        a = list(args)
        self.oid = a.pop(0)
        self.authoritative = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)
        self.optionset = a.pop(0)

    @template("network", ExtNetwork)
    @entry(g_read)
    def get_network(self):
        return self

    @template("authoritative", ExtBoolean)
    @entry(g_read)
    def get_authoritative(self):
        return self.authoritative

    @template("info", ExtString)
    @entry(g_read)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime)
    @entry(g_read)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    @entry(g_read)
    def get_changed_by(self):
        return self.changed_by
    
    @template("options", ExtOptionKeyList, desc="List of options defined for this network")
    @entry(g_read)
    def list_options(self):
        return self.get_optionset().list_options()
    
    @template("optionset", ExtOptionset, model=Optionset)
    @entry(g_read)
    def get_optionset(self):
        return self.optionset_manager.get_optionset(self.optionset)
    
    @update("network", ExtNetworkName)
    @entry(g_write)
    def set_network(self, value):
        q = "UPDATE networks SET id=:value WHERE id=:id"
        self.db.put(q, id=self.oid, value=value)
        self.manager.rename_object(self, value)
        self.event_manager.add("rename", network=self.oid, newstr=value, authuser=self.function.session.authuser)

    @update("authoritative", ExtBoolean)
    @entry(g_write)
    def set_authoritative(self, value):
        q = "UPDATE networks SET authoritative=:authoritative WHERE id=:id"
        self.db.put(q, id=self.oid, authoritative=value)
        self.event_manager.add("update", network=self.oid, authoritative=value, authuser=self.function.session.authuser)
        
    @update("info", ExtNetworkInfo)
    @entry(g_write)
    def set_info(self, value):
        q = "UPDATE networks SET info=:info WHERE id=:id"
        self.db.put(q, id=self.oid, info=value)
        self.event_manager.add("update", network=self.oid, info=value, authuser=self.function.session.authuser)
        

class NetworkManager(AdHocManager):
    name = "network_manager"
    manages = Network

    model_lookup_error = ExtNoSuchNetworkError
    
    def init(self):
        self._model_cache = {}
        
    @classmethod
    def base_query(cls, dq):
        dq.table("networks nw")
        dq.select("nw.id", "nw.authoritative", "nw.info", "nw.mtime", "nw.changed_by", "nw.optionset")
        return dq

    def get_network(self, network_name):
        return self.model(network_name)

    def search_select(self, dq):
        dq.table("networks nw")
        dq.select("nw.id")

    @search("network", StringMatch)
    def s_net(self, dq):
        dq.table("networks nw")
        return "nw.id"
    
    @search("authoritative", BooleanMatch)
    def s_authoritative(self, dq):
        dq.table("networks nw")
        return "nw.authoritative"
    
    @search("info", NullableStringMatch)
    def s_info(self, dq):
        dq.table("networks nw")
        return "nw.info"
    
    @search("optionset", IntegerMatch, desc="Server internal option set number")
    def s_optionset(self, dq):
        dq.table("networks nw")
        return "nw.optionset"
    
    @entry(g_write)
    def create_network(self, fun, network_name, authoritative, info):
        
        optionset = self.optionset_manager.create_optionset(fun)
        
        q = """INSERT INTO networks (id, authoritative, info, changed_by, optionset) 
               VALUES (:id, :authoritative, :info, :changed_by, :optionset)"""
        try:
            self.db.put(q, id=network_name, authoritative=authoritative, 
                        info=info, changed_by=fun.session.authuser, optionset=optionset)
        except IntegrityError:
            raise ExtNetworkAlreadyExistsError()
        self.event_manager.add("create", network=network_name, authoritative=authoritative, 
                               info=info, authuser=fun.session.authuser, optionset=optionset)
        # print "Network created, network_name=", network_name
        
    @entry(g_write)
    def destroy_network(self, fun, network):
        
        network.get_optionset().destroy()
        
        try:
            q = "DELETE FROM networks WHERE id=:id LIMIT 1"
            self.db.put(q, id=network.oid)
        except IntegrityError:
            raise ExtNetworkInUseError()
        self.event_manager.add("destroy", network=network.oid, authuser=fun.session.authuser)
        
    @entry(g_write)
    def update_options(self, fun, network, updates):
        omgr = fun.optionset_manager
        optionset = omgr.get_optionset(network.optionset)
        for (key, value) in updates.iteritems():
            optionset.set_option_by_name(key, value)
            self.event_manager.add("update", network=network.oid, option=key, option_value=unicode(value), authuser=self.function.session.authuser)
