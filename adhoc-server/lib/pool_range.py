#!/usr/bin/env python2.6

# $Id$

from dhcp_server import *
from pool import *
from rpcc import *
from util import *

g_write = AnyGrants(AllowUserWithPriv("write_all_pool_ranges"), AdHocSuperuserGuard)
g_read = AnyGrants(g_write, AllowUserWithPriv("read_all_pool_ranges"))


class ExtNoSuchPoolRangeError(ExtLookupError):
    desc = "No such pool_range exists."
    
    
class ExtPoolRangeAlreadyExistsError(ExtLookupError):
    desc = "The pool_range name is already in use"
    
    
class ExtPoolRangeInUseError(ExtValueError):
    desc = "The pool_range is referred to by other objects. It cannot be destroyed"
    
    
class ExtPoolRangeReversedError(ExtValueError):
    desc = "The end IP address of the range must be higher than the start address"
    
    
class ExtPoolRangeOverlapError(ExtValueError):
    decs = "The specified pool range overlaps another pool range"


class ExtPoolRangeName(ExtIpV4Address):
    name = "pool_range-start"
    desc = "Starting IP address of a pool range"


class IpV4Match(Match):
    @suffix("equal", ExtIpV4Address)
    @suffix("", ExtString)
    def eq(self, fun, q, expr, val):
        q.where("INET_ATON(" + expr + ") = INET_ATON(" + q.var(val) + ")" )
    
    @suffix("not_equal", ExtIpV4Address)
    def neq(self, fun, q, expr, val):
        q.where("INET_ATON(" + expr + ") <> INET_ATON(" + q.var(val) + ")" )
        
    @prefix("max", ExtIpV4Address)
    def max(self, fun, q, expr, val):
        q.where("INET_ATON(" + expr + ") <= INET_ATON(" + q.var(val) + ")" )
    
    @prefix("min", ExtIpV4Address)
    def min(self, fun, q, expr, val):
        q.where("INET_ATON(" + expr + ") >= INET_ATON(" + q.var(val) + ")" )


class ExtPoolRange(ExtPoolRangeName):
    name = "pool_range"
    desc = "A DHCP shared pool_range"

    def lookup(self, fun, cval):
        return fun.pool_range_manager.get_pool_range(str(cval))

    def output(self, fun, obj):
        return obj.oid
    
    
class PoolRangeFunBase(SessionedFunction):  
    params = [("pool_range_start", ExtPoolRange, "Pool range start address")]
   

class PoolRangeCreate(SessionedFunction):
    extname = "pool_range_create"
    params = [("start_ip", ExtPoolRangeName, "Pool range start address"),
              ("end_ip", ExtIpV4Address, "Pool range end address"),
              ("pool", ExtPool, "Pool where the range lives"),
              ("served_by", ExtDHCPServer, "DHCP server to serve the pool range")]
    desc = "Creates a pool_range"
    returns = (ExtNull)

    def do(self):
        
        if (socket.inet_aton(self.end_ip) < socket.inet_aton(self.start_ip)):
            raise ExtPoolRangeReversedError()
        
        self.pool_range_manager.create_pool_range(self,
                                                  self.start_ip, 
                                                  self.end_ip,
                                                  self.pool,
                                                  self.served_by)
        

class PoolRangeDestroy(PoolRangeFunBase):
    extname = "pool_range_destroy"
    desc = "Destroys a shared pool_range"
    returns = (ExtNull)

    def do(self):
        self.pool_range_manager.destroy_pool_range(self, self.pool_range_start)


class PoolRange(AdHocModel):
    name = "pool_range"
    exttype = ExtPoolRange
    id_type = str

    def init(self, *args, **kwargs):
        a = list(args)
        self.oid = a.pop(0)
        self.start_ip = self.oid
        self.end_ip = a.pop(0)
        self.pool = a.pop(0)
        self.served_by = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)
        self.id = a.pop(0)

    @template("start_ip", ExtPoolRange)
    def get_start_ip(self):
        return self
    
    @template("end_ip", ExtIpV4Address)
    def get_end_ip(self):
        return self.end_ip

    @template("pool", ExtPool)
    def get_pool(self):
        return self.pool_manager.get_pool(self.pool)

    # @template("served_by", ExtDHCPServer)
    # def get_served_by(self):
        # return self.dhcp_server_manager.get_dhcp_server(self.served_by)
    
    @template("served_by", ExtDHCPServer, model="dhcp_server")
    @entry(g_read)
    def get_served_by(self):
        q = "SELECT id FROM dhcp_servers WHERE id=:served_by"
        return self.dhcp_server_manager.model(self.db.get_all(q, served_by=self.served_by)[0][0])
        # return [self.dhcp_server_manager.model(a) for (a,) in self.db.get(q, served_by=self.served_by)]
    
    @template("mtime", ExtDateTime)
    @entry(g_read)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    @entry(g_read)
    def get_changed_by(self):
        return self.changed_by
    
    @update("start_ip", ExtPoolRangeName)
    @entry(g_write)
    def set_start_ip(self, value):
        q = "UPDATE pool_ranges SET start_ip=:value WHERE id=:id"
        self.db.put(q, id=self.id, value=value)
        self.manager.rename_object(self, value)
        self.manager.approve_config = True
        self.event_manager.add("rename", pool_range=self.oid, newstr=value, authuser=self.function.session.authuser)
        
    @update("end_ip", ExtIpV4Address)
    @entry(g_write)
    def set_end_ip(self, value):
        q = "UPDATE pool_ranges SET end_ip=:value WHERE id=:id"
        self.db.put(q, id=self.id, value=value)
        self.manager.approve_config = True
        self.event_manager.add("update", pool_range=self.oid, end_ip=value, authuser=self.function.session.authuser)

    @update("pool", ExtPool)
    @entry(g_write)
    def set_pool(self, pool):
        q = "UPDATE pool_ranges SET pool=:pool WHERE start_ip=:id"
        self.db.put(q, id=self.oid, pool=pool.oid)
        self.manager.approve_config = True
        self.event_manager.add("update", pool_range=self.oid, pool=pool.oid, authuser=self.function.session.authuser)
             
    @update("served_by", ExtDHCPServer)
    @entry(g_write)
    def set_info(self, served_by):
        q = "UPDATE pool_ranges SET served_by=:served_by WHERE start_ip=:id"
        self.db.put(q, id=self.oid, served_by=served_by.oid)
        self.event_manager.add("update", pool_range=self.oid, served_by=served_by.oid, authuser=self.function.session.authuser)
        
    def check_model(self):
        """ This method is called after all updates are made
        
            Check for reversed range and for overlaps with other ranges except for the
            range we have changed """
            
        self.manager.check_reversed_range(self.start_ip, self.end_ip)
        self.manager.checkoverlaps()
        self.manager.approve()


class PoolRangeManager(AdHocManager):
    name = "pool_range_manager"
    manages = PoolRange

    model_lookup_error = ExtNoSuchPoolRangeError
    
    def init(self):
        self._model_cache = {}
        
    @classmethod
    def base_query(cls, dq):
        dq.table("pool_ranges pr")
        dq.select("pr.start_ip", "pr.end_ip", "pr.pool", "pr.served_by", "pr.mtime", "pr.changed_by", "pr.id")
        return dq

    def get_pool_range(self, pool_range_name):
        return self.model(pool_range_name)

    def search_select(self, dq):
        dq.table("pool_ranges pr")
        dq.select("pr.start_ip")

    @search("start_ip", IpV4Match)
    def s_start_ip(self, dq):
        dq.table("pool_ranges pr")
        return "pr.start_ip"
    
    @search("end_ip", IpV4Match)
    def s_end_ip(self, dq):
        dq.table("pool_ranges pr")
        return "pr.end_ip"
    
    @search("pool", StringMatch)
    def s_pool(self, dq):
        dq.table("pool_ranges pr")
        return "pr.pool"
    
    @search("served_by", StringMatch, manager_name="dhcp_server_manager")
    def s_served_by(self, q):
        q.table("dhcp_server dc")
        q.where("dc.id = pr.served_by")
        return "dc.id"
    
    @entry(g_write)
    def create_pool_range(self, fun, start_ip, end_ip, pool, served_by):
        q = "INSERT INTO pool_ranges (start_ip, end_ip, pool, served_by, changed_by) VALUES (:start_ip, :end_ip, :pool, :served_by, :changed_by)"
        
        if socket.inet_aton(end_ip) < socket.inet_aton(start_ip):
            raise ExtPoolRangeReversedError()
        self.checkoverlaps()
        try:
            self.db.put(q, start_ip=start_ip, end_ip=end_ip, pool=pool.oid, served_by=served_by.oid, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtPoolRangeAlreadyExistsError()
        self.event_manager.add("create", pool_range=start_ip, parent_object=pool.oid, authuser=fun.session.authuser, end_ip=end_ip)
        self.approve_config = True
        self.approve()
            
    @entry(g_write)
    def destroy_pool_range(self, fun, pool_range):
        try:
            q = "DELETE FROM pool_ranges WHERE start_ip=:start_ip LIMIT 1"  
            self.db.put(q, start_ip=pool_range.oid)
        except IntegrityError:
            raise ExtPoolRangeInUseError()
        self.event_manager.add("destroy", pool_range=pool_range.oid, authuser=fun.session.authuser)
        self.approve_config = True
        self.approve()
        
    def getoverlaps(self, start_ip, end_ip):
        q = """SELECT start_ip, end_ip FROM pool_ranges WHERE
                (INET_ATON(:start_ip) BETWEEN INET_ATON(start_ip) AND INET_ATON(end_ip)) OR
                (INET_ATON(:end_ip) BETWEEN INET_ATON(start_ip) AND INET_ATON(end_ip)) OR
                (INET_ATON(start_ip) BETWEEN INET_ATON(:start_ip) AND INET_ATON(:end_ip)) OR
                (INET_ATON(end_ip) BETWEEN INET_ATON(:start_ip) AND INET_ATON(:end_ip))
                ORDER BY start_ip
                """
        overlaps = self.db.get_all(q, start_ip=start_ip, end_ip=end_ip)
        return overlaps
    
    def getoverlaps2(self):
        q = """SELECT t1.start_ip, t2.end_ip FROM pool_ranges AS t1, pool_ranges AS t2 WHERE
                INET_ATON(t2.start_ip) <= INET_ATON(t1.end_ip) AND
                INET_ATON(t2.end_ip) >= INET_ATON(t1.start_ip) AND t1.id != t2.id"""
        overlaps = self.db.get_all(q)
        return overlaps
    
    def check_reversed_range(self, start_ip, end_ip):
        q = "SELECT INET_ATON(:start_ip) > INET_ATON(:end_ip)"
        val = self.db.get_value(q, start_ip=start_ip, end_ip=end_ip)
        if val:
            raise ExtPoolRangeReversedError()
        
    def checkoverlaps(self):

        overlaps = self.getoverlaps2()
        
        if overlaps:
                raise ExtPoolRangeOverlapError("The change would cause overlap between the ranges: %s" % ",".join(elem[0] for elem in overlaps))
