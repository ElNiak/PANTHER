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

if TYPE_CHECKING:
    pass

from panther.core.events.environment.emitter import EnvironmentEventEmitter
from panther.core.outputs.output_collector import IOutputCollector


class OutputAggregator:
    """

    Aggregates outputs from execution environments and prepares them for tester analysis.
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

        # Create outputs directory
        self.outputs_dir = self.experiment_dir / "outputs"
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

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
            if isinstance(env, IOutputCollector) and hasattr(env, "collect_outputs"):
                env_type = env.__class__.__name__
                self.logger.debug(f"Collecting outputs from {env_type}")

                try:
                    # Collect outputs from this environment
                    outputs = env.collect_outputs()
                    metadata = env.get_output_metadata()

                    if outputs:
                        collected_outputs[env_type] = outputs
                        total_outputs += len(outputs)

                        # Emit individual output collected events
                        for output_type, output_path in outputs.items():
                            output_size = None
                            if os.path.exists(output_path):
                                output_size = os.path.getsize(output_path)

                            self.environment_emitter.emit_output_collected(
                                environment_id=env_type,
                                environment_name=env_type,
                                environment_type="execution",
                                output_type=output_type,
                                output_path=output_path,
                                output_size=output_size,
                                metadata=metadata.get(output_type, {}),
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
        self, collected_outputs: Optional[Dict[str, Dict[str, str]]]= None
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
