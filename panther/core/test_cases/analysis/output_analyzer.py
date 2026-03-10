"""Output collection and analysis for test cases."""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from panther.core.outputs.output_aggregator import OutputAggregator
from panther.core.outputs.service_health_analyzer import (
    ServiceHealth,
    ServiceHealthAnalyzer,
)
from panther.plugins.services.testers.tester_interface import ITesterManager


class OutputAnalyzer:
    """Handles output collection and analysis from test executions."""

    def __init__(self, test_case):
        """Initialize output analyzer with reference to parent test case."""
        self.test_case = test_case
        self.logger = test_case.logger

    def collect_outputs(self) -> Dict[str, Any]:
        """Collect outputs from all execution environments."""
        self.logger.info("Collecting outputs from execution environments")

        try:
            start_time = time.time()

            # CRITICAL FIX: Register outputs before collection
            # This ensures outputs are available for analysis
            self._register_outputs_before_collection()

            # Get environment emitter if available
            env_emitter = None
            if self.test_case.emitter_registry:
                env_emitter = self.test_case.emitter_registry.environment_emitter

            # Emit output collection started
            if env_emitter:
                env_emitter.emit_output_collection_started(
                    environment_id=f"output_collection_{self.test_case.test_name}",
                    environment_name=self.test_case.test_name,
                    environment_type="output_collection",
                    collection_targets=[
                        env.__class__.__name__
                        for env in self.test_case.environment_plugin_manager
                    ],
                )

            # Create output aggregator
            aggregator = OutputAggregator(
                experiment_dir=self.test_case.test_experiment_dir,
                environment_emitter=env_emitter,
            )

            # Collect outputs from execution environments (both network and execution environments)
            self.logger.info(
                f"Getting environments from test_case.environment_plugin_manager: {len(self.test_case.environment_plugin_manager)} environments"
            )
            all_environments = self.test_case.environment_plugin_manager.copy()
            self.logger.info(
                f"Passing {len(all_environments)} environments to aggregator"
            )
            collected_outputs = aggregator.collect_from_environments(all_environments)

            # Prepare outputs for testers
            organized_outputs = aggregator.prepare_for_testers(collected_outputs)

            duration = time.time() - start_time

            # Emit output collection completed
            if env_emitter:
                env_emitter.emit_output_collection_completed(
                    environment_id=f"output_collection_{self.test_case.test_name}",
                    environment_name=self.test_case.test_name,
                    environment_type="output_collection",
                    outputs=organized_outputs,
                    total_outputs=len(organized_outputs),
                    collection_duration=duration,
                )

            self.logger.info(f"Output collection completed in {duration:.2f}s")
            return organized_outputs

        except Exception as e:
            self.logger.error("Failed to collect outputs: %s", e, exc_info=True)
            # Emit output collection failed
            if env_emitter:
                env_emitter.emit_output_collection_failed(
                    environment_id=f"output_collection_{self.test_case.test_name}",
                    environment_name=self.test_case.test_name,
                    environment_type="output_collection",
                    error_message=str(e),
                    error_type=type(e).__name__,
                )
            raise

    def run_tester_analysis(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run analysis on collected outputs using configured testers."""
        self.logger.info("Running tester analysis on collected outputs")

        analysis_results = {}

        try:
            # Get emitters if available
            service_emitter = None
            if self.test_case.emitter_registry:
                service_emitter = self.test_case.emitter_registry.service_emitter

            # Emit analysis started
            if service_emitter:
                service_emitter.emit_tester_analysis_started(
                    service_id="tester_analysis",
                    service_name="Output Analysis",
                    test_name=self.test_case.test_name,
                    output_types=list(outputs.keys()),
                    tester_config={},
                )

            # Find tester service managers
            tester_managers = [
                sm
                for sm in self.test_case.service_managers
                if isinstance(sm, ITesterManager)
            ]

            if not tester_managers:
                self.logger.info("No testers configured for analysis")
                return analysis_results

            # Run analysis with each tester
            for tester in tester_managers:
                try:
                    tester_name = tester.service_name
                    self.logger.info(f"Running analysis with tester: {tester_name}")

                    # Prepare tester inputs
                    tester_inputs = self._prepare_tester_inputs(tester, outputs)

                    # Set collected outputs on the tester
                    tester.set_collected_outputs(outputs)

                    # Run tester analysis
                    start_time = time.time()
                    results = tester.analyze_outputs()
                    duration = time.time() - start_time

                    if results:
                        analysis_results[tester_name] = {
                            "results": results,
                            "duration": duration,
                            "status": "completed",
                        }
                        self.logger.info(
                            f"Tester {tester_name} analysis completed in {duration:.2f}s"
                        )
                    else:
                        analysis_results[tester_name] = {
                            "results": None,
                            "duration": duration,
                            "status": "no_results",
                        }
                        self.logger.warning(f"Tester {tester_name} returned no results")

                except Exception as e:
                    self.logger.error(f"Tester {tester_name} analysis failed: {e}")
                    analysis_results[tester_name] = {
                        "results": None,
                        "error": str(e),
                        "status": "failed",
                    }

            # Save analysis results
            self._save_analysis_results(analysis_results)

            # Emit analysis completed
            if service_emitter:
                passed_count = len(
                    [
                        r
                        for r in analysis_results.values()
                        if r.get("status") == "completed"
                    ]
                )
                service_emitter.emit_tester_analysis_completed(
                    service_id="tester_analysis",
                    service_name="Output Analysis",
                    test_name=self.test_case.test_name,
                    analysis_passed=passed_count == len(tester_managers),
                    findings=analysis_results,
                    summary=f"Analysis completed: {passed_count}/{len(tester_managers)} testers passed",
                    duration=time.time() - start_time,
                )

            return analysis_results

        except Exception as e:
            self.logger.error(f"Tester analysis failed: {e}")
            # Emit analysis failed
            if service_emitter:
                service_emitter.emit_tester_analysis_completed(
                    service_id="tester_analysis",
                    service_name="Output Analysis",
                    test_name=self.test_case.test_name,
                    analysis_passed=False,
                    findings={"error": str(e)},
                    summary=f"Analysis failed: {str(e)}",
                    duration=0,
                )
            return analysis_results

    def _prepare_tester_inputs(
        self, tester: ITesterManager, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare inputs for tester analysis."""
        # Extract relevant outputs for the tester
        tester_inputs = {
            "test_name": self.test_case.test_name,
            "test_dir": str(self.test_case.test_experiment_dir),
            "outputs": outputs,
            "service_logs": {},
            "network_captures": {},
            "metrics": {},
        }

        # Add service-specific logs
        for service_manager in self.test_case.service_managers:
            service_name = service_manager.service_name
            log_path = self.test_case.test_experiment_dir / service_name / "service.log"
            if log_path.exists():
                tester_inputs["service_logs"][service_name] = str(log_path)

        # Add network captures if available
        pcap_dir = self.test_case.test_experiment_dir / "pcaps"
        if pcap_dir.exists():
            for pcap_file in pcap_dir.glob("*.pcap"):
                tester_inputs["network_captures"][pcap_file.stem] = str(pcap_file)

        # Add metrics if available
        metrics_file = self.test_case.test_experiment_dir / "metrics.json"
        if metrics_file.exists():
            import json

            with open(metrics_file, "r") as f:
                tester_inputs["metrics"] = json.load(f)

        return tester_inputs

    def _register_outputs_before_collection(self):
        """
        Register outputs from all environments before collection starts.

        This is a critical fix for the timing issue where outputs were only
        registered during teardown, which happened AFTER tester analysis.
        Now we ensure outputs are registered and available for collection.
        """
        self.logger.debug("Pre-registering outputs before collection")

        # Get all environments that need output registration
        # Use the actual environment plugin manager that contains all environment instances
        all_environments = self.test_case.environment_plugin_manager.copy()

        # Register outputs for each environment
        for env in all_environments:
            if hasattr(env, "output_manager") and hasattr(env, "services_managers"):
                try:
                    self.logger.debug(
                        f"Pre-registering outputs for {env.__class__.__name__}"
                    )
                    env.output_manager.perform_final_output_registration(
                        env.services_managers
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Failed to pre-register outputs for {env.__class__.__name__}: {e}"
                    )
                    # Continue with other environments

        self.logger.debug("Pre-registration complete")

    def _save_analysis_results(self, results: Dict[str, Any]) -> None:
        """Save analysis results to disk."""
        try:
            import json

            analysis_dir = self.test_case.test_experiment_dir / "analysis"
            analysis_dir.mkdir(exist_ok=True)

            # Save combined results
            results_file = analysis_dir / "analysis_results.json"
            with open(results_file, "w") as f:
                json.dump(results, f, indent=2, default=str)

            self.logger.info(f"Analysis results saved to {results_file}")

            # Save individual tester results
            for tester_name, tester_results in results.items():
                if tester_results.get("results"):
                    tester_file = analysis_dir / f"{tester_name}_results.json"
                    with open(tester_file, "w") as f:
                        json.dump(tester_results["results"], f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Failed to save analysis results: {e}")
            # Continue execution even if save fails

    def run_service_health_analysis(self) -> List[ServiceHealth]:
        """Analyze ALL services (IUT + tester) for basic health metrics.

        Iterates through environment plugins to find service managers,
        then runs generic health analysis on each service's log directory.

        Returns:
            List of ServiceHealth results.
        """
        self.logger.info("Running service health analysis for all services")
        analyzer = ServiceHealthAnalyzer()
        health_results: List[ServiceHealth] = []

        try:
            for env in self.test_case.environment_plugin_manager:
                if not hasattr(env, "services_managers"):
                    continue

                def _get_log_dir(service_name: str, _env=env):
                    if hasattr(_env, "_get_service_log_directory"):
                        return _env._get_service_log_directory(service_name)
                    # Fallback: service subdir under test experiment dir
                    return self.test_case.test_experiment_dir / service_name

                results = analyzer.analyze_all_services(
                    env.services_managers,
                    _get_log_dir,
                )
                health_results.extend(results)

            # Deduplicate by service_name — multiple environments share the same
            # services_managers, causing duplicate analysis. Prefer the result
            # with the most log data (highest log_size_bytes).
            seen: dict = {}
            for h in health_results:
                if (
                    h.service_name not in seen
                    or h.log_size_bytes > seen[h.service_name].log_size_bytes
                ):
                    seen[h.service_name] = h
            health_results = list(seen.values())

            self._save_service_health(health_results)
            self.logger.info(
                "Service health analysis complete: %d services analyzed",
                len(health_results),
            )
        except Exception as e:
            self.logger.error("Service health analysis failed: %s", e, exc_info=True)

        return health_results

    def _save_service_health(self, health_results: List[ServiceHealth]) -> None:
        """Save service health results to analysis/service_health.json."""
        try:
            analysis_dir = self.test_case.test_experiment_dir / "analysis"
            analysis_dir.mkdir(exist_ok=True)
            health_file = analysis_dir / "service_health.json"
            with open(health_file, "w") as f:
                json.dump([h.to_dict() for h in health_results], f, indent=2)
            self.logger.info("Service health saved to %s", health_file)
        except Exception as e:
            self.logger.error("Failed to save service health: %s", e)

    def _analyze_test_configuration(self):
        """Analyze basic test configuration."""
        self.logger.info("    📝 Test Name: %s", self.test_config.name)
        self.logger.info("    📄 Description: %s", self.test_config.description)

        if hasattr(self.test_config, "timeout") and self.test_config.timeout:
            self.logger.info("    ⏱️  Timeout: %s", self.test_config.timeout)

    def _analyze_service_configurations(self) -> bool:
        """Analyze service configurations for dry-run."""
        try:
            if hasattr(self.test_config, "iut") and self.test_config.iut:
                self.logger.info("    🎯 IUT: %s", self.test_config.iut.name)

            if hasattr(self.test_config, "tester") and self.test_config.tester:
                self.logger.info("    🧪 Tester: %s", self.test_config.tester.name)

            if hasattr(self.test_config, "services") and self.test_config.services:
                self.logger.info(
                    "    ⚙️  Services: %d configured", len(self.test_config.services)
                )
                for service_name, service_config in self.test_config.services.items():
                    self.logger.info(
                        "      - %s: %s",
                        service_name,
                        getattr(service_config, "name", "unnamed"),
                    )

            return True
        except Exception as e:
            self.logger.error("    ❌ Service configuration analysis failed: %s", e)
            return False

    def _analyze_environment_configuration(self) -> bool:
        """Analyze environment configurations for dry-run."""
        try:
            if (
                hasattr(self.test_config, "network_environment")
                and self.test_config.network_environment
            ):
                env_type = getattr(
                    self.test_config.network_environment, "type", "unknown"
                )
                self.logger.info("    🌐 Network Environment: %s", env_type)

            if (
                hasattr(self.test_config, "execution_environment")
                and self.test_config.execution_environment
            ):
                if isinstance(self.test_config.execution_environment, list):
                    self.logger.info(
                        "    ⚙️  Execution Environments: %d configured",
                        len(self.test_config.execution_environment),
                    )
                    for env in self.test_config.execution_environment:
                        env_name = getattr(env, "name", getattr(env, "type", "unnamed"))
                        self.logger.info("      - %s", env_name)
                else:
                    env_name = getattr(
                        self.test_config.execution_environment,
                        "name",
                        getattr(
                            self.test_config.execution_environment, "type", "unnamed"
                        ),
                    )
                    self.logger.info("    ⚙️  Execution Environment: %s", env_name)
            else:
                self.logger.info("    ⚙️  Execution Environment: None configured")

            return True
        except Exception as e:
            self.logger.error("    ❌ Environment configuration analysis failed: %s", e)
            return False

    def _analyze_steps_configuration(self) -> bool:
        """Analyze test steps configuration for dry-run."""
        try:
            if hasattr(self.test_config, "steps") and self.test_config.steps:
                # Handle StepsConfig object structure
                if hasattr(self.test_config.steps, "wait"):
                    self.logger.info("    📋 Steps: Wait step configured")
                    self.logger.info(
                        "      - Wait: %s seconds", self.test_config.steps.wait
                    )
                elif hasattr(self.test_config.steps, "__len__"):
                    # If it's a list-like object
                    try:
                        step_count = len(self.test_config.steps)
                        self.logger.info("    📋 Steps: %d configured", step_count)
                        for i, step in enumerate(self.test_config.steps, 1):
                            step_type = getattr(step, "type", "unknown")
                            self.logger.info("      %d. %s step", i, step_type)

                            # Show command that would be executed without running it
                            if hasattr(step, "command") and step.command:
                                self.logger.info("         Command: %s", step.command)
                            elif hasattr(step, "wait") and step.wait:
                                self.logger.info("         Wait: %s seconds", step.wait)
                    except:
                        # Fallback for complex step objects
                        self.logger.info("    📋 Steps: Custom steps configured")
                        step_attrs = [
                            attr
                            for attr in dir(self.test_config.steps)
                            if not attr.startswith("_")
                        ]
                        if step_attrs:
                            self.logger.info(
                                "      - Step attributes: %s", ", ".join(step_attrs[:3])
                            )
                else:
                    # Handle single step object
                    self.logger.info("    📋 Steps: Single step configured")
                    step_attrs = [
                        attr
                        for attr in dir(self.test_config.steps)
                        if not attr.startswith("_")
                        and hasattr(self.test_config.steps, attr)
                    ]
                    if step_attrs:
                        self.logger.info(
                            "      - Step type: %s",
                            step_attrs[0] if step_attrs else "unknown",
                        )
            else:
                self.logger.info("    📋 Steps: None configured")

            return True
        except Exception as e:
            self.logger.error("    ❌ Steps configuration analysis failed: %s", e)
            return False
