"""Localhost single-container network environment plugin.

Runs all services inside a single Docker container on localhost.
Useful for rapid iteration and debugging without multi-container overhead.

Key features:
    - Single container deployment (all services share a network namespace)
    - Minimal Docker overhead
    - Simplified debugging with direct process access
"""
