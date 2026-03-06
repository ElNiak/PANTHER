"""System-call tracing execution environment via strace.

Traces system calls and signals for services under test.
No debug symbols or recompilation required.

Key features:
    - Syscall filtering by category or name
    - Timestamp and duration reporting
    - Child process following
    - Per-syscall statistics summary

See `StraceConfig` for all configuration options.
"""
