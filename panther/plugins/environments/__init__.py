"""Environment plugins for PANTHER test execution.

Manages deployment topology and runtime monitoring for experiments.
Each environment plugin controls how services are launched, networked,
health-checked, and torn down.

Environment Categories:
    Network — deployment topology for services under test:
        - **docker_compose** – multi-container orchestration via Docker Compose
        - **shadow_ns** – deterministic replay with Shadow network simulator
        - **localhost_single_container** – single-container local execution

    Execution — runtime monitoring layers attached to running services:
        - **gperf_cpu** / **gperf_heap** – Google Performance Tools profiling
        - **strace** – system-call tracing
        - **memcheck** / **helgrind** – Valgrind memory and thread analysis
        - **gdb** – automated crash analysis with GDB
        - **iterations** – repeated execution for statistical analysis

Event-Driven Lifecycle:
    Environment plugins integrate with PANTHER's event system:

    ```
    EnvironmentSetupEvent
      → EnvironmentConfigurationEvent
      → EnvironmentReadyEvent
      → MonitoringStartEvent / MetricsCollectionEvent
      → EnvironmentTeardownEvent
      (on failure → EnvironmentErrorEvent)
    ```

    Environments generate `ShellCommand` objects executed via the
    command processor, which emits `CommandExecutionEvent` on completion.
    Background monitoring runs in a non-blocking thread with configurable
    metric types (cpu_usage, memory_usage, network_io, disk_io,
    process_stats).
"""
