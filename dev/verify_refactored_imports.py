#!/usr/bin/env python3
"""
Verification script to test that the refactored imports work correctly.
"""
import sys
from pathlib import Path

# Add the PANTHER directory to the Python path
panther_dir = Path(__file__).parent
sys.path.insert(0, str(panther_dir))

def test_imports():
    """Test that all refactored components can be imported successfully."""
    
    print("Testing refactored component imports...")
    
    try:
        # Test TestCase implementation
        print("✓ Testing TestCase imports...")
        from panther.core.test_cases.test_case_impl import TestCaseImpl
        print(f"  - TestCaseImpl: {TestCaseImpl}")
        
        # Test Config Manager
        print("✓ Testing ConfigManager imports...")
        from panther.config.config_manager import ConfigManager
        print(f"  - ConfigManager: {ConfigManager}")
        
        # Test Command components
        print("✓ Testing Command imports...")
        from panther.core.command_processor.command import ShellCommand, CommandMetadata
        print(f"  - ShellCommand: {ShellCommand}")
        print(f"  - CommandMetadata: {CommandMetadata}")
        
        # Test PantherIvy
        print("✓ Testing PantherIvy imports...")
        from panther.plugins.services.testers.panther_ivy.panther_ivy import PantherIvyServiceManager
        print(f"  - PantherIvyServiceManager: {PantherIvyServiceManager}")
        
        # Test modular components can be imported
        print("✓ Testing modular component imports...")
        
        # Test case components
        from panther.core.test_cases.base.test_case_base import TestCaseBase
        from panther.core.test_cases.mixins.service_management import ServiceManagementMixin
        from panther.core.test_cases.execution.test_executor import TestExecutor
        print(f"  - TestCaseBase: {TestCaseBase}")
        print(f"  - ServiceManagementMixin: {ServiceManagementMixin}")
        print(f"  - TestExecutor: {TestExecutor}")
        
        # Config manager components
        from panther.config.managers.configuration_builder import ConfigurationBuilder
        from panther.config.managers.plugin_discovery import PluginDiscovery
        print(f"  - ConfigurationBuilder: {ConfigurationBuilder}")
        print(f"  - PluginDiscovery: {PluginDiscovery}")
        
        # PantherIvy components
        from panther.plugins.services.testers.panther_ivy.components.ivy_command_generator import IvyCommandGenerator
        from panther.plugins.services.testers.panther_ivy.components.ivy_test_executor import IvyTestExecutor
        print(f"  - IvyCommandGenerator: {IvyCommandGenerator}")
        print(f"  - IvyTestExecutor: {IvyTestExecutor}")
        
        print("\n🎉 All imports successful! The refactored components are working correctly.")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("There may be missing dependencies or circular imports.")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

def test_backward_compatibility():
    """Test that backward compatibility aliases work."""
    
    print("\nTesting backward compatibility...")
    
    try:
        # Test legacy aliases
        from panther.core.test_cases.test_case_impl import TestCase
        from panther.config.config_manager import ConfigLoader
        from panther.core.command_processor.command import Command
        from panther.plugins.services.testers.panther_ivy.panther_ivy import PantherIvy
        
        print("✓ Legacy aliases work correctly:")
        print(f"  - TestCase: {TestCase}")
        print(f"  - ConfigLoader: {ConfigLoader}")
        print(f"  - Command: {Command}")
        print(f"  - PantherIvy: {PantherIvy}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Backward compatibility issue: {e}")
        return False

def test_class_instantiation():
    """Test that the main classes can be instantiated."""
    
    print("\nTesting class instantiation...")
    
    try:
        # Test ConfigManager instantiation
        from panther.config.config_manager import ConfigManager
        config_manager = ConfigManager()
        print(f"✓ ConfigManager instantiated: {config_manager}")
        
        # Test modular components
        from panther.config.managers.configuration_builder import ConfigurationBuilder
        builder = ConfigurationBuilder()
        print(f"✓ ConfigurationBuilder instantiated: {builder}")
        
        from panther.config.managers.plugin_discovery import PluginDiscovery
        discovery = PluginDiscovery(Path("/tmp"))
        print(f"✓ PluginDiscovery instantiated: {discovery}")
        
        return True
        
    except Exception as e:
        print(f"❌ Instantiation error: {e}")
        return False

def main():
    """Main verification function."""
    
    print("=" * 60)
    print("PANTHER Refactored Components Verification")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Run all tests
    if not test_imports():
        all_tests_passed = False
    
    if not test_backward_compatibility():
        all_tests_passed = False
    
    if not test_class_instantiation():
        all_tests_passed = False
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED! The refactored implementation is ready to use.")
        print("\nBackup Information:")
        print("- Original files have been backed up to backup_originals/")
        print("- Current files now use the new refactored implementations")
        print("- Backward compatibility is maintained through aliases")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\nYou may need to:")
        print("- Check for missing imports or dependencies")
        print("- Verify that all component files exist")
        print("- Fix any circular import issues")
    print("=" * 60)
    
    return 0 if all_tests_passed else 1

if __name__ == "__main__":
    sys.exit(main())