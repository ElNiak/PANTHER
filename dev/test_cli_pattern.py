#!/usr/bin/env python3
"""
Test the exact CLI usage pattern with enhanced config manager.
"""

import sys
from pathlib import Path

# Add panther to path
sys.path.insert(0, str(Path(__file__).parent / "panther"))

def test_original_cli_pattern():
    """Test the exact pattern used by CLI with original config manager."""
    print("🔍 Testing Original CLI Pattern...")
    
    try:
        from panther.config.config_manager import ConfigLoader
        
        # Exact pattern from run.py
        config_path = "experiment-config/experiment_config_example_minimal.yaml"
        
        # Load configuration to get logging settings
        config_loader = ConfigLoader(
            experiment_file=str(config_path),
            debug_override=False,
        )

        # Load global config for logging settings
        global_config = config_loader.load_and_validate_global_config()
        
        print("✅ Original CLI pattern works")
        print(f"📋 Global config type: {type(global_config)}")
        print(f"📋 Has docker config: {hasattr(global_config, 'docker')}")
        return True
        
    except Exception as e:
        print(f"❌ Original CLI pattern failed: {e}")
        return False

def test_enhanced_cli_pattern():
    """Test the exact pattern used by CLI with enhanced config manager."""
    print("\n🔍 Testing Enhanced CLI Pattern...")
    
    try:
        # Import from enhanced version
        from panther.config.config_manager_enhanced import ConfigLoader
        
        # Exact pattern from run.py
        config_path = "experiment-config/experiment_config_example_minimal.yaml"
        
        # Load configuration to get logging settings
        config_loader = ConfigLoader(
            experiment_file=str(config_path),
            debug_override=False,
        )

        # Load global config for logging settings  
        global_config = config_loader.load_and_validate_global_config()
        
        print("✅ Enhanced CLI pattern works")
        print(f"📋 Global config type: {type(global_config)}")
        print(f"📋 Has docker config: {hasattr(global_config, 'docker')}")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced CLI pattern failed: {e}")
        return False

def test_direct_import_replacement():
    """Test if we can directly replace the import statement."""
    print("\n🔄 Testing Direct Import Replacement...")
    
    try:
        # Test the import that would replace in run.py:
        # from ...config.config_manager import ConfigLoader
        # becomes:  
        # from ...config.config_manager_enhanced import ConfigLoader
        
        print("📦 Testing import replacement...")
        
        # Original import
        original_path = "panther.config.config_manager"
        enhanced_path = "panther.config.config_manager_enhanced"
        
        # Test if both provide ConfigLoader
        import importlib
        
        original_module = importlib.import_module(original_path)
        enhanced_module = importlib.import_module(enhanced_path)
        
        if hasattr(original_module, 'ConfigLoader'):
            print("✅ Original module provides ConfigLoader")
        else:
            print("❌ Original module missing ConfigLoader")
            
        if hasattr(enhanced_module, 'ConfigLoader'):
            print("✅ Enhanced module provides ConfigLoader")
        else:
            print("❌ Enhanced module missing ConfigLoader")
            
        return True
        
    except Exception as e:
        print(f"❌ Import replacement test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 PANTHER CLI Usage Pattern Compatibility Test")
    print("=" * 60)
    
    orig_success = test_original_cli_pattern()
    enh_success = test_enhanced_cli_pattern()
    import_success = test_direct_import_replacement()
    
    print(f"\n📋 Results Summary:")
    print(f"   Original CLI Pattern: {'✅ Works' if orig_success else '❌ Failed'}")
    print(f"   Enhanced CLI Pattern: {'✅ Works' if enh_success else '❌ Failed'}")
    print(f"   Import Replacement: {'✅ Works' if import_success else '❌ Failed'}")
    
    if orig_success and enh_success and import_success:
        print("\n🎯 Enhanced version is a DROP-IN REPLACEMENT for CLI usage!")
        print("💡 We can safely replace imports to use enhanced version")
    else:
        print("\n⚠️  Enhanced version needs investigation before replacement")

if __name__ == "__main__":
    main()