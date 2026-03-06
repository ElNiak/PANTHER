"""Heap profiling execution environment via Google Performance Tools.

Uses gperftools `libtcmalloc.so` to track memory allocations
and detect leaks in services under test. Generates heap profiles
at configurable intervals.

Key features:
    - Periodic heap snapshots by allocation count
    - Leak detection with before/after comparison
    - PDF visualization of allocation call graphs
    - Growth-only filtering to focus on leaks

See `GperfHeapConfig` for all configuration options.
"""
