#!/usr/bin/env python3
"""
MkDocs Navigation Updater

This script updates the navigation structure in mkdocs.yml to include all
Markdown files in the project, organized in a logical hierarchy.
"""

import os
import re
import sys
from pathlib import Path
import yaml
from typing import Dict, List, Any, Optional, Set, Tuple

# Repository root is two directories up from this script
REPO_ROOT = Path(__file__).parent.parent.resolve()
MKDOCS_CONFIG = REPO_ROOT / "mkdocs.yml"

# Create custom tag handlers for YAML
def python_name_constructor(loader, node):
    """Handle !!python/name tags by returning the name as string."""
    return str(node.value)

def python_object_apply_constructor(loader, node):
    """Handle !!python/object/apply tags by returning a placeholder."""
    return f"PYTHON_OBJECT_{node.tag}"

def setup_yaml_handlers():
    """Set up custom YAML tag handlers for MkDocs configuration."""
    yaml.add_constructor('tag:yaml.org,2002:python/name', python_name_constructor, Loader=yaml.SafeLoader)
    yaml.add_constructor('!!python/name', python_name_constructor, Loader=yaml.SafeLoader)
    yaml.add_constructor('tag:yaml.org,2002:python/object/apply', python_object_apply_constructor, Loader=yaml.SafeLoader)
    yaml.add_constructor('!!python/object/apply', python_object_apply_constructor, Loader=yaml.SafeLoader)

# Default sections for organizing documentation
DEFAULT_SECTIONS = {
    "Home": ["README.md", "home.md", "index.md"],
    "Installation": ["INSTALL.md", "installation.md", "setup.md"],
    "Quick Start": ["quick_start.md", "quickstart.md", "getting_started.md"],
    "User Guide": [],  # Will be populated with user-facing documentation
    "Plugin System": [],  # Will be populated with plugin documentation
    "Development": ["CONTRIBUTING.md", "development.md", "DEV_GUIDE.md", "style_guide.md"],
    "API Reference": [],  # Will be populated with API reference documentation
    "Additional Documentation": ["CHANGELOG.md", "PACKAGING.md", "TODO.md", "workflow.md"],
}

# Special handling for plugin directories
PLUGIN_CATEGORIES = {
    "services": "Service Plugins",
    "protocols": "Protocol Plugins",
    "environments": "Environment Plugins",
}


def load_mkdocs_config() -> Dict:
    """Load the current mkdocs.yml configuration."""
    try:
        # Set up custom YAML tag handlers
        setup_yaml_handlers()
        
        # Try loading with custom handlers
        with open(MKDOCS_CONFIG, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
            if config:
                return config
    except yaml.YAMLError as e:
        print(f"YAML parsing error in {MKDOCS_CONFIG}: {e}")
        
        try:
            # If that fails, try a more permissive approach by replacing Python tags
            with open(MKDOCS_CONFIG, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Replace Python tags with strings
            import re
            content = re.sub(r'!!python/name:([^\s]+)', r'"\1"', content)
            content = re.sub(r'!!python/object/apply:([^\s]+)', r'"\1"', content) 
                
            # Now safely load the modified content
            config = yaml.safe_load(content)
            if config:
                return config
        except Exception as e2:
            print(f"Alternative parsing failed: {e2}")
    except Exception as e:
        print(f"Error loading {MKDOCS_CONFIG}: {e}")
    
    print(f"could not determine a constructor for the tag 'tag:yaml.org,2002:python/name'")
    print(f"This error often occurs with pymdownx extensions. Check your mkdocs.yml file.")
    return {}


def save_mkdocs_config(config: Dict) -> bool:
    """Save the updated mkdocs.yml configuration."""
    try:
        with open(MKDOCS_CONFIG, 'w', encoding='utf-8') as file:
            yaml.dump(config, file, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        print(f"Error saving {MKDOCS_CONFIG}: {e}")
        return False


def find_markdown_files() -> List[Path]:
    """Find all Markdown files in the project."""
    # Exclude node_modules, venv, and other directories that should be ignored
    ignore_patterns = [
            "**/node_modules/**", "**/.git/**", "**/.venv*/**", "**/venv*/**",
            "**/build/**", "**/dist/**", "**/__pycache__/**", "**/submodules/**", 
            "**/.venv-10/**", "**/site-packages/**", "**/templates/**",
            ".venv-*/**", "**/licenses/**", "**/panther_ivy/submodules/**",
            "**/panther_ivy/test/**", "**/panther_ivy/ivy/**",
            "**/panther_ivy/doc/**", 
            "**/panther_ivy/examples/**", 
        ]
    
    # Start with an empty list of files
    markdown_files = []
    
    # Walk through the directory
    for path in REPO_ROOT.rglob("*.md"):
        # Check if path matches any ignore pattern
        if not any(path.match(pattern) for pattern in ignore_patterns):
            markdown_files.append(path)
    
    print(f"Found {len(markdown_files)} Markdown files")
    return markdown_files


def get_current_nav_entries(config: Dict) -> Set[str]:
    """Get all entries currently in the navigation."""
    entries = set()
    
    def extract_entries(nav_item):
        if isinstance(nav_item, dict):
            for title, content in nav_item.items():
                if isinstance(content, str):
                    entries.add(content)
                elif isinstance(content, list):
                    for item in content:
                        extract_entries(item)
        elif isinstance(nav_item, str):
            entries.add(nav_item)
    
    if "nav" in config:
        for item in config["nav"]:
            extract_entries(item)
    
    return entries


def group_files_by_directory(files: List[Path]) -> Dict[str, List[Path]]:
    """Group Markdown files by directory."""
    grouped = {}
    
    for file in files:
        rel_path = file.relative_to(REPO_ROOT)
        directory = str(rel_path.parent)
        if directory == ".":
            directory = "root"
        
        if directory not in grouped:
            grouped[directory] = []
        grouped[directory].append(file)
    
    return grouped


def get_title_from_markdown(file_path: Path) -> str:
    """Extract title from the first heading in a Markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                # Look for a level 1 heading (# Title)
                match = re.match(r'^#\s+(.+)$', line.strip())
                if match:
                    return match.group(1)
        
        # If no heading found, use the filename without extension
        return file_path.stem.replace('_', ' ').title()
    except Exception:
        # Default to filename if file can't be read
        return file_path.stem.replace('_', ' ').title()


def build_plugin_nav(markdown_files: List[Path]) -> Dict:
    """Build the navigation structure for plugins."""
    plugins_nav = {}
    
    # Identify plugin categories
    for category, title in PLUGIN_CATEGORIES.items():
        category_files = [f for f in markdown_files if f'plugins/{category}/' in str(f)]
        
        if category_files:
            # Sort files by directory depth to handle README files first
            category_files.sort(key=lambda f: (len(str(f).split('/')), str(f)))
            
            # Create category entry if not exists
            if title not in plugins_nav:
                plugins_nav[title] = []
            
            # Group by subcategory
            subcategories = {}
            general_files = []
            
            for file in category_files:
                rel_path = str(file.relative_to(REPO_ROOT))
                parts = rel_path.split('/')
                
                # Handle top-level README for the plugin category
                if parts[-1] == 'README.md' and len(parts) == 3:  # plugins/category/README.md
                    general_files.append({
                        'Overview': rel_path
                    })
                # Handle development.md for the plugin category
                elif parts[-1] == 'development.md' and len(parts) == 3:  # plugins/category/development.md
                    general_files.append({
                        'Development': rel_path
                    })
                # Handle subcategory files
                elif len(parts) > 3:
                    subcategory = parts[3]  # plugins/category/subcategory/...
                    
                    if subcategory not in subcategories:
                        subcategories[subcategory] = []
                    
                    if parts[-1] == 'README.md' or parts[-1] == 'index.md':
                        subcategories[subcategory].insert(0, {
                            'Overview': rel_path
                        })
                    else:
                        file_title = get_title_from_markdown(file)
                        subcategories[subcategory].append({
                            file_title: rel_path
                        })
            
            # Add general files first
            plugins_nav[title].extend(general_files)
            
            # Add subcategories
            for subcategory, files in sorted(subcategories.items()):
                plugins_nav[title].append({
                    subcategory.replace('_', ' ').title(): files
                })
    
    return plugins_nav


def build_updated_nav(markdown_files: List[Path], current_config: Dict) -> List:
    """Build updated navigation structure based on available files."""
    # Get currently included files
    current_entries = get_current_nav_entries(current_config)
    
    # Get files grouped by directory
    grouped_files = group_files_by_directory(markdown_files)
    
    # Start with empty navigation
    nav = []
    
    # Build plugin navigation first (it's more structured)
    plugin_nav = build_plugin_nav(markdown_files)
    
    # Process root files and organize them by section
    root_files = grouped_files.get("root", [])
    section_entries = {section: [] for section in DEFAULT_SECTIONS}
    
    for file in root_files:
        rel_path = str(file.relative_to(REPO_ROOT))
        file_title = get_title_from_markdown(file)
        
        # Determine which section this file belongs to
        assigned = False
        for section, patterns in DEFAULT_SECTIONS.items():
            for pattern in patterns:
                if rel_path.lower() == pattern.lower() or file.name.lower() == pattern.lower():
                    section_entries[section].append({file_title: rel_path})
                    assigned = True
                    break
            if assigned:
                break
        
        # If not assigned to any specific section, put in "Additional Documentation"
        if not assigned:
            section_entries["Additional Documentation"].append({file_title: rel_path})
    
    # Build the navigation structure
    for section, entries in section_entries.items():
        if entries:
            # For single-entry sections with default files, simplify
            if len(entries) == 1 and section in ["Home", "Quick Start"]:
                nav.append({section: list(entries[0].values())[0]})
            else:
                nav.append({section: entries})
    
    # Add the plugin navigation
    plugin_section_added = False
    for title, entries in plugin_nav.items():
        if entries:
            if not plugin_section_added:
                nav.append({"Plugin System": []})
                plugin_section_added = True
            
            plugin_index = next((i for i, item in enumerate(nav) if "Plugin System" in item), -1)
            if plugin_index >= 0:
                nav[plugin_index]["Plugin System"].append({title: entries})
    
    # Add API Reference placeholder if it exists in the current config
    if any("API Reference" in item for item in current_config.get("nav", [])):
        api_section_found = False
        for item in nav:
            if "API Reference" in item:
                api_section_found = True
                break
        
        if not api_section_found:
            # Find the API Reference section in the current config and preserve it
            for item in current_config["nav"]:
                if isinstance(item, dict) and "API Reference" in item:
                    nav.append({"API Reference": item["API Reference"]})
                    break
    
    return nav


def deduplicate_nav(nav: List) -> List:
    """Remove duplicate entries from navigation."""
    seen = set()
    result = []
    
    def process_item(item):
        if isinstance(item, dict):
            processed_dict = {}
            for title, content in item.items():
                if isinstance(content, str):
                    if content not in seen:
                        seen.add(content)
                        processed_dict[title] = content
                elif isinstance(content, list):
                    processed_list = []
                    for sub_item in content:
                        processed_sub = process_item(sub_item)
                        if processed_sub:
                            processed_list.append(processed_sub)
                    if processed_list:
                        processed_dict[title] = processed_list
            return processed_dict if processed_dict else None
        elif isinstance(item, str):
            if item not in seen:
                seen.add(item)
                return item
            return None
        return item
    
    for item in nav:
        processed = process_item(item)
        if processed:
            result.append(processed)
    
    return result


def main():
    """Main entry point of the script."""
    print("🔄 MkDocs Navigation Updater")
    print("=" * 50)
    
    # Load current config
    config = load_mkdocs_config()
    if not config:
        print("❌ Failed to load MkDocs configuration")
        sys.exit(1)
    
    # Make a backup of the current configuration
    backup_path = MKDOCS_CONFIG.with_suffix('.yml.backup')
    try:
        with open(backup_path, 'w', encoding='utf-8') as backup_file:
            yaml.dump(config, backup_file, default_flow_style=False)
        print(f"✅ Backup saved to {backup_path}")
    except Exception as e:
        print(f"⚠️ Failed to create backup: {e}")
    
    # Find all Markdown files
    markdown_files = find_markdown_files()
    
    # Build updated navigation
    updated_nav = build_updated_nav(markdown_files, config)
    
    # Deduplicate navigation entries
    updated_nav = deduplicate_nav(updated_nav)
    
    # Update the configuration
    config['nav'] = updated_nav
    
    # Save the updated configuration
    if save_mkdocs_config(config):
        print("✅ MkDocs navigation updated successfully")
    else:
        print("❌ Failed to update MkDocs navigation")
        sys.exit(1)
    
    print("\nRun 'mkdocs build --strict' to verify the updated configuration.")


if __name__ == "__main__":
    main()
