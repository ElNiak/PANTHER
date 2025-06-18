#!/usr/bin/env python3
"""
Test enhanced Panther Ivy components vs original implementation.
"""

import sys
from pathlib import Path

# Add panther to path
sys.path.insert(0, str(Path(__file__).parent / "panther"))

def test_original_panther_ivy():
    """Test the original Panther Ivy implementation."""
    print("🔍 Testing Original Panther Ivy...")
    
    try:
        from panther.plugins.services.testers.panther_ivy.panther_ivy import PantherIvyServiceManager
        
        # Test basic instantiation
        # Note: PantherIvy likely needs config parameters
        print("✅ Original PantherIvyServiceManager imported successfully")
        
        # Check file size and complexity
        original_file = Path("panther/plugins/services/testers/panther_ivy/panther_ivy.py")
        if original_file.exists():
            size = original_file.stat().st_size
            print(f"📊 Original file size: {size:,} bytes")
        
        # Check available methods
        methods = [method for method in dir(PantherIvyServiceManager) if not method.startswith('_')]
        print(f"📋 Original methods: {len(methods)} public methods")
        
        return True, PantherIvyServiceManager
        
    except Exception as e:
        print(f"❌ Original Panther Ivy failed: {e}")
        return False, None

def test_enhanced_panther_ivy():
    """Test the enhanced Panther Ivy implementation."""
    print("\n🔍 Testing Enhanced Panther Ivy...")
    
    try:
        from panther.plugins.services.testers.panther_ivy.panther_ivy_enhanced import PantherIvyServiceManager
        
        print("✅ Enhanced PantherIvyServiceManager imported successfully")
        
        # Check file size and complexity
        enhanced_file = Path("panther/plugins/services/testers/panther_ivy/panther_ivy_enhanced.py")
        if enhanced_file.exists():
            size = enhanced_file.stat().st_size
            print(f"📊 Enhanced file size: {size:,} bytes")
        
        # Check available methods
        methods = [method for method in dir(PantherIvyServiceManager) if not method.startswith('_')]
        print(f"📋 Enhanced methods: {len(methods)} public methods")
        
        return True, PantherIvyServiceManager
        
    except Exception as e:
        print(f"❌ Enhanced Panther Ivy failed: {e}")
        return False, None

def test_refactored_panther_ivy():
    """Test the refactored Panther Ivy implementation."""
    print("\n🔍 Testing Refactored Panther Ivy...")
    
    try:
        from panther.plugins.services.testers.panther_ivy.panther_ivy_refactored import PantherIvyServiceManagerRefactored
        
        print("✅ Refactored PantherIvyServiceManagerRefactored imported successfully")
        
        # Check file size and complexity
        refactored_file = Path("panther/plugins/services/testers/panther_ivy/panther_ivy_refactored.py")
        if refactored_file.exists():
            size = refactored_file.stat().st_size
            print(f"📊 Refactored file size: {size:,} bytes")
        
        # Check available methods
        methods = [method for method in dir(PantherIvyServiceManagerRefactored) if not method.startswith('_')]
        print(f"📋 Refactored methods: {len(methods)} public methods")
        
        return True, PantherIvyServiceManagerRefactored
        
    except Exception as e:
        print(f"❌ Refactored Panther Ivy failed: {e}")
        return False, None

def test_enhanced_components():
    """Test the enhanced modular components."""
    print("\n🔍 Testing Enhanced Modular Components...")
    
    components = [
        'ivy_command_generator',
        'ivy_log_analyzer', 
        'ivy_output_manager',
        'ivy_test_executor',
        'ivy_environment_setup',
        'ivy_protocol_handler'
    ]
    
    component_status = {}
    
    for component in components:
        try:
            module_path = f"panther.plugins.services.testers.panther_ivy.components.{component}"
            import importlib
            module = importlib.import_module(module_path)
            
            # Check what classes are available
            classes = [item for item in dir(module) if not item.startswith('_') and item[0].isupper()]
            component_status[component] = {
                'success': True,
                'classes': classes,
                'module': module
            }
            print(f"✅ {component}: {len(classes)} classes")
            
        except Exception as e:
            component_status[component] = {
                'success': False,
                'error': str(e),
                'classes': []
            }
            print(f"❌ {component}: {e}")
            
    return component_status

def compare_implementations(original_cls, enhanced_cls, refactored_cls):
    """Compare the three implementations."""
    print("\n🔄 Comparing Implementations...")
    
    if original_cls and enhanced_cls:
        # Compare method counts
        orig_methods = set(method for method in dir(original_cls) if not method.startswith('_'))
        enh_methods = set(method for method in dir(enhanced_cls) if not method.startswith('_'))
        
        common = orig_methods & enh_methods
        only_orig = orig_methods - enh_methods
        only_enh = enh_methods - orig_methods
        
        print(f"📊 Method comparison (Original vs Enhanced):")
        print(f"   Original: {len(orig_methods)} methods")
        print(f"   Enhanced: {len(enh_methods)} methods")
        print(f"   Common: {len(common)} methods")
        print(f"   Only in original: {len(only_orig)}")
        print(f"   Only in enhanced: {len(only_enh)}")
        
        # Check for key methods
        key_methods = ['generate_run_command', 'prepare', 'initialize']
        print(f"\n🔑 Key methods availability:")
        for method in key_methods:
            orig_has = method in orig_methods
            enh_has = method in enh_methods
            print(f"   {method}: Original {'✅' if orig_has else '❌'}, Enhanced {'✅' if enh_has else '❌'}")

def main():
    """Main test function."""
    print("🧪 PANTHER Enhanced Ivy Components Test")
    print("=" * 50)
    
    # Test all three versions
    orig_success, original_cls = test_original_panther_ivy()
    enh_success, enhanced_cls = test_enhanced_panther_ivy() 
    ref_success, refactored_cls = test_refactored_panther_ivy()
    
    # Test modular components
    component_status = test_enhanced_components()
    
    # Compare implementations
    compare_implementations(original_cls, enhanced_cls, refactored_cls)
    
    # Summary
    print(f"\n📋 Summary:")
    print(f"   Original Panther Ivy: {'✅ Works' if orig_success else '❌ Failed'}")
    print(f"   Enhanced Panther Ivy: {'✅ Works' if enh_success else '❌ Failed'}")
    print(f"   Refactored Panther Ivy: {'✅ Works' if ref_success else '❌ Failed'}")
    
    working_components = sum(1 for comp in component_status.values() if comp['success'])
    total_components = len(component_status)
    print(f"   Modular Components: {working_components}/{total_components} working")
    
    if enh_success and working_components == total_components:
        print("\n🎯 Enhanced version with modular components is ready for integration!")
    elif ref_success:
        print("\n🎯 Refactored version is available for testing!")
    else:
        print("\n⚠️  Issues found - needs investigation before integration")

if __name__ == "__main__":
    main()