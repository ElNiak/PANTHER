#!/usr/bin/env python3
"""
Script to identify execution environment configs that need migration from dataclass to Pydantic.
"""

import os
from pathlib import Path


def analyze_config_files():
    """Analyze config files in execution environment plugins."""
    exec_env_dir = Path("panther/plugins/environments/execution_environment")
    
    print("Analyzing Execution Environment Config Files")
    print("=" * 60)
    
    issues = []
    
    for plugin_dir in exec_env_dir.iterdir():
        if not plugin_dir.is_dir() or plugin_dir.name.startswith('_'):
            continue
            
        config_file = plugin_dir / "config_schema.py"
        if not config_file.exists():
            continue
            
        with open(config_file, 'r') as f:
            content = f.read()
            
        # Check for issues
        uses_dataclass = "@dataclass" in content
        imports_runtime_config = "from panther.config.core.models import" in content and "ExecutionEnvironmentConfig" in content
        imports_plugin_config = "from panther.config.core.models.plugin import" in content
        
        if uses_dataclass or imports_runtime_config:
            issues.append({
                'plugin': plugin_dir.name,
                'file': str(config_file),
                'uses_dataclass': uses_dataclass,
                'imports_runtime_config': imports_runtime_config,
                'imports_plugin_config': imports_plugin_config
            })
            
    # Report findings
    if issues:
        print(f"\nFound {len(issues)} config files that need migration:\n")
        for issue in issues:
            print(f"Plugin: {issue['plugin']}")
            print(f"  File: {issue['file']}")
            if issue['uses_dataclass']:
                print("  ✗ Uses @dataclass (should use Pydantic)")
            if issue['imports_runtime_config']:
                print("  ✗ Imports ExecutionEnvironmentConfig from runtime models")
                print("    (should import ExecutionEnvironmentPluginConfig from plugin models)")
            print()
    else:
        print("\nAll execution environment configs are properly configured!")
        
    return issues


def generate_migration_commands(issues):
    """Generate commands to help with migration."""
    if not issues:
        return
        
    print("\nMigration Steps:")
    print("-" * 60)
    
    for issue in issues:
        plugin = issue['plugin']
        print(f"\nFor {plugin}:")
        print(f"1. Convert from dataclass to Pydantic BaseModel")
        print(f"2. Change inheritance from ExecutionEnvironmentConfig to ExecutionEnvironmentPluginConfig")
        print(f"3. Update imports:")
        print(f"   FROM: from panther.config.core.models import ExecutionEnvironmentConfig")
        print(f"   TO:   from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig")
        print(f"4. Convert dataclass fields to Pydantic Field() descriptors")
        
    print("\nExample migration:")
    print("-" * 60)
    print("""
# Before (dataclass):
from dataclasses import dataclass
from panther.config.core.models import ExecutionEnvironmentConfig

@dataclass
class MyPluginConfig(ExecutionEnvironmentConfig):
    my_field: str = "default"
    
# After (Pydantic):
from pydantic import Field
from panther.config.core.models.plugin import ExecutionEnvironmentPluginConfig

class MyPluginConfig(ExecutionEnvironmentPluginConfig):
    my_field: str = Field(
        default="default",
        description="Description of my field"
    )
""")


if __name__ == "__main__":
    issues = analyze_config_files()
    generate_migration_commands(issues)