#!/usr/bin/env python3
"""
Test specific method compatibility between original and enhanced config managers.
"""

import sys
from pathlib import Path

# Add panther to path
sys.path.insert(0, str(Path(__file__).parent / "panther"))

def test_critical_method_compatibility():
    """Test if enhanced version has the methods that CLI uses."""
    print("🔍 Testing Critical Method Compatibility...")
    
    # Methods that CLI and main codebase use
    critical_methods = [
        'load_and_validate_global_config',
        'load_and_validate_experiment_config', 
        'construct_global_config',
        'construct_experiment_config'
    ]
    
    try:
        # Test original
        from panther.config.config_manager import ConfigLoader as OriginalLoader
        original = OriginalLoader(experiment_file="test.yaml")
        
        print("📋 Original ConfigLoader methods:")
        for method in critical_methods:
            has_method = hasattr(original, method)
            print(f"   {'✅' if has_method else '❌'} {method}")
        
        # Test enhanced
        from panther.config.config_manager_enhanced import ConfigManager as EnhancedLoader
        enhanced = EnhancedLoader()
        
        print("\n📋 Enhanced ConfigLoader methods:")
        for method in critical_methods:
            has_method = hasattr(enhanced, method)
            print(f"   {'✅' if has_method else '❌'} {method}")
            
        print("\n🧪 Testing method calls with sample experiment file...")
        
        # Check if we can find a sample experiment file
        sample_files = [
            "experiment-config/experiment_config_example_minimal.yaml",
            "experiment-config/experiment_config_example.yaml"
        ]
        
        sample_file = None
        for file_path in sample_files:
            full_path = Path(file_path)
            if full_path.exists():
                sample_file = str(full_path)
                break
                
        if sample_file:
            print(f"📁 Using sample file: {sample_file}")
            
            # Test original with real file
            try:
                original_with_file = OriginalLoader(experiment_file=sample_file)
                global_config = original_with_file.load_and_validate_global_config()
                print("✅ Original load_and_validate_global_config() works")
            except Exception as e:
                print(f"❌ Original load_and_validate_global_config() failed: {e}")
                
            # Test enhanced with real file  
            try:
                enhanced_with_file = EnhancedLoader(experiment_file=sample_file)
                global_config = enhanced_with_file.load_and_validate_global_config()
                print("✅ Enhanced load_and_validate_global_config() works")
            except Exception as e:
                print(f"❌ Enhanced load_and_validate_global_config() failed: {e}")
        else:
            print("⚠️  No sample experiment file found for testing")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

def test_import_compatibility():
    """Test if we can import ConfigManager the same way."""
    print("\n🔄 Testing Import Compatibility...")
    
    try:
        # Test if enhanced version exports ConfigLoader alias
        from panther.config.config_manager_enhanced import ConfigLoader
        print("✅ Enhanced version provides ConfigLoader alias")
        
        # Test instantiation
        loader = ConfigLoader()
        print("✅ Enhanced ConfigLoader instantiates without experiment_file")
        
        # Check if it has the required method
        if hasattr(loader, 'load_and_validate_global_config'):
            print("✅ Enhanced ConfigLoader has load_and_validate_global_config")
        else:
            print("❌ Enhanced ConfigLoader missing load_and_validate_global_config")
            
    except ImportError as e:
        print(f"❌ Cannot import ConfigLoader from enhanced version: {e}")
    except Exception as e:
        print(f"❌ Enhanced version error: {e}")

def main():
    """Main test function."""
    print("🧪 PANTHER Enhanced Config Manager Method Compatibility Test")
    print("=" * 70)
    
    test_critical_method_compatibility()
    test_import_compatibility()

if __name__ == "__main__":
    main()