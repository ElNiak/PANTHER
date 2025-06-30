#!/usr/bin/env python3
"""
Load Testing for PANTHER Concurrent Experiments

This module tests PANTHER's ability to handle multiple concurrent experiments,
measuring performance, resource usage, and system stability under load.
"""

import concurrent.futures
import json
import multiprocessing
import shutil
import statistics
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import psutil
import yaml

class ExperimentLoadGenerator:
    """Generate load by running multiple PANTHER experiments concurrently."""

    def __init__(
        self,
        base_config_path: str = "experiment-config/experiment_config_example_minimal.yaml"):
        self.base_config_path = Path(base_config_path)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="panther_load_test_"))
        self.results = []
        self.start_time = None
        self.end_time = None

    def generate_experiment_config(self, experiment_id: int) -> Path:
        """Generate a unique experiment configuration."""
        # Load base config
        with open(self.base_config_path, "r") as f:
            config = yaml.safe_load(f)

        # Modify for unique experiment
        config["paths"]["output_dir"] = str(
            self.temp_dir / f"experiment_{experiment_id}"
        )

        # Create unique test name
        if "tests" in config and len(config["tests"]) > 0:
            config["tests"][0]["name"] = f"load_test_{experiment_id}"

        # Save modified config
        config_path = self.temp_dir / f"config_{experiment_id}.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return config_path

    def run_single_experiment(self, experiment_id: int) -> Dict[str, Any]:
        """Run a single PANTHER experiment and collect metrics."""
        config_path = self.generate_experiment_config(experiment_id)

        # Record start metrics
        start_time = time.time()
        start_cpu = psutil.cpu_percent(interval=0.1)
        start_memory = psutil.virtual_memory().percent

        # Run experiment
        cmd = [
            "python",
            "-m",
            "panther",
            "--experiment-config",
            str(config_path),
            "--quiet",  # Reduce output noise
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300  # 5 minute timeout
            )

            # Record end metrics
            end_time = time.time()
            end_cpu = psutil.cpu_percent(interval=0.1)
            end_memory = psutil.virtual_memory().percent

            return {
                "experiment_id": experiment_id,
                "status": "success" if result.returncode == 0 else "failed",
                "duration": end_time - start_time,
                "cpu_usage": max(start_cpu, end_cpu),
                "memory_usage": max(start_memory, end_memory),
                "return_code": result.returncode,
                "stdout_lines": len(result.stdout.splitlines()),
                "stderr_lines": len(result.stderr.splitlines()),
                "error": result.stderr if result.returncode != 0 else None,
            }

        except subprocess.TimeoutExpired:
            return {
                "experiment_id": experiment_id,
                "status": "timeout",
                "duration": 300,
                "error": "Experiment timed out after 5 minutes",
            }
        except Exception as e:
            return {"experiment_id": experiment_id, "status": "error", "error": str(e)}

    def run_concurrent_experiments(
        self, num_experiments: int, max_workers: int = None
    ) -> Dict[str, Any]:
        """Run multiple experiments concurrently."""
        if max_workers is None:
            max_workers = min(num_experiments, multiprocessing.cpu_count())

        print(
            f"🚀 Starting {num_experiments} concurrent experiments with {max_workers} workers"
        )

        self.start_time = time.time()

        # Monitor system resources
        initial_cpu = psutil.cpu_percent(interval=1)
        initial_memory = psutil.virtual_memory().percent

        # Run experiments concurrently
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        ) as executor:
            # Submit all experiments
            futures = [
                executor.submit(self.run_single_experiment, i)
                for i in range(num_experiments)
            ]

            # Collect results as they complete
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                self.results.append(result)

                # Progress indicator
                completed = len(self.results)
                print(
                    f"   Progress: {completed}/{num_experiments} experiments completed",
                    end="\r",
                )

        self.end_time = time.time()

        # Final system metrics
        final_cpu = psutil.cpu_percent(interval=1)
        final_memory = psutil.virtual_memory().percent

        print(
            f"\n✅ All experiments completed in {self.end_time - self.start_time:.2f} seconds"
        )

        return {
            "total_duration": self.end_time - self.start_time,
            "num_experiments": num_experiments,
            "max_workers": max_workers,
            "system_metrics": {
                "initial_cpu": initial_cpu,
                "initial_memory": initial_memory,
                "peak_cpu": final_cpu,
                "peak_memory": final_memory,
            },
            "results": self.results,
        }

    def analyze_results(self) -> Dict[str, Any]:
        """Analyze load test results."""
        if not self.results:
            return {"error": "No results to analyze"}

        # Categorize results
        successful = [r for r in self.results if r.get("status") == "success"]
        failed = [r for r in self.results if r.get("status") == "failed"]
        timeout = [r for r in self.results if r.get("status") == "timeout"]
        errors = [r for r in self.results if r.get("status") == "error"]

        # Calculate statistics for successful runs
        if successful:
            durations = [r["duration"] for r in successful]
            cpu_usage = [r["cpu_usage"] for r in successful if "cpu_usage" in r]
            memory_usage = [
                r["memory_usage"] for r in successful if "memory_usage" in r
            ]

            duration_stats = {
                "min": min(durations),
                "max": max(durations),
                "mean": statistics.mean(durations),
                "median": statistics.median(durations),
                "stdev": statistics.stdev(durations) if len(durations) > 1 else 0,
            }

            cpu_stats = {
                "mean": statistics.mean(cpu_usage) if cpu_usage else 0,
                "max": max(cpu_usage) if cpu_usage else 0,
            }

            memory_stats = {
                "mean": statistics.mean(memory_usage) if memory_usage else 0,
                "max": max(memory_usage) if memory_usage else 0,
            }
        else:
            duration_stats = cpu_stats = memory_stats = {}

        return {
            "summary": {
                "total": len(self.results),
                "successful": len(successful),
                "failed": len(failed),
                "timeout": len(timeout),
                "errors": len(errors),
                "success_rate": (len(successful) / len(self.results)) * 100,
            },
            "performance": {
                "duration": duration_stats,
                "cpu": cpu_stats,
                "memory": memory_stats,
                "throughput": len(successful) / (self.end_time - self.start_time)
                if self.end_time
                else 0,
            },
            "errors": [
                {"id": r["experiment_id"], "error": r.get("error")}
                for r in self.results
                if r.get("error")
            ],
        }

    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

class LoadTestScenarios:
    """Different load testing scenarios for PANTHER."""

    @staticmethod
    def stress_test(max_concurrent: int = 20) -> Dict[str, Any]:
        """Gradually increase load to find breaking point."""
        print("🔥 PANTHER Stress Test")
        print("=" * 50)

        results = []

        for num_concurrent in [1, 2, 4, 8, 12, 16, max_concurrent]:
            print(f"\n📊 Testing with {num_concurrent} concurrent experiments...")

            generator = ExperimentLoadGenerator()
            try:
                run_results = generator.run_concurrent_experiments(
                    num_concurrent, max_workers=num_concurrent
                )
                analysis = generator.analyze_results()

                results.append(
                    {
                        "concurrent": num_concurrent,
                        "success_rate": analysis["summary"]["success_rate"],
                        "mean_duration": analysis["performance"]["duration"].get(
                            "mean", 0
                        ),
                        "throughput": analysis["performance"]["throughput"],
                    }
                )

                print(f"   Success Rate: {analysis['summary']['success_rate']:.1f}%")
                print(
                    f"   Mean Duration: {analysis['performance']['duration'].get('mean', 0):.2f}s"
                )
                print(
                    f"   Throughput: {analysis['performance']['throughput']:.2f} experiments/second"
                )

                # Stop if success rate drops below 90%
                if analysis["summary"]["success_rate"] < 90:
                    print("   ⚠️  Success rate below 90%, stopping stress test")
                    break

            finally:
                generator.cleanup()

        return {"scenario": "stress_test", "results": results}

    @staticmethod
    def spike_test(baseline: int = 2, spike: int = 10) -> Dict[str, Any]:
        """Test system behavior with sudden load spikes."""
        print("📈 PANTHER Spike Test")
        print("=" * 50)

        results = []

        # Baseline load
        print(f"\n📊 Baseline: {baseline} concurrent experiments...")
        generator = ExperimentLoadGenerator()
        baseline_results = generator.run_concurrent_experiments(baseline)
        baseline_analysis = generator.analyze_results()
        generator.cleanup()

        results.append(
            {
                "phase": "baseline",
                "concurrent": baseline,
                "success_rate": baseline_analysis["summary"]["success_rate"],
                "mean_duration": baseline_analysis["performance"]["duration"].get(
                    "mean", 0
                ),
            }
        )

        # Spike load
        print(f"\n📊 Spike: {spike} concurrent experiments...")
        generator = ExperimentLoadGenerator()
        spike_results = generator.run_concurrent_experiments(spike)
        spike_analysis = generator.analyze_results()
        generator.cleanup()

        results.append(
            {
                "phase": "spike",
                "concurrent": spike,
                "success_rate": spike_analysis["summary"]["success_rate"],
                "mean_duration": spike_analysis["performance"]["duration"].get(
                    "mean", 0
                ),
            }
        )

        # Recovery (back to baseline)
        print(f"\n📊 Recovery: {baseline} concurrent experiments...")
        generator = ExperimentLoadGenerator()
        recovery_results = generator.run_concurrent_experiments(baseline)
        recovery_analysis = generator.analyze_results()
        generator.cleanup()

        results.append(
            {
                "phase": "recovery",
                "concurrent": baseline,
                "success_rate": recovery_analysis["summary"]["success_rate"],
                "mean_duration": recovery_analysis["performance"]["duration"].get(
                    "mean", 0
                ),
            }
        )

        return {"scenario": "spike_test", "results": results}

    @staticmethod
    def endurance_test(
        duration_minutes: int = 5, concurrent: int = 4
    ) -> Dict[str, Any]:
        """Run experiments continuously for extended period."""
        print("⏱️  PANTHER Endurance Test")
        print("=" * 50)
        print(
            f"Running {concurrent} concurrent experiments for {duration_minutes} minutes..."
        )

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        all_results = []
        iteration = 0

        while time.time() < end_time:
            iteration += 1
            elapsed = (time.time() - start_time) / 60
            print(f"\n📊 Iteration {iteration} (Elapsed: {elapsed:.1f} minutes)")

            generator = ExperimentLoadGenerator()
            run_results = generator.run_concurrent_experiments(concurrent)
            analysis = generator.analyze_results()

            all_results.append(
                {
                    "iteration": iteration,
                    "elapsed_minutes": elapsed,
                    "success_rate": analysis["summary"]["success_rate"],
                    "mean_duration": analysis["performance"]["duration"].get("mean", 0),
                    "cpu_usage": analysis["performance"]["cpu"].get("mean", 0),
                    "memory_usage": analysis["performance"]["memory"].get("mean", 0),
                }
            )

            generator.cleanup()

            # Check for degradation
            if len(all_results) > 1:
                if (
                    all_results[-1]["success_rate"]
                    < all_results[0]["success_rate"] - 10
                ):
                    print("   ⚠️  Significant performance degradation detected")

        return {"scenario": "endurance_test", "results": all_results}

def generate_load_test_report(results: List[Dict[str, Any]], output_file: Path = None):
    """Generate comprehensive load test report."""
    output_file = output_file or Path("tests/load/load_test_report.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now().isoformat(),
        "system_info": {
            "cpu_count": multiprocessing.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "platform": platform.platform(),
        },
        "scenarios": results,
    }

    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Load test report saved: {output_file}")

    # Generate summary
    print("\n" + "=" * 50)
    print("📊 LOAD TEST SUMMARY")
    print("=" * 50)

    for scenario in results:
        print(f"\n{scenario['scenario'].replace('_', ' ').title()}:")
        if scenario["scenario"] == "stress_test":
            for result in scenario["results"]:
                print(
                    f"  {result['concurrent']} concurrent: "
                    f"{result['success_rate']:.1f}% success, "
                    f"{result['mean_duration']:.2f}s avg duration"
                )
        elif scenario["scenario"] == "spike_test":
            for result in scenario["results"]:
                print(
                    f"  {result['phase']}: "
                    f"{result['success_rate']:.1f}% success, "
                    f"{result['mean_duration']:.2f}s avg duration"
                )

if __name__ == "__main__":
    import argparse
    import platform

    parser = argparse.ArgumentParser(description="Run PANTHER load tests")
    parser.add_argument(
        "--scenario",
        choices=["stress", "spike", "endurance", "all"],
        default="stress",
        help="Load test scenario to run",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="Maximum concurrent experiments for stress test",
    )
    parser.add_argument(
        "--duration", type=int, default=5, help="Duration in minutes for endurance test"
    )

    args = parser.parse_args()

    results = []

    # Run selected scenarios
    if args.scenario in ["stress", "all"]:
        results.append(LoadTestScenarios.stress_test(args.max_concurrent))

    if args.scenario in ["spike", "all"]:
        results.append(LoadTestScenarios.spike_test())

    if args.scenario in ["endurance", "all"]:
        results.append(LoadTestScenarios.endurance_test(args.duration))

    # Generate report
    generate_load_test_report(results)
