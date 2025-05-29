#!/bin/bash -x
# -x: trace every command (with expansions)

set_environment() {
  log "Setting environment for picoquic_client..."
  export ROLE="client"
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
echo "Ivy testers is ready, starting picoquic_client..." >> /app/logs/tester_ready.log;
(touch /app/logs/picoquic_client.pcap; tshark -a duration:100 -i any -w /app/logs/picoquic_client.pcap;) &
echo "Running timeout 100 ./picoquicdemo -T /opt/ticket/ticket.key -a hq-interop -l - -D -L  -e eth0   -v 00000001  ivy_server 4443 > /app/logs/client.log 2> /app/logs/client.err.log" >> /app/logs/picoquic_client_setup.log;
(sleep 5; exec timeout 100 /opt/picoquic/./picoquicdemo -T /opt/ticket/ticket.key -a hq-interop -l - -D -L  -e eth0   -v 00000001  ivy_server 4443 > /app/logs/client.log 2> /app/logs/client.err.log) ;
( cp /opt/picoquic/picoquicdemo /app/logs/picoquicdemo; )'