from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

"""
Output Aggregator

This module provides functionality to aggregate outputs from multiple execution environments
and prepare them for tester analysis.
"""

import logging
import os
import time
from pathlib import Path

from panther.core.events.environment.emitter import EnvironmentEventEmitter
from panther.core.outputs.output_collector import IOutputCollector


class OutputAggregator:
    """
    Central orchestrator for collecting and organizing outputs from PANTHER execution environments.

    The OutputAggregator coordinates output collection across multiple execution environments,
    providing event-driven progress tracking and organizing collected artifacts for efficient
    tester analysis. It handles heterogeneous environment types (Docker Compose, localhost,
    Shadow NS) and implements the IOutputCollector interface pattern.

    ## Architecture Integration

    ```mermaid
    sequenceDiagram
        participant EA as ExperimentAnalysis
        participant OA as OutputAggregator
        participant ENV as ExecutionEnvironment
        participant EE as EnvironmentEventEmitter

        EA->>OA: collect_from_environments(envs)
        OA->>EE: emit_output_collection_started()

        loop For each environment
            OA->>ENV: hasattr(collect_outputs)
            ENV-->>OA: true/false
            alt Implements IOutputCollector
                OA->>ENV: collect_outputs()
                ENV-->>OA: outputs dict
                OA->>ENV: get_output_metadata()
                ENV-->>OA: metadata dict
                OA->>EE: emit_outputs_collected()
            end
        end

        OA->>EE: emit_output_collection_completed()
        OA-->>EA: collected_outputs
    ```

    ## Collection Strategy

    The aggregator implements a two-phase collection strategy:

    1. **Active Collection**: Iterates through environments that implement `IOutputCollector`
       interface, collecting registered outputs with full metadata
    2. **Event Emission**: Provides real-time progress tracking through environment events
       for monitoring collection performance and debugging failures

    ## Output Organization

    Collected outputs are organized in two formats:
    - **Environment-centric**: `{env_type: {output_type: path}}` - useful for debugging
    - **Type-centric**: `{output_type: {env_type: path}}` - optimized for tester analysis

    ## Error Handling

    The aggregator implements graceful error handling:
    - Individual environment failures don't halt collection
    - Missing files are logged with diagnostic information
    - Partial collections are still returned for analysis
    - Event emission continues even on collection errors

    ## Performance Characteristics

    - **Sequential Collection**: Environments are processed in order
    - **Lazy Evaluation**: Only environments with `collect_outputs` method are processed
    - **Memory Efficient**: Output paths are returned rather than file contents
    """

    def __init__(
        self, experiment_dir: Path, environment_emitter: EnvironmentEventEmitter
    ):
        """
        Initialize the OutputAggregator.

        Args:
            experiment_dir: Directory where experiment outputs are stored
            environment_emitter: Event emitter for environment events
        """
        self.experiment_dir = Path(experiment_dir)
        self.environment_emitter = environment_emitter
        self.logger = logging.getLogger(__name__)

        self.outputs_dir = self.experiment_dir / "outputs"

    def ensure_outputs_dir(self) -> Path:
        """Create outputs directory on demand and return its path."""
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        return self.outputs_dir

    def collect_from_environments(
        self, environments: list
    ) -> Dict[str, Dict[str, str]]:
        """
        Collect outputs from all execution environments that implement IOutputCollector.

        Args:
            environments: List of environment plugins

        Returns:
            Dict[str, Dict[str, str]]: Dictionary mapping environment type to its outputs
                                     Example: {
                                         "strace": {"trace": "/path/to/trace.out"},
                                         "gperf_cpu": {"profile": "/path/to/profile.data"}
                                     }
        """
        self.logger.info("Starting output collection from execution environments")
        self.logger.info(f"Number of environments passed: {len(environments)}")
        self.logger.info(
            f"Environment types: {[env.__class__.__name__ for env in environments]}"
        )

        # Emit output collection started event
        self.environment_emitter.emit_output_collection_started(
            environment_id="all_environments",
            environment_name="Output Collection",
            environment_type="aggregator",
            collection_targets=[env.__class__.__name__ for env in environments],
            collection_config={"output_dir": str(self.outputs_dir)},
        )

        collected_outputs = {}
        collection_start_time = time.time()
        total_outputs = 0

        for env in environments:
            env_type = env.__class__.__name__
            self.logger.debug(f"Checking environment: {env_type}")
            self.logger.debug(
                f"  - isinstance(env, IOutputCollector): {isinstance(env, IOutputCollector)}"
            )
            self.logger.debug(
                f"  - hasattr(env, 'collect_outputs'): {hasattr(env, 'collect_outputs')}"
            )
            self.logger.debug(
                f"  - env.__class__.__mro__: {[cls.__name__ for cls in env.__class__.__mro__]}"
            )

            # Check for collect_outputs method instead of interface
            # This allows mixins that provide the method without declaring the interface
            if hasattr(env, "collect_outputs") and hasattr(env, "get_output_metadata"):
                self.logger.info(f"Collecting outputs from {env_type}")

                try:
                    # Collect outputs from this environment
                    outputs = env.collect_outputs()
                    metadata = env.get_output_metadata()

                    if outputs:
                        collected_outputs[env_type] = outputs
                        total_outputs += len(outputs)

                        # Emit batch outputs collected event
                        self.environment_emitter.emit_outputs_collected(
                            environment_id=env_type,
                            environment_name=env_type,
                            environment_type="execution",
                            outputs=outputs,
                            metadata=metadata,
                        )

                        self.logger.info(
                            f"Collected {len(outputs)} outputs from {env_type}: {list(outputs.keys())}"
                        )
                    else:
                        self.logger.warning(f"No outputs collected from {env_type}")

                except Exception as e:
                    self.logger.error(
                        f"Failed to collect outputs from {env_type}: {e}", exc_info=True
                    )
                    # Continue with other environments
            else:
                self.logger.debug(
                    f"Environment {env.__class__.__name__} does not implement IOutputCollector, skipping"
                )

        collection_duration = time.time() - collection_start_time

        # Emit output collection completed event
        self.environment_emitter.emit_output_collection_completed(
            environment_id="all_environments",
            environment_name="Output Collection",
            environment_type="aggregator",
            outputs={
                env_type: str(len(outputs))
                for env_type, outputs in collected_outputs.items()
            },
            total_outputs=total_outputs,
            collection_duration=collection_duration,
            collection_summary={
                "environments_processed": len(environments),
                "environments_with_outputs": len(collected_outputs),
            },
        )

        self.logger.info(
            f"Output collection completed in {collection_duration:.2f}s. Collected {total_outputs} outputs from {len(collected_outputs)} environments"
        )
        return collected_outputs

    def prepare_for_testers(
        self, collected_outputs: Optional[Dict[str, Dict[str, str]]] = None
    ) -> Dict[str, Dict[str, str]]:
        """
        Prepare collected outputs for tester analysis.

        This method organizes outputs by type rather than by environment,
        making it easier for testers to find relevant data.

        Args:
            collected_outputs: Optional pre-collected outputs. If None, will collect from environments.

        Returns:
            Dict[str, Dict[str, str]]: Dictionary organized by output type
                                     Example: {
                                         "trace": {"strace": "/path/to/trace.out"},
                                         "profile": {"gperf_cpu": "/path/to/profile.data"}
                                     }
        """
        if collected_outputs is None:
            self.logger.warning(
                "No collected outputs provided to prepare_for_testers. Cannot prepare outputs."
            )
            return {}

        self.logger.info("Preparing outputs for tester analysis")

        organized_outputs = {}

        # Reorganize outputs by type instead of by environment
        for env_type, outputs in collected_outputs.items():
            for output_type, output_path in outputs.items():
                if output_type not in organized_outputs:
                    organized_outputs[output_type] = {}
                organized_outputs[output_type][env_type] = output_path

        self.logger.info(
            f"Organized {sum(len(outputs) for outputs in organized_outputs.values())} outputs into {len(organized_outputs)} types: {list(organized_outputs.keys())}"
        )

        return organized_outputs
