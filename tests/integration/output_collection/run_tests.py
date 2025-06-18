#!/usr/bin/env python3
"""
Output Collection Test Runner

This script provides an easy way to run the output collection tests
with different configurations and options.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, description="", timeout=300):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            timeout=timeout,
            text=True,
            capture_output=False  # Show output in real-time
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            print(f"\n✅ {description} - PASSED ({duration:.1f}s)")
            return True
        else:
            print(f"\n❌ {description} - FAILED ({duration:.1f}s)")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n⏰ {description} - TIMEOUT (>{timeout}s)")
        return False
    except KeyboardInterrupt:
        print(f"\n🛑 {description} - INTERRUPTED")
        return False


def check_prerequisites():
    """Check if prerequisites are met."""
    print("🔍 Checking prerequisites...")
    
    # Check Docker
    try:
        result = subprocess.run(
            ["docker", "--version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Docker: {result.stdout.strip()}")
        else:
            print("❌ Docker not available")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Docker not available")
        return False
    
    # Validate E2E setup
    try:
        print("🔧 Validating E2E test setup...")
        validation_script = Path(__file__).parent / "validate_e2e_setup.py"
        result = subprocess.run(
            ["python", str(validation_script)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("✅ E2E setup validation passed")
        else:
            print("❌ E2E setup validation failed")
            print("Output:", result.stdout)
            print("Errors:", result.stderr)
            return False
    except Exception as e:
        print(f"❌ E2E validation error: {e}")
        return False
    
    # Check pytest
    try:
        result = subprocess.run(
            ["pytest", "--version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Pytest: {result.stdout.strip()}")
        else:
            print("❌ Pytest not available")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Pytest not available")
        return False
    
    # Check PANTHER installation
    try:
        result = subprocess.run(
            ["python", "-c", "import panther; print('PANTHER installed')"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            print("✅ PANTHER package available")
        else:
            print("❌ PANTHER package not available")
            print("   Run: pip install -e .")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Python not available")
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run PANTHER output collection tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                    # Run all tests
  %(prog)s --docker-compose         # Run Docker Compose tests only
  %(prog)s --performance            # Run performance tests only
  %(prog)s --quick                  # Run quick unit tests only
  %(prog)s --debug                  # Run with debug output
        """
    )
    
    # Test selection options
    parser.add_argument("--all", action="store_true", 
                       help="Run all output collection tests")
    parser.add_argument("--docker-compose", action="store_true",
                       help="Run Docker Compose environment tests")
    parser.add_argument("--localhost", action="store_true",
                       help="Run localhost container environment tests") 
    parser.add_argument("--shadow-ns", action="store_true",
                       help="Run Shadow NS environment tests")
    parser.add_argument("--edge-cases", action="store_true",
                       help="Run edge case tests")
    parser.add_argument("--performance", action="store_true",
                       help="Run performance tests")
    parser.add_argument("--unit", action="store_true",
                       help="Run unit tests only (no Docker required)")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick tests only (unit + edge cases)")
    
    # Test configuration options
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--timeout", type=int, default=300,
                       help="Test timeout in seconds (default: 300)")
    parser.add_argument("--no-capture", action="store_true",
                       help="Don't capture test output")
    parser.add_argument("--keep-containers", action="store_true",
                       help="Keep Docker containers after tests")
    
    args = parser.parse_args()
    
    # If no specific tests selected, default to all
    if not any([args.all, args.docker_compose, args.localhost, args.shadow_ns, 
                args.edge_cases, args.performance, args.unit, args.quick]):
        args.all = True
    
    print("🚀 PANTHER Output Collection Test Runner")
    print(f"📁 Test directory: {Path(__file__).parent}")
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix the issues above.")
        return 1
    
    # Build base pytest command
    test_dir = Path(__file__).parent
    base_cmd = ["pytest", str(test_dir)]
    
    if args.verbose:
        base_cmd.append("-v")
    
    if args.debug:
        base_cmd.extend(["-s", "--log-cli-level=DEBUG", "--tb=long"])
    
    if args.no_capture:
        base_cmd.append("--capture=no")
    
    base_cmd.append(f"--timeout={args.timeout}")
    
    # Test execution tracking
    tests_run = []
    tests_passed = 0
    tests_failed = 0
    total_start_time = time.time()
    
    # Run selected tests
    if args.unit or args.quick:
        cmd = base_cmd + ["-m", "unit"]
        success = run_command(cmd, "Unit Tests", args.timeout)
        tests_run.append(("Unit Tests", success))
        if success:
            tests_passed += 1
        else:
            tests_failed += 1
    
    if args.edge_cases or args.quick:
        cmd = base_cmd + ["test_edge_cases.py"]
        success = run_command(cmd, "Edge Case Tests", args.timeout)
        tests_run.append(("Edge Case Tests", success))
        if success:
            tests_passed += 1
        else:
            tests_failed += 1
    
    if args.docker_compose or args.all:
        cmd = base_cmd + ["-m", "docker_compose and requires_docker"]
        success = run_command(cmd, "Docker Compose Tests", args.timeout)
        tests_run.append(("Docker Compose Tests", success))
        if success:
            tests_passed += 1
        else:
            tests_failed += 1
    
    if args.localhost or args.all:
        cmd = base_cmd + ["-m", "localhost and requires_docker"]
        success = run_command(cmd, "Localhost Container Tests", args.timeout)
        tests_run.append(("Localhost Container Tests", success))
        if success:
            tests_passed += 1
        else:
            tests_failed += 1
    
    if args.shadow_ns or args.all:
        cmd = base_cmd + ["-m", "shadow_ns and requires_docker"]
        success = run_command(cmd, "Shadow NS Tests", args.timeout)
        tests_run.append(("Shadow NS Tests", success))
        if success:
            tests_passed += 1
        else:
            tests_failed += 1
    
    if args.performance or args.all:
        cmd = base_cmd + ["-m", "performance"]
        success = run_command(cmd, "Performance Tests", args.timeout)
        tests_run.append(("Performance Tests", success))
        if success:
            tests_passed += 1
        else:
            tests_failed += 1
    
    # Clean up containers if requested
    if not args.keep_containers:
        print("\n🧹 Cleaning up Docker containers...")
        subprocess.run(
            ["docker", "container", "prune", "-f"], 
            capture_output=True
        )
        subprocess.run(
            ["docker", "system", "prune", "-f"], 
            capture_output=True
        )
    
    # Final summary
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    for test_name, success in tests_run:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:30} {status}")
    
    print(f"\n📈 Results: {tests_passed} passed, {tests_failed} failed")
    print(f"⏱️  Total time: {total_duration:.1f} seconds")
    
    if tests_failed == 0:
        print("\n🎉 All tests passed! Output collection is working correctly.")
        return 0
    else:
        print(f"\n💥 {tests_failed} test(s) failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())