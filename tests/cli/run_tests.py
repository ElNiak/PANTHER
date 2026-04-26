#!/usr/bin/env python3
"""CLI Test Runner.

Comprehensive test runner for the PANTHER CLI implementation.
Provides different test execution modes and coverage reporting.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, cwd=None):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=False, text=True, check=False
        )

        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
        else:
            print(f"❌ {description} failed with exit code {result.returncode}")

        return result.returncode

    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return 1


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="CLI Test Runner for PANTHER CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --unit             # Run unit tests only
  python run_tests.py --integration      # Run integration tests only
  python run_tests.py --coverage         # Run with coverage
  python run_tests.py --fast             # Skip slow tests
  python run_tests.py --config           # Run config-related tests only
  python run_tests.py --verbose          # Verbose output
        """,
    )

    # Test selection options
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )
    parser.add_argument(
        "--config", action="store_true", help="Run config-related tests only"
    )
    parser.add_argument(
        "--plugins", action="store_true", help="Run plugin-related tests only"
    )
    parser.add_argument(
        "--commands", action="store_true", help="Run command tests only"
    )

    # Test execution options
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument(
        "--coverage", action="store_true", help="Run with coverage reporting"
    )
    parser.add_argument(
        "--html-coverage", action="store_true", help="Generate HTML coverage report"
    )

    # Output options
    parser.add_argument("--junit-xml", help="Generate JUnit XML report")
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Test timeout in seconds (default: 300)",
    )

    # Parallel execution
    parser.add_argument(
        "--parallel", "-n", type=int, help="Run tests in parallel (number of workers)"
    )

    # Specific test selection
    parser.add_argument("--test-file", help="Run specific test file")
    parser.add_argument("--test-pattern", "-k", help="Run tests matching pattern")

    args = parser.parse_args()

    # Determine test directory
    test_dir = Path(__file__).parent
    project_root = test_dir.parent.parent

    print("🧪 PANTHER CLI Test Runner")
    print(f"📁 Test directory: {test_dir}")
    print(f"📁 Project root: {project_root}")

    # Build pytest command
    cmd = ["python", "-m", "pytest"]

    # Add test path selection
    if args.unit:
        cmd.append(str(test_dir / "unit"))
        print("🎯 Running unit tests only")
    elif args.integration:
        cmd.append(str(test_dir / "integration"))
        print("🎯 Running integration tests only")
    elif args.config:
        cmd.extend(["-m", "config"])
        print("🎯 Running config-related tests only")
    elif args.plugins:
        cmd.extend(["-m", "plugins"])
        print("🎯 Running plugin-related tests only")
    elif args.commands:
        cmd.append(str(test_dir / "unit" / "commands"))
        print("🎯 Running command tests only")
    elif args.test_file:
        cmd.append(args.test_file)
        print(f"🎯 Running specific test file: {args.test_file}")
    else:
        cmd.append(str(test_dir))
        print("🎯 Running all CLI tests")

    # Add output options
    if args.verbose:
        cmd.extend(["-v", "--tb=short"])
    else:
        cmd.extend(["--tb=line"])

    if args.debug:
        cmd.extend(["-s", "--tb=long", "--capture=no"])

    # Add filtering options
    if args.fast:
        cmd.extend(["-m", "not slow"])
        print("⚡ Skipping slow tests")

    if args.test_pattern:
        cmd.extend(["-k", args.test_pattern])
        print(f"🔍 Running tests matching pattern: {args.test_pattern}")

    # Add parallel execution
    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])
        print(f"🚀 Running tests in parallel with {args.parallel} workers")

    # Add timeout
    cmd.extend(["--timeout", str(args.timeout)])

    # Add coverage options
    if args.coverage or args.html_coverage:
        cmd.extend(["--cov=panther.cli", "--cov-report=term-missing"])

        if args.html_coverage:
            cmd.extend(["--cov-report=html:htmlcov"])
            print("📊 HTML coverage report will be generated in htmlcov/")

    # Add JUnit XML output
    if args.junit_xml:
        cmd.extend(["--junit-xml", args.junit_xml])
        print(f"📄 JUnit XML report will be generated: {args.junit_xml}")

    # Additional pytest options
    cmd.extend(["--strict-markers", "--strict-config", "--color=yes"])

    # Set environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)
    env["PANTHER_TEST_MODE"] = "1"

    # Change to project root for running tests
    original_cwd = os.getcwd()
    os.chdir(project_root)

    try:
        # Run the tests
        print(f"\n🚀 Executing command: {' '.join(cmd)}")

        result = subprocess.run(cmd, env=env, check=False)

        exit_code = result.returncode

        # Print summary
        print(f"\n{'='*60}")
        if exit_code == 0:
            print("✅ All tests passed!")

            if args.coverage or args.html_coverage:
                print("\n📊 Coverage information displayed above")

                if args.html_coverage:
                    coverage_index = project_root / "htmlcov" / "index.html"
                    if coverage_index.exists():
                        print(f"📊 HTML coverage report: file://{coverage_index}")
        else:
            print(f"❌ Tests failed with exit code {exit_code}")

            # Provide helpful suggestions
            print("\n💡 Troubleshooting suggestions:")
            print("  • Run with --verbose for more detailed output")
            print("  • Run with --debug for full debug information")
            print("  • Run specific test files to isolate failures")
            print("  • Check that all dependencies are installed")

        print(f"{'='*60}")

        return exit_code

    finally:
        # Restore original working directory
        os.chdir(original_cwd)


if __name__ in {"__main__", "__mp_main__"}:
    sys.exit(main())
