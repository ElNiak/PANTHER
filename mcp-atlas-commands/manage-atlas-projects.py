#!/usr/bin/env python3
"""
ATLAS MCP Project Configuration Manager

This script provides an easy way to manage multi-project ATLAS MCP configurations
while maintaining DRY, SOLID, and KISS principles.

Usage:
    python manage-atlas-projects.py add panther /path/to/panther --type fast
    python manage-atlas-projects.py list
    python manage-atlas-projects.py remove panther
    python manage-atlas-projects.py generate
    python manage-atlas-projects.py status
"""

import json
import os
import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


class AtlasProjectManager:
    """Manages ATLAS MCP project configurations with DRY principles."""
    
    def __init__(self, config_file: str = "atlas-project-config.json"):
        self.config_file = Path(config_file)
        self.cache_root = Path.home() / ".atlas-cache"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load project configuration or create default."""
        if self.config_file.exists():
            try:
                return json.loads(self.config_file.read_text())
            except json.JSONDecodeError as e:
                print(f"Error loading config: {e}")
                return self._create_default_config()
        
        return self._create_default_config()
    
    def _create_default_config(self) -> Dict:
        """Create default configuration structure."""
        return {
            "projects": {},
            "global_settings": {
                "cache_root": str(self.cache_root),
                "shared_models": True,
                "max_concurrent_containers": 5,
                "health_check_interval": 30,
                "default_container_type": "fast",
                "default_log_level": "INFO"
            }
        }
    
    def _save_config(self):
        """Save configuration to file."""
        self.config_file.write_text(json.dumps(self.config, indent=2))
        print(f"✓ Configuration saved to {self.config_file}")
    
    def add_project(self, name: str, path: str, container_type: str = "fast", 
                   profile: str = "full", tools: List[str] = None) -> bool:
        """Add new project to configuration."""
        # Validate project path
        project_path = Path(path).resolve()
        if not project_path.exists():
            print(f"❌ Error: Project path does not exist: {path}")
            return False
        
        # Default tools if not specified
        if tools is None:
            tools = ["task_management", "memory_management", "workflow_intelligence", "embeddings"]
        
        # Create project configuration
        project_config = {
            "path": str(project_path),
            "container_type": container_type,
            "profile": profile,
            "tools_enabled": tools,
            "cache_strategy": "project_isolated",
            "log_level": self.config["global_settings"]["default_log_level"],
            "workspace_isolation": True,
            "created_at": self._get_timestamp(),
            "last_updated": self._get_timestamp()
        }
        
        # Add to configuration
        self.config["projects"][name] = project_config
        self._save_config()
        
        print(f"✅ Added project: {name}")
        print(f"   Path: {project_path}")
        print(f"   Container: {container_type}")
        print(f"   Tools: {', '.join(tools)}")
        
        return True
    
    def remove_project(self, name: str) -> bool:
        """Remove project from configuration."""
        if name not in self.config["projects"]:
            print(f"❌ Error: Project not found: {name}")
            return False
        
        # Remove from configuration
        del self.config["projects"][name]
        self._save_config()
        
        # Clean up project files
        mcp_config_file = Path(f".mcp.{name}.json")
        if mcp_config_file.exists():
            mcp_config_file.unlink()
            print(f"✓ Removed MCP config: {mcp_config_file}")
        
        # Ask about cache cleanup
        cache_dir = self.cache_root / name
        if cache_dir.exists():
            response = input(f"Remove cache directory {cache_dir}? [y/N]: ")
            if response.lower() in ['y', 'yes']:
                subprocess.run(['rm', '-rf', str(cache_dir)])
                print(f"✓ Removed cache directory: {cache_dir}")
        
        print(f"✅ Removed project: {name}")
        return True
    
    def list_projects(self):
        """List all configured projects."""
        projects = self.config["projects"]
        
        if not projects:
            print("ℹ️ No projects configured")
            return
        
        print("📋 Configured Projects:")
        print("=" * 80)
        
        for name, config in projects.items():
            status = self._check_project_status(name, config)
            status_icon = "✅" if status["complete"] else "⚠️"
            
            print(f"{status_icon} {name}")
            print(f"   Path: {config['path']}")
            print(f"   Container: {config['container_type']}")
            print(f"   Tools: {', '.join(config['tools_enabled'])}")
            print(f"   Isolation: {config.get('workspace_isolation', False)}")
            
            if not status["complete"]:
                print(f"   Issues: {', '.join(status['issues'])}")
            
            print()
    
    def _check_project_status(self, name: str, config: Dict) -> Dict:
        """Check if project is properly configured."""
        issues = []
        
        # Check project path exists
        if not Path(config["path"]).exists():
            issues.append("path missing")
        
        # Check MCP config exists
        mcp_file = Path(f".mcp.{name}.json")
        if not mcp_file.exists():
            issues.append("MCP config missing")
        
        # Check cache directory exists
        cache_dir = self.cache_root / name
        if not cache_dir.exists():
            issues.append("cache directory missing")
        
        return {
            "complete": len(issues) == 0,
            "issues": issues
        }
    
    def generate_mcp_configs(self):
        """Generate MCP configuration files for all projects."""
        generated_count = 0
        
        for name, project_config in self.config["projects"].items():
            if self._generate_project_mcp_config(name, project_config):
                generated_count += 1
        
        print(f"✅ Generated {generated_count} MCP configuration files")
    
    def _generate_project_mcp_config(self, name: str, config: Dict) -> bool:
        """Generate MCP configuration for single project."""
        try:
            # Create project cache directory
            project_cache_dir = self.cache_root / name
            project_cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            for subdir in ["memory", "tasks", "cache", "logs", "artifacts", "backups"]:
                (project_cache_dir / subdir).mkdir(exist_ok=True)
            
            # Generate MCP configuration
            mcp_config = {
                "mcpServers": {
                    f"atlas-{name}": {
                        "command": "docker",
                        "args": [
                            "run", "-i", "--rm",
                            "--name", f"atlas-{name}",
                            "-v", f"{config['path']}:/app/workspace",
                            "-v", f"{project_cache_dir}:/app/cache",
                            "-v", f"{self.cache_root}/shared:/app/shared:ro",
                            "-e", f"ATLAS_PROJECT_ID={name}",
                            "-e", "ATLAS_PROJECT_ROOT=/app/workspace",
                            "-e", f"ATLAS_WORKSPACE_ISOLATION={str(config.get('workspace_isolation', True)).lower()}",
                            "-e", f"ATLAS_CONTAINER_TYPE={config['container_type']}",
                            "-e", f"ATLAS_TOOLS_ENABLED={','.join(config['tools_enabled'])}",
                            "-e", f"ATLAS_LOG_LEVEL={config['log_level']}",
                            f"atlas-commands-mcp:{config['container_type']}"
                        ],
                        "env": {
                            "ATLAS_PROJECT_ID": name,
                            "ATLAS_ENV": "production"
                        }
                    }
                }
            }
            
            # Write MCP configuration file
            config_file = Path(f".mcp.{name}.json")
            config_file.write_text(json.dumps(mcp_config, indent=2))
            
            print(f"✓ Generated MCP config: {config_file}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to generate MCP config for {name}: {e}")
            return False
    
    def status(self):
        """Show comprehensive status of ATLAS MCP setup."""
        print("🔍 ATLAS MCP Multi-Project Status")
        print("=" * 50)
        
        # Check cache directory
        if self.cache_root.exists():
            try:
                size = subprocess.run(['du', '-sh', str(self.cache_root)], 
                                    capture_output=True, text=True).stdout.split()[0]
                print(f"✅ Cache directory: {self.cache_root} ({size})")
            except:
                print(f"✅ Cache directory: {self.cache_root}")
        else:
            print(f"❌ Cache directory missing: {self.cache_root}")
        
        # Check Docker and container images
        print("\n🐳 Docker Status:")
        try:
            result = subprocess.run(['docker', 'images', '--format', 
                                   '{{.Repository}}:{{.Tag}}\t{{.Size}}', 
                                   '--filter', 'reference=atlas-commands-mcp'],
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                print("   Available images:")
                for image in result.stdout.strip().split('\n'):
                    print(f"     ✅ {image}")
            else:
                print("   ❌ No ATLAS container images found")
        except FileNotFoundError:
            print("   ❌ Docker not available")
        
        # Check running containers
        try:
            result = subprocess.run(['docker', 'ps', '--format', 
                                   '{{.Names}}\t{{.Image}}\t{{.Status}}',
                                   '--filter', 'name=atlas-'],
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                print("   Running containers:")
                for container in result.stdout.strip().split('\n'):
                    print(f"     🔄 {container}")
            else:
                print("   ℹ️ No ATLAS containers running")
        except FileNotFoundError:
            pass
        
        # Project status
        projects = self.config["projects"]
        print(f"\n📊 Projects: {len(projects)} configured")
        
        if projects:
            complete_count = 0
            for name, config in projects.items():
                status = self._check_project_status(name, config)
                if status["complete"]:
                    complete_count += 1
                    icon = "✅"
                else:
                    icon = "⚠️"
                print(f"   {icon} {name} ({config['container_type']})")
                if not status["complete"]:
                    for issue in status["issues"]:
                        print(f"      ⚠️ {issue}")
            
            print(f"\n   Complete setups: {complete_count}/{len(projects)}")
        
        # Global settings
        print(f"\n⚙️ Global Settings:")
        settings = self.config["global_settings"]
        print(f"   Max concurrent containers: {settings.get('max_concurrent_containers', 5)}")
        print(f"   Default container type: {settings.get('default_container_type', 'fast')}")
        print(f"   Default log level: {settings.get('default_log_level', 'INFO')}")
        print(f"   Shared models: {settings.get('shared_models', True)}")
    
    def update_project(self, name: str, **kwargs):
        """Update project configuration."""
        if name not in self.config["projects"]:
            print(f"❌ Error: Project not found: {name}")
            return False
        
        # Update configuration
        project_config = self.config["projects"][name]
        updated_fields = []
        
        for key, value in kwargs.items():
            if key in project_config and project_config[key] != value:
                project_config[key] = value
                updated_fields.append(key)
        
        if updated_fields:
            project_config["last_updated"] = self._get_timestamp()
            self._save_config()
            print(f"✅ Updated project {name}: {', '.join(updated_fields)}")
            
            # Regenerate MCP config if relevant fields changed
            if any(field in ['path', 'container_type', 'tools_enabled', 'log_level'] 
                   for field in updated_fields):
                self._generate_project_mcp_config(name, project_config)
        else:
            print(f"ℹ️ No changes made to project: {name}")
        
        return True
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="ATLAS MCP Project Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s add panther /path/to/panther-project --type fast
  %(prog)s add myapi /path/to/api-project --type full --tools task_management,validation
  %(prog)s list
  %(prog)s update panther --type cached --log-level DEBUG
  %(prog)s remove panther
  %(prog)s generate
  %(prog)s status
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add project command
    add_parser = subparsers.add_parser("add", help="Add new project")
    add_parser.add_argument("name", help="Project name (used in container names)")
    add_parser.add_argument("path", help="Absolute path to project directory")
    add_parser.add_argument("--type", "--container-type", 
                           choices=["fast", "full", "cached", "ml"], 
                           default="fast", help="Container type (default: fast)")
    add_parser.add_argument("--profile", default="full", help="Project profile")
    add_parser.add_argument("--tools", help="Comma-separated list of enabled tools")
    
    # Remove project command
    remove_parser = subparsers.add_parser("remove", help="Remove project")
    remove_parser.add_argument("name", help="Project name to remove")
    
    # Update project command
    update_parser = subparsers.add_parser("update", help="Update project configuration")
    update_parser.add_argument("name", help="Project name to update")
    update_parser.add_argument("--type", "--container-type", help="Container type")
    update_parser.add_argument("--log-level", help="Log level")
    update_parser.add_argument("--tools", help="Comma-separated list of enabled tools")
    
    # List projects command
    subparsers.add_parser("list", help="List all projects")
    
    # Generate configs command
    subparsers.add_parser("generate", help="Generate MCP configurations")
    
    # Status command
    subparsers.add_parser("status", help="Show setup status")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize manager
    manager = AtlasProjectManager()
    
    # Execute commands
    try:
        if args.command == "add":
            tools = args.tools.split(',') if args.tools else None
            manager.add_project(args.name, args.path, args.type, args.profile, tools)
        elif args.command == "remove":
            manager.remove_project(args.name)
        elif args.command == "update":
            kwargs = {}
            if args.type:
                kwargs["container_type"] = args.type
            if args.log_level:
                kwargs["log_level"] = args.log_level
            if args.tools:
                kwargs["tools_enabled"] = args.tools.split(',')
            manager.update_project(args.name, **kwargs)
        elif args.command == "list":
            manager.list_projects()
        elif args.command == "generate":
            manager.generate_mcp_configs()
        elif args.command == "status":
            manager.status()
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()