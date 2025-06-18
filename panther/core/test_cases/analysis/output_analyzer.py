"""Output collection and analysis for test cases."""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from panther.core.outputs.output_aggregator import OutputAggregator
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
                    collection_targets=[env.__class__.__name__ for env in self.test_case.environment_plugin_manager],
                )

            # Create output aggregator
            aggregator = OutputAggregator(
                experiment_dir=self.test_case.test_experiment_dir,
                environment_emitter=env_emitter,
            )

            # Collect outputs from execution environments (both network and execution environments)
            all_environments = self.test_case.environment_plugin_manager.copy()
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
            self.logger.error(f"Failed to collect outputs: {e}")
            # Emit output collection failed
            if env_emitter:
                env_emitter.emit_output_collection_failed(
                    environment_id=f"output_collection_{self.test_case.test_name}",
                    environment_name=self.test_case.test_name,
                    environment_type="output_collection",
                    error_message=str(e),
                    error_type=type(e).__name__
                )
            # Return empty dict to allow test to continue
            return {}

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

                    # Run tester analysis
                    start_time = time.time()
                    results = tester.analyze(tester_inputs)
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
                passed_count = len([r for r in analysis_results.values() if r.get("status") == "completed"])
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
