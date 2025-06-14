#!/bin/bash -x
# -x: trace every command (with expansions)



# Define helper functions
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /app/logs/picoquic_client_entrypoint.log
}
# Export log function so it's available in subshells
export -f log

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

# Service discovery: Write our IP to a shared file
SERVICE_NAME="picoquic_client"
SERVICE_IP=$(hostname -i | grep -v '^127' | head -n 1)
if [ -n "$SERVICE_IP" ]; then
  echo "$SERVICE_IP" > /app/sync_logs/${SERVICE_NAME}_ip.txt
  log "Registered service IP: $SERVICE_IP"
fi


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
(touch /app/logs/picoquic_client.pcap; tshark -a duration:60 -i any -w /app/logs/picoquic_client.pcap;) &
ENDOFCOMMAND
)
# Execute multi-line command with error tracking
log "Executing multi-line $cmd_type command #3"
execute_with_error_tracking "$cmd_type" "$MULTILINE_CMD" "3" "(touch /app/logs/picoquic_client.pcap; tshark -a duration:60 -i any -w /app/logs/picoquic_client.pcap;) & " "true" "true" || {
  exit $?
}




# Wait for dependencies if this is a client/IUT service
log "This service depends on: ivy_server"
wait_for_dependency "ivy_server" "4443" || {
  log "ERROR: Failed to connect to dependency ivy_server"
  exit 1
}

# Execute pre-run commands
log "Executing pre-run commands..."
# Set command type for this context
cmd_type="PRE_RUN"

# Handle multi-line command
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
if [ -z "$EXEC_ENV_WRAPPERS" ]; then
    export EXEC_ENV_WRAPPERS="/usr/bin/strace -e trace="!nanosleep,getitimer,alarm,setitimer,gettimeofday,times,rt_sigtimedwait,utime,adjtimex,settimeofday,time" -e trace=network -e trace=file -y -r -f -s 32 -o /app/logs/picoquic_client_strace_2025-06-14_02-27-34.out"
else
    export EXEC_ENV_WRAPPERS="/usr/bin/strace -e trace="!nanosleep,getitimer,alarm,setitimer,gettimeofday,times,rt_sigtimedwait,utime,adjtimex,settimeofday,time" -e trace=network -e trace=file -y -r -f -s 32 -o /app/logs/picoquic_client_strace_2025-06-14_02-27-34.out $EXEC_ENV_WRAPPERS"
fi
echo "Added strace wrapper: /usr/bin/strace -e trace="!nanosleep,getitimer,alarm,setitimer,gettimeofday,times,rt_sigtimedwait,utime,adjtimex,settimeofday,time" -e trace=network -e trace=file -y -r -f -s 32 -o /app/logs/picoquic_client_strace_2025-06-14_02-27-34.out" >> /app/logs/picoquic_client_exec_env_setup.log
ENDOFCOMMAND
)
# Execute multi-line command with error tracking
log "Executing multi-line $cmd_type command #1"
execute_with_error_tracking "$cmd_type" "$MULTILINE_CMD" "1" "if [ -z \"$EXEC_ENV_WRAPPERS\" ]; then
    export EXEC_ENV_WRAPPERS=\"/usr/bin/strace -e trace=\"!nanosleep,getitimer,alarm,setitimer,gettimeofday,times,rt_sigtimedwait,utime,adjtimex,settimeofday,time\" -e trace=network -e trace=file -y -r -f -s 32 -o /app/logs/picoquic_client_strace_2025-06-14_02-27-34.out\"
else
    export EXEC_ENV_WRAPPERS=\"/usr/bin/strace -e trace=\"!nanosleep,getitimer,alarm,setitimer,gettimeofday,times,rt_sigtimedwait,utime,adjtimex,settimeofday,time\" -e trace=network -e trace=file -y -r -f -s 32 -o /app/logs/picoquic_client_strace_2025-06-14_02-27-34.out $EXEC_ENV_WRAPPERS\"
fi
echo \"Added strace wrapper: /usr/bin/strace -e trace=\"!nanosleep,getitimer,alarm,setitimer,gettimeofday,times,rt_sigtimedwait,utime,adjtimex,settimeofday,time\" -e trace=network -e trace=file -y -r -f -s 32 -o /app/logs/picoquic_client_strace_2025-06-14_02-27-34.out\" >> /app/logs/picoquic_client_exec_env_setup.log" "true" "true" || {
  exit $?
}



# Execute the main command if provided
log "Executing main command..."
pwd > /app/logs/picoquic_client_current_dir_during_exec.log
cd "/opt/picoquic" || {
  log "Failed to change to directory: /opt/picoquic"
  exit 1
}


# Prepare command and execute it
# Handle both string and list command_args
FULL_CMD="./picoquicdemo -a hq-interop  -T  /opt/ticket/ticket.key  -l - -D -L  -v  00000001  ivy_server  4443"
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
  # Check if execution environment wrappers are available and wrap the command
  if [ -n "$EXEC_ENV_WRAPPERS" ]; then
    WRAPPED_CMD="$EXEC_ENV_WRAPPERS $FULL_CMD"
    log "Running command with execution environment wrappers: $WRAPPED_CMD"
    echo "Execution environment wrappers applied: $EXEC_ENV_WRAPPERS" >> /app/logs/picoquic_client_exec_env_wrapping.log
  else
    WRAPPED_CMD="$FULL_CMD"
    log "Running command: $WRAPPED_CMD"
  fi

  timeout 60 $WRAPPED_CMD > /app/logs/picoquic_client_run_cmd.log 2> /app/logs/picoquic_client_run_cmd_error.log
  RUN_STATUS=${PIPESTATUS[0]}
fi

if [ $RUN_STATUS -ne 0 ]; then
  if [ $RUN_STATUS -eq 124 ] || [ $RUN_STATUS -eq 137 ]; then
    log "WARNING: Command timed out after 60 seconds"
  else
    log "ERROR: Command failed with exit status $RUN_STATUS"
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
exit $RUN_STATUS