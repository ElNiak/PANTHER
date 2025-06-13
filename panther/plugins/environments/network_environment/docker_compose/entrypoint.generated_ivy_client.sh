#!/bin/bash -x
# -x: trace every command (with expansions)



# Define helper functions
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /app/logs/ivy_client_entrypoint.log
}

log_function() {
  local fn_name="$1"
  local start_time=$(date +%s)
  local status_file="/app/logs/ivy_client_function_${fn_name}_status.txt"
  local output_file="/app/logs/ivy_client_function_${fn_name}_output.log"

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
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from function ${fn_name}:" >> /app/logs/ivy_client_commands.log
    cat "$output_file" >> /app/logs/ivy_client_commands.log

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
  ping -c 3 "$target" > /app/logs/ivy_client_connectivity.log 2>&1
  if [ $? -eq 0 ]; then
    log "Ping to $target successful"
    return 0
  else
    log "Ping to $target failed"
    return 1
  fi
}

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
    echo "$cmd_desc" > /app/logs/ivy_client_last_failed_command.txt
    echo "Exit status: $exit_status" >> /app/logs/ivy_client_last_failed_command.txt
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
  export TEST_TYPE="server"
  : # No-op command to prevent empty function syntax error
}
# Initialize environment variables
log "Setting up environment variables..."
set_environment

# Wait for dependencies if this is a client/IUT service
log "This service depends on: picoquic_server"
wait_for_dependency "picoquic_server" "4443" || {
  log "ERROR: Failed to connect to dependency picoquic_server"
  exit 1
}


# Function to track command failures with details
execute_with_error_tracking() {
  local phase="$1"
  local cmd="$2"
  local cmd_num="$3"
  local cmd_desc="$4"
  local is_multiline="$5"
  local is_critical="$6"
  local status_file="/app/logs/ivy_client_$phase-cmd-$cmd_num-status.txt"
  local output_file="/app/logs/ivy_client_$phase-cmd-$cmd_num-output.log"

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
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from $phase command #$cmd_num:" >> /app/logs/ivy_client_commands.log
  cat "$output_file" >> /app/logs/ivy_client_commands.log

  # Report exit status
  report_exit "$status" "$phase" "$cmd_num" "$cmd_desc"

  # Return the command's exit status
  return $status
}

# Execute pre-compilation setup commands
log "Executing pre-compilation commands..."
# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle simple function call
log "Executing function call: TARGET_IP=$(getent hosts picoquic_server | awk '{print $1}' | grep -v '^127' | head -n 1)"
# Check if function exists first to avoid errors
if declare -f TARGET_IP=$(getent hosts picoquic_server | awk '{print $1}' | grep -v '^127' | head -n 1) > /dev/null; then
  TARGET_IP=$(getent hosts picoquic_server | awk '{print $1}' | grep -v '^127' | head -n 1) || {
    exit $?
  }
else
  log "ERROR: Function TARGET_IP=$(getent hosts picoquic_server | awk '{print $1}' | grep -v '^127' | head -n 1) not defined"
  exit 1
fi

# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle non-critical command
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
echo "Resolved picoquic_server TARGET_IP IP - $TARGET_IP" >> /app/logs/ivy_setup.log
ENDOFCOMMAND
)

# This command is marked as non-critical, execute it but don't fail if it returns error
log "Executing non-critical $cmd_type command #2"
execute_with_error_tracking "$cmd_type" "$MULTILINE_CMD" "2" "echo \"Resolved picoquic_server TARGET_IP IP - $TARGET_IP\" >> /app/logs/ivy_setup.log" "false" "false" || {
  log "WARNING: Non-critical command failed but continuing execution"
}

# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle simple function call
log "Executing function call: IVY_IP=$(hostname -I | awk '{print $1}' | grep -v '^127' | head -n 1)"
# Check if function exists first to avoid errors
if declare -f IVY_IP=$(hostname -I | awk '{print $1}' | grep -v '^127' | head -n 1) > /dev/null; then
  IVY_IP=$(hostname -I | awk '{print $1}' | grep -v '^127' | head -n 1) || {
    exit $?
  }
else
  log "ERROR: Function IVY_IP=$(hostname -I | awk '{print $1}' | grep -v '^127' | head -n 1) not defined"
  exit 1
fi

# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle non-critical command
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
echo "Resolved ivy_client IVY_IP IP - $IVY_IP" >> /app/logs/ivy_setup.log
ENDOFCOMMAND
)

# This command is marked as non-critical, execute it but don't fail if it returns error
log "Executing non-critical $cmd_type command #4"
execute_with_error_tracking "$cmd_type" "$MULTILINE_CMD" "4" "echo \"Resolved ivy_client IVY_IP IP - $IVY_IP\" >> /app/logs/ivy_setup.log" "false" "false" || {
  log "WARNING: Non-critical command failed but continuing execution"
}

# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle simple function call
log "Executing function call: TARGET_IP_HEX=$(ip_to_decimal $TARGET_IP)"
# Check if function exists first to avoid errors
if declare -f TARGET_IP_HEX=$(ip_to_decimal $TARGET_IP) > /dev/null; then
  TARGET_IP_HEX=$(ip_to_decimal $TARGET_IP) || {
    exit $?
  }
else
  log "ERROR: Function TARGET_IP_HEX=$(ip_to_decimal $TARGET_IP) not defined"
  exit 1
fi

# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle simple function call
log "Executing function call: IVY_IP_HEX=$(ip_to_decimal $IVY_IP)"
# Check if function exists first to avoid errors
if declare -f IVY_IP_HEX=$(ip_to_decimal $IVY_IP) > /dev/null; then
  IVY_IP_HEX=$(ip_to_decimal $IVY_IP) || {
    exit $?
  }
else
  log "ERROR: Function IVY_IP_HEX=$(ip_to_decimal $IVY_IP) not defined"
  exit 1
fi

# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle non-critical command
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
echo "Resolved picoquic_server IP in hex - $TARGET_IP_HEX" >> /app/logs/ivy_setup.log
ENDOFCOMMAND
)

# This command is marked as non-critical, execute it but don't fail if it returns error
log "Executing non-critical $cmd_type command #7"
execute_with_error_tracking "$cmd_type" "$MULTILINE_CMD" "7" "echo \"Resolved picoquic_server IP in hex - $TARGET_IP_HEX\" >> /app/logs/ivy_setup.log" "false" "false" || {
  log "WARNING: Non-critical command failed but continuing execution"
}

# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle non-critical command
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
echo "Resolved ivy_client IP in hex - $IVY_IP_HEX" >> /app/logs/ivy_setup.log
ENDOFCOMMAND
)

# This command is marked as non-critical, execute it but don't fail if it returns error
log "Executing non-critical $cmd_type command #8"
execute_with_error_tracking "$cmd_type" "$MULTILINE_CMD" "8" "echo \"Resolved ivy_client IP in hex - $IVY_IP_HEX\" >> /app/logs/ivy_setup.log" "false" "false" || {
  log "WARNING: Non-critical command failed but continuing execution"
}

# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "rm -rf /opt/panther_ivy/protocol-testing/quic/build/*" "9" "rm -rf /opt/panther_ivy/protocol-testing/quic/build/*" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle function definition
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
ip_to_hex() {
    echo "$1" | awk -F. '{printf("%02X%02X%02X%02X", $1, $2, $3, $4)}';
}
ENDOFCOMMAND
)
# This is a function definition, needs to be defined in the global scope
log "Executing function definition: Function: ip_to_hex"
# Export the function to ensure it's available to all subprocesses
eval "$MULTILINE_CMD"
# Verify the function was properly defined
# Extract function name more reliably - handle both "name()" and "name() {" formats
FUNC_NAME=$(echo "ip_to_hex() {
    echo "$1" | awk -F. '{printf("%02X%02X%02X%02X", $1, $2, $3, $4)}';
}" | grep -o '^[[:space:]]*[[:alnum:]_]*[[:space:]]*()' | sed 's/[[:space:]]*()$//' | xargs)
if ! declare -f "$FUNC_NAME" > /dev/null; then
  log "ERROR: Function $FUNC_NAME failed to define correctly"
  exit 1
else
  log "Function $FUNC_NAME defined successfully"
fi

# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle function definition
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
ip_to_decimal() {
    echo "$1" | awk -F. '{printf("%.0f", ($1 * 256 * 256 * 256) + ($2 * 256 * 256) + ($3 * 256) + $4)}';
}
ENDOFCOMMAND
)
# This is a function definition, needs to be defined in the global scope
log "Executing function definition: Function: ip_to_decimal"
# Export the function to ensure it's available to all subprocesses
eval "$MULTILINE_CMD"
# Verify the function was properly defined
# Extract function name more reliably - handle both "name()" and "name() {" formats
FUNC_NAME=$(echo "ip_to_decimal() {
    echo "$1" | awk -F. '{printf("%.0f", ($1 * 256 * 256 * 256) + ($2 * 256 * 256) + ($3 * 256) + $4)}';
}" | grep -o '^[[:space:]]*[[:alnum:]_]*[[:space:]]*()' | sed 's/[[:space:]]*()$//' | xargs)
if ! declare -f "$FUNC_NAME" > /dev/null; then
  log "ERROR: Function $FUNC_NAME failed to define correctly"
  exit 1
else
  log "Function $FUNC_NAME defined successfully"
fi



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
execute_with_error_tracking "$cmd_type" "find /opt/panther_ivy/ivy/include/1.7/ -type f -name '*.ivy' -exec cp {} /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ \; >> /app/logs/ivy_setup.log 2>&1" "6" "find /opt/panther_ivy/ivy/include/1.7/ -type f -name '*.ivy' -exec cp {} /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ \; >> /app/logs/ivy_setup.log 2>&1" "false" "true" || {
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
execute_with_error_tracking "$cmd_type" "find /opt/panther_ivy/protocol-testing/quic/ -type f -name '*.ivy' -exec cp -f {} /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ \;" "16" "find /opt/panther_ivy/protocol-testing/quic/ -type f -name '*.ivy' -exec cp -f {} /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ \;" "false" "true" || {
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

# Handle command with && operator
log "Command contains && operator: cd /opt/panther_ivy/protocol-testing/quic/quic_tests/server_tests && PYTHONPATH=$PYTHON_IVY_DIR ivyc trace=false show_compiled=false target=test test_iters=300 quic_server_test_stream.ivy >> /app/logs/ivy_setup.log 2>&1 || exit 1"

# Extract parts of the command before and after &&
FIRST_PART="cd /opt/panther_ivy/protocol-testing/quic/quic_tests/server_tests "
REST_OF_CMD=" PYTHONPATH=$PYTHON_IVY_DIR ivyc trace=false show_compiled=false target=test test_iters=300 quic_server_test_stream.ivy >> /app/logs/ivy_setup.log 2>&1 || exit 1"

# Create output files for this command
FIRST_OUTPUT="/app/logs/ivy_client_$cmd_type-cmd18_first_part.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting execution of $cmd_type command #18 first part" > "$FIRST_OUTPUT"
echo "Command: ${FIRST_PART}" >> "$FIRST_OUTPUT"
echo "----------------------------------------" >> "$FIRST_OUTPUT"

# First execute the part before && and capture output
log "Executing first part: ${FIRST_PART}"
# Check if this is a function call - needs special handling
if type "$(echo "${FIRST_PART}" | awk '{print $1}')" 2>/dev/null | grep -q 'function'; then
  # Part is a function call, use eval to execute in current shell context
  FUNCTION_NAME=$(echo "${FIRST_PART}" | awk '{print $1}')
  FUNCTION_ARGS=$(echo "${FIRST_PART}" | awk '{$1=""; print $0}')
  log "Detected function call to: ${FUNCTION_NAME}"
  # Use log_function helper for tracking
  log_function ${FUNCTION_NAME} ${FUNCTION_ARGS} >> "$FIRST_OUTPUT" 2>&1
  FIRST_STATUS=$?
else
  # Not a function call, use bash -c as before
  bash -c "${FIRST_PART}" >> "$FIRST_OUTPUT" 2>&1
  FIRST_STATUS=$?
fi

# Record completion time for first part
echo "----------------------------------------" >> "$FIRST_OUTPUT"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] First part completed with exit code: $FIRST_STATUS" >> "$FIRST_OUTPUT"

# Log the captured output
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from $cmd_type command #18 first part:" >> /app/logs/ivy_client_commands.log
cat "$FIRST_OUTPUT" >> /app/logs/ivy_client_commands.log

if [ $FIRST_STATUS -eq 0 ]; then
  # If first part succeeded, execute rest of command
  log "First part succeeded. Executing rest: ${REST_OF_CMD}"
  REST_OUTPUT="/app/logs/ivy_client_$cmd_type-cmd18_rest.log"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting execution of $cmd_type command #18 rest part" > "$REST_OUTPUT"
  echo "Command: ${REST_OF_CMD}" >> "$REST_OUTPUT"
  echo "----------------------------------------" >> "$REST_OUTPUT"

  # Execute rest of command - check if it's a function call
  if [ -n "${REST_OF_CMD}" ] && type "$(echo "${REST_OF_CMD}" | awk '{print $1}')" 2>/dev/null | grep -q 'function'; then
    # Part is a function call, use eval to execute in current shell context
    FUNCTION_NAME=$(echo "${REST_OF_CMD}" | awk '{print $1}')
    FUNCTION_ARGS=$(echo "${REST_OF_CMD}" | awk '{$1=""; print $0}')
    log "Detected function call to: ${FUNCTION_NAME}"
    # Use log_function helper for tracking
    log_function ${FUNCTION_NAME} ${FUNCTION_ARGS} >> "$REST_OUTPUT" 2>&1
    REST_STATUS=$?
  else
    # Not a function call, use bash -c as before
    bash -c "${REST_OF_CMD}" >> "$REST_OUTPUT" 2>&1
    REST_STATUS=$?
  fi

  # Record completion time for rest part
  echo "----------------------------------------" >> "$REST_OUTPUT"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rest part completed with exit code: $REST_STATUS" >> "$REST_OUTPUT"

  # Log the captured output
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from $cmd_type command #18 rest part:" >> /app/logs/ivy_client_commands.log
  cat "$REST_OUTPUT" >> /app/logs/ivy_client_commands.log

  # Exit with status from rest part
  if [ $REST_STATUS -ne 0 ]; then
    exit $REST_STATUS
  fi
else
  exit $FIRST_STATUS
fi


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
execute_with_error_tracking "$cmd_type" "cp /opt/panther_ivy/protocol-testing/quic/quic_tests/server_tests/quic_server_test_stream* /opt/panther_ivy/protocol-testing/quic/build/" "21" "cp /opt/panther_ivy/protocol-testing/quic/quic_tests/server_tests/quic_server_test_stream* /opt/panther_ivy/protocol-testing/quic/build/" "false" "true" || {
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
log "Executing shell builtin: cd /opt/panther_ivy/protocol-testing/quic/;"
# Use eval to properly execute these special command types while preserving their syntax
eval "cd /opt/panther_ivy/protocol-testing/quic/;" || {
  exit $?
}



# Execute pre-run commands
log "Executing pre-run commands..."


# Execute the main command if provided
log "Executing main command..."
pwd > /app/logs/ivy_client_current_dir_during_exec.log
cd "/opt/panther_ivy/protocol-testing/quic/" || {
  log "Failed to change to directory: /opt/panther_ivy/protocol-testing/quic/"
  exit 1
}


# Prepare command and execute it
FULL_CMD="./build/quic_server_test_stream "
FULL_CMD="$(echo "$FULL_CMD" | xargs)"  # Trim whitespace

if [ -z "$FULL_CMD" ]; then
  log "WARNING: No command to run, skipping execution"
  RUN_STATUS=0
else
  log "Running command: $FULL_CMD"

  timeout 100 $FULL_CMD > /app/logs/ivy_client_run_cmd.log 2> /app/logs/ivy_client_run_cmd_error.log
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
execute_with_error_tracking "$cmd_type" "cp /opt/panther_ivy/protocol-testing/quic/build/quic_server_test_stream /app/logs/quic_server_test_stream" "1" "cp /opt/panther_ivy/protocol-testing/quic/build/quic_server_test_stream /app/logs/quic_server_test_stream" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="POST_RUN"

# Handle regular command
execute_with_error_tracking "$cmd_type" "rm /opt/panther_ivy/protocol-testing/quic/build/quic_server_test_stream*" "2" "rm /opt/panther_ivy/protocol-testing/quic/build/quic_server_test_stream*" "false" "true" || {
  exit $?
}


log "All commands executed successfully. Service 'ivy_client' entrypoint complete."
exit $RUN_STATUS