# Advanced Usage Patterns

## Overview
This document covers advanced usage patterns, edge cases, and sophisticated integration scenarios for the PANTHER command processor module.

## Pattern 1: Complex Shell Function Processing

### Multi-Function Command Sets
Handle commands that define and use multiple related functions:

```python
from panther.core.command_processor import CommandProcessor

processor = CommandProcessor()

complex_functions = {
    "pre_run_cmds": [
        """
        # Database backup function
        backup_db() {
            local timestamp=$(date +%Y%m%d_%H%M%S)
            pg_dump $DATABASE_URL > "backup_${timestamp}.sql"
            echo "Database backed up to backup_${timestamp}.sql"
        }
        """,
        """
        # Deployment preparation function
        prepare_deploy() {
            backup_db
            if [ $? -eq 0 ]; then
                echo "Backup successful, proceeding with deployment"
                return 0
            else
                echo "Backup failed, aborting deployment"
                return 1
            fi
        }
        """,
        "prepare_deploy"  # Execute the preparation
    ],
    "run_cmd": {
        "command_args": "docker-compose up -d",
        "working_dir": "/app",
        "environment": {"COMPOSE_PROJECT_NAME": "myapp"}
    }
}

result = processor.process_commands(complex_functions)

# Examine function detection
for cmd in result["pre_run_cmds"]:
    if cmd.get("is_function_definition"):
        print(f"Function detected: {cmd['command'][:50]}...")
        print(f"  Multiline: {cmd['is_multiline']}")
        print(f"  Critical: {cmd['is_critical']}")
```

### Advanced Function Detection Edge Cases

```python
# Test various function definition patterns
function_patterns = [
    # Standard function syntax
    "function deploy() { echo 'deploying'; }",

    # Compact function syntax
    "deploy() { echo 'deploying'; }",

    # Multi-line with complex logic
    """
    deploy() {
        if [ -z "$VERSION" ]; then
            echo "VERSION not set"
            return 1
        fi

        case "$ENVIRONMENT" in
            "prod"|"production")
                echo "Deploying to production"
                ;;
            "stage"|"staging")
                echo "Deploying to staging"
                ;;
            *)
                echo "Unknown environment: $ENVIRONMENT"
                return 1
                ;;
        esac
    }
    """,

    # Function with local variables
    """
    process_files() {
        local input_dir="$1"
        local output_dir="$2"

        for file in "$input_dir"/*.txt; do
            if [ -f "$file" ]; then
                basename=$(basename "$file")
                cp "$file" "$output_dir/$basename.processed"
            fi
        done
    }
    """
]

for pattern in function_patterns:
    properties = processor.detect_command_properties(pattern)
    print(f"Pattern: {pattern[:30]}...")
    print(f"  Function definition: {properties['is_function_definition']}")
    print(f"  Control structure: {properties['is_control_structure']}")
    print(f"  Multiline: {properties['is_multiline']}")
    print()
```

## Pattern 2: Environment-Specific Command Adaptation

### Custom Environment Adapter
Create environment-specific command adaptations:

```python
from panther.core.command_processor.core.interfaces import IEnvironmentCommandAdapter

class DockerEnvironmentAdapter(IEnvironmentCommandAdapter):
    """Adapter for Docker container environments."""

    def adapt_commands(self, commands):
        """Adapt commands for Docker execution."""
        adapted = {}

        for cmd_type, cmds in commands.items():
            if cmd_type == "run_cmd":
                # Wrap command in Docker execution context
                adapted[cmd_type] = self._adapt_run_cmd(cmds)
            elif isinstance(cmds, list):
                # Adapt command lists
                adapted[cmd_type] = [self._adapt_shell_command(cmd) for cmd in cmds]
            else:
                adapted[cmd_type] = cmds

        return adapted

    def _adapt_run_cmd(self, run_cmd):
        """Adapt run_cmd for Docker environment."""
        docker_cmd = {
            "command_binary": "docker",
            "command_args": f"exec -w {run_cmd.get('working_dir', '/app')} myapp-container {run_cmd.get('command_args', '')}",
            "environment": run_cmd.get("environment", {}),
            "timeout": run_cmd.get("timeout", 300)
        }
        return docker_cmd

    def _adapt_shell_command(self, cmd):
        """Adapt shell command for Docker execution."""
        if isinstance(cmd, dict) and "command" in cmd:
            # Wrap shell commands in docker exec
            adapted_cmd = cmd.copy()
            adapted_cmd["command"] = f"docker exec myapp-container bash -c '{cmd['command']}'"
            return adapted_cmd
        return cmd

# Usage with environment adapter
processor = CommandProcessor()
docker_adapter = DockerEnvironmentAdapter()

commands = {
    "pre_run_cmds": ["echo 'Starting application'"],
    "run_cmd": {
        "command_args": "python manage.py migrate",
        "working_dir": "/app"
    }
}

# Process and adapt for Docker
processed = processor.process_commands(commands)
docker_adapted = docker_adapter.adapt_commands(processed)

print("Original run_cmd:", processed["run_cmd"]["command_args"])
print("Docker adapted:", docker_adapted["run_cmd"]["command_args"])
```

## Pattern 3: High-Performance Batch Processing

### Optimized Command Processing
Handle large batches of commands efficiently:

```python
from panther.core.command_processor import CommandProcessor
from panther.core.command_processor.utils.summarizer import CommandSummarizer

class BatchCommandProcessor:
    """High-performance processor for command batches."""

    def __init__(self):
        self.processor = CommandProcessor()
        self.summarizer = CommandSummarizer()
        self.batch_stats = {
            "processed": 0,
            "errors": 0,
            "optimizations": 0
        }

    def process_command_batch(self, command_sets, optimization_level="aggressive"):
        """Process multiple command sets with optimization."""
        results = []

        for i, commands in enumerate(command_sets):
            try:
                # Apply optimizations based on level
                if optimization_level == "aggressive":
                    commands = self._apply_aggressive_optimizations(commands)

                # Process commands
                result = self.processor.process_commands(commands)

                # Generate summary for large batches
                if len(command_sets) > 10:
                    summary = self.summarizer.summarize_commands(result)
                    result["_summary"] = summary

                results.append(result)
                self.batch_stats["processed"] += 1

            except Exception as e:
                self.batch_stats["errors"] += 1
                results.append({"error": str(e), "original_commands": commands})

        return results

    def _apply_aggressive_optimizations(self, commands):
        """Apply aggressive optimizations to command set."""
        optimized = commands.copy()

        # Combine sequential echo commands
        if "pre_run_cmds" in optimized:
            echo_commands = []
            other_commands = []

            for cmd in optimized["pre_run_cmds"]:
                if isinstance(cmd, str) and cmd.strip().startswith("echo"):
                    echo_commands.append(cmd.replace("echo ", "").strip("'\""))
                else:
                    other_commands.append(cmd)

            if len(echo_commands) > 1:
                # Combine multiple echo commands
                combined_echo = f"echo '{'; '.join(echo_commands)}'"
                optimized["pre_run_cmds"] = [combined_echo] + other_commands
                self.batch_stats["optimizations"] += 1

        return optimized

    def get_batch_statistics(self):
        """Get processing statistics."""
        total = self.batch_stats["processed"] + self.batch_stats["errors"]
        success_rate = (self.batch_stats["processed"] / total * 100) if total > 0 else 0

        return {
            "total_processed": total,
            "successful": self.batch_stats["processed"],
            "errors": self.batch_stats["errors"],
            "success_rate": f"{success_rate:.1f}%",
            "optimizations_applied": self.batch_stats["optimizations"]
        }

# Example usage
batch_processor = BatchCommandProcessor()

# Large batch of similar commands
command_batch = [
    {
        "pre_run_cmds": [f"echo 'Processing file {i}'", f"mkdir -p /tmp/batch_{i}"],
        "run_cmd": {"command_args": f"process_file input_{i}.txt output_{i}.txt"}
    }
    for i in range(100)
]

# Process with optimization
results = batch_processor.process_command_batch(command_batch, "aggressive")
stats = batch_processor.get_batch_statistics()

print(f"Processed {stats['total_processed']} command sets")
print(f"Success rate: {stats['success_rate']}")
print(f"Optimizations applied: {stats['optimizations_applied']}")
```

## Pattern 4: Advanced Error Handling and Recovery

### Resilient Command Processing
Implement sophisticated error handling with recovery mechanisms:

```python
from panther.core.command_processor import CommandProcessor
from panther.core.exceptions.fast_fail import PantherException, ErrorSeverity, ErrorCategory

class ResilientCommandProcessor:
    """Command processor with advanced error handling and recovery."""

    def __init__(self, max_retries=3, recovery_strategies=None):
        self.processor = CommandProcessor()
        self.max_retries = max_retries
        self.recovery_strategies = recovery_strategies or {}
        self.error_history = []

    def process_with_recovery(self, commands, recovery_context=None):
        """Process commands with automatic recovery on failures."""
        attempt = 0
        last_error = None

        while attempt < self.max_retries:
            try:
                # Attempt processing
                result = self.processor.process_commands(commands)

                # Clear error history on success
                if self.error_history:
                    self.error_history.clear()

                return result

            except PantherException as e:
                attempt += 1
                last_error = e
                self.error_history.append({
                    "attempt": attempt,
                    "error": str(e),
                    "category": e.category,
                    "severity": e.severity,
                    "context": e.context
                })

                # Try recovery if not final attempt
                if attempt < self.max_retries:
                    recovery_result = self._attempt_recovery(e, commands, recovery_context)
                    if recovery_result:
                        commands = recovery_result  # Use recovered commands
                        continue

                # Log error for analysis
                self.processor.logger.warning(
                    f"Command processing attempt {attempt} failed: {e.message}"
                )

        # All retries exhausted
        raise PantherException(
            message=f"Command processing failed after {self.max_retries} attempts",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.COMMAND_EXECUTION,
            context={
                "last_error": str(last_error),
                "error_history": self.error_history,
                "original_commands": commands
            }
        )

    def _attempt_recovery(self, error, commands, recovery_context):
        """Attempt to recover from processing error."""
        error_type = self._classify_error(error)

        if error_type in self.recovery_strategies:
            strategy = self.recovery_strategies[error_type]
            return strategy(error, commands, recovery_context)

        # Default recovery strategies
        if error_type == "invalid_command_structure":
            return self._recover_invalid_structure(commands)
        elif error_type == "missing_required_fields":
            return self._recover_missing_fields(commands)

        return None

    def _classify_error(self, error):
        """Classify error for recovery strategy selection."""
        if "must be a dictionary" in error.message:
            return "invalid_command_structure"
        elif "run_cmd must be a dictionary" in error.message:
            return "invalid_run_cmd"
        elif "Command type must be string" in error.message:
            return "invalid_command_type"
        else:
            return "unknown_error"

    def _recover_invalid_structure(self, commands):
        """Attempt to fix invalid command structure."""
        if isinstance(commands, str):
            # Convert string to proper structure
            return {
                "run_cmd": {"command_args": commands}
            }
        elif isinstance(commands, list):
            # Convert list to proper structure
            return {
                "pre_run_cmds": commands
            }

        return None

    def _recover_missing_fields(self, commands):
        """Add missing required fields."""
        if "run_cmd" in commands and not isinstance(commands["run_cmd"], dict):
            # Fix run_cmd structure
            fixed_commands = commands.copy()
            if isinstance(commands["run_cmd"], str):
                fixed_commands["run_cmd"] = {
                    "command_args": commands["run_cmd"]
                }
            return fixed_commands

        return None

# Example usage with custom recovery strategies
def custom_docker_recovery(error, commands, context):
    """Custom recovery strategy for Docker-related errors."""
    if "docker" in str(error).lower():
        # Add Docker availability check
        recovery_commands = commands.copy()
        if "pre_run_cmds" not in recovery_commands:
            recovery_commands["pre_run_cmds"] = []

        recovery_commands["pre_run_cmds"].insert(0,
            "command -v docker >/dev/null 2>&1 || { echo 'Docker not found' >&2; exit 1; }"
        )
        return recovery_commands
    return None

resilient_processor = ResilientCommandProcessor(
    max_retries=3,
    recovery_strategies={
        "docker_error": custom_docker_recovery
    }
)

# Test with potentially problematic commands
problematic_commands = "echo 'test'"  # Invalid structure (string instead of dict)

try:
    result = resilient_processor.process_with_recovery(problematic_commands)
    print("Processing succeeded after recovery")
except PantherException as e:
    print(f"Processing failed permanently: {e.message}")
    print(f"Error history: {resilient_processor.error_history}")
```

## Pattern 5: Integration with Monitoring and Observability

### Command Processing Metrics
Integrate command processing with monitoring systems:

```python
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from panther.core.command_processor import CommandProcessor

@dataclass
class ProcessingMetrics:
    """Metrics for command processing operations."""
    start_time: float
    end_time: Optional[float] = None
    command_count: int = 0
    function_count: int = 0
    error_count: int = 0
    optimization_count: int = 0
    validation_time: float = 0
    processing_time: float = 0

class ObservableCommandProcessor:
    """Command processor with comprehensive observability."""

    def __init__(self, metrics_collector=None):
        self.processor = CommandProcessor()
        self.metrics_collector = metrics_collector
        self.current_metrics = None
        self.historical_metrics = []

    def process_commands_with_metrics(self, commands, operation_id=None):
        """Process commands while collecting detailed metrics."""
        self.current_metrics = ProcessingMetrics(start_time=time.time())

        try:
            # Pre-processing metrics
            self._collect_pre_processing_metrics(commands)

            # Validation timing
            validation_start = time.time()
            # This would normally be done inside processor, but we're measuring it
            self.current_metrics.validation_time = time.time() - validation_start

            # Processing timing
            processing_start = time.time()
            result = self.processor.process_commands(commands)
            self.current_metrics.processing_time = time.time() - processing_start

            # Post-processing metrics
            self._collect_post_processing_metrics(result)

            # Finalize metrics
            self.current_metrics.end_time = time.time()
            self.historical_metrics.append(self.current_metrics)

            # Send to metrics collector if available
            if self.metrics_collector:
                self.metrics_collector.record_processing_metrics(
                    self.current_metrics, operation_id
                )

            return result

        except Exception as e:
            self.current_metrics.error_count += 1
            self.current_metrics.end_time = time.time()

            # Record error metrics
            if self.metrics_collector:
                self.metrics_collector.record_error_metrics(
                    self.current_metrics, str(e), operation_id
                )

            raise

    def _collect_pre_processing_metrics(self, commands):
        """Collect metrics before processing."""
        total_commands = 0

        for cmd_type, cmds in commands.items():
            if isinstance(cmds, list):
                total_commands += len(cmds)
            elif cmds:
                total_commands += 1

        self.current_metrics.command_count = total_commands

    def _collect_post_processing_metrics(self, result):
        """Collect metrics after processing."""
        function_count = 0
        optimization_count = 0

        for cmd_type, cmds in result.items():
            if isinstance(cmds, list):
                for cmd in cmds:
                    if isinstance(cmd, dict):
                        if cmd.get("is_function_definition"):
                            function_count += 1
                        # Count optimizations (combined commands)
                        if cmd.get("_combined_from_count", 0) > 1:
                            optimization_count += 1

        self.current_metrics.function_count = function_count
        self.current_metrics.optimization_count = optimization_count

    def get_performance_summary(self, last_n_operations=10):
        """Get performance summary for recent operations."""
        recent_metrics = self.historical_metrics[-last_n_operations:]

        if not recent_metrics:
            return {"message": "No metrics available"}

        total_time = sum(m.end_time - m.start_time for m in recent_metrics)
        total_commands = sum(m.command_count for m in recent_metrics)
        total_errors = sum(m.error_count for m in recent_metrics)

        avg_processing_time = sum(m.processing_time for m in recent_metrics) / len(recent_metrics)
        avg_validation_time = sum(m.validation_time for m in recent_metrics) / len(recent_metrics)

        return {
            "operations": len(recent_metrics),
            "total_commands_processed": total_commands,
            "total_errors": total_errors,
            "error_rate": f"{(total_errors / len(recent_metrics) * 100):.1f}%",
            "avg_processing_time_ms": f"{avg_processing_time * 1000:.2f}",
            "avg_validation_time_ms": f"{avg_validation_time * 1000:.2f}",
            "total_time_seconds": f"{total_time:.2f}",
            "commands_per_second": f"{total_commands / total_time:.2f}" if total_time > 0 else "0"
        }

# Example metrics collector
class MetricsCollector:
    """Simple metrics collector for demonstration."""

    def __init__(self):
        self.metrics_log = []

    def record_processing_metrics(self, metrics, operation_id):
        """Record successful processing metrics."""
        self.metrics_log.append({
            "timestamp": time.time(),
            "operation_id": operation_id,
            "type": "processing_success",
            "duration": metrics.end_time - metrics.start_time,
            "command_count": metrics.command_count,
            "function_count": metrics.function_count,
            "optimization_count": metrics.optimization_count
        })

    def record_error_metrics(self, metrics, error_message, operation_id):
        """Record error metrics."""
        self.metrics_log.append({
            "timestamp": time.time(),
            "operation_id": operation_id,
            "type": "processing_error",
            "error_message": error_message,
            "command_count": metrics.command_count,
            "duration": metrics.end_time - metrics.start_time
        })

# Usage example
metrics_collector = MetricsCollector()
observable_processor = ObservableCommandProcessor(metrics_collector)

# Process commands with metrics
commands = {
    "pre_run_cmds": ["echo 'start'", "mkdir -p /tmp/test"],
    "run_cmd": {"command_args": "python script.py"}
}

result = observable_processor.process_commands_with_metrics(commands, "operation_001")
summary = observable_processor.get_performance_summary()

print("Performance Summary:")
for key, value in summary.items():
    print(f"  {key}: {value}")
```

## Edge Cases and Troubleshooting

### Common Edge Cases

1. **Nested Quotes in Commands**
```python
# Commands with complex quoting
complex_quote_cmd = '''echo "He said 'Hello, world!' to me"'''
result = processor.process_commands({"run_cmd": {"command_args": complex_quote_cmd}})
```

2. **Very Long Command Lines**
```python
# Commands exceeding typical limits
long_cmd = "echo " + " ".join([f"'item_{i}'" for i in range(1000)])
# Process with truncation handling
```

3. **Binary Data in Commands**
```python
# Commands that might contain binary-like content
binary_cmd = "echo -e '\\x48\\x65\\x6c\\x6c\\x6f'"
```

4. **Unicode and International Characters**
```python
# Commands with unicode content
unicode_cmd = "echo 'Hello 世界 🌍'"
```

### Performance Optimization Tips

1. **Batch Processing**: Use batch processors for multiple command sets
2. **Validation Caching**: Cache validation results for repeated patterns
3. **Lazy Evaluation**: Only detect properties when needed
4. **Memory Management**: Clear large command structures after processing
5. **Logging Optimization**: Use high-entropy logging to reduce overhead

### Monitoring and Alerting

1. **Processing Time Alerts**: Alert on processing times > 5 seconds
2. **Error Rate Monitoring**: Alert on error rates > 5%
3. **Memory Usage**: Monitor command object memory consumption
4. **Validation Failures**: Track patterns of validation failures

This advanced patterns documentation provides comprehensive guidance for sophisticated use cases and production deployment scenarios.
