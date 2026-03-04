"""PANTHER Plugin System.

Modular, extensible testing framework for network protocols using
inheritance-based architecture with decorator-based registration.

Plugin Categories:
    Services
        - IUT (Implementation Under Test): protocol implementations to evaluate
          (picoquic, aioquic, quiche, quinn, lsquic, mvfst, quant, quic-go)
        - Testers: validation tools (panther_ivy formal verification)

    Protocols
        - Client-Server: HTTP, QUIC client-server testing
        - Peer-to-Peer: distributed protocol testing

    Environments
        - Network: deployment topology (docker_compose, shadow_ns, localhost)
        - Execution: runtime monitoring (gperf_cpu, gperf_heap, strace)

Inheritance Architecture::

    BaseQUICServiceManager           <-- template method pattern
    ├── PythonQUICServiceManager     <-- async/await (aioquic)
    ├── RustQUICServiceManager       <-- Cargo integration (quiche, quinn)
    └── Direct inheritance           <-- C/Go (picoquic, lsquic, etc.)

Plugin Registration:
    Plugins use ``@register_plugin()`` decorator for automatic discovery
    and validation. The PluginManager provides thread-safe singleton
    access, multi-level caching, and lifecycle management.

Directory Layout::

    plugins/
    ├── environments/         # Network and execution environment plugins
    ├── protocols/            # Protocol definitions (client_server, peer_to_peer)
    ├── services/             # IUT implementations and tester plugins
    ├── plugin_interface.py   # Base plugin interface
    ├── plugin_manager.py     # Plugin lifecycle management
    └── plugin_loader.py      # Plugin loading utilities

See Also:
    ``panther/plugins/development.md`` for the plugin development guide.
"""

# Define the public API - but use lazy imports to avoid circular dependencies
__all__ = [
    "plugin_interface",
    "plugin_manager",
    "plugin_loader_utils",
]

# Protocol plugins are auto-discovered through the plugin system
# No need for explicit imports here


def __getattr__(name):  # pylint: disable=invalid-name
    """Lazy import implementation to avoid circular imports."""
    if name == "plugin_interface":
        from . import plugin_interface  # pylint: disable=import-outside-toplevel

        return plugin_interface
    elif name == "plugin_manager":
        from . import plugin_manager  # pylint: disable=import-outside-toplevel

        return plugin_manager
    elif name == "plugin_creator":
        try:
            from ..tools.plugins import (  # pylint: disable=import-outside-toplevel
                plugin_creator,
            )

            return plugin_creator
        except ImportError:
            # Fallback if tools.plugins doesn't exist or doesn't have plugin_creator
            raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
