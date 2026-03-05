"""Environment plugins for PANTHER test execution.

Manages deployment topology and runtime monitoring for experiments.
Each environment plugin controls how services are launched, networked,
health-checked, and torn down.

Environment Categories:
    Network
        Deployment topology for services under test.

        - **docker_compose** – multi-container orchestration via Docker Compose
        - **shadow_ns** – deterministic replay with Shadow network simulator
        - **localhost_single_container** – single-container local execution

    Execution
        Runtime monitoring layers attached to running services.

        - **gperf_cpu** / **gperf_heap** – Google Performance Tools profiling
        - **strace** – system-call tracing
        - **memcheck** / **helgrind** – Valgrind memory and thread analysis

Event-Driven Lifecycle::

    EnvironmentSetupEvent
        → EnvironmentConfigurationEvent
        → EnvironmentReadyEvent
        → MonitoringStartEvent / MetricsCollectionEvent
        → EnvironmentTeardownEvent
        (on failure → EnvironmentErrorEvent)

Environments generate ``ShellCommand`` objects executed via the
command processor, which emits ``CommandExecutionEvent`` on completion.
Background monitoring runs in a non-blocking thread with configurable
metric types (cpu_usage, memory_usage, network_io, disk_io,
process_stats).

See Also:
    :mod:`panther.plugins.environments.config_schema`
        Base ``EnvironmentConfig`` dataclass.
    :doc:`/network_environment`
        Network environment user guide.
    :doc:`/execution_environment`
        Execution environment user guide.
"""
