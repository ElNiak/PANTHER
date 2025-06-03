#!/usr/bin/env python3
"""
Command generation validation script

This script validates the command generation across different Panther plugins
to ensure they follow the structured approach and handle special characters properly.
"""

import os
import sys
import logging
import argparse
from typing import Dict, List, Tuple, Any
import importlib.util
import inspect

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Try to import Panther modules, but don't fail if they're not found
try:
    from panther.plugins.services.command_validation_util import (
        validate_command_arguments,
        validate_environment_variables,
        validate_shell_command
    )
except ImportError:
    logging.warning("Could not import command_validation_util module. Some validation features will be limited.")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("command_validation")


def load_module_from_path(module_name: str, file_path: str) -> Any:
    """Load a Python module from a file path."""
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module from {file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.debug(f"Error loading module {module_name} from {file_path}: {e}")
        return None


def find_service_plugins() -> List[str]:
    """Find all service plugins in the Panther directory."""
    service_dirs = []
    
    # Base paths for service plugins
    base_paths = [
        os.path.join("panther", "plugins", "services", "testers"),
        os.path.join("panther", "plugins", "services", "iut")
    ]
    
    for base_path in base_paths:
        if not os.path.exists(base_path):
            logger.warning(f"Path {base_path} does not exist, skipping")
            continue
            
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    service_dirs.append(os.path.join(root, file))
    
    return service_dirs


def validate_plugin_commands(plugin_path: str) -> Tuple[bool, List[str]]:
    """Validate commands for a specific plugin."""
    try:
        # Extract module name from path
        module_name = os.path.splitext(os.path.basename(plugin_path))[0]
        
        # Load the module
        module = load_module_from_path(module_name, plugin_path)
        if module is None:
            return False, [f"Could not load module from {plugin_path}"]
        
        # Find service manager classes
        service_managers = []
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and 
                "ServiceManager" in name and 
                hasattr(obj, "generate_deployment_commands")):
                service_managers.append(obj)
        
        if not service_managers:
            return True, [f"No service manager found in {plugin_path}"]
        
        # Check each service manager
        issues = []
        for manager_class in service_managers:
            issues.extend(validate_service_manager(manager_class, plugin_path))
        
        return len(issues) == 0, issues
    
    except Exception as e:
        return False, [f"Error validating {plugin_path}: {str(e)}"]


def validate_service_manager(manager_class: Any, plugin_path: str) -> List[str]:
    """Validate a specific service manager class."""
    issues = []
    
    # Check if generate_deployment_commands uses structured arguments
    if hasattr(manager_class, "generate_deployment_commands"):
        try:
            source = inspect.getsource(manager_class.generate_deployment_commands)
            
            # Check for structured command patterns
            if "command_args" not in source:
                issues.append(f"{manager_class.__name__} in {plugin_path} does not use structured command_args")
            
            # Check for render_commands with structured args
            if "command_args=" not in source and "command_args =" not in source:
                issues.append(f"{manager_class.__name__} in {plugin_path} does not pass command_args to render_commands")
        except Exception as e:
            issues.append(f"Error examining source for {manager_class.__name__}: {e}")
    
    # Check template files if they exist
    template_dir = os.path.join(os.path.dirname(plugin_path), "templates")
    if os.path.exists(template_dir):
        for template_file in os.listdir(template_dir):
            if template_file.endswith(".jinja"):
                template_issues = validate_template_file(os.path.join(template_dir, template_file))
                issues.extend(template_issues)
    
    return issues


def validate_template_file(template_path: str) -> List[str]:
    """Validate a Jinja2 template file for structured command patterns."""
    issues = []
    
    try:
        with open(template_path, 'r') as f:
            content = f.read()
            
        # Check for proper quoting filters
        if "quote_shell" not in content and "|quote_shell" not in content:
            issues.append(f"Template {template_path} does not use quote_shell filter")
        
        # Check for structured command iteration
        if "for arg in command_args" not in content and "{% for arg in command_args %}" not in content:
            issues.append(f"Template {template_path} does not iterate over command_args")
            
    except Exception as e:
        issues.append(f"Error validating template {template_path}: {str(e)}")
    
    return issues


def main():
    parser = argparse.ArgumentParser(description="Validate command generation across Panther plugins")
    parser.add_argument("--plugin", help="Path to specific plugin to validate")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Find plugins to validate
    if args.plugin:
        plugin_paths = [args.plugin]
    else:
        logger.info("Searching for service plugins...")
        plugin_paths = find_service_plugins()
        logger.info(f"Found {len(plugin_paths)} service plugins")
    
    # Validate each plugin
    total_issues = 0
    passed = 0
    failed = 0
    
    for plugin_path in plugin_paths:
        try:
            is_valid, issues = validate_plugin_commands(plugin_path)
            
            if is_valid:
                logger.info(f"✅ {plugin_path} passes command generation validation")
                passed += 1
            else:
                logger.error(f"❌ {plugin_path} has command generation issues:")
                for issue in issues:
                    logger.error(f"  - {issue}")
                failed += 1
                total_issues += len(issues)
                
        except Exception as e:
            logger.error(f"Error validating {plugin_path}: {str(e)}")
            failed += 1
    
    # Summary
    logger.info(f"\nValidation complete: {passed} plugins passed, {failed} plugins failed with {total_issues} total issues")
    
    # Return non-zero exit code if any issues were found
    return 1 if total_issues > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
