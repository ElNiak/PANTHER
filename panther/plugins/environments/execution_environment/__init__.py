"""Execution environment plugins for runtime monitoring and profiling.

Execution environments wrap service processes with monitoring, profiling,
and analysis tools. They modify Docker commands (via ``LD_PRELOAD``,
command prefixes, or environment variables) to inject instrumentation
without changing the service itself.

Available Plugins:
    - **gdb** -- automated crash analysis, stack traces, core dumps
    - **gperf_cpu** -- CPU profiling via Google Performance Tools
    - **gperf_heap** -- heap allocation profiling via Google Performance Tools
    - **strace** -- system-call tracing
    - **memcheck** -- Valgrind memory error detection
    - **helgrind** -- Valgrind thread-safety analysis
    - **iterations** -- repeated execution for statistical analysis

All plugins inherit from ``BaseExecutionEnvironment`` and implement
``IExecutionEnvironment``. Configuration uses Pydantic schemas in
each plugin's ``config_schema.py``.

Creating a New Execution Environment Plugin:
    Directory structure::

        plugins/environments/execution_environment/your_plugin/
        +-- __init__.py
        +-- your_plugin.py      # Inherits from BaseExecutionEnvironment
        +-- config_schema.py    # Pydantic config (set _config_class on your class)

    Key methods to implement:
        - ``setup_environment()`` -- install/configure the tool in the container
        - ``is_service_compatible()`` -- check if a service can use this env
        - ``generate_command()`` -- wrap the service command with instrumentation

    Subclasses set ``_config_class = YourConfig`` and use inherited
    ``_get_plugin_config()`` / ``_get_config_value()`` helpers from
    ``BaseExecutionEnvironment``.

    Reference implementations: ``gperf_cpu/``, ``strace/``, ``memcheck/``.
"""

from .base_execution_environment import BaseExecutionEnvironment
from .execution_environment_interface import IExecutionEnvironment

__all__ = ["BaseExecutionEnvironment", "IExecutionEnvironment"]
