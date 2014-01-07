#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction


class ExtNoSuchBuildingError(ExtLookupError):
    desc = "No such building exists."


class ExtBuildingName(ExtString):
    name = "building-name"
    desc = "ID of a building"
    regexp = "^[-a-zA-Z0-9_]+$"


class ExtBuildingRe(ExtString):
    name = "building-re"
    desc = "Re. A regular expression"
    regexp = "^.*$"


class ExtBuilding(ExtBuildingName):
    name = "building"
    desc = "A building instance"

    def lookup(self, fun, cval):
        return fun.building_manager.get_building(cval)

    def output(self, fun, obj):
        return obj.oid
   
    
class BuildingCreate(SessionedFunction):
    extname = "building_create"
    params = [("id", ExtBuildingName, "Building name to create"),
              ("re", ExtBuildingRe, "The regular expression rooms must match for this building"),
              ("info", ExtString, "Building description")]
    desc = "Creates a building"
    returns = (ExtNull)

    def do(self):
        self.building_manager.create_building(self, self.id, self.re, self.info)


class BuildingDestroy(SessionedFunction):
    extname = "building_destroy"
    params = [("building", ExtBuilding, "Building to destroy")]
    desc = "Destroys a building"
    returns = (ExtNull)

    def do(self):
        self.building_manager.destroy_building(self, self.building)


class Building(Model):
    name = "building"
    exttype = ExtBuilding
    id_type = unicode

    def init(self, *args, **kwargs):
        a = list(args)
        #print "Building.init", a
        self.oid = a.pop(0)
        self.re = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)

    @template("building", ExtBuilding)
    def get_building(self):
        return self

    @template("re", ExtBuildingRe)
    def get_re(self):
        if self.re == None:
            return ""
        return self.re

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    def get_changed_by(self):
        return self.changed_by
    
    @update("building", ExtString)
    def set_building(self, newbuilding):
        nn = str(newbuilding)
        q = "UPDATE buildings SET id=:newbuilding WHERE id=:id LIMIT 1"
        self.db.put(q, id=self.oid, newbuilding=nn)
        self.db.commit()
        print "Building %s changed ID to %s" % (self.oid, nn)
        self.manager.rename_building(self, nn)
        
    @update("info", ExtString)
    def set_info(self, newinfo):
        q = "UPDATE buildings SET info=:info WHERE id=:id"
        self.db.put(q, id=self.oid, info=newinfo)
        self.db.commit()
        
    @update("re", ExtBuildingRe)
    def set_re(self, newre):
        q = "UPDATE buildings SET re=:re WHERE id=:id"
        self.db.put(q, id=self.oid, re=newre)
        self.db.commit()


class BuildingManager(Manager):
    name = "building_manager"
    manages = Building

    model_lookup_error = ExtNoSuchBuildingError

    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.select("r.id", "r.re", "r.info", "r.mtime", "r.changed_by")
        dq.table("buildings r")
        return dq

    def get_building(self, building_name):
        return self.model(building_name)

    def search_select(self, dq):
        dq.table("buildings r")
        dq.select("r.id")
    
    @search("building", StringMatch)
    def s_building(self, dq):
        dq.table("buildings r")
        return "r.id"
    
    def create_building(self, fun, building_name, re, info):
        q = "INSERT INTO buildings (id, re, info, changed_by) VALUES (:id, :re, :info, :changed_by)"
        self.db.put(q, id=building_name, re=re, info=info, changed_by=fun.session.authuser)
        print "Building created, name=", building_name
        self.db.commit()
        
    def destroy_building(self, fun, building):
        q = "DELETE FROM buildings WHERE id=:id LIMIT 1"
        self.db.put(q, id=building.oid)
        print "Building destroyed, id=", building.oid
        self.db.commit()
        
    def rename_building(self, obj, building_name):
        oid = obj.oid
        obj.oid = building_name
        del(self._model_cache[oid])
        self._model_cache[building_name] = obj