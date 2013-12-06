#!/usr/bin/env python2.6

"""
A Model/Manager pair represents some complex data type in the underlying
data model.

A Model instance represents exactly one instance of the underlying type,
such as a particular account, one computer, or a specific individual 
person.

A Manager instance manages models of a certain type as a group - creating 
and destroying individual data objects, returning Model instances for
its type, and performing operations on multiple data objects at one
time.

Every running Function can create a Manager by internal methods, which also
makes sure that there is only one Manager of a particular type for that
Function at any one time.

In a database-backed system, Functions get their own database link (and
therefore their own transaction space). Managers can use the database
link of the Function that created them, as can the Model instances that
a Manager creates. Once a Function completes running, the Managers and
Models it has created are deallocated.

Model classes can also ease the creation of standard Functions and
external data types. They do this by using the @extattr() decorator on
methods named get_*() and set_*(). The decorator specifies the external
data type that is returned/expected, the external attribute name (if other
than what follows get_/set_), and the API versions between which the
attribute is to be defined this way.

@extattr decorators may be nested, and may choose to supply different
descriptions of the attribute by the 'desc' keyword argument. Normally,
however, the description is stable while types and names vary over
API versions. There is therefore a special @extdesc() decorator which
sets a default external description.
"""

import random
import datetime
import functools

from error import IntAPIValidationError
from exttype import *
from default_type import *

class _TmpReference(object):
    def __init__(self, other, nullable=False, islist=False):
        if type(other) == type(type) and issubclass(other, Model):
            other = other._name()
        self.name = other
        self.nullable = nullable
        self.islist = islist

class ExternalAttribute(object):
    # Valid for one particular API version.
    def __init__(self, name, type=None, method=None, desc=None, model=None, default=False):
        self.extname = name
        self.exttype = type
        self.method = method
        self.extdesc = desc
        self.model = model
        self.default = default

    def __repr__(self):
        return "%s attr=%s type=%s method=%s" % (self.__class__.__name__, self.extname, self.exttype, self.method)


class ExternalReadAttribute(ExternalAttribute):
    def fill_template_type(self, tmpl):
        if self.model:
            if isinstance(ExtType.instance(self.exttype), ExtOrNull):
                nullable = True
            else:
                nullable = False
            tmpl.optional[self.extname] = (_TmpReference(self.model, nullable), self.extdesc)
        else:
            tmpl.optional[self.extname] = (ExtBoolean, self.extdesc)

    def fill_data_type(self, data):
        if self.model:
            if isinstance(ExtType.instance(self.exttype), ExtOrNull):
                nullable, islist = True, False
            elif isinstance(ExtType.instance(self.exttype), ExtList):
                nullable, islist = False, True
            else:
                nullable, islist = False, False
                
            data.optional[self.extname] = (_TmpReference(self.model, nullable, islist), self.extdesc)
        else:
            data.optional[self.extname] = (self.exttype, self.extdesc)

    def fill_update_type(self, upd):
        pass


class ExternalWriteAttribute(ExternalAttribute):
    def fill_template_type(self, tmpl):
        pass

    def fill_data_type(self, data):
        pass

    def fill_update_type(self, upd):
        upd.optional[self.extname] = (self.exttype, self.extdesc)


# NOTE! In order for @entry and @template to be stackable in arbitrary
# order, @entry needs to know about (and copy) the _template method
# attribute.
def template(name, exttype, minv=0, maxv=10000, desc=None, model=None, default=False):
    def decorate(decorated):
        data = dict(name=name, type=exttype, desc=desc, model=model, 
                    default=default)
        if hasattr(decorated, "_update"):
            raise IntAPIValidationError("Both @template and @update cannot be applied to the same method, but are for %s" % (decorated,))

        if hasattr(decorated, "_template"):
            for (submin, submax, subdata) in decorated._template:
                if submin < maxv and submax > minv:
                    raise IntAPIValidationError("Two @template directives have overlapping API versions for %s" % (decorated,))
            decorated._template.append((minv, maxv, data))
        else:
            decorated._template = [(minv, maxv, data)]
        return decorated
    return decorate


# NOTE! In order for @entry and @update to be stackable in arbitrary
# order, @entry needs to know about (and copy) the _update method
# attribute.
def update(name, exttype, minv=0, maxv=10000, desc=None):
    def decorate(decorated):
        data = dict(name=name, type=exttype, desc=desc)
        if hasattr(decorated, "_template"):
            raise IntAPIValidationError("Both @template and @update cannot be applied to the same method, but are for %s" % (decorated,))
        if hasattr(decorated, "_update"):
            for (submin, submax, subdata) in decorated._update:
                if submin < maxv and submax > minv:
                    raise IntAPIValidationError("Two @update directives have overlapping API versions for %s" % (decorated,))
            decorated._update.append((minv, maxv, data))
        else:
            decorated._update = [(minv, maxv, data)]
        return decorated
    return decorate



class Model(object):
    # The name attribute is used when cross-referencing between
    # templates, and in auto-generation by the server. 

    # * Types <name>-data-template, <name>-templated-data,
    #   <name>-search-options and <name>-update options will be
    #   created (using @template and @update decorators on methods in
    #   the subclass).  

    # * Function subclasses for RPCs named <name>_dig(),
    #   <name>_fetch() and <name>_update() will also be created.

    # * When auto-generating, the Ext<Name> type must exist, and
    #   represent one instance of <name> externally.
    
    # It cannot be changed between API versions (since we, in
    # principle, never change the model completely, we only modify it
    # and adapt the API with which that model is accessed). Choose
    # carefully.
    name = ""

    # The ID type determines, among other things, which result set
    # table will be used. Valid values are basestring/int (the Python types).
    id_type = basestring

    def __init__(self, manager, *args, **kwargs):
        if not isinstance(manager, Manager):
            raise ValueError("The first argument to all Model instances must be the Manager that created them - received %s instead" % (manager,))
        self.manager = manager
        self.function = manager.function
        self.db = manager.function.db
        self._templated = {}

        # Dict of Model-stable _Decision:s, indexed by Guard instance.
        self._decision_cache = {}

        if len(args) == 0:
            raise ValueError("There must be a second argument to a Model instance  - the object id - but none was received by %s." % (self.__class__.__name__,))
        if not isinstance(args[0], self.id_type):
            raise ValueError("The object id %s is not of type %s, which %s.id_type says it should be." % (args[0], self.id_type, self.__class__.__name__))

        self.init(*args, **kwargs)
        if not hasattr(self, "oid"):
            raise ValueError("self.oid must be set to the primary ID of the model")

    def reload(self):
        """Reset internal caches, and reload data from the manager.

        This method is never called by the system, only by yourself.
        IF you choose to call it, .init() must be written so that it can 
        handle being run more than once.
        """
        self._decision_cache = {}
        self._templated = {}

        self.init(*self.manager.args_for_model(self.oid))

    def init(self, *args):
        """Given a list of values generated by the Manager's
        args_for_model() method, set up internal state.

        Note that IF you call .reload(), this method will be run again, 
        with new values fetched from the manager, and you must be able 
        to handle that. Without .reload(), this method is only ever 
        called once.
        """

        raise NotImplementedError()

    def __getattr__(self, attr):
        if attr.endswith("_manager"):
            setattr(self, attr, getattr(self.manager, attr))
            return getattr(self, attr)
        else:
            raise AttributeError(attr)

    @classmethod
    def _name(cls):
        return cls.name

    @classmethod
    def _attributes(cls, api_version):
        # Note: the result is cached in the _class_ object, and
        # therefore only ever calculated once.

        # Note 2: If the attribute has a "model" attribute, the
        # _TmpReference object is used in the templates on an
        # "<attr>_data" attribute. _TmpReferences are used as
        # placeholders, to resolve mutual references between template
        # types.

        try:
            return cls._attributes_cache[api_version]
        except KeyError:
            cls._attributes_cache[api_version] = ({}, {})
        except AttributeError:
            cls._attributes_cache = {api_version: ({}, {})}

        for candname in dir(cls):
            candidate = getattr(cls, candname)
            if hasattr(candidate, "_template"):
                attrcls = ExternalReadAttribute
                defs = candidate._template
                dest = cls._attributes_cache[api_version][0]
            elif hasattr(candidate, "_update"):
                attrcls = ExternalWriteAttribute
                defs = candidate._update
                dest = cls._attributes_cache[api_version][1]
            else:
                continue

            for (minv, maxv, data) in defs:
                if api_version >= minv and api_version <= maxv:
                    break
            else:
                continue

            name = data.pop("name")
            if name in dest:
                raise IntAPIValidationError("Multiple @template/@update definitions uses the public name %s for API version %d" % (name, api_version))

            typminv, typmaxv = ExtType.instance(data["type"])._api_versions()
            if api_version < typminv or api_version > typmaxv:
                raise IntAPIValidationError("@template/@update definition on method %s.%s says its valid through API versions (%d, %d), but the type %s it uses is valid through (%d, %d) making it invalid for version %d" % (cls, candname, minv, maxv, data["type"], typminv, typmaxv, api_version))

            data["method"] = candidate

            if "model" in data and data["model"]:
                dest[name + "_data"] = attrcls(name + "_data", **data)

            dummy = data.pop("model", None)
            dest[name] = attrcls(name, **data)

        return cls._attributes_cache[api_version]

    @classmethod
    def _read_attributes(cls, api_version):
        return cls._attributes(api_version)[0]

    @classmethod
    def _write_attributes(cls, api_version):
        return cls._attributes(api_version)[1]

    @classmethod
    def _template_type(cls, api_version):
        tmpl = ExtStruct()
        tmpl.from_version = api_version
        tmpl.to_version = api_version
        tmpl.name = cls.name + "-data-template"

        for attr in cls._read_attributes(api_version).values():
            attr.fill_template_type(tmpl)
        tmpl.optional["_"] = (ExtBoolean, "A default set of attributes will be returned. This set changes over time, so only use this key interactively. Be explicit in your scripts!")

        return tmpl

    @classmethod
    def _data_type(cls, api_version):
        data = ExtStruct()
        data.from_version = api_version
        data.to_version = api_version
        data.name = cls.name + "-templated-data"
        
        for attr in cls._read_attributes(api_version).values():
            attr.fill_data_type(data)
        return data

    @classmethod
    def _update_type(cls, api_version):
        upd = ExtStruct()
        upd.from_version = api_version
        upd.to_version = api_version
        upd.name = cls.name + "-update"

        for attr in cls._write_attributes(api_version).values():
            attr.fill_update_type(upd)
        return upd

    def apply_update(self, api_version, updates):
        writeattrs = self._write_attributes(api_version)
        for (name, newval) in updates.items():
            attr = writeattrs[name]
            attr.method(self, newval, *attr.args, **attr.kwargs)

    def apply_template(self, api_version, tmpl):
        # Note: many different other Model instances may call
        # .apply_template on this instance, with the same or another
        # template instance (remember that templates may be nested
        # arbitrarily deep by the client). They should all get the
        # same data for the same template - make sure it is cached!

        tmplidx = str(tmpl)
        if (api_version, tmplidx) in self._templated:
            return self._templated[(api_version, tmplidx)]

        if "_" in tmpl and tmpl["_"]:
            tmpl = tmpl.copy()
            dummy = tmpl.pop("_")
            for (name, attr) in self._read_attributes(api_version).items():
                if attr.default and name not in tmpl:
                    tmpl[name] = True

        out = {}
        readattrs = self._read_attributes(api_version)
        for (name, tmpl_value) in tmpl.items():
            if tmpl_value == False:
                continue

            # The ExternalAttribute instance has a reference to the
            # method (directly from the class, i.e. unbound so we need
            # to pass self explicitly) and any parameters to
            # it.
            attr = readattrs[name]
            value = attr.method(self)

            if value is None:
                if "_remove_nulls" in tmpl and tmpl["_remove_nulls"]:
                    continue
                out[attr.name] = None
                continue

            if attr.model:
                subtmpl = tmpl_value
                if "_remove_nulls" in tmpl and "_remove_nulls" not in subtmpl:
                    subtmpl = subtmpl.copy()
                    subtmpl["_remove_nulls"] = tmpl["_remove_nulls"]
                
                if isinstance(ExtType.instance(attr.exttype), ExtList):
                    out[name] = [d.apply_template(api_version, subtmpl) for d in value]
                else:
                    out[name] = value.apply_template(api_version, subtmpl)
            else:
                out[name] = value
        self._templated[(api_version, tmplidx)] = out
        return out



# Search system.

# From the external viewpoint, search keys are exposed that can be fed
# to the system. Each search key represents a combination of a search
# method (which sets up a DynamicQuery to include a particular
# attribute) and a match method (which adds a comparison to the
# DynamicQuery involving the external value and the attribute set up
# by the search method).

# Internally, Managers expose methods, called search methods, that
# when called set up a DynamicQuery to contain a particular attribute
# and return the SQL for that attribute.

# Search methods are decorated with one or more @search() decorators,
# each belonging to non-overlapping API version ranges. In the
# decorator, the external name of the attribute is specified, as is
# the Match subclass that implements all matching mechanisms
# (comparisons and such) that should be usable with the attribute. The
# data from the decorator(s) is stored on the method as a list of
# _SearchSpec instances.

# A Match subclass implements different matching methods, each
# decorated with a @prefix() or @suffix() decorator. When a matching
# method is called because of external stimuli, it adds a comparison
# to a DynamicQuery, containing the attribute SQL returned by the
# search method. The decorator contains the string to prepend/append
# to the attribute name to form a search key.

# For each search method, a Match instance is created. Each
# combination of a search method and a match method is then
# represented by a _SearchKey. A _SearchKey contains the manager
# method to call for setting up the attribute, the Match object and
# method on it to call to add the comparison.


class _SearchKey(object):
    def __init__(self, key, manager_method, match_callable, exttype, desc):
        self.key = key
        self.manager_method = manager_method
        self.match_callable = match_callable
        self.exttype = exttype
        self.desc = desc

    def get_key(self):
        return self.key

    def get_exttype(self):
        return self.exttype

    def use(self, dynamic_query, manager, searchval):
        # The manager modifies the dynamic query as needed to define
        # the match expression and then returns it (e.g. "p.firstname").
        match_expr = self.manager_method(manager, dynamic_query)

        # The matcher modifies the dynamic query by adding the match
        # operation with the match expression returned above and the
        # value from the search (e.g. "p.firstname = <searchval>").
        self.match_callable(manager.function, dynamic_query, match_expr,
                            searchval)


# NOTE! In order for @entry and @suffix to be stackable in arbitrary
# order, @entry needs to know about (and copy) the _matchers method
# attribute.
def suffix(suff, exttype, desc="", minv=0, maxv=10000):
    def decorate(decorated):
        data = dict(prefix=None, suffix=suff, exttype=exttype, desc=desc, 
                    minv=minv, maxv=maxv)

        if hasattr(decorated, "_matchers"):
            decorated._matchers.append(data)
        else:
            decorated._matchers = [data]
        return decorated
    return decorate


# NOTE! In order for @entry and @prefix to be stackable in arbitrary
# order, @entry needs to know about (and copy) the _matchers method
# attribute.
def prefix(pref, exttype, desc="", minv=0, maxv=10000):
    def decorate(decorated):
        data = dict(prefix=pref, suffix=None, exttype=exttype, desc=desc,
                    minv=minv, maxv=maxv)

        if hasattr(decorated, "_matchers"):
            decorated._matchers.append(data)
        else:
            decorated._matchers = [data]
        return decorated
    return decorate


class Match(object):
    """When searches are performed, each incoming key is mapped
    to a combination of a Match subclass method and a Manager 
    subclass method. The Manager subclass method adds to a search 
    query by adding necessary tables and returning the expression
    the Match subclass method is to work with. The Match subclass
    method then updates the query by adding the search expression.

    As an example, a 'firstname_like' search parameter might map
    to a StringMatch method .like() and a PersonManager method
    .firstname_search(). .firstname_search(query) adds some tables
    to the query, then returns 'p.fname'. .firstname_search(query, 
    searchopt) adds the condition 'p.fname LIKE searchopt'.
    """

    _instance_cache = {}

    # NOTE! The Match.instance() method creates singletons which are
    # cached in the Match base class in the below attribute. Since
    # they are cached in the class, they are shared across Functions
    # and threads and this means that:

    # * ALL MATCH METHODS MUST BE RE-ENTRANT.

    # * They must never, under any circumstance, change state when
    #   being invoked.

    @classmethod
    def instance(cls, thing):
        if isinstance(thing, Match):
            return thing        
        elif type(thing) == type(type) and issubclass(thing, Match):
            if thing not in cls._instance_cache:
                cls._instance_cache[thing] = thing()
            return cls._instance_cache[thing]
        else:
            raise ValueError("%s is neither a Match instance nor a Match subclass" % (thing,))

    def keys_for_attribute(self, manager_method, api_version, name, desc):
        ret = []
        prefixes = {}
        suffixes = {}

        for candname in dir(self):
            candidate = getattr(self, candname)
            if not hasattr(candidate, "_matchers"):
                continue

            for m in candidate._matchers:
                # Only one decorator in the entire class
                # (independently of which method it is on) may claim a
                # particular prefix/suffix for a particular API
                # version.

                if m["prefix"]:
                    if m["prefix"] in prefixes:
                        raise IntAPIValidationError("Two @prefix decorators (on %s and %s) both claim the prefix %s for version %d of the API" % (candidate, prefixes[m["prefix"]], m["prefix"], api_version))
                    prefixes[m["prefix"]] = candidate
                    key = m["prefix"] + "_" + name
                elif m["suffix"]:
                    if m["suffix"] in suffixes:
                        raise IntAPIValidationError("Two @suffix decorators (on %s and %s) both claim the suffix %s for version %d of the API" % (candidate, suffixes[m["suffix"]], m["suffix"], api_version))
                    suffixes[m["suffix"]] = candidate
                    key = name + "_" + m["suffix"]
                else:
                    if "" in suffixes:
                        raise IntAPIValidationError("Two @suffix decorators (on %s and %s) both claim the empty suffix for version %d of the API" % (candidate, suffixes[""], api_version))
                    suffixes[""] = candidate
                    key = name

                if m["desc"]:
                    desc = desc + "(" + m["desc"] + ")"

                ret.append(_SearchKey(key, manager_method, candidate, m["exttype"], desc))
                #ret.append( (key, candidate, m["exttype"], desc) )
        return ret

    def __init__(self):
        pass


class EqualityMatchMixin(object):
    @suffix("equal", ExtString)
    @suffix("", ExtString)
    def eq(self, fun, q, expr, val):
        q.where(expr + "=" + q.var(val))

    @suffix("not_equal", ExtString)
    def neq(self, fun, q, expr, val):
        q.where(expr + "<>" + q.var(val))


class StringMatch(EqualityMatchMixin, Match):
    @suffix("maxlen", ExtInteger)
    def maxlen(self, fun, q, expr, val):
        q.where("LENGTH(" + expr + ") <= " + q.var(val))

    @suffix("like", ExtLikePattern)
    def like(self, fun, q, expr, val):
        q.where(expr + " LIKE " + q.var(val))

    @suffix("nocase_equal", ExtString)
    def nceq(self, fun, q, expr, val):
        q.where("LOWER(" + expr + ") = LOWER(" + q.var(val) + ") ")

    @suffix("nocase_not_equal", ExtString)
    def ncneq(self, fun, q, expr, val):
        q.where("LOWER(" + expr + ") <> LOWER(" + q.var(val) + ") ")


class IntegerMatch(EqualityMatchMixin, Match):
    @prefix("max", ExtInteger)
    def max(self, fun, q, expr, val):
        q.where(expr + "<=" + q.var(val))
    
    @prefix("min", ExtInteger)
    def min(self, fun, q, expr, val):
        q.where(expr + ">=" + q.var(val))




class _SearchSpec(object):
    """Represents one @search decorator and the data in it."""

    def __init__(self, minv, maxv, name, matcher, desc, manager_name):
        self.minv = minv
        self.maxv = maxv
        self.name = name
        self.matcher = matcher
        self.desc = desc
        self.manager_name = manager_name

    def covers_api_version(self, api_version):
        return (api_version >= self.minv and api_version <= self.maxv)
    
    def overlaps_api_range(self, other):
        return (self.minv < other.maxv and self.maxv > other.minv)

    def search_keys(self, manager_method, api_version):
        """Return the _SearchKey instances representing each
        combination of manager_method and the matchers match 
        methods, for a particular api version.

        """

        if not self.covers_api_version(api_version):
            raise ValueError("This cannot happen, but anyways...")
        
        matcher = Match.instance(self.matcher)
        keys = matcher.keys_for_attribute(manager_method, api_version, self.name, self.desc)

        if self.manager_name:
            subsearcher = _Subsearch(self.manager_name)
            subkeyname = self.name + "_in"
            
            keys.append(_SearchKey(subkeyname, manager_method, subsearcher.subsearch, _TmpReference(self.manager_name, nullable=False), self.desc))

            #ss = _Subsearch(srch["manager"])
            #cls._search_lookup[srch["name"] + "_in"] = (candidate, (ss, ss.subsearch), _TmpReference(srch["manager"], nullable=False), desc)

        #print "QBHD", self, [k.key for k in keys]
        return keys


# NOTE! In order for @entry and @search to be stackable in arbitrary
# order, @entry needs to know about (and copy) the _searches method
# attribute.
def search(name, matchcls, minv=0, maxv=10000, desc=None, manager_name=None):
    def decorate(decorated):
        newsobj = _SearchSpec(minv, maxv, name, matchcls, desc, manager_name)
        if hasattr(decorated, "_searches"):
            for oldsobj in decorated._searches:
                if oldsobj.overlaps_api_range(newsobj):
                    raise IntAPIValidationError("Two @template directives have overlapping API versions for %s" % (decorated,))
            decorated._searches.append(newsobj)
        else:
            decorated._searches = [newsobj]
        return decorated
    return decorate


class _Subsearch(object):
    def __init__(self, manager_name):
        self.manager_name = manager_name

    def subsearch(self, fun, dq, expr, val):
        mgr = getattr(fun, self.manager_name)
        subq = dq.subquery(expr)
        mgr.inner_search(subq, val)


class Manager(object):
    # If name="foo_manager", then <function>.foo_manager,
    # <manager>.foo_manager and <model>.foo_manager will return a
    # function-specific manager instance of this class. The
    # name must end in "_manager".
    name = None

    # The model class that this manager creates instances of.
    manages = None

    # The table to insert search results into ("rpcc_result_string" or
    # "rpcc_result_int" depending on data type of the models ID)
    #result_table = "rpcc_result_string"

    model_lookup_error = ExtLookupError

    @classmethod
    def _name(cls):
        assert cls.name.endswith("_manager")
        return cls.name

    @classmethod
    def _shortname(cls):
        return cls._name()[:-8]

    @classmethod
    def _search_methods(cls):
        """Return all methods on cls which was decorated by at least one
        @search() decorator.
        """

        meths = []
        for candname in dir(cls):
            candidate = getattr(cls, candname)
            if not hasattr(candidate, "_searches"):
                continue
            meths.append(candidate)
        return meths

    @classmethod
    def _has_search_attr(cls, attr, api=None):
        for meth in cls._search_methods():
            for sobj in meth._searches:
                if api is not None and not sobj.covers_api_version(api):
                    continue
                if sobj.name == attr:
                    return True
        return False

    @classmethod
    def _make_search_keys(cls, api_version):
        if hasattr(cls, "_search_lookup"):
            if api_version in cls._search_lookup:
                return
            else:
                cls._search_lookup[api_version] = {}
        else:
            cls._search_lookup = {api_version: {}}

        for meth in cls._search_methods():
            for searchspec in meth._searches:
                if searchspec.covers_api_version(api_version):
                    break
            else:
                continue

            for skey in searchspec.search_keys(meth, api_version):
                if skey.key in cls._search_lookup[api_version]:
                    raise ValueError("Search key %s defined twice, second time for %s" % (skey.key, meth))
                cls._search_lookup[api_version][skey.key] = skey

    @classmethod
    def _get_search_key(cls, api_version, key):
        return cls._search_lookup[api_version][key]

    @classmethod
    def _all_search_keys(cls, api_version):
        return cls._search_lookup[api_version].values()

    @classmethod
    def _search_type(cls, api_version):
        cls._make_search_keys(api_version)
        
        styp = ExtStruct()
        styp.from_version = api_version
        styp.to_version = api_version
        styp.name = cls._name()[:-8] + "-search-options"
        for skey in cls._all_search_keys(api_version):
            styp.optional[skey.key] = (skey.exttype, skey.desc)

        return styp
        
    @classmethod
    def on_register(cls, srv, db):
        """When the manager is registered with the Server, this method
        will be run and passed a database link.

        It can perform startup tasks such as checking/setting up
        tables in the database.

        If the database has not yet been enabled in the server,
        the db argument will be None.
        """
        pass

    def __init__(self, function, *args, **kwargs):
        self.function = function
        self.server = function.server
        self.db = function.db

        # Dict of Model instances already created, indexed by Model id.
        self._model_cache = {}

        # Dict of Model-stable _Decision:s, indexed by Guard instance.
        self._decision_cache = {}

        self.init(*args, **kwargs)

    def init(self, *args, **kwargs):
        return

    def base_query(self, dq):
        """Fill a supplied empty DynamicQuery instance, to set it up to 
        select the attributes that the model expects as input.

        In the DynamicQuery, the object ID column MUST be the
        first column in the select - the first returned column is used for
        caching and for matching.        
        """
        raise NotImplementedError()

    def kwargs_for_model(self, mid):
        """Return the **kwargs to send on Model instantiation."""
        return None

    def args_for_model(self, mid):
        dq = self.db.dynamic_query()
        self.base_query(dq)
        dq.where(dq.get_select_at(0) + "=" + dq.var(mid))
        try:
            (args,) = dq.run()
            return args
        except:
            raise self.model_lookup_error(value=mid)

    def model(self, oid):
        """Return one instance of self.manages, created by passing the
        result of self.base_query() to the Model's constructor."""

        if oid not in self._model_cache:
            if not isinstance(oid, self.manages.id_type):
                raise ValueError("%s id must be of type %s - supplied value %s isn't" % (self.manages.__name__, self.manages.id_type, oid))
            args = self.args_for_model(oid)
            kwargs = self.kwargs_for_model(oid) or {}
            self._model_cache[oid] = self.manages(self, *args, **kwargs)
        return self._model_cache[oid]

    def result_table(self):
        if issubclass(self.manages.id_type, basestring):
            return "rpcc_result_string"
        elif self.manages.id_type == int:
            return "rpcc_result_int"
        else:
            raise ValueError()

    def kwargs_for_result(self, rid):
        """Return a dict of dicts. The outer dict is indexed by
        model id, and the inner dicts are the **kwargs to send
        to the Model instantation for the respective model id.

        Although the 'empty' result should be a dictionary with all
        model id:s from the result mapping to empty dictionaries,
        None is accepted as meaning no kwargs for any model.
        """

        return None

    def models_by_result_id(self, rid):
        rtbl = self.result_table()
        dq = self.db.dynamic_query()
        self.base_query(dq)
        dq.table("rpcc_result", rtbl)
        dq.where("rpcc_result.resid = " + dq.var(rid))
        dq.where("rpcc_result.manager = " + dq.var(self._shortname()))
        dq.where(rtbl + ".resid = " + dq.var(rid))
        dq.where(rtbl + ".value = " + dq.get_select_at(0))
        res = []
        allargs = dq.run()
        extras = self.kwargs_for_result(rid)
        for args in dq.run():
            oid = args[0]
            if not oid in self._model_cache:
                if extras:
                    kwargs = extras.get(oid, {})
                else:
                    kwargs = {}
                self._model_cache[oid] = self.manages(self, *args, **kwargs)
            res.append(self._model_cache[oid])
        return res

    def __getattr__(self, attr):
        if self.name and attr == self.name + "_manager":
            return self
        elif attr.endswith("_manager"):
            setattr(self, attr, getattr(self.function, attr))
            return getattr(self, attr)
        else:
            raise AttributeError(attr)

    def new_result_set(self):
        q = "SELECT resid FROM rpcc_result WHERE expires > :now"
        for (expired,) in self.db.get(q, now=self.function.started_at()):
            q = "DELETE FROM rpcc_result_string WHERE resid=:r"
            self.db.put(q, r=expired)
            q = "DELETE FROM rpcc_result_int WHERE resid=:r"
            self.db.put(q, r=expired)

        while 1:
            rid = random.randint(0, 1<<31)
            q = "SELECT COUNT(*) FROM rpcc_result WHERE resid=:rid"
            if self.db.get_value(q, rid=rid) == 0:
                break

        q = "INSERT INTO rpcc_result (resid, manager, expires) "
        q += "VALUES (:r, :m, :e) "
        self.db.put(q, r=rid, m=self._shortname(), e=self.function.started_at() + datetime.timedelta(hours=1))

        return rid

    def search_select(self, dq):
        raise NotImplementedError()

    def perform_search(self, opts):
        dq = self.db.dynamic_query()
        rid = self.new_result_set()
        dq.store_result("INSERT INTO " + self.result_table() + " (resid, value)")
        dq.select(dq.var(rid))
        self.inner_search(dq, opts)
        dq.run()
        return rid

    def inner_search(self, dq, opts):
        self.search_select(dq)
        for (key, search_val) in opts.items():
            skey = self._get_search_key(self.function.api.version, key)
            skey.use(dq, self, search_val)
    
if __name__ == "__main__":
    from exttype import *

    class ExtName03(ExtString):
        to_version = 3
        desc = "A person's name (either firstname or lastname)"
        regexp = "[A-Z][a-z]+"

    class ExtName25(ExtName03):
        from_version = 2
        to_version = 5

    class ExtName48(ExtName03):
        from_version = 4
        to_version = 8

    class ExtAccount(ExtString):
        pass

    class ExtPerson(ExtString):
        pass

    class Person(Model):
        name = "person"

        def get_int(self):
            return "int"

        @template(ExtName03, maxv=3)
        @template(ExtName48, minv=4, name="newapa")
        def get_apa(self):
            pass

        @update(ExtName03, maxv=2)
        def set_apa(self):
            pass

        @template(ExtAccount, model="account")
        def get_account(self):
            pass


    class Account(Model):
        name = "account"

        @template(ExtString, model="person")
        def get_owner(self):
            pass


    for v in range(0, 5):
        print
        print v
        print "tmpl", Person._template_type(v).optional
        print "data", Person._data_type(v).optional
        print "update", Person._update_type(v).optional
        print "tmpl", Account._template_type(v).optional
        print "data", Account._data_type(v).optional
        print "update", Account._update_type(v).optional

        


    