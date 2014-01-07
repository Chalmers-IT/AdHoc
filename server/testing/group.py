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
                 "mtime": True
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
            
            
class T1120_GroupCreate(UnAuthTests):
    """ Test group_create """
    
    def do(self):  
        if self.proxy != self.superuser:
            return
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
        
        
class T1130_GroupDestroy(UnAuthTests):
    """ Test group destroy """
    
    def do(self):
        if self.proxy != self.superuser:
            return
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
            
        
class T1140_GroupSetName(UnAuthTests):
    """ Test setting group of a group"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
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
                
                
class T1150_GroupSetInfo(UnAuthTests):
    """ Test setting info on a group"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
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
                
                
class T1150_GroupSetParent(UnAuthTests):
    """ Test setting parent on a group"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
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
        
if __name__ == "__main__":
    sys.exit(main())