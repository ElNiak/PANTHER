from typing import TYPE_CHECKING, List, Optional

"""
Iterations execution environment for running tests multiple times.

This plugin creates a wrapper script that executes the original command multiple times,
useful for statistical analysis, stress testing, and measuring performance variance.
"""

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.execution_environment.base_execution_environment import (
    BaseExecutionEnvironment,
)
from panther.plugins.environments.execution_environment.command_generation_utils import (
    create_execution_environment_builder,
)
from panther.plugins.environments.execution_environment.iterations.config_schema import (
    IterationsConfig,
)
from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    pass


@register_plugin(
    plugin_type="environment",
    name="iterations",
    version="1.0.0",
    description="Execution environment for running multiple test iterations",
    author="PANTHER Team",
    capabilities=["iterative_testing", "statistical_analysis", "performance_variance"],
    external_dependencies=[],
)
class IterationsEnvironment(BaseExecutionEnvironment):
    """

    Iterations execution environment for running multiple test iterations.

    This environment creates a wrapper script that executes the original command
    multiple times with optional delays between iterations, collecting execution
    statistics and results.
    """

    def __init__(
        self,
        env_config_to_test: IterationsConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        """Initialize the iterations environment."""
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

    def _setup_plugin_specific_environment(
        self, services_managers: List[IServiceManager], timestamp: str
    ):
        """
        Set up iterative testing environment using shared utilities.

        Args:
            services_managers: List of service managers to run iterations on
            timestamp: Timestamp for this execution (used for file naming)
        """
        iterations = self.env_config_to_test.iterations
        delay = self.env_config_to_test.delay_between_iterations

        self.logger.info(
            "Setting up iterations environment for %d iterations with %ds delay",
            iterations,
            delay,
        )

        # Only set up iterations wrapper if we have more than 1 iteration
        if iterations <= 1:
            self.logger.info("Single iteration configured, no wrapper needed")
            return

        for service in services_managers:
            service_name = getattr(service, "service_name", service.__class__.__name__)

            # Create command builder using shared utilities
            command_builder = create_execution_environment_builder(
                service=service,
                environment_name="iterations",
                timestamp=timestamp,
                register_output_callback=self.register_output_file,
                logger=self.logger,
            )

            # Register iteration log file
            iteration_log = command_builder.register_output_file(
                file_type="iterations",
                extension="log",
                description=f"Iteration execution log for {iterations} iterations",
            )

            # Create the iterations wrapper script
            wrapper_script_content = f"""#!/bin/bash
iterations_log="{iteration_log}"
iterations_count={iterations}
delay_between={delay}

echo "Starting iterations wrapper for $iterations_count iterations" >> "$iterations_log"

for iteration in $(seq 1 $iterations_count); do
    echo "Starting iteration $iteration of $iterations_count" >> "$iterations_log"
    if [ $iteration -gt 1 ] && [ $delay_between -gt 0 ]; then
        echo "Waiting $delay_between seconds between iterations..." >> "$iterations_log"
        sleep $delay_between
    fi

    # Execute the wrapped command
    echo "Executing command: $*" >> "$iterations_log"
    start_time=$(date +%s)
    "$@"
    exit_code=$?
    end_time=$(date +%s)
    duration=$((end_time - start_time))

    echo "Completed iteration $iteration of $iterations_count (exit code: $exit_code, duration: ${duration}s)" >> "$iterations_log"

    # If command failed, should we continue? For now, continue iterations
    if [ $exit_code -ne 0 ]; then
        echo "Iteration $iteration failed with exit code $exit_code, continuing..." >> "$iterations_log"
    fi
done

echo "All iterations completed" >> "$iterations_log"
"""

            # Build wrapper setup command
            wrapper_setup_cmd = f"""
# Create iterations wrapper script
cat > /tmp/iterations_wrapper_{service_name}.sh << 'ITER_EOF'
{wrapper_script_content}
ITER_EOF

chmod +x /tmp/iterations_wrapper_{service_name}.sh

if [ -z "$EXEC_ENV_WRAPPERS" ]; then
    export EXEC_ENV_WRAPPERS="/tmp/iterations_wrapper_{service_name}.sh"
else
    export EXEC_ENV_WRAPPERS="/tmp/iterations_wrapper_{service_name}.sh $EXEC_ENV_WRAPPERS"
fi
echo "Added iterations wrapper for {iterations} iterations" >> /app/logs/{service_name}_exec_env_setup.log
""".strip()

            # Add environment variables for iteration tracking
            env_vars = {
                "ITERATIONS_OUTPUT_FILE": iteration_log,
                "ITERATIONS_COUNT": str(iterations),
                "ITERATIONS_DELAY": str(delay),
            }

            # Use shared utilities to add wrapper command
            command_builder.add_wrapper_command(
                wrapper_command=wrapper_setup_cmd,
                description=f"Setup iterations wrapper for {service_name} ({iterations} iterations)",
                additional_env_vars=env_vars,
                is_critical=False,
            )

            # Apply the configuration
            command_builder.build_and_apply(self.modify_service_commands)

            self.logger.info(
                "Enhanced service %s with iterations wrapper for %d iterations",
                service_name,
                iterations,
            )

        self.logger.info("Iterations environment setup completed")

    def to_command(self, *args, **kwargs) -> str:
        """
        Generate the iterations wrapper script path.

        Args:
            *args: Variable arguments (for compatibility with base class)
            **kwargs: Keyword arguments (for compatibility with base class)
                - service_name: Name of the service for logging purposes
                - output_file: Optional output file path for iteration logs

        Returns:
            Path to the iterations wrapper script
        """
        # Extract service_name from args/kwargs for compatibility
        service_name = kwargs.get("service_name")
        if not service_name and args:
            service_name = args[0] if isinstance(args[0], str) else None

        iterations = self.env_config_to_test.iterations

        if iterations <= 1:
            # No wrapper needed for single iteration
            return ""

        # Return the path to the wrapper script that will be created
        service_part = f"_{service_name}" if service_name else ""
        return f"/tmp/iterations_wrapper{service_part}.sh"
