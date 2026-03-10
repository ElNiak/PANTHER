"""Thread-safety analysis execution environment via Valgrind Helgrind.

Detects data races, lock-order violations, and misuse of the
POSIX threading API in services under test. Runs the service
under Valgrind's Helgrind tool.

Key features:
    - Data race detection on shared memory
    - Lock ordering violation analysis
    - POSIX threading API misuse detection
    - Configurable history and conflict-cache sizes

See `HelgrindConfig` for all configuration options.
"""
