#!/usr/bin/env python3
"""
MkDocs Config Enhancer

This script enhances the MkDocs configuration to include plugins for link checking,
ensuring that all links in the documentation are valid.
"""

import sys
from pathlib import Path
import yaml
import re
from typing import Dict, Any, List

# Repository root is two directories up from this script
REPO_ROOT = Path(__file__).parent.parent.resolve()
MKDOCS_CONFIG = REPO_ROOT / "mkdocs.yml"

# Create custom tag handlers for YAML
def python_name_constructor(loader, node):
    """Handle !!python/name tags by returning the name as string."""
    # Just return the module name or import path as a string
    return f"__python_name__{node.value}"

def python_name_with_args_constructor(loader, node):
    """Handle !!python/name tags with arguments."""
    # Extract module name and return it as a string
    module_name = node.tag.split(':', 1)[1] if ':' in node.tag else str(node.value)
    return f"__python_name__{module_name}"

def python_object_apply_constructor(loader, node):
    """Handle !!python/object/apply tags by returning a placeholder."""
    # For object/apply tags, return a placeholder that won't break YAML parsing
    return f"__python_object_apply__"

def python_module_constructor(loader, node):
    """Handle Python module references."""
    # For module imports, return a placeholder
    return f"__python_module__"

def setup_yaml_handlers():
    """Set up custom YAML tag handlers for MkDocs configuration."""
    # Standard Python object tags
    yaml.add_constructor('tag:yaml.org,2002:python/name', python_name_constructor, Loader=yaml.SafeLoader)
    yaml.add_constructor('tag:yaml.org,2002:python/object/apply', python_object_apply_constructor, Loader=yaml.SafeLoader)
    
    # PyMdown Extensions specific tags
    yaml.add_constructor('tag:yaml.org,2002:python/name:pymdownx.emoji.gemoji', python_name_with_args_constructor, Loader=yaml.SafeLoader)
    yaml.add_constructor('tag:yaml.org,2002:python/name:pymdownx.emoji.twemoji', python_name_with_args_constructor, Loader=yaml.SafeLoader)
    yaml.add_constructor('tag:yaml.org,2002:python/name:pymdownx.emoji.emojione', python_name_with_args_constructor, Loader=yaml.SafeLoader)
    yaml.add_constructor('tag:yaml.org,2002:python/name:pymdownx.superfences.fence_code_format', python_name_with_args_constructor, Loader=yaml.SafeLoader)
    yaml.add_constructor('tag:yaml.org,2002:python/name:pymdownx.slugs.slugify', python_name_with_args_constructor, Loader=yaml.SafeLoader)
    yaml.add_constructor('tag:yaml.org,2002:python/object/apply:pymdownx.slugs.slugify', python_object_apply_constructor, Loader=yaml.SafeLoader)
    
    # Any other Python-related tags
    yaml.add_multi_constructor('tag:yaml.org,2002:python/', python_module_constructor, Loader=yaml.SafeLoader)

def load_mkdocs_config() -> Dict[str, Any]:
    """Load the current mkdocs.yml configuration."""
    try:
        # First try to load with custom tag handlers
        setup_yaml_handlers()
        
        try:
            # Try direct loading with custom handlers
            with open(MKDOCS_CONFIG, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            if config:
                return config
        except yaml.YAMLError as yaml_err:
            print(f"YAML parsing error: {yaml_err}")
            # If that fails, try the regex replacement approach
            with open(MKDOCS_CONFIG, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Replace Python tags with strings
            content = re.sub(r'!!python/name:([^\s]+)', r'"\1"', content)
            content = re.sub(r'!!python/object/apply:([^\s]+)', r'"\1"', content)
                
            # Now safely load the modified content
            config = yaml.safe_load(content)
            if config:
                return config
            else:
                print("Failed to parse YAML after tag replacement")
    except Exception as e:
        print(f"Error loading {MKDOCS_CONFIG}: {e}")
        print(f"could not determine a constructor for pymdownx tags")
        print(f"This error often occurs with pymdownx extensions. Check your mkdocs.yml file.")
        return {}


def save_mkdocs_config(config: Dict[str, Any]) -> bool:
    """Save the updated mkdocs.yml configuration."""
    try:
        with open(MKDOCS_CONFIG, 'w', encoding='utf-8') as file:
            yaml.dump(config, file, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        print(f"Error saving {MKDOCS_CONFIG}: {e}")
        return False

def ensure_plugins_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure the MkDocs configuration has the necessary plugins for link checking.
    """
    # Initialize plugins section if it doesn't exist
    if 'plugins' not in config:
        config['plugins'] = []
    
    # Convert to list of dicts if it's not already
    if isinstance(config['plugins'], list):
        plugins_list = config['plugins']
    else:
        plugins_list = [config['plugins']]
        config['plugins'] = plugins_list
    
    # Find existing plugins by name
    plugin_names = []
    for plugin in plugins_list:
        if isinstance(plugin, str):
            plugin_names.append(plugin)
        elif isinstance(plugin, dict):
            plugin_names.extend(plugin.keys())
    
    # Add search plugin if not present
    if 'search' not in plugin_names:
        plugins_list.append('search')
    
    # Add mkdocstrings plugin if not present
    if 'mkdocstrings' not in plugin_names:
        mkdocstrings_config = {
            'mkdocstrings': {
                'handlers': {
                    'python': {
                        'options': {
                            'show_source': True,
                            'show_root_heading': True,
                            'show_category_heading': True,
                        }
                    }
                }
            }
        }
        plugins_list.append(mkdocstrings_config)
    
    # Add material plugins if not present
    material_plugins = ['navigation.instant', 'navigation.tracking', 'search.highlight', 'search.share']
    if 'material' not in plugin_names:
        for plugin in material_plugins:
            if plugin not in plugin_names:
                plugins_list.append(plugin)
    
    # Add link-check plugin if not present
    if 'link-check' not in plugin_names:
        link_check_config = {
            'link-check': {
                'timeout': 5,
                'retry_times': 2,
                'exclude': [
                    r'^https://github\.com/.*#.*$',  # Skip GitHub anchor links (often 404 but work)
                ]
            }
        }
        plugins_list.append(link_check_config)
    
    return config

def main():
    """Main entry point of the script."""
    print("🔄 MkDocs Config Enhancer")
    print("=" * 50)
    
    # Load the current configuration
    config = load_mkdocs_config()
    if not config:
        print("❌ Failed to load MkDocs configuration")
        return 1
    
    # Ensure plugins are configured
    config = ensure_plugins_config(config)
    
    # Save the updated configuration
    if save_mkdocs_config(config):
        print("✅ MkDocs configuration updated successfully")
        return 0
    else:
        print("❌ Failed to update MkDocs configuration")
        return 1

if __name__ == "__main__":
    sys.exit(main())
