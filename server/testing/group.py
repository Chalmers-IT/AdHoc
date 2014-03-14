#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC group API test suite"""
from framework import *
from util import *

data_template = {
                 "optionspace": True,
                 "parent": True,
                 "info": True, 
                 "group": True,
                 "changed_by": True,
                 "mtime": True,
                 "optionset_data": {"_": True, "_remove_nulls": True},
                 "optionset": True,
                 "literal_options": True
                 }


class T1100_GroupList(UnAuthTests):
    """ Test group listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.group_dig({}, data_template)
            
            assert len(ret) > 0, "Too few groups returned"
            #for ds in ret:
                #print ds.re, ds.group, ds.info
  
  
class T1110_GroupFetch(UnAuthTests):
    """ Test group_fetch """

    def do(self):
        groups = [x.group for x in self.superuser.group_dig({}, data_template)]
        
        n = 0
        for group in groups:
            ret = self.proxy.group_fetch(group, data_template)
            self.assertindict(ret, data_template.keys(), exact=True)
            n += 1
            if n > 50:  # There are too many groups to check, 50 is enough
                break
            
            
class T1120_GroupCreate(ServiceDeskTests):
    """ Test group_create """
    
    def do(self):
        try:
            self.superuser.group_destroy('QZ1243A')
        except:
            pass
        with AssertAccessError(self):
            try:
                self.proxy.group_create('QZ1243A', 'altiris', "TestGroup", {})
                ret = self.superuser.group_fetch('QZ1243A', data_template)
                self.assertindict(ret, data_template.keys(), exact=True)
                
                assert ret.group == "QZ1243A", "Bad group group, is % should be %s" % (ret.group, "QZ1243A")
                assert ret.info == "TestGroup", "Info is " + ret.info + "but should be 'TestGroup'"
                assert ret.parent == "altiris", "Bad parent %s, should be 'altiris'" % ret.parent
            finally:
                try:
                    self.superuser.group_destroy('QZ1243A')
                except:
                    pass
        
        
class T1130_GroupDestroy(ServiceDeskTests):
    """ Test group destroy """

    def do(self):
        try:
            self.superuser.group_create('QZ1243A', 'altiris', "TestGroup", {})
            try:
                with AssertAccessError(self):
                    self.proxy.group_destroy('QZ1243A')
                    with AssertRPCCError("LookupError::NoSuchGroup", True):
                        self.superuser.group_fetch('QZ1243A', data_template)
            finally:
                try:
                    self.superuser.group_destroy('QZ1243A')
                except:
                    pass
        finally:
                try:
                    self.superuser.group_destroy('QZ1243A')
                except:
                    pass
            
        
class T1140_GroupSetName(ServiceDeskTests):
    """ Test setting group of a group"""
    def do(self):
        self.superuser.group_create('QZ1243A', 'altiris', "TestGroup", {})
        with AssertAccessError(self):
            try:
                self.proxy.group_update('QZ1243A', {"group": 'ZQ1296'})
                nd = self.superuser.group_fetch('ZQ1296', data_template)
                assert nd.group == "ZQ1296", "Bad group group"
                assert nd.info == "TestGroup", "Bad info"
                assert nd.parent == "altiris", "Bad parent %s, should be 'altiris'" % nd.parent
            finally:
                try:
                    self.superuser.group_destroy('ZQ1296')
                except:
                    pass
                try:
                    self.superuser.group_destroy('QZ1243A')
                except:
                    pass
                
                
class T1150_GroupSetInfo(ServiceDeskTests):
    """ Test setting info on a group"""
    
    def do(self):
        self.superuser.group_create('QZ1243A', 'altiris', "TestGroup", {})
        with AssertAccessError(self):
            try:
                self.proxy.group_update('QZ1243A', {"info": "ZQ1296 option"})
                nd = self.superuser.group_fetch('QZ1243A', data_template)
                assert nd.group == "QZ1243A", "Bad group group"
                assert nd.info == "ZQ1296 option", "Bad info"
                assert nd.parent == "altiris", "Bad parent %s, should be 'altiris'" % nd.parent
            finally:
                try:
                    self.superuser.group_destroy('QZ1243A')
                except:
                    pass
                
                
class T1150_GroupSetParent(ServiceDeskTests):
    """ Test setting parent on a group"""
    
    def do(self):
        self.superuser.group_create('QZ1243A', 'altiris', "TestGroup", {})
        with AssertAccessError(self):
            try:
                self.proxy.group_update('QZ1243A', {"parent": "plain"})
                nd = self.superuser.group_fetch('QZ1243A', data_template)
                assert nd.group == "QZ1243A", "Bad group group"
                assert nd.info == "TestGroup", "Bad info"
                assert nd.parent == "plain", "Bad parent %s, should be 'plain'" % nd.parent
            finally:
                try:
                    self.superuser.group_destroy('QZ1243A')
                except:
                    pass
                
                
class T1160_GroupSetOption(ServiceDeskTests):
    """ Test setting options on a group"""
    
    def do(self):
        try:
            self.superuser.group_destroy('QZ1243A')
        except:
            pass

        self.superuser.group_create('QZ1243A', 'altiris', "TestGroup", {})
        
        with AssertAccessError(self):
            try:
                self.proxy.group_options_update("QZ1243A", {"subnet-mask": "255.255.255.0"})
                #self.proxy.network_option_set("network_test", "subnet-mask", "255.255.255.0")
                nd = self.superuser.group_fetch('QZ1243A', data_template)
            
                assert nd.group == "QZ1243A", "Bad group id"
                assert nd.info == "TestGroup", "Bad info"
                assert nd.optionset_data["subnet-mask"] == "255.255.255.0", "Bad subnet-mask in options"
                
            finally:
                try:
                    self.superuser.group_destroy('QZ1243A')
                except:
                    pass
                
                
class T1170_GroupUnsetOption(ServiceDeskTests):
    """ Test unsetting options on a group"""
    
    def do(self):
        self.superuser.group_create('QZ1243A', 'altiris', "TestGroup", {})
        
        with AssertAccessError(self):
            try:
                self.proxy.group_options_update("QZ1243A", {"subnet-mask": "255.255.255.0"})
                self.proxy.group_options_update("QZ1243A", {"subnet-mask": None})
                nd = self.superuser.group_fetch("QZ1243A", data_template)
                assert nd.group == "QZ1243A", "Bad group id"
                assert nd.info == "TestGroup", "Bad info"
                assert "subnet-mask" not in nd.optionset_data, "Subnet-mask still in options"
                
            finally:
                try:
                    self.superuser.group_destroy('QZ1243A')
                except:
                    pass

              
class T1180_GroupAddLiteralOption(SuperUserTests):
    """ Test adding a literal option to a group"""

    def do(self):
        try:
            self.superuser.group_create('QZ1243A', 'altiris', "TestGroup", {})
        
            with AssertAccessError(self):
                try:
                    pass
                    literal_value = "#This is a literal option"
                    id = self.proxy.group_literal_option_add('QZ1243A', literal_value)
                    #print "Literal option ID=%d" % id
                    opts = self.proxy.group_fetch('QZ1243A', data_template).literal_options
                    #print opts
                    assert id in [x.id for x in opts], "The returned id is not returned in when fetching the group"
                    assert "#This is a literal option" in [x.value for x in opts], "The literal value is not returned in when fetching the group"
                    
                    for opt in opts:
                        if opt.id == id:
                            assert opt.value == literal_value, "Returned literal option has the wrong value"
                finally:
                    try:
                        self.superuser.group_destroy('QZ1243A')
                    except:
                        pass
        finally:
                try:
                    self.superuser.group_destroy('QZ1243A')
                except:
                    pass
                
                
class T1180_GroupDestroyLiteralOption(SuperUserTests):
    """ Test destroying a literal option from a group"""
    def do(self):
        try:
            self.superuser.group_create('QZ1243A', 'altiris', "TestGroup", {})
        
            with AssertAccessError(self):
                try:
                    pass
                    literal_value = "#This is a literal option"
                    id = self.superuser.group_literal_option_add('QZ1243A', literal_value)
                    #print "Literal option ID=%d" % id
                    opts = self.superuser.group_fetch('QZ1243A', data_template).literal_options
                    #print opts
                    assert id in [x.id for x in opts], "The returned id is not returned in when fetching the group"
                    assert "#This is a literal option" in [x.value for x in opts], "The literal value is not returned in when fetching the group"
                    
                    for opt in opts:
                        if opt.id == id:
                            assert opt.value == literal_value, "Returned literal option has the wrong value"
                    
                    self.proxy.group_literal_option_destroy('QZ1243A', id)
                    opts = self.superuser.group_fetch('QZ1243A', data_template).literal_options
                    assert id not in [x.id for x in opts], "The returned id is still returned in when fetching the group"
                    assert "#This is a literal option" not in [x.value for x in opts], "The literal value is still returned in when fetching the group"
                    
                finally:
                    try:
                        self.superuser.group_destroy('QZ1243A')
                    except:
                        pass
        finally:
                try:
                    self.superuser.group_destroy('QZ1243A')
                except:
                    pass
if __name__ == "__main__":
    sys.exit(main())
