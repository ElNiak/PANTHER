"""GDB debugging execution environment plugin.

Wraps service processes with GDB for automated crash analysis.
On crash (SIGSEGV, SIGABRT, SIGFPE), GDB captures stack traces,
register state, local variables, and core dumps automatically.

Key features:
    - Post-mortem stack traces with local variables (`bt full`)
    - Core dump generation for offline analysis
    - AddressSanitizer (ASan) integration for memory error detection
    - Configurable signal breakpoints and C++ exception catching
    - Debug symbol compilation flags (`-g`, `-O0`, `-fno-omit-frame-pointer`)

See `GdbConfig` for all configuration options.
"""

from .config_schema import GdbConfig

__all__ = ["GdbConfig"]

# GdbEnvironment is available but not imported here to avoid circular imports
# during plugin discovery. It will be discovered by the plugin system.
