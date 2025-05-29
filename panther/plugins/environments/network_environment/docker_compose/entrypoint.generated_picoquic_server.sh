#!/bin/bash -x
# -x: trace every command (with expansions)

set_environment() {
  log "Setting environment for picoquic_server..."
  export ROLE="server"
}

# Initialize environment variables
log "Setting up environment variables..."
set_environment

set -x;
PS4="+ [${BASH_SOURCE:-sh}:${LINENO}] "; export PS4;
export SHELLOPTS
export PATH=$PATH:$ADDITIONAL_PATH;
export PYTHONPATH=$PYTHONPATH:$ADDITIONAL_PYTHONPATH;
env >> /app/logs/ivy_setup.log;
while [ ! -f /app/sync_logs/ivy_ready.log ]; do
	echo "Waiting for Ivy testers to be ready..." >> /app/logs/tester_ready.log;
	sleep 2;
done;
echo "Ivy testers is ready, starting picoquic_server..." >> /app/logs/tester_ready.log;
(touch /app/logs/picoquic_server.pcap; tshark -a duration:200 -i any -w /app/logs/picoquic_server.pcap;) &
echo "Running timeout 200 ./picoquicdemo -a hq-interop -l - -n servername -D -L  -e eth0  -p 4443 > /app/logs/server.log 2> /app/logs/server.err.log" >> /app/logs/picoquic_server_setup.log;
(exec timeout 200 /opt/picoquic/./picoquicdemo -a hq-interop -l - -n servername -D -L  -e eth0  -p 4443 > /app/logs/server.log 2> /app/logs/server.err.log) ;
( cp /opt/picoquic/picoquicdemo /app/logs/picoquicdemo; )'