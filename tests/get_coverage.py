#!/usr/bin/env python3
"""
Quick coverage analysis for PANTHER tests
"""

import subprocess
import json
import sys

def get_coverage_stats():
    """Run coverage and get statistics."""
    
    # Test files to analyze
    test_files = [
        "tests/unit/test_core/test_event_system.py",
        "tests/unit/test_core/test_docker_builder.py", 
        "tests/unit/test_core/test_observer_system.py",
        "tests/unit/test_plugins/test_plugin_discovery.py"
    ]
    
    # Modules to analyze coverage for
    modules = [
        "panther.core.events",
        "panther.core.docker_builder",
        "panther.core.observer",
        "panther.plugins"
    ]
    
    print("Running coverage analysis on PANTHER tests...")
    print("=" * 60)
    
    for test_file, module in zip(test_files, modules):
        print(f"\nAnalyzing: {test_file}")
        print(f"Module: {module}")
        
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "--override-ini=addopts=",
            f"--cov={module}",
            "--cov-report=term",
            "--no-cov-on-fail",
            "-v",  # Add verbose flag for more detailed output
            "-s",  # Disable output capturing to see print statements
        ]
        # Print the command being executed
        print(f"Command: {' '.join(cmd)}")
        try:
            result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=6000
            )
            
            # Print the captured stdout to see test output
            if result.stdout:
                print("\n--- Test Output ---")
                print(result.stdout)
            
            # Also print stderr if there are any errors
            if result.stderr:
                print("\n--- Error Output ---")
                print(result.stderr)
            
            # Extract coverage percentage from output
            lines = result.stdout.splitlines()
            for line in lines:
                if "TOTAL" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        coverage = parts[-1]
                        print(f"Coverage: {coverage}")
                        break
            else:
                # Try to find any percentage in output
                for line in lines:
                    if "%" in line and module in line:
                        print(f"Coverage line: {line}")
                        break
                        
        except subprocess.TimeoutExpired:
            print("Timeout - skipping")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("Note: Full coverage requires all tests to run successfully.")
    print("Some tests may be skipped due to missing dependencies or imports.")

if __name__ == "__main__":
    get_coverage_stats()
