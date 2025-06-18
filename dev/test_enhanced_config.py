#!/usr/bin/env python3
"""
Test script to compare original vs enhanced config manager functionality.
This will help us understand if the enhanced version can be a drop-in replacement.
"""

import sys
from pathlib import Path

# Add panther to path
sys.path.insert(0, str(Path(__file__).parent / "panther"))

def test_original_config_manager():
    """Test the original config manager."""
    print("🔍 Testing Original Config Manager...")
    try:
        from panther.config.config_manager import ConfigLoader
        
        # Test basic instantiation (original requires experiment_file)
        config_loader = ConfigLoader(experiment_file="test.yaml")
        print("✅ Original ConfigLoader instantiated successfully")
        
        # Check available methods
        methods = [method for method in dir(config_loader) if not method.startswith('_')]
        print(f"📋 Original methods: {len(methods)} public methods")
        for method in sorted(methods)[:10]:  # Show first 10
            print(f"   - {method}")
        if len(methods) > 10:
            print(f"   ... and {len(methods) - 10} more")
            
        return True, config_loader
    except Exception as e:
        print(f"❌ Original config manager failed: {e}")
        return False, None

def test_enhanced_config_manager():
    """Test the enhanced config manager."""
    print("\n🔍 Testing Enhanced Config Manager...")
    try:
        # Test if we can import the enhanced version
        from panther.config.config_manager_enhanced import ConfigManager as ConfigLoader
        
        # Test basic instantiation
        config_loader = ConfigLoader()
        print("✅ Enhanced ConfigLoader instantiated successfully")
        
        # Check available methods
        methods = [method for method in dir(config_loader) if not method.startswith('_')]
        print(f"📋 Enhanced methods: {len(methods)} public methods")
        for method in sorted(methods)[:10]:  # Show first 10
            print(f"   - {method}")
        if len(methods) > 10:
            print(f"   ... and {len(methods) - 10} more")
            
        return True, config_loader
    except Exception as e:
        print(f"❌ Enhanced config manager failed: {e}")
        return False, None

def test_refactored_config_manager():
    """Test the refactored config manager directly."""
    print("\n🔍 Testing Refactored Config Manager...")
    try:
        from panther.config.config_manager_refactored import ConfigManagerRefactored
        
        # Test basic instantiation
        config_loader = ConfigManagerRefactored()
        print("✅ Refactored ConfigManagerRefactored instantiated successfully")
        
        # Check available methods
        methods = [method for method in dir(config_loader) if not method.startswith('_')]
        print(f"📋 Refactored methods: {len(methods)} public methods")
        for method in sorted(methods)[:10]:  # Show first 10
            print(f"   - {method}")
        if len(methods) > 10:
            print(f"   ... and {len(methods) - 10} more")
            
        return True, config_loader
    except Exception as e:
        print(f"❌ Refactored config manager failed: {e}")
        return False, None

def compare_interfaces(original, enhanced, refactored):
    """Compare the interfaces of the three versions."""
    print("\n🔄 Comparing Interfaces...")
    
    if original:
        orig_methods = set(method for method in dir(original) if not method.startswith('_'))
    else:
        orig_methods = set()
        
    if enhanced:
        enh_methods = set(method for method in dir(enhanced) if not method.startswith('_'))
    else:
        enh_methods = set()
        
    if refactored:
        ref_methods = set(method for method in dir(refactored) if not method.startswith('_'))
    else:
        ref_methods = set()
    
    print(f"📊 Method count comparison:")
    print(f"   Original: {len(orig_methods)}")
    print(f"   Enhanced: {len(enh_methods)}")
    print(f"   Refactored: {len(ref_methods)}")
    
    if orig_methods and enh_methods:
        common = orig_methods & enh_methods
        only_orig = orig_methods - enh_methods
        only_enh = enh_methods - orig_methods
        
        print(f"\n🤝 Common methods: {len(common)}")
        print(f"🔴 Only in original: {len(only_orig)}")
        if only_orig:
            for method in sorted(only_orig)[:5]:
                print(f"   - {method}")
            if len(only_orig) > 5:
                print(f"   ... and {len(only_orig) - 5} more")
                
        print(f"🟢 Only in enhanced: {len(only_enh)}")
        if only_enh:
            for method in sorted(only_enh)[:5]:
                print(f"   - {method}")
            if len(only_enh) > 5:
                print(f"   ... and {len(only_enh) - 5} more")

def main():
    """Main test function."""
    print("🧪 PANTHER Enhanced Config Manager Compatibility Test")
    print("=" * 60)
    
    # Test all three versions
    orig_success, original = test_original_config_manager()
    enh_success, enhanced = test_enhanced_config_manager()
    ref_success, refactored = test_refactored_config_manager()
    
    # Compare interfaces
    compare_interfaces(original, enhanced, refactored)
    
    # Summary
    print("\n📋 Summary:")
    print(f"   Original Config Manager: {'✅ Works' if orig_success else '❌ Failed'}")
    print(f"   Enhanced Config Manager: {'✅ Works' if enh_success else '❌ Failed'}")
    print(f"   Refactored Config Manager: {'✅ Works' if ref_success else '❌ Failed'}")
    
    if enh_success and orig_success:
        print("\n🎯 Enhanced version can potentially replace original!")
    elif ref_success:
        print("\n🎯 Refactored version is available for integration!")
    else:
        print("\n⚠️  Need to investigate issues before integration")

if __name__ == "__main__":
    main()