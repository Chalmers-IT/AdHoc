#!/usr/bin/env python2.6
import inspect
import os
import sys

env_prefix = "ADHOC_"

# Automagic way to find out the home of adhoc.
adhoc_home = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/.."
#print "ADHOC_HOME=", adhoc_home
os.environ[env_prefix + "RUNTIME_HOME"] = adhoc_home  # Export as env variable ADHOC_RUNTIME_HOME if needed outside server

sys.path.append(adhoc_home)
sys.path.append(os.path.join(adhoc_home, 'server'))
sys.path.append(os.path.join(adhoc_home, 'lib'))
sys.path.append(os.path.join(adhoc_home, 'lib','python2.6'))

from rpcc import *
from util import *
from protocol import *


class AdHocServer(Server):
    envvar_prefix = env_prefix
    service_name = "AdHoc"
    major_version = 0
    minor_version = 1
    
    superuser_guard = AdHocSuperuserGuard
    
    
    
class StartMe(object):
    def __init__(self, host, port, generic_password=None, enable_ssl=False):

        ssl_config = None
        if enable_ssl:
            print "Enabling SSL"
            keyfile = os.environ.get('RPCC_SERVER_SSL_KEYFILE', 'etc/rpcc_server.key')
            certfile = os.environ.get('RPCC_SERVER_SSL_CERTFILE', 'etc/rpcc_server.cert')

            ssl_config = SSLConfig(keyfile, certfile)

        srv = AdHocServer(host, port, ssl_config)

        srv.enable_database(MySQLDatabase)
        srv.database.check_rpcc_tables()

        scriptdir = os.path.dirname(os.path.realpath(__file__))
        (scriptparent, tail) = os.path.split(scriptdir)
        serverdir = os.path.join(scriptparent, "lib")

        srv.register_manager(session.DatabaseBackedSessionManager)
        
        srv.register_manager(event.EventManager)
        srv.generic_password=generic_password
        
        srv.register_from_directory(serverdir)
        
        srv.register_manager(authentication.NullAuthenticationManager)
        srv.enable_global_functions()
        srv.enable_documentation()
        srv.enable_static_documents(os.path.join(adhoc_home, 'docroot'))
        srv.enable_digs_and_updates()
        srv.add_protocol_handler("dhcpd", DhcpdConfProtocol)
        srv.serve_forever()
        


if __name__ == "__main__":
    import sys, os
    
    if len(sys.argv) > 1:
        if ':' in sys.argv[1]:
            host, port = sys.argv[1].split(':')
            port = int(port)
        else:
            host = 'localhost'
            port = int(sys.argv[1])
    else:
        host, port = 'localhost', 4433

    generic_password = os.environ.get("ADHOC_GENERIC_PASSWORD", None)

    enable_ssl = os.environ.get("ADHOC_SSL_ENABLE", False)
    
    if enable_ssl:
        print "Serving HTTPS on '%s' port %d." % (host, port)
    else:
        print "Serving HTTP on '%s' port %d." % (host, port)
        
    starter = StartMe(host, port, generic_password=generic_password, enable_ssl=enable_ssl)
    starter.serve_forever()
    
