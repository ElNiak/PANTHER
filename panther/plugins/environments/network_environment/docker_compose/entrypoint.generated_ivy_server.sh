#!/bin/bash -x
# -x: trace every command (with expansions)

# Define helper functions
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /app/logs/ivy_server_entrypoint.log
}

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
  export IVY_DIR="/opt//panther_ivy"
  export PYTHON_IVY_DIR="/usr/local/lib/python3.10/dist-packages/"
  export IVY_INCLUDE_PATH="$$IVY_INCLUDE_PATH:/usr/local/lib/python3.10/dist-packages/ivy/include/1.7"
  export Z3_LIBRARY_DIRS="/opt//panther_ivy/submodules/z3/build"
  export Z3_LIBRARY_PATH="/opt//panther_ivy/submodules/z3/build"
  export LD_LIBRARY_PATH="$$LD_LIBRARY_PATH:/opt//panther_ivy/submodules/z3/build"
  export PROOTPATH="/opt/"
  export ADDITIONAL_PYTHONPATH="/app/implementations/quic-implementations/aioquic/src/:/opt//panther_ivy/submodules/z3/build/python:/usr/local/lib/python3.10/dist-packages/"
  export ADDITIONAL_PATH="/go/bin:/opt//panther_ivy/submodules/z3/build"
  export TEST_ALPN="hq-interop"
  export ZRTT_SSLKEYLOGFILE="/opt//panther_ivy/protocol-testing/quic/last_tls_key.txt"
  export RETRY_TOKEN_FILE="/opt//panther_ivy/protocol-testing/quic/last_retry_token.txt"
  export NEW_TOKEN_FILE="/opt//panther_ivy/protocol-testing/quic/last_new_token.txt"
  export ENCRYPT_TICKET_FILE="/opt//panther_ivy/protocol-testing/quic/last_encrypt_session_ticket.txt"
  export SESSION_TICKET_FILE="/opt//panther_ivy/protocol-testing/quic/last_session_ticket_cb.txt"
  export SAVED_PACKET="/opt//panther_ivy/protocol-testing/quic/saved_packet.txt"
  export initial_max_stream_id_bidi="/opt//panther_ivy/protocol-testing/quic/initial_max_stream_id_bidi.txt"
  export active_connection_id_limit="/opt//panther_ivy/protocol-testing/quic/active_connection_id_limit.txt"
  export initial_max_stream_data_bidi_local="/opt//panther_ivy/protocol-testing/quic/initial_max_stream_data_bidi_local.txt"
  export initial_max_stream_data_bidi_remote="/opt//panther_ivy/protocol-testing/quic/initial_max_stream_data_bidi_remote.txt"
  export initial_max_stream_data_uni="/opt//panther_ivy/protocol-testing/quic/initial_max_stream_data_uni.txt"
  export initial_max_data="/opt//panther_ivy/protocol-testing/quic/initial_max_data.txt"
  export INITIAL_VERSION="1"
  export TEST_TYPE="client"
  : # No-op command to prevent empty function syntax error
}
# Initialize environment variables
log "Setting up environment variables..."
set_environment



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
execute_with_error_tracking "$cmd_type" "set -x;" "1" "set -x;" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "export SHELLOPTS" "2" "export SHELLOPTS" "false" "true" || {
  exit $?
}
# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle non-critical command
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
export PATH=$PATH:$ADDITIONAL_PATH;
ENDOFCOMMAND
)

# This command is marked as non-critical, execute it but don't fail if it returns error
log "Executing non-critical $cmd_type command #3"
execute_with_error_tracking "$cmd_type" "$MULTILINE_CMD" "3" "export PATH=$PATH:$ADDITIONAL_PATH;" "false" "false" || {
  log "WARNING: Non-critical command failed but continuing execution"
}

# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle non-critical command
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
export PYTHONPATH=$PYTHONPATH:$ADDITIONAL_PYTHONPATH;
ENDOFCOMMAND
)

# This command is marked as non-critical, execute it but don't fail if it returns error
log "Executing non-critical $cmd_type command #4"
execute_with_error_tracking "$cmd_type" "$MULTILINE_CMD" "4" "export PYTHONPATH=$PYTHONPATH:$ADDITIONAL_PYTHONPATH;" "false" "false" || {
  log "WARNING: Non-critical command failed but continuing execution"
}

# Set command type for this context
cmd_type="PRE_COMPILE"

# Handle non-critical command
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
env >> /app/logs/env.log;
ENDOFCOMMAND
)

# This command is marked as non-critical, execute it but don't fail if it returns error
log "Executing non-critical $cmd_type command #5"
execute_with_error_tracking "$cmd_type" "$MULTILINE_CMD" "5" "env >> /app/logs/env.log;" "false" "false" || {
  log "WARNING: Non-critical command failed but continuing execution"
}


# Execute compilation commands with error checking
log "Executing compilation commands..."

# Set command type for this context
cmd_type="COMPILE"

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
if ! declare -f ip_to_hex > /dev/null; then
  log "ERROR: Function ip_to_hex failed to define correctly"
  exit 1
else
  log "Function ip_to_hex defined successfully"
fi


# Set command type for this context
cmd_type="COMPILE"

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
if ! declare -f ip_to_decimal > /dev/null; then
  log "ERROR: Function ip_to_decimal failed to define correctly"
  exit 1
else
  log "Function ip_to_decimal defined successfully"
fi


# Set command type for this context
cmd_type="COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing variable assignment: TARGET_IP=$(getent hosts  | awk '{print $1}' | grep -v '^127' | head -n 1)"
# Use eval to properly execute these special command types while preserving their syntax
eval "TARGET_IP=$(getent hosts  | awk '{print $1}' | grep -v '^127' | head -n 1)" || {
  exit $?
}


# Set command type for this context
cmd_type="COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing variable assignment: IVY_IP=$(hostname -I | awk \"{print \$1}\" | grep -v \"^127\" | head -n 1)"
# Use eval to properly execute these special command types while preserving their syntax
eval "IVY_IP=$(hostname -I | awk "{print \$1}" | grep -v "^127" | head -n 1)" || {
  exit $?
}


# Set command type for this context
cmd_type="COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing variable assignment: TARGET_IP_HEX=$(ip_to_decimal $TARGET_IP)"
# Use eval to properly execute these special command types while preserving their syntax
eval "TARGET_IP_HEX=$(ip_to_decimal $TARGET_IP)" || {
  exit $?
}


# Set command type for this context
cmd_type="COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing variable assignment: IVY_IP_HEX=$(ip_to_decimal $IVY_IP)"
# Use eval to properly execute these special command types while preserving their syntax
eval "IVY_IP_HEX=$(ip_to_decimal $IVY_IP)" || {
  exit $?
}


# Set command type for this context
cmd_type="COMPILE"

# Handle function definition
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
quic_lib_setup() {
        echo "Copying QUIC libraries..." >> /app/logs/ivy_setup.log
        cp -f -a /opt/picotls/*.a "/usr/local/lib/python3.10/dist-packages/ivy/lib/"
        cp -f -a /opt/picotls/*.a "/opt/panther_ivy/ivy/lib/"
        cp -f /opt/picotls/include/picotls.h "/usr/local/lib/python3.10/dist-packages/ivy/include/picotls.h"
        cp -f /opt/picotls/include/picotls.h "/opt/panther_ivy/ivy/include/picotls.h"
        cp -r -f /opt/picotls/include/picotls/. "/usr/local/lib/python3.10/dist-packages/ivy/include/picotls"
        
        # Add the correct path for quic_ser_deser.h based on configuration
        if [ -f "/opt/panther_ivy/protocol-testing/quic//quic_utils/quic_ser_deser.h" ]; then
            cp -f "/opt/panther_ivy/protocol-testing/quic//quic_utils/quic_ser_deser.h" "/usr/local/lib/python3.10/dist-packages/ivy/include/1.7/"
        else
            echo "Warning: quic_ser_deser.h not found at /opt/panther_ivy/protocol-testing/quic//quic_utils/quic_ser_deser.h" >> /app/logs/ivy_setup.log
        fi
    }
ENDOFCOMMAND
)
# This is a function definition, needs to be defined in the global scope
log "Executing function definition: Function: quic_lib_setup"
# Export the function to ensure it's available to all subprocesses
eval "$MULTILINE_CMD"
# Verify the function was properly defined
if ! declare -f quic_lib_setup > /dev/null; then
  log "ERROR: Function quic_lib_setup failed to define correctly"
  exit 1
else
  log "Function quic_lib_setup defined successfully"
fi


# Set command type for this context
cmd_type="COMPILE"

# Handle simple function call
log "Executing function call: quic_lib_setup"
# Check if function exists first to avoid errors
if declare -f quic_lib_setup > /dev/null; then
  quic_lib_setup || {
    exit $?
  }
else
  log "ERROR: Function quic_lib_setup not defined"
  exit 1
fi


# Set command type for this context
cmd_type="COMPILE"

# Handle command with && operator
log "Command contains && operator: quic_lib_setup &&"

# Extract parts of the command before and after &&
FIRST_PART="quic_lib_setup "
REST_OF_CMD=""

# Create output files for this command
FIRST_OUTPUT="/app/logs/ivy_server_$cmd_type-cmd9_first_part.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting execution of $cmd_type command #9 first part" > "$FIRST_OUTPUT"
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
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from $cmd_type command #9 first part:" >> /app/logs/ivy_server_commands.log
cat "$FIRST_OUTPUT" >> /app/logs/ivy_server_commands.log

if [ $FIRST_STATUS -eq 0 ]; then
  # If first part succeeded, execute rest of command
  log "First part succeeded. Executing rest: ${REST_OF_CMD}"
  REST_OUTPUT="/app/logs/ivy_server_$cmd_type-cmd9_rest.log"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting execution of $cmd_type command #9 rest part" > "$REST_OUTPUT"
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
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from $cmd_type command #9 rest part:" >> /app/logs/ivy_server_commands.log
  cat "$REST_OUTPUT" >> /app/logs/ivy_server_commands.log
  
  # Exit with status from rest part
  if [ $REST_STATUS -ne 0 ]; then
    exit $REST_STATUS
  fi
else
  exit $FIRST_STATUS
fi


# Set command type for this context
cmd_type="COMPILE"

# Handle function definition
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
update_ivy_tool() {
    echo "Updating Ivy tool..." >> /app/logs/ivy_setup.log;
    cd "/opt/panther_ivy" || exit 1;
    cat setup.py >> /app/logs/ivy_setup.log;
    sudo python3.10 setup.py install >> /app/logs/ivy_setup.log 2>&1 &&
    cp lib/libz3.so submodules/z3/build/python/z3 >> /app/logs/ivy_setup.log 2>&1 &&
    echo "Copying updated Ivy files..." >> /app/logs/ivy_setup.log;
    find /opt/panther_ivy/ivy/include/1.7/ -type f -name "*.ivy" -exec cp {} /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ \; >> /app/logs/ivy_setup.log 2>&1;
    echo "Copying updated Z3 files..." >> /app/logs/ivy_setup.log 2>&1;
    cp -f -a /opt/panther_ivy/ivy/lib/*.a "/usr/local/lib/python3.10/dist-packages/ivy/lib/" >> /app/logs/ivy_setup.log 2>&1;
}
ENDOFCOMMAND
)
# This is a function definition, needs to be defined in the global scope
log "Executing function definition: Function: update_ivy_tool"
# Export the function to ensure it's available to all subprocesses
eval "$MULTILINE_CMD"
# Verify the function was properly defined
if ! declare -f update_ivy_tool > /dev/null; then
  log "ERROR: Function update_ivy_tool failed to define correctly"
  exit 1
else
  log "Function update_ivy_tool defined successfully"
fi


# Set command type for this context
cmd_type="COMPILE"

# Handle simple function call
log "Executing function call: update_ivy_tool"
# Check if function exists first to avoid errors
if declare -f update_ivy_tool > /dev/null; then
  update_ivy_tool || {
    exit $?
  }
else
  log "ERROR: Function update_ivy_tool not defined"
  exit 1
fi


# Set command type for this context
cmd_type="COMPILE"

# Handle function definition
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
remove_debug_events() {
    echo "Removing debug events..." >> /app/logs/ivy_setup.log;
    printf "%s\n" "$@" | xargs -I {} sh -c "
        if [ -f \"\$1\" ]; then
            sed -i \"s/^\\([^#]*debug_event.*\\)/##\\1/\" \"\$1\";
        else
            echo \"File not found - \$1\" >> /app/logs/ivy_setup.log;
        fi
    " _ {};
}
ENDOFCOMMAND
)
# This is a function definition, needs to be defined in the global scope
log "Executing function definition: Function: remove_debug_events"
# Export the function to ensure it's available to all subprocesses
eval "$MULTILINE_CMD"
# Verify the function was properly defined
if ! declare -f remove_debug_events > /dev/null; then
  log "ERROR: Function remove_debug_events failed to define correctly"
  exit 1
else
  log "Function remove_debug_events defined successfully"
fi


# Set command type for this context
cmd_type="COMPILE"

# Handle function definition
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
restore_debug_events() {
    echo "Restoring debug events..." >> /app/logs/ivy_setup.log;
    printf "%s\n" "$@" | xargs -I {} sh -c "
        if [ -f \"\$1\" ]; then
            sed -i \"s/^##\\(.*debug_event.*\\)/\\1/\" \"\$1\";
        else
            echo \"File not found - \$1\" >> /app/logs/ivy_setup.log;
        fi
    " _ {};
}
ENDOFCOMMAND
)
# This is a function definition, needs to be defined in the global scope
log "Executing function definition: Function: restore_debug_events"
# Export the function to ensure it's available to all subprocesses
eval "$MULTILINE_CMD"
# Verify the function was properly defined
if ! declare -f restore_debug_events > /dev/null; then
  log "ERROR: Function restore_debug_events failed to define correctly"
  exit 1
else
  log "Function restore_debug_events defined successfully"
fi


# Set command type for this context
cmd_type="COMPILE"

# Handle function definition
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
setup_ivy_model() {
    echo "Setting up Ivy model..." >> /app/logs/ivy_setup.log &&
    echo "Updating include path of Python with updated version of the project from /opt/panther_ivy/protocol-testing/quic/" >> /app/logs/ivy_setup.log &&
    echo "Finding .ivy files..." >> /app/logs/ivy_setup.log &&
    find "/opt/panther_ivy/protocol-testing/quic/" -type f -name "*.ivy" -exec sh -c "
        echo \"Found Ivy file - \$1\" >> /app/logs/ivy_setup.log;
        if [ 10 -gt 10 ]; then
            echo \"Removing debug events from \$1\" >> /app/logs/ivy_setup.log;
            remove_debug_events \"\$1\";
        fi;
        echo \"Copying Ivy file to include path...\" >> /app/logs/ivy_setup.log;
        cp -f \"\$1\" \"/usr/local/lib/python3.10/dist-packages/ivy/include/1.7/\";
    " _ {} \;;
    ls -l /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ >> /app/logs/ivy_setup.log;
}
ENDOFCOMMAND
)
# This is a function definition, needs to be defined in the global scope
log "Executing function definition: Function: setup_ivy_model"
# Export the function to ensure it's available to all subprocesses
eval "$MULTILINE_CMD"
# Verify the function was properly defined
if ! declare -f setup_ivy_model > /dev/null; then
  log "ERROR: Function setup_ivy_model failed to define correctly"
  exit 1
else
  log "Function setup_ivy_model defined successfully"
fi


# Set command type for this context
cmd_type="COMPILE"

# Handle simple function call
log "Executing function call: setup_ivy_model"
# Check if function exists first to avoid errors
if declare -f setup_ivy_model > /dev/null; then
  setup_ivy_model || {
    exit $?
  }
else
  log "ERROR: Function setup_ivy_model not defined"
  exit 1
fi


# Set command type for this context
cmd_type="COMPILE"

# Handle function definition
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
restore_debug_events() {
    echo "Restoring debug events..." >> /app/logs/ivy_setup.log;
    printf "%s\n" "$@" | xargs -I {} sh -c "
        if [ -f \"\$1\" ]; then
            sed -i \"s/^##\\(.*debug_event.*\\)/\\1/\" \"\$1\";
        else
            echo \"File not found - \$1\" >> /app/logs/ivy_setup.log;
        fi
    " _ {};
}
ENDOFCOMMAND
)
# This is a function definition, needs to be defined in the global scope
log "Executing function definition: Function: restore_debug_events"
# Export the function to ensure it's available to all subprocesses
eval "$MULTILINE_CMD"
# Verify the function was properly defined
if ! declare -f restore_debug_events > /dev/null; then
  log "ERROR: Function restore_debug_events failed to define correctly"
  exit 1
else
  log "Function restore_debug_events defined successfully"
fi


# Set command type for this context
cmd_type="COMPILE"

# Handle function definition
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
setup_ivy_model() {
    echo "Setting up Ivy model..." >> /app/logs/ivy_setup.log &&
    echo "Updating include path of Python with updated version of the project from /opt/panther_ivy/protocol-testing/quic/" >> /app/logs/ivy_setup.log &&
    echo "Finding .ivy files..." >> /app/logs/ivy_setup.log &&
    find "/opt/panther_ivy/protocol-testing/quic/" -type f -name "*.ivy" -exec sh -c "
        echo \"Found Ivy file - \$1\" >> /app/logs/ivy_setup.log;
        if [ 10 -gt 10 ]; then
            echo \"Removing debug events from \$1\" >> /app/logs/ivy_setup.log;
            remove_debug_events \"\$1\";
        fi;
        echo \"Copying Ivy file to include path...\" >> /app/logs/ivy_setup.log;
        cp -f \"\$1\" \"/usr/local/lib/python3.10/dist-packages/ivy/include/1.7/\";
    " _ {} \;;
    ls -l /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ >> /app/logs/ivy_setup.log;
}
ENDOFCOMMAND
)
# This is a function definition, needs to be defined in the global scope
log "Executing function definition: Function: setup_ivy_model"
# Export the function to ensure it's available to all subprocesses
eval "$MULTILINE_CMD"
# Verify the function was properly defined
if ! declare -f setup_ivy_model > /dev/null; then
  log "ERROR: Function setup_ivy_model failed to define correctly"
  exit 1
else
  log "Function setup_ivy_model defined successfully"
fi


# Set command type for this context
cmd_type="COMPILE"

# Handle command with && operator
log "Command contains && operator: setup_ivy_model &&"

# Extract parts of the command before and after &&
FIRST_PART="setup_ivy_model "
REST_OF_CMD=""

# Create output files for this command
FIRST_OUTPUT="/app/logs/ivy_server_$cmd_type-cmd18_first_part.log"
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
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from $cmd_type command #18 first part:" >> /app/logs/ivy_server_commands.log
cat "$FIRST_OUTPUT" >> /app/logs/ivy_server_commands.log

if [ $FIRST_STATUS -eq 0 ]; then
  # If first part succeeded, execute rest of command
  log "First part succeeded. Executing rest: ${REST_OF_CMD}"
  REST_OUTPUT="/app/logs/ivy_server_$cmd_type-cmd18_rest.log"
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
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from $cmd_type command #18 rest part:" >> /app/logs/ivy_server_commands.log
  cat "$REST_OUTPUT" >> /app/logs/ivy_server_commands.log
  
  # Exit with status from rest part
  if [ $REST_STATUS -ne 0 ]; then
    exit $REST_STATUS
  fi
else
  exit $FIRST_STATUS
fi


# Set command type for this context
cmd_type="COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing shell builtin: cd /opt/panther_ivy/protocol-testing/quic/build;"
# Use eval to properly execute these special command types while preserving their syntax
eval "cd /opt/panther_ivy/protocol-testing/quic/build;" || {
  exit $?
}


# Set command type for this context
cmd_type="COMPILE"

# Handle multi-line command
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
PYTHONPATH=$PYTHON_IVY_DIR ivyc trace=false show_compiled=false target=test test_iters=300 quic_client_test_max.ivy 2>&1 | tee -a /app/logs/ivy_setup.log /app/logs/ivy_compilation.log;exit_code=${PIPESTATUS[0]}; if [ $exit_code -ne 0 ]; then echo "Ivy compilation failed with code $exit_code" | tee -a /app/logs/ivy_compilation_error.log; exit $exit_code; fi
ENDOFCOMMAND
)
# Execute multi-line command with error tracking
log "Executing multi-line $cmd_type command #20"
execute_with_error_tracking "$cmd_type" "$MULTILINE_CMD" "20" "PYTHONPATH=$PYTHON_IVY_DIR ivyc trace=false show_compiled=false target=test test_iters=300 quic_client_test_max.ivy 2>&1 | tee -a /app/logs/ivy_setup.log /app/logs/ivy_compilation.log;exit_code=${PIPESTATUS[0]}; if [ $exit_code -ne 0 ]; then echo \"Ivy compilation failed with code $exit_code\" | tee -a /app/logs/ivy_compilation_error.log; exit $exit_code; fi" "true" "true" || {
  exit $?
}


# Set command type for this context
cmd_type="COMPILE"

# Handle regular command
execute_with_error_tracking "$cmd_type" "ls >> /app/logs/ivy_setup.log 2>&1;" "21" "ls >> /app/logs/ivy_setup.log 2>&1;" "false" "true" || {
  exit $?
}

# Set command type for this context
cmd_type="COMPILE"

# Handle command with && operator
log "Command contains && operator: ls /opt/panther_ivy/protocol-testing/quic/build/ >> /app/logs/ivy_setup.log 2>&1; && (touch /app/sync_logs/ivy_ready.log)"

# Extract parts of the command before and after &&
FIRST_PART="ls /opt/panther_ivy/protocol-testing/quic/build/ >> /app/logs/ivy_setup.log 2>&1; "
REST_OF_CMD=" (touch /app/sync_logs/ivy_ready.log)"

# Create output files for this command
FIRST_OUTPUT="/app/logs/ivy_server_$cmd_type-cmd22_first_part.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting execution of $cmd_type command #22 first part" > "$FIRST_OUTPUT"
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
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from $cmd_type command #22 first part:" >> /app/logs/ivy_server_commands.log
cat "$FIRST_OUTPUT" >> /app/logs/ivy_server_commands.log

if [ $FIRST_STATUS -eq 0 ]; then
  # If first part succeeded, execute rest of command
  log "First part succeeded. Executing rest: ${REST_OF_CMD}"
  REST_OUTPUT="/app/logs/ivy_server_$cmd_type-cmd22_rest.log"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting execution of $cmd_type command #22 rest part" > "$REST_OUTPUT"
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
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from $cmd_type command #22 rest part:" >> /app/logs/ivy_server_commands.log
  cat "$REST_OUTPUT" >> /app/logs/ivy_server_commands.log
  
  # Exit with status from rest part
  if [ $REST_STATUS -ne 0 ]; then
    exit $REST_STATUS
  fi
else
  exit $FIRST_STATUS
fi


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

# Set command type for this context
cmd_type="POST_COMPILE"

# Handle multi-line command
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
(touch /app/logs/ivy_server.pcap; tshark -a duration:100 -i any -w /app/logs/ivy_server.pcap;) & 
ENDOFCOMMAND
)
# Execute multi-line command with error tracking
log "Executing multi-line $cmd_type command #2"
execute_with_error_tracking "$cmd_type" "$MULTILINE_CMD" "2" "(touch /app/logs/ivy_server.pcap; tshark -a duration:100 -i any -w /app/logs/ivy_server.pcap;) & " "true" "true" || {
  exit $?
}


# Execute pre-run commands
log "Executing pre-run commands..."

# Execute the main command if provided
log "Executing main command..."
cd "/opt/panther_ivy/protocol-testing/quic/" || {
  log "Failed to change to directory: /opt/panther_ivy/protocol-testing/quic/"
  exit 1
}


# Prepare command and execute it
FULL_CMD="./build/quic_client_test_max     seed=0 the_cid=1 server_port=4443 iversion=1 server_addr=$TARGET_IP_HEX > /app/logs/quic_client_test_max.log 2> /app/logs/quic_client_test_max.err"
FULL_CMD="$(echo "$FULL_CMD" | xargs)"  # Trim whitespace

if [ -z "$FULL_CMD" ]; then
  log "WARNING: No command to run, skipping execution"
  RUN_STATUS=0
else
  log "Running command: $FULL_CMD"

  timeout 100 $FULL_CMD 2>&1 | tee -a /app/logs/ivy_server_run.log
  RUN_STATUS=${PIPESTATUS[0]}
fi

if [ $RUN_STATUS -ne 0 ]; then
  if [ $RUN_STATUS -eq 124 ] || [ $RUN_STATUS -eq 137 ]; then
    log "WARNING: Command timed out after 100 seconds"
  else
    log "ERROR: Command failed with exit status $RUN_STATUS"
    exit $RUN_STATUS
  fi
fi

# Execute post-run commands
log "Executing post-run commands..."
# Set command type for this context
cmd_type="POST_RUN"

# Handle command with && operator
log "Command contains && operator: cp /opt/panther_ivy/protocol-testing/quic/build/quic_client_test_max /app/logs/quic_client_test_max && "

# Extract parts of the command before and after &&
FIRST_PART="cp /opt/panther_ivy/protocol-testing/quic/build/quic_client_test_max /app/logs/quic_client_test_max "
REST_OF_CMD=" "

# Create output files for this command
FIRST_OUTPUT="/app/logs/ivy_server_$cmd_type-cmd1_first_part.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting execution of $cmd_type command #1 first part" > "$FIRST_OUTPUT"
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
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from $cmd_type command #1 first part:" >> /app/logs/ivy_server_commands.log
cat "$FIRST_OUTPUT" >> /app/logs/ivy_server_commands.log

if [ $FIRST_STATUS -eq 0 ]; then
  # If first part succeeded, execute rest of command
  log "First part succeeded. Executing rest: ${REST_OF_CMD}"
  REST_OUTPUT="/app/logs/ivy_server_$cmd_type-cmd1_rest.log"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting execution of $cmd_type command #1 rest part" > "$REST_OUTPUT"
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
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from $cmd_type command #1 rest part:" >> /app/logs/ivy_server_commands.log
  cat "$REST_OUTPUT" >> /app/logs/ivy_server_commands.log
  
  # Exit with status from rest part
  if [ $REST_STATUS -ne 0 ]; then
    exit $REST_STATUS
  fi
else
  exit $FIRST_STATUS
fi

# Set command type for this context
cmd_type="POST_RUN"

# Handle regular command
execute_with_error_tracking "$cmd_type" "rm /opt/panther_ivy/protocol-testing/quic/build/quic_client_test_max*;" "2" "rm /opt/panther_ivy/protocol-testing/quic/build/quic_client_test_max*;" "false" "true" || {
  exit $?
}

log "All commands executed successfully. Service 'ivy_server' entrypoint complete."
exit 0