#!/usr/bin/env python3
"""
Logging Scenarios Validation Script

This script tests different granular logging configurations to validate
the feature-based logging system implementation with integrated log statistics.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import re
import logging
import tempfile

# Import the log statistics components
try:
    from panther.core.utils.log_statistics_collector import LogStatisticsCollector
    from panther.core.utils.log_statistics_reporter import LogStatisticsReporter
    from panther.core.utils.log_feature_analyzer import LogFeatureAnalyzer
    from panther.core.utils.log_performance_analyzer import LogPerformanceAnalyzer
    from panther.core.utils.logger_factory import LoggerFactory
    STATISTICS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Log statistics components not available: {e}")
    STATISTICS_AVAILABLE = False


class LoggingScenarioValidator:
    """Validates different logging scenarios for PANTHER's granular feature debugging."""
    
    def __init__(self, project_root: str = "/Users/elniak/Documents/Project/PANTHER"):
        self.project_root = Path(project_root)
        self.experiment_config_dir = self.project_root / "experiment-config"
        self.validation_results = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize statistics components if available
        self.statistics_enabled = STATISTICS_AVAILABLE
        self.collectors = {}  # Store collectors for each scenario
        
        # Define test scenarios
        self.scenarios = {
            "baseline": {
                "config": "experiment_config_example_minimal.yaml",
                "description": "Baseline test with standard INFO logging",
                "expected_features": ["minimal logging", "standard verbosity"],
                "timeout": 120
            },
            "full_debug": {
                "config": "test_logging_full_debug.yaml", 
                "description": "Maximum verbosity with all features at DEBUG/TRACE",
                "expected_features": ["maximum verbosity", "trace logging", "debug details"],
                "timeout": 180
            },
            "docker_focus": {
                "config": "test_logging_docker_focus.yaml",
                "description": "Docker operations and build debugging focus", 
                "expected_features": ["docker operations", "container details", "build processes"],
                "timeout": 150
            },
            "service_focus": {
                "config": "test_logging_service_focus.yaml",
                "description": "Service management and QUIC implementation debugging",
                "expected_features": ["service coordination", "quic details", "plugin operations"],
                "timeout": 150
            },
            "network_focus": {
                "config": "test_logging_network_focus.yaml", 
                "description": "Network environment and deployment debugging",
                "expected_features": ["network setup", "port management", "protocol communication"],
                "timeout": 150
            },
            "event_focus": {
                "config": "test_logging_event_focus.yaml",
                "description": "Event system and state management debugging", 
                "expected_features": ["event emission", "state transitions", "observer patterns"],
                "timeout": 120
            },
            "minimal_noise": {
                "config": "test_logging_minimal_noise.yaml",
                "description": "Production-like minimal logging with essential info only",
                "expected_features": ["minimal noise", "production ready", "clean output"],
                "timeout": 100
            },
            "statistics_enabled": {
                "config": "test_logging_with_statistics.yaml",
                "description": "Test with log statistics collection enabled",
                "expected_features": ["statistics collection", "performance monitoring", "feature analysis"],
                "timeout": 120,
                "enable_statistics": True
            }
        }
    
    def validate_scenario(self, scenario_name: str, config_data: Dict) -> Dict:
        """Validate a single logging scenario."""
        print(f"\n{'='*60}")
        print(f"VALIDATING SCENARIO: {scenario_name.upper()}")
        print(f"{'='*60}")
        print(f"Description: {config_data['description']}")
        print(f"Config file: {config_data['config']}")
        print(f"Expected features: {', '.join(config_data['expected_features'])}")
        
        # Check if statistics should be enabled for this scenario
        enable_statistics = config_data.get('enable_statistics', False) and self.statistics_enabled
        if enable_statistics:
            print(f"🔍 Log statistics collection: ENABLED")
        
        config_path = self.experiment_config_dir / config_data['config']
        
        # Check if config file exists
        if not config_path.exists():
            return {
                "status": "FAILED",
                "error": f"Configuration file not found: {config_path}",
                "log_analysis": None,
                "performance": None,
                "statistics_analysis": None
            }
        
        # Prepare output directory
        output_dir = self.project_root / "outputs" / f"logging_validation_{scenario_name}_{self.timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize statistics collector if enabled
        statistics_collector = None
        if enable_statistics:
            try:
                statistics_collector = LogStatisticsCollector(
                    buffer_size=1000,
                    track_performance=True
                )
                self.collectors[scenario_name] = statistics_collector
                print(f"📊 Statistics collector initialized for {scenario_name}")
            except Exception as e:
                print(f"⚠️ Failed to initialize statistics collector: {e}")
                enable_statistics = False
        
        # Prepare command
        cmd = [
            "python", "-m", "panther", "run", 
            "--config", str(config_path)
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        print(f"Output directory: {output_dir}")
        
        # Run the test
        start_time = time.time()
        try:
            # Set environment variables
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.project_root)
            
            # Change to project directory
            original_cwd = os.getcwd()
            os.chdir(self.project_root)
            
            # Activate virtual environment and run
            venv_cmd = f"source .venv/bin/activate && {' '.join(cmd)}"
            
            result = subprocess.run(
                ["bash", "-c", venv_cmd],
                capture_output=True,
                text=True,
                timeout=config_data['timeout'],
                env=env
            )
            
            os.chdir(original_cwd)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Analyze results
            log_analysis = self._analyze_logs(result.stdout, result.stderr, scenario_name)
            performance_metrics = self._calculate_performance_metrics(execution_time, log_analysis)
            
            # Generate statistics analysis if collector is available
            statistics_analysis = None
            if statistics_collector and enable_statistics:
                try:
                    statistics_analysis = self._generate_statistics_analysis(
                        statistics_collector, scenario_name, output_dir
                    )
                    print(f"📈 Generated statistics analysis for {scenario_name}")
                except Exception as e:
                    print(f"⚠️ Failed to generate statistics analysis: {e}")
            
            success = result.returncode == 0
            
            # Save detailed output
            self._save_scenario_output(scenario_name, result, log_analysis, performance_metrics, statistics_analysis)
            
            return {
                "status": "SUCCESS" if success else "FAILED",
                "returncode": result.returncode,
                "execution_time": execution_time,
                "log_analysis": log_analysis,
                "performance": performance_metrics,
                "statistics_analysis": statistics_analysis,
                "stdout_preview": result.stdout[:1000] if result.stdout else "",
                "stderr_preview": result.stderr[:1000] if result.stderr else "",
                "error": result.stderr if not success else None
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "TIMEOUT",
                "error": f"Test timed out after {config_data['timeout']} seconds",
                "log_analysis": None,
                "performance": None,
                "statistics_analysis": None
            }
        except Exception as e:
            return {
                "status": "ERROR", 
                "error": str(e),
                "log_analysis": None,
                "performance": None,
                "statistics_analysis": None
            }
    
    def _analyze_logs(self, stdout: str, stderr: str, scenario_name: str) -> Dict:
        """Analyze log output to validate feature-specific logging."""
        analysis = {
            "total_lines": 0,
            "log_levels": {"TRACE": 0, "DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0},
            "feature_detections": {},
            "color_codes_detected": False,
            "unique_modules": set(),
            "error_count": 0,
            "docker_operations": 0,
            "service_operations": 0,
            "network_operations": 0,
            "event_operations": 0
        }
        
        # Combine stdout and stderr for analysis
        all_output = stdout + "\n" + stderr
        lines = all_output.split('\n')
        analysis["total_lines"] = len(lines)
        
        # ANSI color code pattern
        ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
        
        # Feature-specific patterns
        feature_patterns = {
            "docker_operations": [r"docker", r"container", r"build", r"compose"],
            "service_operations": [r"service", r"quic", r"picoquic", r"aioquic", r"ivy"],
            "network_operations": [r"network", r"port", r"certificate", r"protocol"],
            "event_operations": [r"event", r"state", r"observer", r"emit"]
        }
        
        for line in lines:
            if not line.strip():
                continue
                
            # Check for color codes
            if ansi_pattern.search(line):
                analysis["color_codes_detected"] = True
            
            # Extract log level
            for level in analysis["log_levels"]:
                if f"[{level}]" in line:
                    analysis["log_levels"][level] += 1
                    break
            
            # Count errors
            if "ERROR" in line or "Exception" in line or "Traceback" in line:
                analysis["error_count"] += 1
            
            # Extract module names
            module_match = re.search(r'\] - (\w+) - ', line)
            if module_match:
                analysis["unique_modules"].add(module_match.group(1))
            
            # Check for feature-specific operations
            line_lower = line.lower()
            for feature, patterns in feature_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line_lower):
                        analysis[feature] += 1
                        break
        
        # Convert set to list for JSON serialization
        analysis["unique_modules"] = list(analysis["unique_modules"])
        
        return analysis
    
    def _generate_statistics_analysis(self, collector: LogStatisticsCollector, 
                                    scenario_name: str, output_dir: Path) -> Dict:
        """Generate comprehensive statistics analysis using the collector."""
        try:
            # Create reporter and analyzers
            reporter = LogStatisticsReporter(collector)
            feature_analyzer = LogFeatureAnalyzer(collector)
            performance_analyzer = LogPerformanceAnalyzer(collector)
            
            # Generate comprehensive report
            summary_report = collector.generate_summary_report()
            
            # Generate feature analysis
            feature_analysis = feature_analyzer.analyze_feature_activity()
            
            # Generate performance analysis
            performance_analysis = performance_analyzer.analyze_logging_overhead(detailed=True)
            
            # Get optimization recommendations
            optimizations = performance_analyzer.recommend_optimizations()
            level_suggestions = feature_analyzer.suggest_level_optimizations()
            
            # Save detailed reports to output directory
            stats_dir = output_dir / "statistics"
            stats_dir.mkdir(exist_ok=True)
            
            # Export in multiple formats
            reporter.export_to_file(stats_dir / "summary_report.json", format="json")
            reporter.export_to_file(stats_dir / "summary_report.csv", format="csv")
            reporter.export_to_file(stats_dir / "summary_report.txt", format="text")
            
            # Save feature analysis
            with open(stats_dir / "feature_analysis.json", 'w') as f:
                json.dump(feature_analysis, f, indent=2, default=str)
            
            # Save performance analysis
            with open(stats_dir / "performance_analysis.json", 'w') as f:
                json.dump(performance_analysis, f, indent=2, default=str)
            
            # Save optimization recommendations
            with open(stats_dir / "optimizations.json", 'w') as f:
                json.dump({
                    "performance_optimizations": optimizations,
                    "level_suggestions": level_suggestions
                }, f, indent=2, default=str)
            
            # Return summary for inclusion in main results
            return {
                "summary": {
                    "total_messages": summary_report['summary']['session_info']['total_messages'],
                    "session_duration": summary_report['summary']['session_info']['duration_seconds'],
                    "message_rate": summary_report['summary']['session_info']['messages_per_second'],
                    "unique_features": len(summary_report.get('feature_analysis', {})),
                    "error_rate": summary_report['summary']['error_statistics']['error_rate_percent']
                },
                "feature_insights": {
                    "high_volume_features": len(feature_analysis.get('activity_categories', {}).get('high_volume', [])),
                    "moderate_volume_features": len(feature_analysis.get('activity_categories', {}).get('moderate_volume', [])),
                    "total_active_features": feature_analysis.get('summary', {}).get('total_features_active', 0)
                },
                "performance_insights": {
                    "status": performance_analysis.get('summary', {}).get('is_concerning', False),
                    "average_overhead_ms": performance_analysis.get('summary', {}).get('average_overhead_ms', 0),
                    "memory_usage_mb": performance_analysis.get('resource_impact', {}).get('memory', {}).get('current_usage_mb', 0),
                    "bottlenecks_detected": len(performance_analysis.get('bottlenecks', {}).get('detected', []))
                },
                "recommendations": {
                    "performance_count": len(optimizations),
                    "level_adjustments_count": len(level_suggestions),
                    "top_recommendations": performance_analysis.get('recommendations', [])[:3]
                },
                "reports_saved": {
                    "directory": str(stats_dir),
                    "files": [
                        "summary_report.json", "summary_report.csv", "summary_report.txt",
                        "feature_analysis.json", "performance_analysis.json", "optimizations.json"
                    ]
                }
            }
            
        except Exception as e:
            return {
                "error": f"Failed to generate statistics analysis: {e}",
                "details": str(e)
            }
    
    def _calculate_performance_metrics(self, execution_time: float, log_analysis: Dict) -> Dict:
        """Calculate performance metrics for the logging scenario."""
        return {
            "execution_time_seconds": round(execution_time, 2),
            "logs_per_second": round(log_analysis["total_lines"] / execution_time, 2) if execution_time > 0 else 0,
            "average_line_length": 0,  # Could be calculated if needed
            "performance_category": self._categorize_performance(execution_time, log_analysis["total_lines"])
        }
    
    def _categorize_performance(self, execution_time: float, total_lines: int) -> str:
        """Categorize performance based on execution time and log volume."""
        if execution_time < 60 and total_lines < 1000:
            return "FAST"
        elif execution_time < 120 and total_lines < 5000:
            return "MODERATE"
        elif execution_time < 180 and total_lines < 10000:
            return "SLOW"
        else:
            return "VERY_SLOW"
    
    def _save_scenario_output(self, scenario_name: str, result: subprocess.CompletedProcess, 
                             log_analysis: Dict, performance_metrics: Dict, 
                             statistics_analysis: Optional[Dict] = None) -> None:
        """Save detailed output for a scenario."""
        output_file = self.project_root / f"logging_validation_{scenario_name}_{self.timestamp}.json"
        
        data = {
            "scenario": scenario_name,
            "timestamp": self.timestamp,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "log_analysis": log_analysis,
            "performance_metrics": performance_metrics,
            "statistics_analysis": statistics_analysis,
            "statistics_enabled": statistics_analysis is not None
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def run_all_scenarios(self) -> Dict:
        """Run all logging scenarios and collect results."""
        print(f"PANTHER Logging Scenarios Validation")
        print(f"Started at: {datetime.now()}")
        print(f"Project root: {self.project_root}")
        print(f"Scenarios to test: {len(self.scenarios)}")
        
        results = {}
        
        for scenario_name, config_data in self.scenarios.items():
            try:
                result = self.validate_scenario(scenario_name, config_data)
                results[scenario_name] = result
                
                # Print summary
                status = result["status"]
                if status == "SUCCESS":
                    exec_time = result.get("execution_time", 0)
                    log_count = result.get("log_analysis", {}).get("total_lines", 0)
                    stats_enabled = "📊" if result.get("statistics_analysis") else ""
                    print(f"✅ {scenario_name}: SUCCESS ({exec_time:.1f}s, {log_count} log lines) {stats_enabled}")
                    
                    # Print statistics summary if available
                    if result.get("statistics_analysis"):
                        stats = result["statistics_analysis"]
                        if "summary" in stats:
                            msg_rate = stats["summary"].get("message_rate", 0)
                            features = stats["summary"].get("unique_features", 0)
                            print(f"   📈 Stats: {msg_rate:.1f} msg/s, {features} features analyzed")
                else:
                    error = result.get("error", "Unknown error")
                    print(f"❌ {scenario_name}: {status} - {error}")
                    
            except Exception as e:
                print(f"❌ {scenario_name}: EXCEPTION - {str(e)}")
                results[scenario_name] = {
                    "status": "EXCEPTION",
                    "error": str(e)
                }
        
        return results
    
    def generate_summary_report(self, results: Dict) -> str:
        """Generate a summary report of all scenarios."""
        report = []
        report.append("PANTHER LOGGING SCENARIOS VALIDATION REPORT")
        report.append("=" * 50)
        report.append(f"Validation timestamp: {self.timestamp}")
        report.append(f"Total scenarios tested: {len(results)}")
        report.append("")
        
        # Summary statistics
        successful = sum(1 for r in results.values() if r.get("status") == "SUCCESS")
        failed = len(results) - successful
        statistics_enabled = sum(1 for r in results.values() if r.get("statistics_analysis"))
        
        report.append(f"Results Summary:")
        report.append(f"  ✅ Successful: {successful}")
        report.append(f"  ❌ Failed: {failed}")
        report.append(f"  📊 With Statistics: {statistics_enabled}")
        report.append("")
        
        # Detailed results
        report.append("Detailed Results:")
        report.append("-" * 30)
        
        for scenario_name, result in results.items():
            status = result.get("status", "UNKNOWN")
            report.append(f"\n{scenario_name.upper()}:")
            report.append(f"  Status: {status}")
            
            if status == "SUCCESS":
                exec_time = result.get("execution_time", 0)
                log_analysis = result.get("log_analysis", {})
                performance = result.get("performance", {})
                
                report.append(f"  Execution time: {exec_time:.2f}s")
                report.append(f"  Total log lines: {log_analysis.get('total_lines', 0)}")
                report.append(f"  Performance category: {performance.get('performance_category', 'UNKNOWN')}")
                report.append(f"  Color codes detected: {log_analysis.get('color_codes_detected', False)}")
                report.append(f"  Unique modules: {len(log_analysis.get('unique_modules', []))}")
                
                # Log level distribution
                log_levels = log_analysis.get('log_levels', {})
                report.append(f"  Log levels: {dict(log_levels)}")
                
                # Feature-specific operations
                docker_ops = log_analysis.get('docker_operations', 0)
                service_ops = log_analysis.get('service_operations', 0)
                network_ops = log_analysis.get('network_operations', 0)
                event_ops = log_analysis.get('event_operations', 0)
                
                report.append(f"  Docker operations: {docker_ops}")
                report.append(f"  Service operations: {service_ops}")
                report.append(f"  Network operations: {network_ops}")
                report.append(f"  Event operations: {event_ops}")
                
                # Add statistics analysis if available
                statistics_analysis = result.get("statistics_analysis")
                if statistics_analysis:
                    report.append(f"")
                    report.append(f"  📊 STATISTICS ANALYSIS:")
                    if "summary" in statistics_analysis:
                        stats_sum = statistics_analysis["summary"]
                        report.append(f"    Message rate: {stats_sum.get('message_rate', 0):.2f} msg/s")
                        report.append(f"    Unique features: {stats_sum.get('unique_features', 0)}")
                        report.append(f"    Error rate: {stats_sum.get('error_rate', 0):.2f}%")
                    
                    if "feature_insights" in statistics_analysis:
                        feat_insights = statistics_analysis["feature_insights"]
                        report.append(f"    High volume features: {feat_insights.get('high_volume_features', 0)}")
                        report.append(f"    Active features: {feat_insights.get('total_active_features', 0)}")
                    
                    if "performance_insights" in statistics_analysis:
                        perf_insights = statistics_analysis["performance_insights"]
                        overhead = perf_insights.get('average_overhead_ms', 0)
                        memory = perf_insights.get('memory_usage_mb', 0)
                        bottlenecks = perf_insights.get('bottlenecks_detected', 0)
                        report.append(f"    Avg overhead: {overhead:.2f}ms, Memory: {memory:.1f}MB")
                        if bottlenecks > 0:
                            report.append(f"    ⚠️  {bottlenecks} performance bottlenecks detected")
                    
                    if "recommendations" in statistics_analysis:
                        rec = statistics_analysis["recommendations"]
                        perf_recs = rec.get('performance_count', 0)
                        level_recs = rec.get('level_adjustments_count', 0)
                        if perf_recs > 0 or level_recs > 0:
                            report.append(f"    💡 {perf_recs} performance + {level_recs} level recommendations")
                
            else:
                error = result.get("error", "No error details")
                report.append(f"  Error: {error}")
        
        return "\n".join(report)
    
    def generate_statistics_comparison_report(self, results: Dict) -> str:
        """Generate a comparison report of statistics across scenarios."""
        if not self.statistics_enabled:
            return "Statistics comparison not available - log statistics components not imported."
        
        scenarios_with_stats = {
            name: result for name, result in results.items() 
            if result.get("statistics_analysis") and result.get("status") == "SUCCESS"
        }
        
        if not scenarios_with_stats:
            return "No scenarios with statistics analysis found."
        
        report = []
        report.append("PANTHER LOGGING STATISTICS COMPARISON REPORT")
        report.append("=" * 55)
        report.append(f"Scenarios with statistics: {len(scenarios_with_stats)}")
        report.append("")
        
        # Prepare comparison data
        comparison_data = []
        for scenario_name, result in scenarios_with_stats.items():
            stats = result["statistics_analysis"]
            if "summary" in stats:
                summary = stats["summary"]
                comparison_data.append({
                    "scenario": scenario_name,
                    "message_rate": summary.get("message_rate", 0),
                    "total_messages": summary.get("total_messages", 0),
                    "unique_features": summary.get("unique_features", 0),
                    "error_rate": summary.get("error_rate", 0),
                    "execution_time": result.get("execution_time", 0)
                })
        
        if not comparison_data:
            return "No valid statistics data found for comparison."
        
        # Sort by message rate
        comparison_data.sort(key=lambda x: x["message_rate"], reverse=True)
        
        report.append("📊 MESSAGE RATE COMPARISON (highest to lowest):")
        report.append("-" * 50)
        for data in comparison_data:
            report.append(f"  {data['scenario']:20s}: {data['message_rate']:8.1f} msg/s "
                         f"({data['total_messages']:5d} total, {data['unique_features']:2d} features)")
        
        report.append("")
        report.append("⏱️  EXECUTION TIME COMPARISON:")
        report.append("-" * 50)
        comparison_data.sort(key=lambda x: x["execution_time"])
        for data in comparison_data:
            report.append(f"  {data['scenario']:20s}: {data['execution_time']:6.1f}s "
                         f"(rate: {data['message_rate']:6.1f} msg/s)")
        
        report.append("")
        report.append("🔧 FEATURE ACTIVITY COMPARISON:")
        report.append("-" * 50)
        comparison_data.sort(key=lambda x: x["unique_features"], reverse=True)
        for data in comparison_data:
            report.append(f"  {data['scenario']:20s}: {data['unique_features']:3d} features "
                         f"(error rate: {data['error_rate']:5.2f}%)")
        
        # Add insights
        report.append("")
        report.append("💡 INSIGHTS:")
        report.append("-" * 50)
        
        fastest_scenario = min(comparison_data, key=lambda x: x["execution_time"])
        highest_rate = max(comparison_data, key=lambda x: x["message_rate"])
        most_features = max(comparison_data, key=lambda x: x["unique_features"])
        
        report.append(f"  Fastest execution: {fastest_scenario['scenario']} ({fastest_scenario['execution_time']:.1f}s)")
        report.append(f"  Highest msg rate: {highest_rate['scenario']} ({highest_rate['message_rate']:.1f} msg/s)")
        report.append(f"  Most features: {most_features['scenario']} ({most_features['unique_features']} features)")
        
        # Calculate averages
        avg_rate = sum(d["message_rate"] for d in comparison_data) / len(comparison_data)
        avg_features = sum(d["unique_features"] for d in comparison_data) / len(comparison_data)
        avg_time = sum(d["execution_time"] for d in comparison_data) / len(comparison_data)
        
        report.append(f"")
        report.append(f"  Average message rate: {avg_rate:.1f} msg/s")
        report.append(f"  Average features active: {avg_features:.1f}")
        report.append(f"  Average execution time: {avg_time:.1f}s")
        
        return "\n".join(report)


def main():
    """Main function to run logging scenario validation."""
    validator = LoggingScenarioValidator()
    
    # Run all scenarios
    results = validator.run_all_scenarios()
    
    # Generate and save reports
    report = validator.generate_summary_report(results)
    print("\n" + report)
    
    # Generate statistics comparison report if applicable
    stats_comparison = validator.generate_statistics_comparison_report(results)
    if "not available" not in stats_comparison and "No scenarios" not in stats_comparison:
        print("\n" + stats_comparison)
    
    # Save results to file
    results_file = validator.project_root / f"logging_validation_results_{validator.timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    report_file = validator.project_root / f"logging_validation_report_{validator.timestamp}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    # Save statistics comparison report
    stats_report_file = validator.project_root / f"logging_validation_statistics_{validator.timestamp}.txt"
    with open(stats_report_file, 'w') as f:
        f.write(stats_comparison)
    
    print(f"\nFiles saved:")
    print(f"  📄 Results: {results_file}")
    print(f"  📋 Report: {report_file}")
    print(f"  📊 Statistics: {stats_report_file}")
    
    # Show statistics summary
    stats_scenarios = sum(1 for r in results.values() if r.get("statistics_analysis"))
    if stats_scenarios > 0:
        print(f"\n✨ Generated detailed statistics analysis for {stats_scenarios} scenarios")
        print(f"   Check individual scenario output directories for detailed analytics files")
    
    # Return success if all scenarios passed
    successful_scenarios = sum(1 for r in results.values() if r.get("status") == "SUCCESS")
    return 0 if successful_scenarios == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())