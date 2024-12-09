#!/bin/bash
set -e

# Setup logging directory
mkdir -p /app/logs
mkdir -p /app/logs/picoquic_client
echo "Initializing picoquic_client logs..." > /app/logs/picoquic_client/stdout.log
echo "Initializing picoquic_client logs..." > /app/logs/picoquic_client/stderr.log
mkdir -p /app/logs/ivy_server
echo "Initializing ivy_server logs..." > /app/logs/ivy_server/stdout.log
echo "Initializing ivy_server logs..." > /app/logs/ivy_server/stderr.log

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
  log "Setting environment for picoquic_client..."
  export ROLE="client"
  log "Setting environment for ivy_server..."
  export ROLE="server"
  export PROTOCOL_TESTED="quic"
  export RUST_LOG="debug"
  export RUST_BACKTRACE="1"
  export SOURCE_DIR="/opt/"
  export IVY_DIR="$SOURCE_DIR/panther_ivy"
  export PYTHON_IVY_DIR="/usr/local/lib/python3.10/dist-packages/ms_ivy-1.8.25-py3.10-linux-x86_64.egg/"
  export IVY_INCLUDE_PATH="$IVY_INCLUDE_PATH:/usr/local/lib/python3.10/dist-packages/ms_ivy-1.8.25-py3.10-linux-x86_64.egg/ivy/include/1.7"
  export Z3_LIBRARY_DIRS="$IVY_DIR/submodules/z3/build"
  export Z3_LIBRARY_PATH="$IVY_DIR/submodules/z3/build"
  export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$IVY_DIR/submodules/z3/build"
  export PROOTPATH="$SOURCE_DIR"
  export ADDITIONAL_PYTHONPATH="/app/implementations/quic-implementations/aioquic/src/:$IVY_DIR/submodules/z3/build/python:$PYTHON_IVY_DIR"
  export ADDITIONAL_PATH="/go/bin:$IVY_DIR/submodules/z3/build"
  export TEST_ALPN="hq-interop"
  export ZRTT_SSLKEYLOGFILE="$SOURCE_DIR/panther_ivy/protocol-testing/quic/last_tls_key.txt"
  export RETRY_TOKEN_FILE="$SOURCE_DIR/panther_ivy/protocol-testing/quic/last_retry_token.txt"
  export NEW_TOKEN_FILE="$SOURCE_DIR/panther_ivy/protocol-testing/quic/last_new_token.txt"
  export ENCRYPT_TICKET_FILE="$SOURCE_DIR/panther_ivy/protocol-testing/quic/last_encrypt_session_ticket.txt"
  export SESSION_TICKET_FILE="$SOURCE_DIR/panther_ivy/protocol-testing/quic/last_session_ticket_cb.txt"
  export SAVED_PACKET="$SOURCE_DIR/panther_ivy/protocol-testing/quic/saved_packet.txt"
  export initial_max_stream_id_bidi="$SOURCE_DIR/panther_ivy/protocol-testing/quic/initial_max_stream_id_bidi.txt"
  export active_connection_id_limit="$SOURCE_DIR/panther_ivy/protocol-testing/quic/active_connection_id_limit.txt"
  export initial_max_stream_data_bidi_local="$SOURCE_DIR/panther_ivy/protocol-testing/quic/initial_max_stream_data_bidi_local.txt"
  export initial_max_stream_data_bidi_remote="$SOURCE_DIR/panther_ivy/protocol-testing/quic/initial_max_stream_data_bidi_remote.txt"
  export initial_max_stream_data_uni="$SOURCE_DIR/panther_ivy/protocol-testing/quic/initial_max_stream_data_uni.txt"
  export initial_max_data="$SOURCE_DIR/panther_ivy/protocol-testing/quic/initial_max_data.txt"
  export INITIAL_VERSION="1"
  export TEST_TYPE="client"
}

# Initialize environment variables
log "Setting up environment variables..."
set_environment

# Start PCAP recording for each service
log "Starting PCAP recording..."
start_pcap "lo" "/app/logs/picoquic_client/pcap_pkt.pcap" 60
start_pcap "lo" "/app/logs/ivy_server/pcap_pkt.pcap" 60


# Start all services
log "Starting all services..."
log "Starting picoquic_client..."
(
    sleep 5  # Delay to ensure server is ready
    cd /opt/picoquic_client/picoquic
    timeout  60 ./picoquicdemo -c /opt/certs/cert.pem -k /opt/certs/key.pem -T /opt/ticket/ticket.key -a hq-interop -l - -D -L  -e lo   -v 00000001  127.0.0.1 4443 > /app/logs/client.log 2> /app/logs/client.err.log \
      >> /app/logs/picoquic_client/stdout.log \
      2>> /app/logs/picoquic_client/stderr.log
    log "picoquic_client completed successfully."
) &
log "Starting ivy_server..."
(
    cd /opt/panther_ivy/protocol-testing/quic
    timeout  60 build//quic_client_test_max seed=0 the_cid=0 server_port=4443 iversion=1 server_addr=0x7f000001 server_cid=0 > /app/logs/testers.log 2> /app/logs/testers.err \
      >> /app/logs/ivy_server/stdout.log \
      2>> /app/logs/ivy_server/stderr.log
    log "ivy_server completed successfully."
) &

# Wait for all services to finish
log "Waiting for services to complete..."
wait

log "All services have completed."