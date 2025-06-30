#!/usr/bin/env python3
"""
Baseline validation script for environment refactoring.

This script tests that core environment functionality works BEFORE refactoring.
It should be run before and after refactoring to ensure no regressions.

Usage:
    python tests/test_refactoring_baseline.py
"""

import sys
import traceback
from unittest.mock import Mock


def test_imports():
    """Test that all critical imports work."""
    print("Testing imports...")

    try:
        # Test monitor imports
        from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
            BackgroundServiceMonitor,
        )

        print("✓ BackgroundServiceMonitor imported")

        # Test environment imports
        from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
            DockerComposeEnvironment,
        )

        print("✓ DockerComposeEnvironment imported")

        from panther.plugins.environments.network_environment.localhost_single_container.localhost_single_container import (
            LocalhostSingleContainerEnvironment,
        )

        print("✓ LocalhostSingleContainerEnvironment imported")

        from panther.plugins.environments.network_environment.shadow_ns.shadow_ns import (
            ShadowNsEnvironment,
        )

        print("✓ ShadowNsEnvironment imported")

        return True

    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False


def test_monitor_instantiation():
    """Test that monitors can be instantiated."""
    print("\nTesting monitor instantiation...")

    try:
        from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
            BackgroundServiceMonitor,
        )

        # Create mock dependencies
        mock_env = Mock()
        mock_env.logger = Mock()
        mock_env._is_service_ready = Mock(return_value=True)

        mock_config = Mock()
        mock_config.monitoring_interval_seconds = 1.0
        mock_config.failure_threshold_count = 2
        mock_config.critical_services = []
        mock_config.allow_partial_deployment = False

        # Test instantiation
        monitor = BackgroundServiceMonitor(mock_env, ["service1"], mock_config)
        print("✓ BackgroundServiceMonitor instantiated")

        # Test basic properties
        assert monitor.monitoring_active is False
        assert monitor.monitor_thread is None
        print("✓ Monitor has expected initial state")

        return True

    except Exception as e:
        print(f"✗ Monitor instantiation failed: {e}")
        traceback.print_exc()
        return False


def test_monitor_thread_operations():
    """Test basic monitor thread operations."""
    print("\nTesting monitor thread operations...")

    try:
        import time

        from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
            BackgroundServiceMonitor,
        )

        # Create mock dependencies
        mock_env = Mock()
        mock_env.logger = Mock()
        mock_env._is_service_ready = Mock(return_value=True)

        mock_config = Mock()
        mock_config.monitoring_interval_seconds = 0.1  # Fast for testing
        mock_config.failure_threshold_count = 2
        mock_config.critical_services = []
        mock_config.allow_partial_deployment = False

        monitor = BackgroundServiceMonitor(mock_env, ["service1"], mock_config)

        # Test starting monitoring
        monitor.start_monitoring()
        assert monitor.monitoring_active is True
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()
        print("✓ Monitor started successfully")

        # Let it run briefly
        time.sleep(0.2)

        # Test stopping monitoring
        monitor.stop_monitoring()
        assert monitor.monitoring_active is False
        print("✓ Monitor stopped successfully")

        # Give thread time to clean up
        time.sleep(0.1)
        assert not monitor.monitor_thread.is_alive()
        print("✓ Monitor thread cleaned up")

        return True

    except Exception as e:
        print(f"✗ Monitor thread operations failed: {e}")
        traceback.print_exc()
        return False


def test_environment_instantiation():
    """Test that environments can be instantiated."""
    print("\nTesting environment instantiation...")

    try:
        from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
            DockerComposeEnvironment,
        )

        # Create mock dependencies
        mock_config = Mock()
        mock_config.type = "docker_compose"
        mock_config.enable_background_monitoring = False

        mock_event_manager = Mock()

        # Test instantiation
        env = DockerComposeEnvironment(
            env_config_to_test=mock_config,
            output_dir="/tmp/test",
            env_type="network",
            env_sub_type="docker_compose",
            event_manager=mock_event_manager,
        )

        print("✓ DockerComposeEnvironment instantiated")

        # Test basic properties
        assert env.env_type == "network"
        assert env.env_sub_type == "docker_compose"
        assert hasattr(env, "logger")
        print("✓ Environment has expected properties")

        return True

    except Exception as e:
        print(f"✗ Environment instantiation failed: {e}")
        traceback.print_exc()
        return False


def test_network_resolver_imports():
    """Test that network resolvers can be imported."""
    print("\nTesting network resolver imports...")

    try:
        from panther.plugins.environments.network_environment.docker_compose.docker_network_resolver import (
            DockerComposeNetworkResolver,
        )

        print("✓ DockerComposeNetworkResolver imported")

        from panther.plugins.environments.network_environment.localhost_single_container.localhost_network_resolver import (
            LocalhostNetworkResolver,
        )

        print("✓ LocalhostNetworkResolver imported")

        from panther.plugins.environments.network_environment.shadow_ns.shadow_network_resolver import (
            ShadowNetworkResolver,
        )

        print("✓ ShadowNetworkResolver imported")

        return True

    except Exception as e:
        print(f"✗ Network resolver imports failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all baseline tests."""
    print("=" * 60)
    print("PANTHER Environment Refactoring - Baseline Validation")
    print("=" * 60)

    tests = [
        test_imports,
        test_monitor_instantiation,
        test_monitor_thread_operations,
        test_environment_instantiation,
        test_network_resolver_imports,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"BASELINE VALIDATION RESULTS:")
    print(f"PASSED: {passed}")
    print(f"FAILED: {failed}")
    print(f"TOTAL:  {passed + failed}")

    if failed == 0:
        print("\n🎉 ALL BASELINE TESTS PASSED! Safe to proceed with refactoring.")
        return 0
    else:
        print(f"\n❌ {failed} BASELINE TESTS FAILED! Fix issues before refactoring.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
