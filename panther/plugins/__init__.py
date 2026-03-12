"""PANTHER Plugin System.

Modular, extensible testing framework for network protocols using
inheritance-based architecture with decorator-based registration.

Plugin Categories:
    - **Services** -- IUT (Implementation Under Test) protocol
      implementations (picoquic, aioquic, quiche, quinn, lsquic, mvfst,
      quant, quic-go) and testers (panther_ivy formal verification).
    - **Protocols** -- Client-Server (HTTP, QUIC) and Peer-to-Peer
      (BitTorrent) protocol definitions.
    - **Environments** -- Network topology (docker_compose, shadow_ns,
      localhost) and Execution monitoring (gperf, strace, valgrind, gdb).

Service Inheritance::

    BaseQUICServiceManager           <- template method pattern
    +-- PythonQUICServiceManager     <- async/await (aioquic)
    +-- RustQUICServiceManager       <- Cargo integration (quiche, quinn)
    +-- Direct inheritance           <- C/Go (picoquic, lsquic, etc.)

Plugin Registration:
    Plugins use ``@register_plugin()`` for automatic discovery and validation.
    ``PluginManager`` provides thread-safe singleton access, multi-level
    caching, and lifecycle management.

    Discovery: Import -> Discovery -> Validation -> Instantiation -> Runtime.

Directory Layout::

    plugins/
    +-- environments/         # Network and execution environment plugins
    +-- protocols/            # Protocol definitions
    +-- services/             # IUT implementations and tester plugins
    +-- plugin_interface.py   # Base plugin interface
    +-- plugin_manager.py     # Plugin lifecycle management
    +-- plugin_loader.py      # Plugin loading utilities

Plugin Creation CLI:
    PANTHER provides CLI commands for scaffolding new plugins from templates::

        # Create a top-level plugin
        panther create plugin <TYPE> <NAME>
        # Types: service, environment, protocol

        # Create a subplugin within an existing plugin
        panther create subplugin <PLUGIN_TYPE> <PLUGIN_NAME> <SUBPLUGIN_TYPE>
        # e.g.: panther create subplugin service my_protocol iut

        # Create a complete service plugin with all subplugins
        panther create plugin service my_protocol --with-subplugins

        # Launch interactive tutorials for guided development
        panther tutorial run service
        panther tutorial run environment
        panther tutorial run protocol
        panther tutorial interactive

    In development mode (cloned repo), plugins are created in the source tree.
    In production mode (pip-installed), plugins go to ``~/.panther/plugins/``.

Per-Type Directory Structures:
    **Network Environment**::

        plugins/environments/network_environment/your_plugin/
        +-- __init__.py
        +-- your_plugin.py      # Inherits from INetworkEnvironment
        +-- config_schema.py    # Inherits from NetworkEnvironmentConfig

    **Execution Environment**::

        plugins/environments/execution_environment/your_plugin/
        +-- __init__.py
        +-- your_plugin.py      # Inherits from BaseExecutionEnvironment
        +-- config_schema.py    # Pydantic schema

    **Protocol**::

        plugins/protocols/client_server/your_protocol/  # or peer_to_peer/
        +-- __init__.py
        +-- protocol_plugin.py  # Inherits from ProtocolInterface
        +-- config_schema.py

    **IUT Service**::

        plugins/services/iut/<protocol>/<implementation>/
        +-- __init__.py
        +-- <implementation>.py # Inherits from BaseQUICServiceManager (or similar)
        +-- config_schema.py

    **Tester Service**::

        plugins/services/testers/your_tester/
        +-- __init__.py
        +-- plugin.py           # Inherits from IServiceManager
        +-- config_schema.py

Reference Implementations:
    Study these existing plugins as examples when building your own:

    - **IUT (C)**: ``services/iut/quic/picoquic/``
    - **IUT (Python)**: ``services/iut/quic/aioquic/``
    - **IUT (Rust)**: ``services/iut/quic/quiche/``
    - **Tester**: ``services/testers/panther_ivy/``
    - **Network env**: ``environments/network_environment/docker_compose/``
    - **Execution env**: ``environments/execution_environment/strace/``
    - **Protocol**: ``protocols/client_server/quic/``
"""

# Define the public API - but use lazy imports to avoid circular dependencies
__all__ = [
    "plugin_interface",
    "plugin_manager",
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
