#!/bin/bash -x
# -x: trace every command (with expansions)



# Define helper functions
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /app/logs/ivy_server_entrypoint.log
}
# Export log function so it's available in subshells
export -f log

log_function() {
  local fn_name="$1"
  local start_time=$(date +%s)
  local status_file="/app/logs/ivy_server_function_${fn_name}_status.txt"
  local output_file="/app/logs/ivy_server_function_${fn_name}_output.log"

  # Create header for the output file
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting execution of function: ${fn_name}" > "$output_file"
  echo "----------------------------------------" >> "$output_file"

  # Execute the function and capture output
  shift
  if type "${fn_name}" 2>/dev/null | grep -q 'function'; then
    log "Executing function: ${fn_name}"
    { ${fn_name} "$@" >> "$output_file" 2>&1; }
    local status=$?
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Record completion time and status
    echo "----------------------------------------" >> "$output_file"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Function completed with exit code: $status (duration: ${duration}ms)" >> "$output_file"
    echo "$status" > "$status_file"

    # Log output to main log file
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from function ${fn_name}:" >> /app/logs/ivy_server_commands.log
    cat "$output_file" >> /app/logs/ivy_server_commands.log

    return $status
  else
    log "ERROR: Function ${fn_name} is not defined"
    echo "ERROR: Function ${fn_name} is not defined" >> "$output_file"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Function call failed - function not defined" >> "$output_file"
    echo "1" > "$status_file"
    return 1
  fi
}

check_connectivity() {
  local target="$1"
  local port="$2"
  log "Checking connectivity to $target:$port..."

  # Try ping first to check basic connectivity
  ping -c 3 "$target" > /app/logs/ivy_server_connectivity.log 2>&1
  if [ $? -eq 0 ]; then
    log "Ping to $target successful"
    return 0
  else
    log "Ping to $target failed"
    return 1
  fi
}

resolve_hostname() {
  local hostname="$1"
  local format="${2:-ip}"  # Default to IP format, can be: ip, decimal, hex
  local ip=""

  # Try service discovery file first (most reliable for our services)
  if [ -f "/app/sync_logs/${hostname}_ip.txt" ]; then
    ip=$(cat "/app/sync_logs/${hostname}_ip.txt" 2>/dev/null | head -n1)
    log "Found IP from service discovery: $ip" >&2
  fi

  if [ -z "$ip" ]; then
    # Try getent (most reliable in Docker)
    ip=$(getent hosts "$hostname" 2>/dev/null | awk '{ print $1 }' | head -n1)
  fi

  if [ -z "$ip" ]; then
    # Fallback to nslookup
    ip=$(nslookup "$hostname" 2>/dev/null | grep -A1 'Name:' | grep 'Address:' | tail -n1 | awk '{print $2}')
  fi

  if [ -z "$ip" ]; then
    # Fallback to ping
    ip=$(ping -c 1 "$hostname" 2>/dev/null | grep PING | sed -n 's/.*(\([0-9.]*\)).*/\1/p')
  fi

  if [ -n "$ip" ]; then
    log "Resolved hostname '$hostname' to IP '$ip'" >&2

    # Convert based on requested format
    case "$format" in
      decimal)
        # Convert IP to decimal (for panther_ivy)
        echo "$ip" | awk -F. '{printf("%.0f", ($1 * 256 * 256 * 256) + ($2 * 256 * 256) + ($3 * 256) + $4)}'
        ;;
      hex)
        # Convert IP to hex
        echo "$ip" | awk -F. '{printf("%02X%02X%02X%02X", $1, $2, $3, $4)}'
        ;;
      *)
        # Default: return IP as-is
        echo "$ip"
        ;;
    esac
  else
    log "WARNING: Could not resolve hostname '$hostname'" >&2
    echo "$hostname"  # Return original hostname if resolution fails
  fi
}

# Export the function so it's available in subshells
export -f resolve_hostname

wait_for_dependency() {
  local target="$1"
  local port="${2:-4443}"
  local timeout="${3:-300}"  # Default 5 minutes timeout
  local interval="${4:-5}"   # Check every 5 seconds
  local start_time=$(date +%s)

  log "Waiting for dependency $target:$port to become ready (timeout: ${timeout}s)..."

  # First wait for basic connectivity
  while true; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))

    if [ $elapsed -gt $timeout ]; then
      log "ERROR: Timeout waiting for $target after ${timeout} seconds"
      return 1
    fi

    # Check if host is reachable
    if ping -c 1 -W 2 "$target" >/dev/null 2>&1; then
      log "Host $target is reachable, checking service port..."
      break
    fi

    log "Waiting for $target to become reachable... (${elapsed}s elapsed)"
    sleep $interval
  done

  # For tester services, check for ready marker files
  if [[ "$target" == *"ivy"* ]] || [[ "$target" == *"tester"* ]]; then
    log "Detected tester service, checking for ready marker..."
    local ready_marker="/app/sync_logs/ivy_ready.log"

    while true; do
      current_time=$(date +%s)
      elapsed=$((current_time - start_time))

      if [ $elapsed -gt $timeout ]; then
        log "ERROR: Timeout waiting for tester service $target to be ready after ${timeout} seconds"
        return 1
      fi

      # Check if the ready marker exists
      if [ -f "$ready_marker" ]; then
        log "Tester service $target is ready (found ready marker)"
        return 0
      fi

      log "Waiting for tester service $target to complete initialization... (${elapsed}s elapsed)"
      sleep $interval
    done
  else
    # For regular services, check port availability
    while true; do
      current_time=$(date +%s)
      elapsed=$((current_time - start_time))

      if [ $elapsed -gt $timeout ]; then
        log "ERROR: Timeout waiting for $target:$port after ${timeout} seconds"
        return 1
      fi

      # Use nc (netcat) to check if port is open
      if nc -z -w 2 "$target" "$port" 2>/dev/null; then
        log "Service $target:$port is ready"
        return 0
      fi

      log "Waiting for $target:$port to become available... (${elapsed}s elapsed)"
      sleep $interval
    done
  fi
}

report_exit() {
  local exit_status=$1
  local phase=$2
  local cmd_num=$3
  local cmd_desc=$4

  log "Command $cmd_num in phase $phase exited with status $exit_status: $cmd_desc"
  if [ $exit_status -ne 0 ]; then
    log "ERROR: Command failed with exit status $exit_status"
    echo "$cmd_desc" > /app/logs/ivy_server_last_failed_command.txt
    echo "Exit status: $exit_status" >> /app/logs/ivy_server_last_failed_command.txt
  fi
}

set_environment() {
  # Set environment variables for the service
  export PROTOCOL_TESTED="quic"
  export RUST_LOG="debug"
  export RUST_BACKTRACE="1"
  export SOURCE_DIR="/opt/"
  export IVY_DIR="$SOURCE_DIR/panther_ivy"
  export PYTHON_IVY_DIR="/usr/local/lib/python3.10/dist-packages/"
  export IVY_INCLUDE_PATH="$IVY_INCLUDE_PATH:/usr/local/lib/python3.10/dist-packages/ivy/include/1.7"
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
  : # No-op command to prevent empty function syntax error
}
# Initialize environment variables
log "Setting up environment variables..."
set_environment

# Service discovery: Write our IP to a shared file
SERVICE_NAME="ivy_server"
SERVICE_IP=$(hostname -i | grep -v '^127' | head -n 1)
if [ -n "$SERVICE_IP" ]; then
  echo "$SERVICE_IP" > /app/sync_logs/${SERVICE_NAME}_ip.txt
  log "Registered service IP: $SERVICE_IP"
fi

# Wait for dependencies if this is a client/IUT service


# Function to track command failures with details
execute_with_error_tracking() {
  local phase="$1"
  local cmd="$2"
  local cmd_num="$3"
  local cmd_desc="$4"
  local is_multiline="$5"
  local is_critical="$6"
  local status_file="/app/logs/ivy_server_$phase-cmd-$cmd_num-status.txt"
  local output_file="/app/logs/ivy_server_$phase-cmd-$cmd_num-output.log"

  # Create header for the output file
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting execution of $phase command #$cmd_num" > "$output_file"
  echo "Command: $cmd_desc" >> "$output_file"
  echo "----------------------------------------" >> "$output_file"

  # Execute the command and capture output and status
  if [ "$is_multiline" = "true" ]; then
    # For multiline commands, use eval
    eval "$cmd" >> "$output_file" 2>&1
  else
    # For single line commands, use bash -c
    bash -c "$cmd" >> "$output_file" 2>&1
  fi
  local status=$?

  # Record completion time and status
  echo "----------------------------------------" >> "$output_file"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Command completed with exit code: $status" >> "$output_file"
  echo "$status" > "$status_file"

  # Log the output to main log file
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from $phase command #$cmd_num:" >> /app/logs/ivy_server_commands.log
  cat "$output_file" >> /app/logs/ivy_server_commands.log

  # Report exit status
  report_exit "$status" "$phase" "$cmd_num" "$cmd_desc"

  # Return the command's exit status
  return $status
}

# Execute pre-compilation setup commands
log "Executing pre-compilation commands..."
# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "TARGET_IP=null" "1" "TARGET_IP=null" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "TARGET_IP_DEC=null" "2" "TARGET_IP_DEC=null" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "TARGET_IP_HEX=null" "3" "TARGET_IP_HEX=null" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "echo \"Server mode: target IP will be determined at runtime\" >> /app/logs/ivy_setup.log" "4" "echo \"Server mode: target IP will be determined at runtime\" >> /app/logs/ivy_setup.log" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "IVY_IP=\$(hostname -i | grep -v '^127' | head -n 1)" "5" "IVY_IP=\$(hostname -i | grep -v '^127' | head -n 1)" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "IVY_IP_DEC=\$(resolve_hostname \"\$IVY_IP\" decimal)" "6" "IVY_IP_DEC=\$(resolve_hostname \"\$IVY_IP\" decimal)" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "IVY_IP_HEX=\$(resolve_hostname \"\$IVY_IP\" hex)" "7" "IVY_IP_HEX=\$(resolve_hostname \"\$IVY_IP\" hex)" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "echo \"Local ivy_server IP: \$IVY_IP (decimal: \$IVY_IP_DEC, hex: \$IVY_IP_HEX)\" >> /app/logs/ivy_setup.log" "8" "echo \"Local ivy_server IP: \$IVY_IP (decimal: \$IVY_IP_DEC, hex: \$IVY_IP_HEX)\" >> /app/logs/ivy_setup.log" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "rm -rf /opt/panther_ivy/protocol-testing/quic/build/*" "9" "rm -rf /opt/panther_ivy/protocol-testing/quic/build/*" "false" "true" || {
  exit $?
}


# Execute compilation commands with error checking
log "Executing compilation commands..."
# Set command type for this context
cmd_type="COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing shell builtin: echo 'Updating Ivy tool...' >> /app/logs/ivy_setup.log"
# Use eval to properly execute these special command types while preserving their syntax
eval "echo 'Updating Ivy tool...' >> /app/logs/ivy_setup.log" || {
  exit $?
}

# Set command type for this context
cmd_type="COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing shell builtin: cd /opt/panther_ivy"
# Use eval to properly execute these special command types while preserving their syntax
eval "cd /opt/panther_ivy" || {
  exit $?
}

# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "sudo python3.10 setup.py install >> /app/logs/ivy_setup.log 2>&1" "3" "sudo python3.10 setup.py install >> /app/logs/ivy_setup.log 2>&1" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "cp lib/libz3.so submodules/z3/build/python/z3 >> /app/logs/ivy_setup.log 2>&1" "4" "cp lib/libz3.so submodules/z3/build/python/z3 >> /app/logs/ivy_setup.log 2>&1" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing shell builtin: echo 'Copying updated Ivy files...' >> /app/logs/ivy_setup.log"
# Use eval to properly execute these special command types while preserving their syntax
eval "echo 'Copying updated Ivy files...' >> /app/logs/ivy_setup.log" || {
  exit $?
}

# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "find /opt/panther_ivy/ivy/include/1.7/ -type f -name '*.ivy' -exec cp {} /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ \\; >> /app/logs/ivy_setup.log 2>&1" "6" "find /opt/panther_ivy/ivy/include/1.7/ -type f -name '*.ivy' -exec cp {} /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ \\; >> /app/logs/ivy_setup.log 2>&1" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing shell builtin: echo 'Copying QUIC libraries...' >> /app/logs/ivy_setup.log"
# Use eval to properly execute these special command types while preserving their syntax
eval "echo 'Copying QUIC libraries...' >> /app/logs/ivy_setup.log" || {
  exit $?
}

# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "cp -f -a /opt/picotls/*.a /usr/local/lib/python3.10/dist-packages/ivy/lib/" "8" "cp -f -a /opt/picotls/*.a /usr/local/lib/python3.10/dist-packages/ivy/lib/" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "cp -f -a /opt/picotls/*.a /opt/panther_ivy/ivy/lib/" "9" "cp -f -a /opt/picotls/*.a /opt/panther_ivy/ivy/lib/" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "cp -f /opt/picotls/include/picotls.h /usr/local/lib/python3.10/dist-packages/ivy/include/picotls.h" "10" "cp -f /opt/picotls/include/picotls.h /usr/local/lib/python3.10/dist-packages/ivy/include/picotls.h" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "cp -f /opt/picotls/include/picotls.h /opt/panther_ivy/ivy/include/picotls.h" "11" "cp -f /opt/picotls/include/picotls.h /opt/panther_ivy/ivy/include/picotls.h" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "cp -r -f /opt/picotls/include/picotls/. /usr/local/lib/python3.10/dist-packages/ivy/include/picotls" "12" "cp -r -f /opt/picotls/include/picotls/. /usr/local/lib/python3.10/dist-packages/ivy/include/picotls" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "cp -f /opt/panther_ivy/protocol-testing/quic//quic_utils/quic_ser_deser.h /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/" "13" "cp -f /opt/panther_ivy/protocol-testing/quic//quic_utils/quic_ser_deser.h /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing shell builtin: echo 'Setting up Ivy model...' >> /app/logs/ivy_setup.log"
# Use eval to properly execute these special command types while preserving their syntax
eval "echo 'Setting up Ivy model...' >> /app/logs/ivy_setup.log" || {
  exit $?
}

# Set command type for this context
cmd_type="COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing shell builtin: echo 'Updating include path from /opt/panther_ivy/protocol-testing/quic/' >> /app/logs/ivy_setup.log"
# Use eval to properly execute these special command types while preserving their syntax
eval "echo 'Updating include path from /opt/panther_ivy/protocol-testing/quic/' >> /app/logs/ivy_setup.log" || {
  exit $?
}

# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "find /opt/panther_ivy/protocol-testing/quic/ -type f -name '*.ivy' -exec cp -f {} /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ \\;" "16" "find /opt/panther_ivy/protocol-testing/quic/ -type f -name '*.ivy' -exec cp -f {} /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ \\;" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "ls -l /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ >> /app/logs/ivy_setup.log" "17" "ls -l /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ >> /app/logs/ivy_setup.log" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing shell builtin: cd /opt/panther_ivy/protocol-testing/quic/quic_tests/client_tests ; PYTHONPATH=$PYTHON_IVY_DIR ivyc trace=false show_compiled=false target=test test_iters=300 quic_client_test_max.ivy >> /app/logs/ivy_setup.log 2>&1 || exit 1"
# Use eval to properly execute these special command types while preserving their syntax
eval "cd /opt/panther_ivy/protocol-testing/quic/quic_tests/client_tests ; PYTHONPATH=$PYTHON_IVY_DIR ivyc trace=false show_compiled=false target=test test_iters=300 quic_client_test_max.ivy >> /app/logs/ivy_setup.log 2>&1 || exit 1" || {
  exit $?
}

# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "ls >> /app/logs/ivy_setup.log 2>&1" "19" "ls >> /app/logs/ivy_setup.log 2>&1" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "mkdir -p /opt/panther_ivy/protocol-testing/quic/build/" "20" "mkdir -p /opt/panther_ivy/protocol-testing/quic/build/" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "cp /opt/panther_ivy/protocol-testing/quic/quic_tests/client_tests/quic_client_test_max* /opt/panther_ivy/protocol-testing/quic/build/" "21" "cp /opt/panther_ivy/protocol-testing/quic/quic_tests/client_tests/quic_client_test_max* /opt/panther_ivy/protocol-testing/quic/build/" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "ls /opt/panther_ivy/protocol-testing/quic/build/ >> /app/logs/ivy_setup.log 2>&1" "22" "ls /opt/panther_ivy/protocol-testing/quic/build/ >> /app/logs/ivy_setup.log 2>&1" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "touch /app/sync_logs/ivy_ready.log" "23" "touch /app/sync_logs/ivy_ready.log" "false" "true" || {
  exit $?
}


log "Compilation completed successfully."

# Execute post-compilation commands
log "Executing post-compilation commands..."
# Set command type for this context
cmd_type="POST_COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing shell builtin: cd /opt/panther_ivy/protocol-testing/quic/"
# Use eval to properly execute these special command types while preserving their syntax
eval "cd /opt/panther_ivy/protocol-testing/quic/" || {
  exit $?
}

# Set command type for this context
cmd_type="POST_COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing shell builtin: pwd >> /app/logs/ivy_post_compile.log"
# Use eval to properly execute these special command types while preserving their syntax
eval "pwd >> /app/logs/ivy_post_compile.log" || {
  exit $?
}



# Execute pre-run commands
log "Executing pre-run commands..."


# Execute the main command if provided
log "Executing main command..."
pwd > /app/logs/ivy_server_current_dir_during_exec.log
cd "/opt/panther_ivy/protocol-testing/quic/" || {
  log "Failed to change to directory: /opt/panther_ivy/protocol-testing/quic/"
  exit 1
}


# Prepare command and execute it
# Handle both string and list command_args
FULL_CMD="./build/quic_client_test_max seed=0 the_cid=1 server_port=4443 iversion=1 server_addr=$IVY_IP_DEC"
FULL_CMD="$(echo "$FULL_CMD" | xargs)"  # Trim whitespace

# Resolve hostnames to IPs for better compatibility
# This helps with applications that have DNS resolution issues in Docker
# Match any service pattern: *_server, *_client, *_tester, *_iut
while [[ "$FULL_CMD" =~ ([a-zA-Z][a-zA-Z0-9_-]*_(server|client|tester|iut)) ]]; do
  SERVICE_HOSTNAME="${BASH_REMATCH[0]}"
  SERVICE_IP=$(resolve_hostname "$SERVICE_HOSTNAME")
  if [ -n "$SERVICE_IP" ] && [ "$SERVICE_IP" != "$SERVICE_HOSTNAME" ]; then
    FULL_CMD="${FULL_CMD//$SERVICE_HOSTNAME/$SERVICE_IP}"
    log "Replaced hostname '$SERVICE_HOSTNAME' with IP '$SERVICE_IP' in command"
  else
    # If we can't resolve, break to avoid infinite loop
    break
  fi
done

if [ -z "$FULL_CMD" ]; then
  log "WARNING: No command to run, skipping execution"
  RUN_STATUS=0
else
  log "Running command: $FULL_CMD"

  timeout 100 $FULL_CMD > /app/logs/ivy_server_run_cmd.log 2> /app/logs/ivy_server_run_cmd_error.log
  RUN_STATUS=${PIPESTATUS[0]}
fi

if [ $RUN_STATUS -ne 0 ]; then
  if [ $RUN_STATUS -eq 124 ] || [ $RUN_STATUS -eq 137 ]; then
    log "WARNING: Command timed out after 100 seconds"
  else
    log "ERROR: Command failed with exit status $RUN_STATUS"
  fi
fi

# Execute post-run commands
log "Executing post-run commands..."
# Set command type for this context
cmd_type="POST_RUN"

# Handle regular command
execute_with_error_tracking "$cmd_type" "cp /opt/panther_ivy/protocol-testing/quic/build/quic_client_test_max /app/logs/quic_client_test_max" "1" "cp /opt/panther_ivy/protocol-testing/quic/build/quic_client_test_max /app/logs/quic_client_test_max" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="POST_RUN"

# Handle regular command
execute_with_error_tracking "$cmd_type" "rm /opt/panther_ivy/protocol-testing/quic/build/quic_client_test_max*" "2" "rm /opt/panther_ivy/protocol-testing/quic/build/quic_client_test_max*" "false" "true" || {
  exit $?
}


log "All commands executed successfully. Service 'ivy_server' entrypoint complete."
exit $RUN_STATUS