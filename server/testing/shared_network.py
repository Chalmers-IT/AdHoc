#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC network API test suite"""
from framework import *
from util import *


class T0400_networkList(UnAuthTests):
    """ Test network listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.network_dig({}, {"network": True, "info": True, "authoritative": True, "mtime": True, "changed_by":True})
            
            assert len(ret) > 90, "Too few networks returned"
            #for n in ret:
                #print n
                #print n.authoritative, n.network, n.info, n.mtime, n.changed_by
  
  
class T0410_networkFetch(UnAuthTests):
    """ Test network_fetch """
    
    def do(self):
        networks = [x.network for x in self.superuser.network_dig({}, {"network":True})]
        
        for network in networks:
            ret = self.proxy.network_fetch(network, {"network": True, "info": True, "authoritative": True})
            assert "network" in ret, "Key network missing in returned struct from network_fetch"
            assert "info" in ret, "Key authoritative missing in returned struct from network_fetch"
            assert "authoritative" in ret, "Key authoritative missing in returned struct from network_fetch"
            
            
class T0420_networkCreate(AuthTests):
    """ Test network_create """
    
    def do(self):
        try:
            self.superuser.network_destroy('network_test')
        except:
            pass
        try:
            with AssertAccessError(self):
                self.proxy.network_create('network_test', False, "Testnätverk")
                ret = self.superuser.network_fetch('network_test', {"network": True, "info": True, "authoritative": True})
                assert "network" in ret, "Key network missing in returned struct from network_fetch"
                assert "info" in ret, "Key authoritative missing in returned struct from network_fetch"
                assert "authoritative" in ret, "Key authoritative missing in returned struct from network_fetch" 
                assert ret.network == "network_test", "Bad network, is % should be %s" % (ret.network, "network_test")
                assert ret.authoritative == False, "Authoritative is " + ret.authoritative + " but should be False"
        finally:
            try:
                self.superuser.network_destroy('network_test')
            except:
                pass
        
        
class T0430_networkDestroy(AuthTests):
    """ Test network destroy """
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk")
        try:
            with AssertAccessError(self):
                self.proxy.network_destroy('network_test')
                with AssertRPCCError("LookupError::NoSuchNetwork", True):
                    self.superuser.network_fetch('network_test', {"network": True})
        finally:
            try:
                self.superuser.network_destroy('network_test')
            except:
                pass
            
        
class T0440_networkSetAuthoritative(AuthTests):
    """ Test setting authoritative flag on a network"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        try:
            with AssertAccessError(self):
                self.proxy.network_update('network_test', {"authoritative": True})
                nd = self.superuser.network_fetch('network_test', {"network": True, "info": True, "authoritative": True})
                assert nd.network == "network_test", "Bad network"
                assert nd.authoritative, "Bad autoritativity"
                assert nd.info == "Testnätverk 2", "Bad info"
        finally:
            try:
                self.superuser.network_destroy('network_test')
            except:
                pass
                
                
class T0450_networkSetInfo(AuthTests):
    """ Test setting info on a network"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        try:
            with AssertAccessError(self):
                self.proxy.network_update('network_test', {"info": "Provnät 1"})
                nd = self.superuser.network_fetch('network_test', {"network": True, "info": True, "authoritative": True})
                assert nd.network == "network_test", "Bad network"
                assert not nd.authoritative, "Bad autoritativity"
                assert nd.info == "Provnät 1", "Bad info"
        finally:
            try:
                self.superuser.network_destroy('network_test')
            except:
                pass
                
                
class T0460_NetworkSetOption(AuthTests):
    """ Test setting options on a network"""
    
    def do(self):
        try:
            self.superuser.network_destroy('network_test')
        except:
            pass

        self.superuser.network_create('network_test', False, "Testnätverk 2")
        
        try:
            with AssertAccessError(self):
                self.proxy.network_option_set("network_test", "subnet-mask", "255.255.255.0")
                nd = self.superuser.network_fetch('network_test', {"info": True, "network": True, "options": True})
                assert nd.network == "network_test", "Bad network id"
                assert nd.info == "Testnätverk 2", "Bad info"
                assert nd.options["subnet-mask"] == "255.255.255.0", "Bad subnet-mask in options"
                
        finally:
            try:
                self.superuser.network_destroy('network_test')
            except:
                pass
                
                
class T0470_NetworkUnsetOption(AuthTests):
    """ Test unsetting options on a network"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        
        try:
            with AssertAccessError(self):

                self.proxy.network_option_set("network_test", "subnet-mask", "255.255.255.0")
                self.proxy.network_option_unset("network_test", "subnet-mask")
                nd = self.superuser.network_fetch("network_test", {"info": True, "network": True, "options": True})
                assert nd.network == "network_test", "Bad network id"
                assert nd.info == "Testnätverk 2", "Bad info"
                assert "subnet-mask" not in nd.options, "Subnet-mask still in options"
                
        finally:
            try:
                self.superuser.network_destroy('network_test')
            except:
                pass

if __name__ == "__main__":
    sys.exit(main())
