"""Network environment plugins for deployment topology management.

Network environments control how services are deployed, networked,
and orchestrated during PANTHER experiments.

Available Plugins:
    - **docker_compose** -- multi-container orchestration via Docker Compose
    - **shadow_ns** -- deterministic network simulation via Shadow
    - **localhost_single_container** -- single-container local execution

Each plugin generates Docker Compose YAML or equivalent configuration,
manages container lifecycle, and provides network topology to the
experiment manager.

Creating a New Network Environment Plugin:
    Directory structure::

        plugins/environments/network_environment/your_plugin/
        +-- __init__.py
        +-- your_plugin.py      # Inherits from INetworkEnvironment
        +-- config_schema.py    # Inherits from NetworkEnvironmentConfig

    Key methods to implement:
        - ``prepare_environment()`` -- validate config, allocate resources
        - ``setup_environment()`` -- create network topology
        - ``deploy_services()`` -- start containers/processes
        - ``monitor_environment()`` -- health checks during test execution
        - ``teardown_environment()`` -- clean up all resources

    Reference implementations: ``docker_compose/``, ``shadow_ns/``,
    ``localhost_single_container/``.
"""
