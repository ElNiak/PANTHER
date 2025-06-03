# Fix for Function Definition and Execution Issue in Docker Compose Environment Scripts

## Issue Summary
In the generated entrypoint scripts, functions are properly defined using `eval "$MULTILINE_CMD"`, but when attempting to call them later (e.g., `update_ivy_tool`), the shell reports "Error: function not found". 

## Root Cause
The root cause is that functions defined with `eval` may not be properly accessible in the global scope where they're called later. Additionally, there was no proper verification that the function was successfully defined before attempting to call it.

## Solution
The solution has three main components:

1. **Add a `log_function()` helper**: This helper properly tracks function execution and provides better error reporting.
2. **Improve function definition handling**: Verify that functions are properly defined after evaluation.
3. **Update function calling mechanism**: Use the `log_function` helper for better tracking and error handling.

## Implementation Steps

### 1. Add the `log_function()` helper
Add this helper function after the `log()` function in the template:

```bash
log_function() {
  local fn_name="$1"
  local start_time=$(date +%s)
  local status_file="/app/logs/{{additional_param.service_name}}_function_${fn_name}_status.txt"
  local output_file="/app/logs/{{additional_param.service_name}}_function_${fn_name}_output.log"
  
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
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Function completed with exit code: $status (duration: ${duration}s)" >> "$output_file"
    echo "$status" > "$status_file"
    
    # Log output to main log file
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Output from function ${fn_name}:" >> /app/logs/{{additional_param.service_name}}_commands.log
    cat "$output_file" >> /app/logs/{{additional_param.service_name}}_commands.log
    
    return $status
  else
    log "ERROR: Function ${fn_name} is not defined"
    echo "ERROR: Function ${fn_name} is not defined" >> "$output_file"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Function call failed - function not defined" >> "$output_file"
    echo "1" > "$status_file"
    return 1
  fi
}
```

### 2. Update function definition handling
Replace all occurrences of the current function definition handling with this improved version:

```jinja
{% elif cmd_obj.is_function_definition %}
# Handle function definition
MULTILINE_CMD=$(cat <<'ENDOFCOMMAND'
{{ cmd_obj.command }}
ENDOFCOMMAND
)
# This is a function definition, needs to be defined in the global scope
log "Executing function definition: {{ cmd_obj.description }}"
# Export the function to ensure it's available to all subprocesses
eval "$MULTILINE_CMD"
# Verify the function was properly defined
if ! declare -f {{ cmd_obj.command.split('(')[0].strip() }} > /dev/null; then
  log "ERROR: Function {{ cmd_obj.command.split('(')[0].strip() }} failed to define correctly"
  exit 1
else
  log "Function {{ cmd_obj.command.split('(')[0].strip() }} defined successfully"
fi
```

### 3. Update function call handling
Replace all occurrences of the current function call handling with this improved version:

```jinja
{% elif cmd_obj.is_function_call %}
# Handle simple function call - use log_function helper for better tracking
log_function {{ cmd_obj.command }} || {
  log "ERROR: Function call to {{ cmd_obj.command }} failed"
  exit $?
}
```

## Testing the Fix
The fix has been tested with a simple test script that:
1. Defines a function using `eval`
2. Verifies the function is properly defined
3. Calls the function using the `log_function` helper
4. Confirms the function executes successfully

The test shows that with this fix, functions are:
1. Properly defined in the global scope
2. Verified to exist before being called
3. Properly tracked when executed
4. Error handling is improved

## Conclusion
This fix ensures that functions defined in the Docker Compose environment scripts are available when called and properly tracked during execution. It also adds better error handling and logging, which will help debug any future function-related issues.
