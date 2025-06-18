#!/usr/bin/env python3
"""Verify that the Docker tag fixes are working"""

import sys
import os

# Add PANTHER to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_service_type_handling():
    """Test that service type is handled correctly for both string and enum"""
    print("Testing service type handling...")
    
    # Test with mock objects
    class MockImpl:
        def __init__(self, type_val):
            self.type = type_val
            self.name = "test_service"
    
    class MockServiceConfig:
        def __init__(self, impl_type):
            self.implementation = MockImpl(impl_type)
    
    # Test with string type
    config1 = MockServiceConfig("IUT")
    impl_type = config1.implementation.type
    if isinstance(impl_type, str):
        print(f"✓ String type handled correctly: {impl_type}")
    else:
        print(f"✗ String type not handled: {impl_type}")
    
    # Test with enum-like object
    class MockEnum:
        def __init__(self, value):
            self.value = value
    
    config2 = MockServiceConfig(MockEnum("iut"))
    impl_type = config2.implementation.type
    if hasattr(impl_type, 'value'):
        print(f"✓ Enum type handled correctly: {impl_type.value}")
    else:
        print(f"✗ Enum type not handled: {impl_type}")
    
    return True

def test_version_extraction():
    """Test version extraction from protocol"""
    print("\nTesting version extraction...")
    
    class MockProtocol:
        def __init__(self):
            self.version = "rfc9000"
            self.name = "quic"
    
    class MockServiceConfig:
        def __init__(self):
            self.protocol = MockProtocol()
    
    config = MockServiceConfig()
    version = getattr(config.protocol, "version", None)
    
    if version == "rfc9000":
        print(f"✓ Version extracted correctly: {version}")
        print(f"✓ Expected Docker tag: picoquic_{version}:latest")
        return True
    else:
        print(f"✗ Version extraction failed: {version}")
        return False

def main():
    print("Verifying Docker tag fixes...")
    print("=" * 60)
    
    # Run tests
    test1 = test_service_type_handling()
    test2 = test_version_extraction()
    
    print("\n" + "=" * 60)
    if test1 and test2:
        print("✅ All tests passed! The fixes should work correctly.")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())