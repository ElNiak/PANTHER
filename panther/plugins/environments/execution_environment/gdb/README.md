# GDB Execution Environment Plugin

> **Plugin Type**: Execution Environment
> **Source Location**: `plugins/environments/execution_environment/gdb/`

## Overview

The GDB Execution Environment wraps the GNU Debugger (GDB) around service processes to provide systematic, automated crash analysis during PANTHER experiments. When a service crashes (segfault, abort, floating-point exception), GDB automatically captures stack traces, register state, local variables, disassembly, and core dumps -- without requiring manual debugging sessions.

This environment is designed for investigating crashes, segfaults, and assertion failures in native (C/C++) protocol implementations such as Picoquic or LSQUIC. It can also integrate with AddressSanitizer (ASan) for combined coverage of memory errors.

### When to Use GDB vs Other Environments

| Environment | Focus |
|-------------|-------|
| **GDB** | Crash debugging, post-mortem analysis, stack traces |
| **Memcheck** | Runtime memory error detection (no recompilation needed, slower) |
| **Helgrind** | Thread safety and race condition analysis |
| **Strace** | Syscall-level tracing (no debug symbols needed) |
| **GPerf CPU** | CPU profiling for performance analysis |

## Configuration Options

<!-- src: config_schema.py -->

`GdbConfig` inherits from `ExecutionEnvironmentPluginConfig`, which provides the `enabled` (default: `True`) and `collect_metrics` (default: `True`) fields.

### Inherited Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `True` | Enable or disable the plugin |
| `collect_metrics` | `bool` | `True` | Whether to collect metrics |

### Plugin Type

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `str` | `"gdb"` | Execution environment type identifier |

### GDB Binary Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `gdb_binary` | `str` | `"/usr/bin/gdb"` | Absolute path to the GDB binary |

### Debugging Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enable_core_dumps` | `bool` | `True` | Enable core dump generation for post-mortem analysis |
| `auto_backtrace` | `bool` | `True` | Automatically print a stack trace on crash |
| `backtrace_full` | `bool` | `True` | Include local variable values in stack traces (`bt full`) |
| `max_backtrace_depth` | `int` | `50` | Maximum number of stack frames in a backtrace |

### Compilation Flags for Debug Symbols

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `debug_symbols` | `bool` | `True` | Add `-g` flag during compilation for source-level debug info |
| `optimization_level` | `str` | `"O0"` | Compiler optimization level. Valid: `O0`, `O1`, `O2`, `O3`, `Os`, `Og` |
| `frame_pointer` | `bool` | `True` | Keep frame pointers (`-fno-omit-frame-pointer`) for reliable stack traces |
| `rdynamic` | `bool` | `True` | Add `-rdynamic` linker flag for dynamic symbol resolution in backtraces |

### AddressSanitizer Integration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enable_asan` | `bool` | `False` | Enable AddressSanitizer (`-fsanitize=address`). Requires recompilation |
| `asan_options` | `List[str]` | `["symbolize=1", "print_stacktrace=1", "check_initialization_order=1", "strict_init_order=1"]` | ASan runtime options passed via `ASAN_OPTIONS` env var |

### GDB Automation Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `run_command` | `str` | `"run"` | Initial GDB command to execute when the session starts |
| `break_on_signals` | `List[str]` | `["SIGSEGV", "SIGABRT", "SIGFPE"]` | Signals that GDB should automatically break on |
| `break_on_exceptions` | `bool` | `True` | Set a catchpoint to break on C++ exceptions |

### Output Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `output_format` | `str` | `"detailed"` | Report detail level. Valid: `minimal`, `standard`, `detailed` |
| `save_gdb_log` | `bool` | `True` | Save the complete GDB session log to a file |
| `save_core_dump` | `bool` | `True` | Preserve core dump files for post-mortem analysis |

### Timeout Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `execution_timeout` | `int` | `300` | Maximum execution time (seconds) before forced termination |
| `gdb_timeout` | `int` | `60` | Maximum time (seconds) to wait for individual GDB commands |

### Additional GDB Commands

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `init_commands` | `List[str]` | `[]` | Custom GDB commands to run at session startup before the program launches |
| `post_crash_commands` | `List[str]` | `["info registers", "info locals", "info args", "disassemble", "thread apply all bt"]` | GDB commands executed automatically after a crash is detected |

### Environment Variables for Debugging

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `debug_env_vars` | `dict` | `{"MALLOC_CHECK_": "2", "LIBC_FATAL_STDERR_": "1", "SEGFAULT_SIGNALS": "all"}` | Environment variables injected into the debugged process for enhanced error reporting |

## Usage Example

### Basic Crash Analysis

```yaml
tests:
  - name: "crash_analysis"
    network_environment:
      type: docker_compose
    execution_environments:
      - type: gdb
        auto_backtrace: true
        backtrace_full: true
        enable_core_dumps: true
        debug_symbols: true
        optimization_level: O0
        output_format: detailed
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
```

### With AddressSanitizer

```yaml
tests:
  - name: "asan_crash_analysis"
    execution_environments:
      - type: gdb
        enable_asan: true
        asan_options:
          - "symbolize=1"
          - "print_stacktrace=1"
          - "detect_leaks=1"
        auto_backtrace: true
        debug_symbols: true
        optimization_level: O0
        save_core_dump: true
        execution_timeout: 600
```

### Custom GDB Commands

```yaml
tests:
  - name: "custom_debug_session"
    execution_environments:
      - type: gdb
        init_commands:
          - "set pagination off"
          - "set print pretty on"
          - "set print array on"
        post_crash_commands:
          - "info registers"
          - "info locals"
          - "info args"
          - "disassemble"
          - "thread apply all bt"
          - "info sharedlibrary"
        break_on_signals:
          - "SIGSEGV"
          - "SIGABRT"
          - "SIGFPE"
          - "SIGBUS"
        break_on_exceptions: true
        output_format: detailed
```

## Integration

- **Service Managers** -- Wraps service commands with GDB in batch mode for automated crash capture.
- **Result Collection** -- Generates GDB session logs, stack traces, core dumps, register/variable dumps, and disassembly as test artifacts.
- **AddressSanitizer** -- Optionally combines with ASan for memory error detection alongside crash analysis.
- **Compilation Pipeline** -- Injects debug flags (`-g`, `-O0`, `-fno-omit-frame-pointer`) into the build to ensure meaningful stack traces.

## Troubleshooting

### Missing GDB Binary

Ensure GDB is installed in the container. Add to your Dockerfile:

```dockerfile
RUN apt-get update && apt-get install -y gdb
```

Or override the binary path:

```yaml
execution_environments:
  - type: gdb
    gdb_binary: "/usr/local/bin/gdb"
```

### No Debug Symbols in Stack Traces

If stack traces show only hex addresses without function names, ensure `debug_symbols: true` and `optimization_level: O0`. The service's implementation must be compiled with `-g` for source-level information.

### Core Dumps Not Generated

Verify the container has permission to write core dumps. The container may need `SYS_PTRACE` capability and `ulimit -c unlimited`.

### Timeout Issues

For long-running debug sessions, increase both timeout values:

```yaml
execution_environments:
  - type: gdb
    execution_timeout: 600   # 10 minutes for the debugged process
    gdb_timeout: 120          # 2 minutes per GDB command
```

## References

- [GDB Documentation](https://sourceware.org/gdb/current/onlinedocs/gdb/)
- [AddressSanitizer Documentation](https://clang.llvm.org/docs/AddressSanitizer.html)
- [PANTHER Execution Environment Interface](../README.md)
