#!/bin/bash
#
# chkconfig: 35 90 12
# description: AdHoc server
#
# Get function from functions library
. /etc/init.d/functions
# Start the AdHoc server

ADHOC_RUNTIME_HOME=${ADHOC_RUNTIME_HOME:-/server/AdHoc}
ADHOC_USER=bernerus
start() 
{
        echo -n Starting AdHoc server:
        . $ADHOC_RUNTIME_HOME/.bashrc
        /usr/local/bin/daemon -P ${ADHOC_RUNTIME_HOME}/var/run --name=adhoc -d -v -r --user=${ADHOC_USER} --delay=1800  -outlog=/var/log/AdHoc.log python ${ADHOC_RUNTIME_HOME}/bin/adhocserv.py
        ### Create the lock file ###
        success "AdHoc server startup"
        echo
}
# Stop the service AdHoc
stop() {
        echo -n Stopping AdHoc server:
        /usr/local/bin/daemon -P ${ADHOC_RUNTIME_HOME}/var/run --name=adhoc --stop
        echo
}

restart() 
{
	echo -n "Restarting AdHoc server: "
	. $ADHOC_RUNTIME_PATH/.bashrc
	/usr/local/bin/daemon -P ${ADHOC_RUNTIME_HOME}/var/run --name=adhoc --restart
}

status()
{
	if /usr/local/bin/daemon -P ${ADHOC_RUNTIME_HOME}/var/run --name=adhoc --running; then
		echo The AdHoc server is running
	else
		echo The AdHoc server is not running
	fi
}

### main logic ###
case "$1" in
  start)
        start
        ;;
  stop)
        stop
        ;;
  status)
        status AdHoc
        ;;
  restart|reload|condrestart)
        restart
        ;;
  *)
        echo "Usage: $0 {start|stop|restart|reload|status}"
        exit 1
esac
exit 0