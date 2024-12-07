#!/bin/bash
set -e

# Setup logging directory
mkdir -p /app/logs
mkdir -p /app/logs/picoquic_server
echo "Initializing picoquic_server logs..." > /app/logs/picoquic_server/stdout.log
echo "Initializing picoquic_server logs..." > /app/logs/picoquic_server/stderr.log
mkdir -p /app/logs/picoquic_client
echo "Initializing picoquic_client logs..." > /app/logs/picoquic_client/stdout.log
echo "Initializing picoquic_client logs..." > /app/logs/picoquic_client/stderr.log

# Define helper functions
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> /app/logs/combined.log
}

start_pcap() {
  local interface=$1
  local output=$2
  local duration=$3
  tshark -i "$interface" -a duration:"$duration" -w "$output" &
  echo $!
}

# TODO add loop for multiple iterations

set_environment() {
  log "Setting environment for picoquic_server..."
  export ROLE="server"
  log "Setting environment for picoquic_client..."
  export ROLE="client"
}

# Initialize environment variables
log "Setting up environment variables..."
set_environment

# Start PCAP recording for each service
log "Starting PCAP recording..."
start_pcap "lo" "/app/logs/picoquic_server/pcap_pkt.pcap" 60
start_pcap "lo" "/app/logs/picoquic_client/pcap_pkt.pcap" 60


# Start all services
log "Starting all services..."
log "Starting picoquic_server..."
(
    cd /opt/picoquic_server/picoquic
    timeout  60 ./picoquicdemo -c /opt/certs/cert.pem -k /opt/certs/key.pem -a hq-interop -l - -n servername -D -L  -e lo  -p 4443 > /app/logs/server.log 2> /app/logs/server.err.log \
      >> /app/logs/picoquic_server/stdout.log \
      2>> /app/logs/picoquic_server/stderr.log
    log "picoquic_server completed successfully."
) &
log "Starting picoquic_client..."
(
    sleep 5  # Delay to ensure server is ready
    cd /opt/picoquic_client/picoquic
    timeout  60 ./picoquicdemo -c /opt/certs/cert.pem -k /opt/certs/key.pem -T /opt/ticket/ticket.key -a hq-interop -l - -D -L  -e lo   -v 00000001  127.0.0.1 4443 > /app/logs/client.log 2> /app/logs/client.err.log \
      >> /app/logs/picoquic_client/stdout.log \
      2>> /app/logs/picoquic_client/stderr.log
    log "picoquic_client completed successfully."
) &

# Wait for all services to finish
log "Waiting for services to complete..."
wait

log "All services have completed."