"""Forge fetch: pull/merge-request data cached as immutable disk snapshots.

The ONLY networked stage in the package. It fetches once, writes a sorted
immutable snapshot, and every downstream stage reads only the cache — same
inputs, same bytes, network or no network.
"""

from .store import ForgeError, read_snapshot, write_snapshot

__all__ = ["ForgeError", "read_snapshot", "write_snapshot"]
