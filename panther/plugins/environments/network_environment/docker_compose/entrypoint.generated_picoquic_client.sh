#!/bin/bash -x
# -x: trace every command (with expansions)

# Define helper functions
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /app/logs/picoquic_client_entrypoint.log
}

log_function() {
  local fn_name="$1"
  local start_time=$(date +%s)
  local status_file="/app/logs/picoquic_client_function_${fn_name}_status.txt"
  local output_file="/app/logs/picoquic_client_function_${fn_name}_output.log"

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
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from function ${fn_name}:" >> /app/logs/picoquic_client_commands.log
    cat "$output_file" >> /app/logs/picoquic_client_commands.log

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
  ping -c 3 "$target" > /app/logs/picoquic_client_connectivity.log 2>&1
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
    echo "$cmd_desc" > /app/logs/picoquic_client_last_failed_command.txt
    echo "Exit status: $exit_status" >> /app/logs/picoquic_client_last_failed_command.txt
  fi
}

set_environment() {
  # Set environment variables for the service
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
  local status_file="/app/logs/picoquic_client_$phase-cmd-$cmd_num-status.txt"
  local output_file="/app/logs/picoquic_client_$phase-cmd-$cmd_num-output.log"

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
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from $phase command #$cmd_num:" >> /app/logs/picoquic_client_commands.log
  cat "$output_file" >> /app/logs/picoquic_client_commands.log

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

log "Compilation completed successfully."

# Execute post-compilation commands
log "Executing post-compilation commands..."
# Set command type for this context
cmd_type="POST_COMPILE"

# Handle multi-line command
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
while [ ! -f /app/sync_logs/ivy_ready.log ]; do
	echo "Waiting for Ivy testers to be ready..." >> /app/logs/tester_ready.log;
	sleep 2;
done;
ENDOFCOMMAND
)
# Execute multi-line command with error tracking
log "Executing multi-line $cmd_type command #1"
execute_with_error_tracking "$cmd_type" "$MULTILINE_CMD" "1" "while [ ! -f /app/sync_logs/ivy_ready.log ]; do
	echo \"Waiting for Ivy testers to be ready...\" >> /app/logs/tester_ready.log;
	sleep 2;
done;" "true" "true" || {
  exit $?
}

# Set command type for this context
cmd_type="POST_COMPILE"

# Handle special command types: variable assignment, shell builtin, control structure, or nested quotes
log "Executing shell builtin: echo \"Ivy testers is ready, starting picoquic_client...\" >> /app/logs/tester_ready.log;"
# Use eval to properly execute these special command types while preserving their syntax
eval "echo "Ivy testers is ready, starting picoquic_client..." >> /app/logs/tester_ready.log;" || {
  exit $?
}

# Set command type for this context
cmd_type="POST_COMPILE"

# Handle multi-line command
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
(touch /app/logs/picoquic_client.pcap; tshark -a duration:50 -i any -w /app/logs/picoquic_client.pcap;) &
ENDOFCOMMAND
)
# Execute multi-line command with error tracking
log "Executing multi-line $cmd_type command #3"
execute_with_error_tracking "$cmd_type" "$MULTILINE_CMD" "3" "(touch /app/logs/picoquic_client.pcap; tshark -a duration:50 -i any -w /app/logs/picoquic_client.pcap;) & " "true" "true" || {
  exit $?
}


# Execute pre-run commands
log "Executing pre-run commands..."

# Execute the main command if provided
log "Executing main command..."
pwd > /app/logs/picoquic_client_current_dir_during_exec.log
cd "/opt/picoquic" || {
  log "Failed to change to directory: /opt/picoquic"
  exit 1
}


# Prepare command and execute it
FULL_CMD="./picoquicdemo -T  /opt/ticket/ticket.key  -a  hq-interop  -l - -D -L  -e  eth0  -v  00000001  ivy_server  4443"
FULL_CMD="$(echo "$FULL_CMD" | xargs)"  # Trim whitespace

if [ -z "$FULL_CMD" ]; then
  log "WARNING: No command to run, skipping execution"
  RUN_STATUS=0
else
  log "Running command: $FULL_CMD"

  timeout 50 $FULL_CMD > /app/logs/picoquic_client_run_cmd.log 2> /app/logs/picoquic_client_run_cmd_error.log
  RUN_STATUS=${PIPESTATUS[0]}
fi

if [ $RUN_STATUS -ne 0 ]; then
  if [ $RUN_STATUS -eq 124 ] || [ $RUN_STATUS -eq 137 ]; then
    log "WARNING: Command timed out after 50 seconds"
  else
    log "ERROR: Command failed with exit status $RUN_STATUS"
    exit $RUN_STATUS
  fi
fi

# Execute post-run commands
log "Executing post-run commands..."
# Set command type for this context
cmd_type="POST_RUN"

# Handle regular command
execute_with_error_tracking "$cmd_type" "cp /opt/picoquic/picoquicdemo /app/logs/picoquicdemo;" "1" "cp /opt/picoquic/picoquicdemo /app/logs/picoquicdemo;" "false" "true" || {
  exit $?
}

log "All commands executed successfully. Service 'picoquic_client' entrypoint complete."
exit 0