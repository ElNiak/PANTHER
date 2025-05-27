#!/usr/bin/env python3
# filepath: /Users/elniak/Documents/Project/PANTHER/docs-gen/generate_plugin_inventory.py

"""
Plugin Inventory Generator

This script walks through the PANTHER plugin directories and generates
an inventory of all plugins, their types, and paths. It can also
identify plugins without proper documentation.
"""

import os
import sys
import json
from pathlib import Path
import argparse

def is_plugin_directory(path):
    """
    Check if a directory is likely a plugin directory.
    
    Args:
        path: Directory path to check
    
    Returns:
        bool: True if the directory appears to be a plugin
    """
    if not path.is_dir():
        return False
    
    # Plugins typically have these files
    plugin_indicators = ['plugin.py', '__init__.py']
    
    return any(Path(path / indicator).exists() for indicator in plugin_indicators)

def has_documentation(path):
    """
    Check if a plugin directory has proper documentation.
    
    Args:
        path: Plugin directory path
    
    Returns:
        bool: True if documentation exists
    """
    return Path(path / 'README.md').exists()

def generate_plugin_inventory(plugin_root, output_format='text'):
    """
    Generate an inventory of all plugins in the plugin directory.
    
    Args:
        plugin_root: Root directory of plugins
        output_format: Output format ('text', 'json', or 'markdown')
    
    Returns:
        dict: Plugin inventory data
    """
    plugin_root = Path(plugin_root)
    if not plugin_root.exists():
        print(f"Error: Plugin root directory not found: {plugin_root}")
        sys.exit(1)
        
    inventory = {
        'environments': {
            'execution_environment': [],
            'network_environment': []
        },
        'protocols': {
            'client_server': [],
            'peer_to_peer': []
        },
        'services': {
            'iut': [],
            'testers': []
        }
    }
    
    missing_docs = []
    
    # Scan environment plugins
    env_path = plugin_root / 'environments'
    if env_path.exists():
        for env_type in ['execution_environment', 'network_environment']:
            type_path = env_path / env_type
            if type_path.exists():
                for plugin_dir in type_path.iterdir():
                    if is_plugin_directory(plugin_dir):
                        plugin_info = {
                            'name': plugin_dir.name,
                            'path': str(plugin_dir.relative_to(plugin_root)),
                            'has_docs': has_documentation(plugin_dir)
                        }
                        inventory['environments'][env_type].append(plugin_info)
                        
                        if not plugin_info['has_docs']:
                            missing_docs.append(plugin_info['path'])
    
    # Scan protocol plugins
    proto_path = plugin_root / 'protocols'
    if proto_path.exists():
        for proto_type in ['client_server', 'peer_to_peer']:
            type_path = proto_path / proto_type
            if type_path.exists():
                for plugin_dir in type_path.iterdir():
                    if is_plugin_directory(plugin_dir):
                        plugin_info = {
                            'name': plugin_dir.name,
                            'path': str(plugin_dir.relative_to(plugin_root)),
                            'has_docs': has_documentation(plugin_dir)
                        }
                        inventory['protocols'][proto_type].append(plugin_info)
                        
                        if not plugin_info['has_docs']:
                            missing_docs.append(plugin_info['path'])
    
    # Scan service plugins
    service_path = plugin_root / 'services'
    if service_path.exists():
        for service_type in ['iut', 'testers']:
            type_path = service_path / service_type
            if type_path.exists():
                for plugin_dir in type_path.iterdir():
                    if is_plugin_directory(plugin_dir):
                        plugin_info = {
                            'name': plugin_dir.name,
                            'path': str(plugin_dir.relative_to(plugin_root)),
                            'has_docs': has_documentation(plugin_dir)
                        }
                        inventory['services'][service_type].append(plugin_info)
                        
                        if not plugin_info['has_docs']:
                            missing_docs.append(plugin_info['path'])
    
    # Output inventory in the requested format
    if output_format == 'json':
        print(json.dumps(inventory, indent=2))
    elif output_format == 'markdown':
        output_markdown(inventory, missing_docs)
    else:  # text format
        output_text(inventory, missing_docs)
        
    return inventory, missing_docs

def output_text(inventory, missing_docs):
    """Output inventory in plain text format."""
    print("PANTHER Plugin Inventory")
    print("=======================")
    
    for category, subcategories in inventory.items():
        print(f"\n{category.upper()}")
        for subcategory, plugins in subcategories.items():
            print(f"  {subcategory}:")
            for plugin in plugins:
                doc_status = "✓" if plugin['has_docs'] else "✗"
                print(f"    - {plugin['name']} ({plugin['path']}) [{doc_status}]")
    
    if missing_docs:
        print("\nPlugins missing documentation:")
        for path in missing_docs:
            print(f"  - {path}")

def output_markdown(inventory, missing_docs):
    """Output inventory in markdown format."""
    print("# PANTHER Plugin Inventory\n")
    
    for category, subcategories in inventory.items():
        print(f"## {category.title()}\n")
        for subcategory, plugins in subcategories.items():
            print(f"### {subcategory.replace('_', ' ').title()}\n")
            
            print("| Plugin | Path | Documentation |")
            print("|--------|------|---------------|")
            for plugin in plugins:
                doc_status = "✅" if plugin['has_docs'] else "❌"
                print(f"| {plugin['name']} | `{plugin['path']}` | {doc_status} |")
            print()
    
    if missing_docs:
        print("## Plugins Missing Documentation\n")
        for path in missing_docs:
            print(f"- `{path}`")

def main():
    parser = argparse.ArgumentParser(description='Generate PANTHER plugin inventory')
    parser.add_argument('--root', default='panther/plugins', help='Root directory of plugins')
    parser.add_argument('--format', choices=['text', 'json', 'markdown'], default='text',
                       help='Output format (text, json, or markdown)')
    parser.add_argument('--output', help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    if args.output:
        # Redirect stdout to the output file
        sys.stdout = open(args.output, 'w')
    
    generate_plugin_inventory(args.root, args.format)
    
    if args.output:
        sys.stdout.close()

if __name__ == '__main__':
    main()
