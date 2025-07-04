#!/usr/bin/env python
"""Test runner script for ATLAS Commands MCP Server."""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(args):
    """Run the test suite with specified options."""
    
    # Base pytest command
    cmd = ["pytest"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-vv")
    
    # Add specific test file/directory
    if args.path:
        cmd.append(args.path)
    
    # Add marker filter
    if args.mark:
        cmd.extend(["-m", args.mark])
    
    # Add keyword filter
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    
    # Disable coverage for quick runs
    if args.no_cov:
        cmd.append("--no-cov")
    
    # Stop on first failure
    if args.failfast:
        cmd.append("-x")
    
    # Run only last failed tests
    if args.lf:
        cmd.append("--lf")
    
    # Show local variables in tracebacks
    if args.showlocals:
        cmd.append("-l")
    
    # Parallel execution
    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])
    
    # Run tests
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def run_specific_test_suites():
    """Run specific test suites with descriptions."""
    
    suites = {
        "unit": "Run unit tests only",
        "integration": "Run integration tests only",
        "checklist": "Run checklist-related tests",
        "memory": "Run memory graph tests",
        "workflow": "Run workflow enforcement tests",
        "validation": "Run validation tests",
        "errors": "Run error handling tests",
        "resources": "Run resource management tests",
        "all": "Run all tests"
    }
    
    print("\nAvailable test suites:")
    for name, desc in suites.items():
        print(f"  {name:12} - {desc}")
    
    suite = input("\nSelect test suite (or press Enter for all): ").strip()
    
    if not suite or suite == "all":
        return run_tests(argparse.Namespace(
            verbose=True,
            path=None,
            mark=None,
            keyword=None,
            no_cov=False,
            failfast=False,
            lf=False,
            showlocals=False,
            parallel=None
        ))
    
    if suite == "unit":
        args = argparse.Namespace(
            verbose=True,
            path=None,
            mark="unit",
            keyword=None,
            no_cov=False,
            failfast=False,
            lf=False,
            showlocals=False,
            parallel=None
        )
    elif suite == "integration":
        args = argparse.Namespace(
            verbose=True,
            path=None,
            mark="integration",
            keyword=None,
            no_cov=False,
            failfast=False,
            lf=False,
            showlocals=False,
            parallel=None
        )
    elif suite in ["checklist", "memory", "workflow", "validation", "errors", "resources"]:
        args = argparse.Namespace(
            verbose=True,
            path=f"tests/test_{suite}*.py",
            mark=None,
            keyword=None,
            no_cov=False,
            failfast=False,
            lf=False,
            showlocals=False,
            parallel=None
        )
    else:
        print(f"Unknown suite: {suite}")
        return 1
    
    return run_tests(args)


def main():
    """Main entry point."""
    
    parser = argparse.ArgumentParser(
        description="Run tests for ATLAS Commands MCP Server"
    )
    
    parser.add_argument(
        "path",
        nargs="?",
        help="Specific test file or directory to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-m", "--mark",
        help="Run tests matching given mark expression"
    )
    parser.add_argument(
        "-k", "--keyword",
        help="Run tests matching given keyword expression"
    )
    parser.add_argument(
        "--no-cov",
        action="store_true",
        help="Disable coverage reporting"
    )
    parser.add_argument(
        "-x", "--failfast",
        action="store_true",
        help="Stop on first failure"
    )
    parser.add_argument(
        "--lf",
        action="store_true",
        help="Run last failed tests only"
    )
    parser.add_argument(
        "-l", "--showlocals",
        action="store_true",
        help="Show local variables in tracebacks"
    )
    parser.add_argument(
        "-n", "--parallel",
        type=int,
        help="Number of parallel workers"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Interactive test suite selection"
    )
    
    args = parser.parse_args()
    
    # Ensure we're in the right directory
    project_root = Path(__file__).parent
    if project_root != Path.cwd():
        print(f"Changing to project directory: {project_root}")
        import os
        os.chdir(project_root)
    
    # Run tests
    if args.interactive:
        return run_specific_test_suites()
    else:
        return run_tests(args)


if __name__ == "__main__":
    sys.exit(main())