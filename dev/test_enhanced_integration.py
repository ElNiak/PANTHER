#!/usr/bin/env python3
"""
Integration test for enhanced versions with real PANTHER functionality.
Tests enhanced config manager with actual CLI commands.
"""

import sys
import subprocess
from pathlib import Path
import tempfile
import shutil

# Add panther to path
sys.path.insert(0, str(Path(__file__).parent / "panther"))

def backup_and_replace_config_manager():
    """Temporarily replace config manager imports with enhanced version."""
    print("📦 Temporarily replacing config manager imports...")
    
    files_to_modify = [
        "panther/cli/subcommands/run.py",
        "panther/cli/subcommands/config.py", 
        "panther/cli/subcommands/plugins.py",
        "panther/webapp/web_app.py"
    ]
    
    backup_files = {}
    
    try:
        for file_path in files_to_modify:
            full_path = Path(file_path)
            if full_path.exists():
                # Create backup
                backup_path = full_path.with_suffix('.py.backup_enhanced_test')
                shutil.copy2(full_path, backup_path)
                backup_files[str(full_path)] = str(backup_path)
                
                # Read current content
                content = full_path.read_text()
                
                # Replace the import
                old_import = "from ...config.config_manager import ConfigLoader"
                new_import = "from ...config.config_manager_enhanced import ConfigLoader"
                
                if old_import in content:
                    new_content = content.replace(old_import, new_import)
                    full_path.write_text(new_content)
                    print(f"✅ Modified {file_path}")
                else:
                    print(f"⚠️  {file_path} doesn't have expected import pattern")
                    
        return backup_files
        
    except Exception as e:
        print(f"❌ Failed to modify files: {e}")
        # Restore any backups made so far
        restore_files(backup_files)
        return {}

def restore_files(backup_files):
    """Restore original files from backups."""
    print("🔄 Restoring original files...")
    
    for original_path, backup_path in backup_files.items():
        try:
            if Path(backup_path).exists():
                shutil.copy2(backup_path, original_path)
                Path(backup_path).unlink()  # Remove backup
                print(f"✅ Restored {original_path}")
        except Exception as e:
            print(f"❌ Failed to restore {original_path}: {e}")

def test_enhanced_cli_commands():
    """Test CLI commands with enhanced config manager."""
    print("\n🧪 Testing CLI Commands with Enhanced Config Manager...")
    
    test_results = {}
    
    # Test config validation command
    try:
        print("🔍 Testing: panther config validate")
        result = subprocess.run([
            sys.executable, "-m", "panther", "config", "validate", 
            "--config", "experiment-config/experiment_config_example_minimal.yaml"
        ], capture_output=True, text=True, timeout=30)
        
        test_results['config_validate'] = {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
        if result.returncode == 0:
            print("✅ Config validation works with enhanced version")
        else:
            print(f"❌ Config validation failed: {result.stderr}")
            
    except Exception as e:
        test_results['config_validate'] = {
            'success': False,
            'error': str(e)
        }
        print(f"❌ Config validation test failed: {e}")

    # Test plugins list command
    try:
        print("🔍 Testing: panther plugins list")
        result = subprocess.run([
            sys.executable, "-m", "panther", "plugins", "list"
        ], capture_output=True, text=True, timeout=30)
        
        test_results['plugins_list'] = {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
        if result.returncode == 0:
            print("✅ Plugins list works with enhanced version")
        else:
            print(f"❌ Plugins list failed: {result.stderr}")
            
    except Exception as e:
        test_results['plugins_list'] = {
            'success': False,
            'error': str(e)
        }
        print(f"❌ Plugins list test failed: {e}")

    # Test config help
    try:
        print("🔍 Testing: panther config --help")
        result = subprocess.run([
            sys.executable, "-m", "panther", "config", "--help"
        ], capture_output=True, text=True, timeout=30)
        
        test_results['config_help'] = {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
        if result.returncode == 0:
            print("✅ Config help works with enhanced version")
        else:
            print(f"❌ Config help failed: {result.stderr}")
            
    except Exception as e:
        test_results['config_help'] = {
            'success': False,
            'error': str(e)
        }
        print(f"❌ Config help test failed: {e}")
    
    return test_results

def test_import_timing():
    """Test import timing to see if enhanced version is faster."""
    print("\n⏱️ Testing Import Performance...")
    
    import time
    
    # Test original import time
    start_time = time.time()
    try:
        # Clear any cached imports
        if 'panther.config.config_manager' in sys.modules:
            del sys.modules['panther.config.config_manager']
        
        from panther.config.config_manager import ConfigLoader as OriginalLoader
        original_time = time.time() - start_time
        print(f"📊 Original import time: {original_time:.4f}s")
        
    except Exception as e:
        print(f"❌ Original import failed: {e}")
        original_time = None
        
    # Test enhanced import time
    start_time = time.time()
    try:
        # Clear any cached imports
        if 'panther.config.config_manager_enhanced' in sys.modules:
            del sys.modules['panther.config.config_manager_enhanced']
            
        from panther.config.config_manager_enhanced import ConfigLoader as EnhancedLoader
        enhanced_time = time.time() - start_time
        print(f"📊 Enhanced import time: {enhanced_time:.4f}s")
        
    except Exception as e:
        print(f"❌ Enhanced import failed: {e}")
        enhanced_time = None
        
    if original_time and enhanced_time:
        if enhanced_time < original_time:
            improvement = ((original_time - enhanced_time) / original_time) * 100
            print(f"🚀 Enhanced version is {improvement:.1f}% faster to import")
        else:
            slower = ((enhanced_time - original_time) / original_time) * 100
            print(f"⚠️  Enhanced version is {slower:.1f}% slower to import")

def main():
    """Main integration test function."""
    print("🧪 PANTHER Enhanced Versions Integration Test")
    print("=" * 60)
    
    # Test import timing first (before modifying files)
    test_import_timing()
    
    # Backup and temporarily replace imports
    backup_files = backup_and_replace_config_manager()
    
    if not backup_files:
        print("❌ Failed to modify files for testing - aborting")
        return
        
    try:
        # Test CLI commands with enhanced version
        test_results = test_enhanced_cli_commands()
        
        # Summary
        print(f"\n📋 Integration Test Results:")
        for test_name, result in test_results.items():
            status = "✅ PASSED" if result.get('success', False) else "❌ FAILED"
            print(f"   {test_name}: {status}")
            
        # Overall assessment
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results.values() if result.get('success', False))
        
        print(f"\n📊 Overall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎯 Enhanced config manager is ready for production integration!")
        elif passed_tests > 0:
            print("⚠️  Enhanced version works partially - needs investigation")
        else:
            print("❌ Enhanced version has issues - not ready for integration")
            
    finally:
        # Always restore original files
        restore_files(backup_files)
        print("\n🔄 Files restored to original state")

if __name__ == "__main__":
    main()