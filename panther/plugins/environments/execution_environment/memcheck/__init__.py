"""Memory error detection execution environment via Valgrind Memcheck.

Detects memory leaks, use-after-free, uninitialised reads, and
buffer overflows in services under test. No recompilation needed —
runs the unmodified binary under Valgrind.

Key features:
    - Full leak checking with loss-record categorisation
    - Uninitialised value origin tracking
    - Configurable free-list size and redzone bytes
    - XML output for automated parsing

See `MemcheckConfig` for all configuration options.
"""
