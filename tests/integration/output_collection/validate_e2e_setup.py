#!/usr/bin/env python3
"""
Validation script to check if our E2E test setup is working correctly.

This script validates that:
1. The test service plugin is properly registered
2. PANTHER can discover and load the test service
3. Basic functionality works before running full integration tests
"""

import sys
from pathlib import Path

# Add PANTHER to Python path
panther_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(panther_root))

try:
    from panther.plugins.plugin_manager import PluginManager
    from panther.config.config_manager import ConfigLoader
    print("✅ PANTHER imports successful")
except ImportError as e:
    print(f"❌ Failed to import PANTHER: {e}")
    sys.exit(1)


def test_plugin_discovery():
    """Test that our test service plugin can be discovered."""
    print("\n🔍 Testing plugin discovery...")
    
    try:
        # Test that we can import the plugin directly
        from panther.plugins.services.iut.testing.test_output_service.test_output_service import TestOutputServiceManager
        print("✅ Test service plugin can be imported directly")
        
        # Test that the plugin is properly decorated
        if hasattr(TestOutputServiceManager, '_plugin_metadata'):
            metadata = TestOutputServiceManager._plugin_metadata
            print(f"✅ Plugin metadata found: {metadata.get('name', 'unknown')}")
        else:
            print("⚠️  Plugin metadata not found (may still work)")
        
        return True
        
    except Exception as e:
        print(f"❌ Plugin discovery failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_loading():
    """Test that our test configurations can be loaded."""
    print("\n📋 Testing configuration loading...")
    
    config_files = [
        "test_configs/docker_compose_minimal.yaml",
        "test_configs/localhost_minimal.yaml", 
        "test_configs/shadow_ns_minimal.yaml"
    ]
    
    success_count = 0
    
    for config_file in config_files:
        config_path = Path(__file__).parent / config_file
        
        if not config_path.exists():
            print(f"❌ Config file not found: {config_path}")
            continue
            
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            print(f"✅ Successfully loaded: {config_file}")
            
            # Basic validation
            if 'tests' in config and len(config['tests']) > 0:
                test_config = config['tests'][0]
                if 'services' in test_config:
                    services = test_config['services']
                    for service_name, service_config in services.items():
                        impl_name = service_config.get('implementation', {}).get('name')
                        if impl_name == 'test_output_service':
                            print(f"  ✅ Found test_output_service in {service_name}")
                        else:
                            print(f"  ⚠️  Service {service_name} uses {impl_name}")
            
            success_count += 1
            
        except Exception as e:
            print(f"❌ Failed to load {config_file}: {e}")
    
    return success_count == len(config_files)


def test_service_instantiation():
    """Test that the test service can be instantiated."""
    print("\n🏭 Testing service instantiation...")
    
    try:
        from panther.plugins.services.iut.testing.test_output_service.test_output_service import TestOutputServiceManager
        from panther.plugins.services.iut.testing.test_output_service.config_schema import TestOutputServiceConfig
        from panther.plugins.protocols.config_schema import ProtocolConfig
        
        # Create test configuration with basic required fields
        service_config = TestOutputServiceConfig(
            name="test_service",
            timeout=30,
            runtime_seconds=1,
            create_additional_files=True
        )
        
        protocol_config = ProtocolConfig(
            name="quic",
            version="rfc9000"
        )
        
        # Try to instantiate the service with minimal args
        service = TestOutputServiceManager(
            service_config_to_test=service_config,
            service_type="iut",
            protocol=protocol_config,
            implementation_name="test_output_service"
        )
        
        print(f"✅ Service instantiated successfully")
        print(f"  Implementation name: {service._get_implementation_name()}")
        print(f"  Binary name: {service._get_binary_name()}")
        print(f"  Supported features: {service.get_supported_features()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Service instantiation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("🚀 PANTHER E2E Test Setup Validation")
    print("=" * 50)
    
    tests = [
        ("Plugin Discovery", test_plugin_discovery),
        ("Configuration Loading", test_config_loading),
        ("Service Instantiation", test_service_instantiation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
    
    print(f"\n📊 Validation Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All validations passed! E2E test setup is ready.")
        return 0
    else:
        print("💥 Some validations failed. Please fix issues before running E2E tests.")
        return 1


if __name__ == "__main__":
    sys.exit(main())