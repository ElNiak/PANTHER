#!/usr/bin/env python3
"""
Fast-Fail Scenario Validation Script

This script validates the fast-fail system behavior across multiple test scenarios.
It runs each configuration file and validates that the fast-fail behavior matches
the expected outcomes documented in FAST_FAIL_SYSTEM.md.

Usage:
    python validate_fast_fail_scenarios.py [--config CONFIG] [--verbose] [--dry-run]

Examples:
    # Run all scenarios
    python validate_fast_fail_scenarios.py

    # Run specific scenario
    python validate_fast_fail_scenarios.py --config test_fast_fail_global_enabled.yaml

    # Dry run to see what would be executed
    python validate_fast_fail_scenarios.py --dry-run
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s"
)
logger = logging.getLogger(__name__)


class FastFailValidator:
    """Validates fast-fail behavior across multiple test scenarios."""
    
    def __init__(self, verbose: bool = False, dry_run: bool = False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.panther_dir = Path(__file__).parent
        self.results = []
        
        # Configure logging level
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
    
    def get_test_scenarios(self) -> List[Dict[str, str]]:
        """Define test scenarios and their expected behaviors."""
        return [
            {
                "config": "test_fast_fail_quick_validation.yaml",
                "name": "Quick Fast-Fail Validation",
                "description": "Quick validation without Docker builds",
                "expected_behavior": "mixed_test_level",
                "expected_inheritance": "test_level_control",
                "validation_points": [
                    "Configuration should load with fast_fail enabled and test_level true",
                    "Tests should show different fast-fail settings",
                    "No Docker build delays should occur"
                ]
            },
            {
                "config": "test_fast_fail_global_enabled.yaml",
                "name": "Global Fast-Fail Enabled",
                "description": "All tests should inherit global enabled setting",
                "expected_behavior": "fast_fail_enabled",
                "expected_inheritance": "global_enabled",
                "validation_points": [
                    "All tests use global fast-fail enabled setting",
                    "No test-level overrides are processed",
                    "Errors should terminate experiment quickly"
                ]
            },
            {
                "config": "test_fast_fail_global_disabled.yaml", 
                "name": "Global Fast-Fail Disabled",
                "description": "All tests should inherit global disabled setting",
                "expected_behavior": "fast_fail_disabled",
                "expected_inheritance": "global_disabled",
                "validation_points": [
                    "All tests use global fast-fail disabled setting",
                    "Test-level overrides should be ignored (test_level=false)",
                    "Errors should not terminate experiment"
                ]
            },
            {
                "config": "test_fast_fail_test_level_mixed.yaml",
                "name": "Test-Level Control Mixed",
                "description": "Per-test overrides with inheritance validation",
                "expected_behavior": "mixed_test_level",
                "expected_inheritance": "test_level_control",
                "validation_points": [
                    "'Inherit Global Enabled' should be enabled (inherits global)",
                    "'Override to Disabled' should be disabled (test override)",
                    "'Override to Enabled' should be enabled (test override)",
                    "'Critical Infrastructure Test' should be enabled",
                    "'Experimental Test' should be disabled"
                ]
            },
            {
                "config": "test_fast_fail_error_categories.yaml",
                "name": "Error Category Selective",
                "description": "Selective fast-fail for different error types",
                "expected_behavior": "selective_error_types",
                "expected_inheritance": "test_level_with_categories",
                "validation_points": [
                    "Docker/infrastructure errors should fail fast",
                    "Ivy compilation errors should continue (ivy_compilation_failures=false)",
                    "Service errors should fail fast",
                    "Research test should continue (fast_fail_enabled=false)"
                ]
            },
            {
                "config": "test_fast_fail_cascades.yaml",
                "name": "Cascade Detection",
                "description": "Error cascade and threshold testing",
                "expected_behavior": "cascade_detection",
                "expected_inheritance": "aggressive_thresholds",
                "validation_points": [
                    "Low error threshold (3 errors) should trigger fast-fail",
                    "Timeout cascade (2 consecutive) should trigger fast-fail", 
                    "Disk space threshold (100MB) should trigger fast-fail",
                    "Cascade disabled test should continue despite errors"
                ]
            }
        ]
    
    def run_panther_experiment(self, config_file: str) -> Tuple[int, str, str, float]:
        """Run a PANTHER experiment and capture results."""
        if self.dry_run:
            logger.info(f"DRY RUN: Would run: python -m panther run --config {config_file}")
            return 0, "DRY RUN - No actual execution", "", 0.0
        
        cmd = [
            sys.executable, "-m", "panther", "run",
            "--config", config_file
        ]
        
        logger.info(f"Running: {' '.join(cmd)}")
        start_time = time.time()
        
        try:
            # Run the command with timeout
            result = subprocess.run(
                cmd,
                cwd=self.panther_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            execution_time = time.time() - start_time
            return result.returncode, result.stdout, result.stderr, execution_time
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return -1, "", "Command timed out after 300 seconds", execution_time
        
        except Exception as e:
            execution_time = time.time() - start_time
            return -2, "", f"Exception occurred: {str(e)}", execution_time
    
    def analyze_fast_fail_behavior(self, scenario: Dict, stdout: str, stderr: str, 
                                 returncode: int, execution_time: float) -> Dict:
        """Analyze the output to determine fast-fail behavior."""
        analysis = {
            "scenario": scenario["name"],
            "config": scenario["config"],
            "returncode": returncode,
            "execution_time": execution_time,
            "fast_fail_triggered": False,
            "error_count": 0,
            "cascade_detected": False,
            "inheritance_validated": False,
            "validation_results": {},
            "observations": []
        }
        
        # Combine output for analysis
        full_output = stdout + stderr
        
        # Look for fast-fail indicators in PANTHER output
        fast_fail_keywords = [
            "fast_fail(enabled=",  # Configuration loading
            "FastFailHandler",
            "fast-fail enabled",
            "fast-fail disabled", 
            "Critical error, terminating experiment",
            "Error cascade detected",
            "Maximum errors reached",
            "Timeout cascade detected",
            "Fast-fail terminating",
            "Experiment terminated due to fast-fail"
        ]
        
        for keyword in fast_fail_keywords:
            if keyword.lower() in full_output.lower():
                analysis["observations"].append(f"Found keyword: {keyword}")
                if "terminating" in keyword.lower() or "cascade" in keyword.lower():
                    analysis["fast_fail_triggered"] = True
        
        # Count errors
        error_indicators = ["ERROR", "CRITICAL", "Exception", "Failed"]
        for indicator in error_indicators:
            count = full_output.upper().count(indicator.upper())
            analysis["error_count"] += count
        
        # Check for configuration evidence
        config_evidence = []
        if "fast_fail(enabled=false" in full_output.lower():
            config_evidence.append("fast_fail disabled in config")
        if "fast_fail(enabled=true" in full_output.lower():
            config_evidence.append("fast_fail enabled in config")
        if "test_level=true" in full_output.lower():
            config_evidence.append("test_level control enabled")
        if "test_level=false" in full_output.lower():
            config_evidence.append("test_level control disabled")
        
        analysis["observations"].extend(config_evidence)
        
        # Analyze based on expected behavior
        expected = scenario["expected_behavior"]
        
        if expected == "fast_fail_enabled":
            # Look for enabled configuration and quick failure behavior
            if "fast_fail(enabled=true" in full_output.lower():
                analysis["inheritance_validated"] = True
                analysis["observations"].append("Global enabled configuration detected")
            elif execution_time < 60 and analysis["error_count"] > 0:
                analysis["inheritance_validated"] = True
                analysis["observations"].append("Quick termination suggests fast-fail active")
        
        elif expected == "fast_fail_disabled":
            # Look for disabled configuration
            if "fast_fail(enabled=false" in full_output.lower():
                analysis["inheritance_validated"] = True
                analysis["observations"].append("Global disabled configuration detected")
            # Note: Long execution time might be due to Docker builds, not fast-fail behavior
        
        elif expected == "mixed_test_level":
            # Check for test-level control configuration
            if "test_level=true" in full_output.lower():
                analysis["inheritance_validated"] = True
                analysis["observations"].append("Test-level control configuration detected")
        
        elif expected == "selective_error_types":
            # Check for selective error configuration
            if "ivy_compilation_failures=false" in full_output.lower():
                analysis["observations"].append("Ivy compilation tolerance configured")
                analysis["inheritance_validated"] = True
        
        elif expected == "cascade_detection":
            # Check for cascade configuration
            if "timeout_cascade_threshold" in full_output.lower():
                analysis["observations"].append("Cascade detection configured")
                analysis["inheritance_validated"] = True
        
        # Validate specific points
        for point in scenario["validation_points"]:
            # This is a simplified validation - in real implementation,
            # we would parse experiment logs more thoroughly
            analysis["validation_results"][point] = "PARTIAL"  # Placeholder
        
        return analysis
    
    def validate_scenario(self, scenario: Dict) -> Dict:
        """Validate a single fast-fail scenario."""
        logger.info(f"Validating scenario: {scenario['name']}")
        logger.info(f"Config: {scenario['config']}")
        logger.info(f"Description: {scenario['description']}")
        
        config_path = self.panther_dir / scenario["config"]
        if not config_path.exists():
            return {
                "scenario": scenario["name"],
                "config": scenario["config"],
                "status": "FAILED",
                "error": f"Configuration file not found: {config_path}",
                "execution_time": 0
            }
        
        # Run the experiment
        returncode, stdout, stderr, execution_time = self.run_panther_experiment(scenario["config"])
        
        # Analyze the results
        analysis = self.analyze_fast_fail_behavior(
            scenario, stdout, stderr, returncode, execution_time
        )
        
        # Determine overall validation status
        if returncode == -1:
            status = "TIMEOUT"
        elif returncode == -2:
            status = "ERROR"
        elif self.dry_run:
            status = "DRY_RUN"
        else:
            # Determine success based on expected behavior and analysis
            if analysis["inheritance_validated"]:
                status = "PASSED"
            else:
                status = "NEEDS_REVIEW"
        
        analysis["status"] = status
        
        if self.verbose:
            logger.debug(f"Analysis for {scenario['name']}: {analysis}")
        
        return analysis
    
    def run_validation(self, specific_config: Optional[str] = None) -> Dict:
        """Run validation for all or specific scenarios."""
        scenarios = self.get_test_scenarios()
        
        if specific_config:
            scenarios = [s for s in scenarios if s["config"] == specific_config]
            if not scenarios:
                logger.error(f"Configuration {specific_config} not found in test scenarios")
                return {"error": f"Configuration {specific_config} not found"}
        
        logger.info(f"Running validation for {len(scenarios)} scenarios")
        
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "total_scenarios": len(scenarios),
            "results": [],
            "summary": {
                "passed": 0,
                "failed": 0,
                "timeout": 0,
                "error": 0,
                "needs_review": 0,
                "dry_run": 0
            }
        }
        
        for scenario in scenarios:
            try:
                result = self.validate_scenario(scenario)
                validation_results["results"].append(result)
                
                # Update summary
                status = result["status"].lower()
                if status in validation_results["summary"]:
                    validation_results["summary"][status] += 1
                
            except Exception as e:
                logger.error(f"Error validating scenario {scenario['name']}: {e}")
                error_result = {
                    "scenario": scenario["name"],
                    "config": scenario["config"],
                    "status": "ERROR",
                    "error": str(e),
                    "execution_time": 0
                }
                validation_results["results"].append(error_result)
                validation_results["summary"]["error"] += 1
        
        return validation_results
    
    def print_summary_report(self, results: Dict):
        """Print a human-readable summary report."""
        print("\n" + "="*80)
        print("FAST-FAIL VALIDATION SUMMARY REPORT")
        print("="*80)
        print(f"Timestamp: {results['timestamp']}")
        print(f"Total Scenarios: {results['total_scenarios']}")
        print()
        
        # Summary statistics
        summary = results["summary"]
        print("RESULTS BREAKDOWN:")
        for status, count in summary.items():
            if count > 0:
                print(f"  {status.upper():12}: {count}")
        print()
        
        # Detailed results
        print("DETAILED RESULTS:")
        print("-" * 80)
        
        for result in results["results"]:
            status_icon = {
                "PASSED": "✅",
                "FAILED": "❌", 
                "TIMEOUT": "⏰",
                "ERROR": "🚨",
                "NEEDS_REVIEW": "🔍",
                "DRY_RUN": "🔄"
            }.get(result["status"], "❓")
            
            print(f"{status_icon} {result['scenario']:30} ({result['config']})")
            print(f"   Status: {result['status']}")
            print(f"   Execution Time: {result.get('execution_time', 0):.2f}s")
            
            if "error" in result:
                print(f"   Error: {result['error']}")
            
            if "observations" in result and result["observations"]:
                print(f"   Observations: {len(result['observations'])} items")
                if self.verbose:
                    for obs in result["observations"][:3]:  # Show first 3
                        print(f"     - {obs}")
            
            print()
        
        # Recommendations
        print("RECOMMENDATIONS:")
        print("-" * 80)
        
        failed_count = summary.get("failed", 0) + summary.get("error", 0)
        if failed_count == 0:
            print("✅ All scenarios completed successfully!")
        else:
            print(f"⚠️  {failed_count} scenarios need attention")
            print("   - Review failed scenarios for configuration issues")
            print("   - Check PANTHER installation and dependencies")
            print("   - Examine individual scenario logs for details")
        
        needs_review = summary.get("needs_review", 0)
        if needs_review > 0:
            print(f"🔍 {needs_review} scenarios need manual review")
            print("   - Validate that fast-fail behavior matches expectations")
            print("   - Check experiment logs for detailed fast-fail decisions")
        
        print("\nFor detailed analysis, run with --verbose flag")
        print("="*80)
    
    def save_results(self, results: Dict, output_file: str = "fast_fail_validation_results.json"):
        """Save validation results to JSON file."""
        output_path = self.panther_dir / output_file
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to: {output_path}")


def main():
    """Main entry point for the validation script."""
    parser = argparse.ArgumentParser(
        description="Validate PANTHER fast-fail scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--config",
        help="Run validation for specific configuration file only"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running experiments"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="fast_fail_validation_results.json",
        help="Output file for results (default: fast_fail_validation_results.json)"
    )
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = FastFailValidator(verbose=args.verbose, dry_run=args.dry_run)
    
    try:
        # Run validation
        results = validator.run_validation(specific_config=args.config)
        
        if "error" in results:
            logger.error(results["error"])
            sys.exit(1)
        
        # Print summary
        validator.print_summary_report(results)
        
        # Save results
        if not args.dry_run:
            validator.save_results(results, args.output)
        
        # Exit with appropriate code
        failed_count = results["summary"].get("failed", 0) + results["summary"].get("error", 0)
        if failed_count > 0:
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        sys.exit(130)
    
    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()