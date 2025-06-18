#!/usr/bin/env python3
"""
Migration script to transition from hardcoded plugin configs to dynamic discovery.

This script helps identify and update code that imports plugin-specific configs
from core models, replacing them with dynamic resolution.
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Set, Tuple

# Plugin configs that need to be migrated
PLUGIN_CONFIGS = {
    'StraceConfig',
    'GperfCpuConfig', 
    'GperfHeapConfig',
    'MemcheckConfig',
    'HelgrindConfig',
    'IterationsConfig',
    'DockerComposeConfig',
    'LocalhostSingleContainerConfig',
    'ShadowNsConfig'
}

# Mapping of old imports to new plugin paths
CONFIG_MAPPING = {
    'StraceConfig': 'panther.plugins.environments.execution_environment.strace.config_schema',
    'GperfCpuConfig': 'panther.plugins.environments.execution_environment.gperf_cpu.config_schema',
    'GperfHeapConfig': 'panther.plugins.environments.execution_environment.gperf_heap.config_schema',
    'MemcheckConfig': 'panther.plugins.environments.execution_environment.memcheck.config_schema',
    'HelgrindConfig': 'panther.plugins.environments.execution_environment.helgrind.config_schema',
    'IterationsConfig': 'panther.plugins.environments.execution_environment.iterations.config_schema',
    'DockerComposeConfig': 'panther.plugins.environments.network_environment.docker_compose.config_schema',
    'LocalhostSingleContainerConfig': 'panther.plugins.environments.network_environment.localhost_single_container.config_schema',
    'ShadowNsConfig': 'panther.plugins.environments.network_environment.shadow_ns.config_schema'
}


class ImportVisitor(ast.NodeVisitor):
    """AST visitor to find imports of plugin configs from core models."""
    
    def __init__(self):
        self.core_imports: List[Tuple[int, str]] = []
        self.plugin_imports: List[Tuple[int, str]] = []
        
    def visit_ImportFrom(self, node):
        if node.module and 'panther.config.core.models' in node.module:
            for alias in node.names:
                if alias.name in PLUGIN_CONFIGS:
                    self.core_imports.append((node.lineno, alias.name))
        elif node.module and 'config_schema' in node.module:
            for alias in node.names:
                if alias.name in PLUGIN_CONFIGS:
                    self.plugin_imports.append((node.lineno, alias.name))
        self.generic_visit(node)


def find_files_with_imports(root_dir: Path) -> List[Tuple[Path, List[Tuple[int, str]]]]:
    """Find all Python files that import plugin configs from core models."""
    files_with_imports = []
    
    for py_file in root_dir.rglob("*.py"):
        # Skip migration script and test files
        if 'migrate_to_dynamic' in str(py_file) or '__pycache__' in str(py_file):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
            tree = ast.parse(content)
            visitor = ImportVisitor()
            visitor.visit(tree)
            
            if visitor.core_imports:
                files_with_imports.append((py_file, visitor.core_imports))
                
        except Exception as e:
            print(f"Error processing {py_file}: {e}")
            
    return files_with_imports


def generate_migration_report(files: List[Tuple[Path, List[Tuple[int, str]]]]) -> str:
    """Generate a report of files that need migration."""
    report = ["# Plugin Config Migration Report\n"]
    report.append(f"Found {len(files)} files importing plugin configs from core models:\n")
    
    for file_path, imports in files:
        report.append(f"\n## {file_path}")
        for line_no, config_name in imports:
            report.append(f"  - Line {line_no}: {config_name}")
            if config_name in CONFIG_MAPPING:
                report.append(f"    → Should import from: {CONFIG_MAPPING[config_name]}")
                
    return "\n".join(report)


def check_duplicates(root_dir: Path) -> List[Tuple[str, List[Path]]]:
    """Find duplicate config class definitions."""
    config_definitions = {}
    
    for py_file in root_dir.rglob("*.py"):
        if '__pycache__' in str(py_file):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
            # Find class definitions
            for config_name in PLUGIN_CONFIGS:
                pattern = rf'class\s+{config_name}\s*\('
                if re.search(pattern, content):
                    if config_name not in config_definitions:
                        config_definitions[config_name] = []
                    config_definitions[config_name].append(py_file)
                    
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
            
    # Find duplicates
    duplicates = []
    for config_name, paths in config_definitions.items():
        if len(paths) > 1:
            duplicates.append((config_name, paths))
            
    return duplicates


def main():
    """Run the migration analysis."""
    # Get PANTHER root directory
    panther_root = Path(__file__).parent.parent.parent
    
    print("Analyzing PANTHER codebase for plugin config imports...")
    
    # Find files with core model imports
    files_with_imports = find_files_with_imports(panther_root)
    
    # Check for duplicate definitions
    duplicates = check_duplicates(panther_root)
    
    # Generate report
    report = generate_migration_report(files_with_imports)
    
    # Add duplicate report
    if duplicates:
        report += "\n\n# Duplicate Config Definitions Found\n"
        for config_name, paths in duplicates:
            report += f"\n## {config_name} defined in multiple locations:"
            for path in paths:
                report += f"\n  - {path}"
                
    # Save report
    report_path = panther_root / "dev" / "PLUGIN_CONFIG_MIGRATION_REPORT.md"
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(report)
        
    print(f"\nMigration report saved to: {report_path}")
    
    # Print summary
    print(f"\nSummary:")
    print(f"- Files needing migration: {len(files_with_imports)}")
    print(f"- Duplicate config definitions: {len(duplicates)}")
    
    if duplicates:
        print("\nDuplicate configs found:")
        for config_name, paths in duplicates:
            print(f"  - {config_name}: {len(paths)} definitions")


if __name__ == "__main__":
    main()