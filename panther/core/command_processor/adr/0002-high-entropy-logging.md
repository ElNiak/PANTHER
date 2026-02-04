# ADR-0002: High-Entropy Logging Strategy

## Status
Accepted

## Context
Traditional verbose logging in command processing generates excessive log volume, making it difficult to identify important events. Command processing can involve hundreds of commands, and logging each individual command creates noise that obscures critical information.

## Decision
Implement high-entropy logging that focuses on summarization and exceptional cases rather than routine operations.

## Rationale
- **Signal vs Noise**: Log only information that provides value for debugging
- **Performance**: Reduce logging overhead in high-throughput scenarios
- **Operational Clarity**: Make logs useful for production monitoring
- **Information Theory**: Apply Shannon's entropy principle to logging

## Implementation

### Summary-Based Logging
```python
def _log_processing_summary(self, commands):
    """Log a concise summary instead of verbose details."""
    command_counts = {}
    total_commands = 0

    for cmd_type, cmds in commands.items():
        count = len(cmds) if isinstance(cmds, list) else (1 if cmds else 0)
        command_counts[cmd_type] = count
        total_commands += count

    summary = f"Processing {total_commands} commands: {', '.join(f'{cmd_type}({count})' for cmd_type, count in command_counts.items() if count > 0)}"
    self.logger.info(summary)
```

### Conditional Detail Logging
```python
# Only log individual command types at DEBUG level if needed
if self.logger.isEnabledFor(logging.DEBUG):
    self.logger.debug("Processing command type '%s'", cmd_type)
    if cmd_type == "pre_run_cmds" and cmds:
        # Only show first command to reduce verbosity
        first_cmd_preview = str(first_cmd)[:100] + "..." if len(str(first_cmd)) > 100 else str(first_cmd)
        self.logger.debug("pre_run_cmds preview: %s", first_cmd_preview)
```

## High-Entropy vs Low-Entropy Information

### High-Entropy (Always Log)
- **Validation failures** with specific error context
- **Processing summaries** with command counts by type
- **Unexpected edge cases** in command detection
- **Performance anomalies** (timeouts, memory issues)
- **Integration failures** with other PANTHER components

### Low-Entropy (Skip or Debug-Only)
- Individual command processing steps
- Successful routine operations
- Standard parameter values
- Expected control flow

## Consequences

### Positive
- **Reduced Log Volume**: 80-90% reduction in production logs
- **Improved Signal Quality**: Important events are visible
- **Better Performance**: Lower logging overhead
- **Operational Efficiency**: Easier log analysis and monitoring
- **Cost Reduction**: Lower log storage and processing costs

### Negative
- **Less Detailed Debugging**: May need to enable DEBUG for detailed investigation
- **Learning Curve**: Developers must understand entropy-based approach
- **Context Loss**: Some debugging context requires additional work to retrieve

### Implementation Notes
- Use structured logging for better filtering
- Include context IDs for request correlation
- Provide debug modes for detailed investigation
- Monitor log volume and adjust thresholds

## Monitoring
- Track log volume reduction
- Monitor debug session frequency
- Measure problem resolution time
- Assess operational visibility

## Related Decisions
- ADR-0001: Fast-Fail Validation Pattern
- ADR-0003: Command Detection Strategy
