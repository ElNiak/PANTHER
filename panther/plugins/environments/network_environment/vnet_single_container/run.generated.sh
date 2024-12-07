#!/bin/bash
set -e

# Constants
NETNS_DIR="/var/run/netns"
MAX_IFNAME_LEN=15

# Setup logging directory
mkdir -p /app/logs
mkdir -p /app/logs/picoquic_server
echo "Initializing picoquic_server logs..." > /app/logs/picoquic_server/stdout.log
echo "Initializing picoquic_server logs..." > /app/logs/picoquic_server/stderr.log
mkdir -p /app/logs/ivy_client
echo "Initializing ivy_client logs..." > /app/logs/ivy_client/stdout.log
echo "Initializing ivy_client logs..." > /app/logs/ivy_client/stderr.log

# Define helper functions
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> /app/logs/combined.log
}


generate_ifname() {
  local base_name=$1
  if [[ ${#base_name} -gt $MAX_IFNAME_LEN ]]; then
    echo "${base_name:0:$((MAX_IFNAME_LEN - 7))}_$(echo -n "$base_name" | md5sum | cut -c1-6)"
  else
    echo "$base_name"
  fi
}

create_namespace() {
  local namespace=$1
  log "Creating network namespace: $namespace"
  ip netns add "$namespace"
}

setup_veth_pair() {
  local namespace=$1
  local veth_host=$2
  local veth_ns=$3
  local ip_host=$4
  local ip_ns=$5
  log "Setting up veth pair for namespace $namespace..."
  ip link add "$veth_host" type veth peer name "$veth_ns"
  ip link set "$veth_ns" netns "$namespace"
  ip addr add "$ip_host" dev "$veth_host"
  ip netns exec "$namespace" ip addr add "$ip_ns" dev "$veth_ns"
  ip link set "$veth_host" up
  ip netns exec "$namespace" ip link set "$veth_ns" up
  ip netns exec "$namespace" ip link set lo up
}

delete_namespace() {
  local namespace=$1
  log "Deleting network namespace: $namespace"
  ip netns delete "$namespace"
}

# Create namespaces and veth pairs for each service
create_namespace "picoquic_server"
setup_veth_pair \
  "$(generate_ifname veth_picoquic_server)" \
  "picoquic_server" \
  "$(generate_ifname veth_picoquic_server_peer)" \
  "192.168.1.2/24" \
  "/24"
create_namespace "ivy_client"
setup_veth_pair \
  "$(generate_ifname veth_ivy_client)" \
  "ivy_client" \
  "$(generate_ifname veth_ivy_client_peer)" \
  "192.168.1.3/24" \
  "/24"


start_pcap() {
  local namespace=$1
  local interface=$2
  local output=$3
  local duration=$4

  log "Starting PCAP for namespace $namespace on interface $interface..."
  ip netns exec "$namespace" tshark -i "$interface" -a duration:"$duration" -w "$output" &
  echo $!
}

# Initialize environment variables
log "Setting up environment variables..."
log "Setting environment for picoquic_server..."
export ROLE="server"
log "Setting environment for ivy_client..."
export ROLE="client"
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
export TEST_TYPE="server"

# Start PCAP recording for each service
log "Starting PCAP recording..."
start_pcap "picoquic_server" "$(generate_ifname veth_picoquic_server_peer)" \
  "/app/logs/picoquic_server/pcap_pkt.pcap" 60
start_pcap "ivy_client" "$(generate_ifname veth_ivy_client_peer)" \
  "/app/logs/ivy_client/pcap_pkt.pcap" 60

# Start all services
log "Starting all services..."
log "Starting picoquic_server..."
(
  ip netns exec "picoquic_server" \
  cd picoquic
  timeout  60 ./picoquicdemo -c /opt/certs/cert.pem -k /opt/certs/key.pem -a hq-interop -l - -n servername -D -L  -e eth0  -p 4443 > /app/logs/server.log 2> /app/logs/server.err.log \
    >> /app/logs/picoquic_server/stdout.log \
    2>> /app/logs/picoquic_server/stderr.log
  log "picoquic_server completed successfully."
) &
log "Starting ivy_client..."
(
  sleep 5  # Delay to ensure server is ready
  ip netns exec "ivy_client" \
  cd panther_ivy/protocol-testing/quic
  timeout  60 build//quic_server_test_stream seed=0 the_cid=0 server_port=4443 iversion=1 server_addr=0x02 server_cid=0 client_port=4997 client_port_alt=4444 client_addr=0x03 > /app/logs/tester.log 2> /app/logs/tester.err \
    >> /app/logs/ivy_client/stdout.log \
    2>> /app/logs/ivy_client/stderr.log
  log "ivy_client completed successfully."
) &

# Wait for all services to finish
log "Waiting for services to complete..."
wait

# Clean up namespaces
log "Cleaning up namespaces..."
delete_namespace "picoquic_server"
delete_namespace "ivy_client"

log "All services have completed."