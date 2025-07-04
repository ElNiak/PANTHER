#!/usr/bin/env python3
"""
ATLAS MCP Project Configuration Manager

A Python utility for managing multi-project ATLAS MCP configurations
that reuses existing task management components following DRY, SOLID, and KISS principles.

Usage:
    python atlas-project-manager.py add panther /path/to/project
    python atlas-project-manager.py list
    python atlas-project-manager.py generate
    python atlas-project-manager.py status
"""

import json
import os
import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class AtlasProjectManager:
    """Manages ATLAS MCP project configurations with minimal complexity."""
    
    def __init__(self, config_file: str = "atlas-project-config.json"):
        self.config_file = Path(config_file)
        self.cache_root = Path.home() / ".atlas-cache"
        self.script_dir = Path(__file__).parent
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load project configuration or create default."""
        if self.config_file.exists():
            try:
                return json.loads(self.config_file.read_text())
            except json.JSONDecodeError as e:
                print(f"Error loading config: {e}")
                return self._create_default_config()
        
        return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration structure."""
        return {
            "projects": {},
            "global_settings": {
                "cache_root": str(self.cache_root),
                "shared_models": True,
                "max_concurrent_containers": 5,
                "health_check_interval": 30,
                "default_container_type": "fast",
                "default_log_level": "INFO",
                "workspace_isolation": True
            },
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "atlas_version": "1.10.1"
            }
        }
    
    def _save_config(self) -> bool:
        """Save configuration to file."""
        try:
            self.config["metadata"]["updated_at"] = datetime.utcnow().isoformat()
            self.config_file.write_text(json.dumps(self.config, indent=2))
            print(f"✓ Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"✗ Failed to save configuration: {e}")
            return False
    
    def add_project(self, name: str, path: str, container_type: str = "fast", 
                   profile: str = "full", tools: List[str] = None) -> bool:
        """Add new project to configuration."""
        
        # Validate project path
        project_path = Path(path).resolve()
        if not project_path.exists():
            print(f"✗ Project path does not exist: {project_path}")
            return False
        
        if not project_path.is_dir():
            print(f"✗ Project path is not a directory: {project_path}")
            return False
        
        # Default tools if not specified
        if tools is None:
            tools = [
                "task_management", 
                "memory_management", 
                "workflow_intelligence",
                "embeddings"
            ]
        
        # Detect project type and adjust tools
        detected_tools = self._detect_project_tools(project_path)
        if detected_tools:
            tools.extend(detected_tools)
            tools = list(set(tools))  # Remove duplicates
        
        # Create project configuration
        project_config = {
            "path": str(project_path),
            "container_type": container_type,
            "profile": profile,
            "tools_enabled": tools,
            "cache_strategy": "project_isolated",
            "log_level": self.config["global_settings"]["default_log_level"],
            "workspace_isolation": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Add project to configuration
        self.config["projects"][name] = project_config
        
        if self._save_config():
            print(f"✓ Added project '{name}' at {project_path}")
            print(f"  Container type: {container_type}")
            print(f"  Tools enabled: {', '.join(tools)}")
            return True
        
        return False
    
    def _detect_project_tools(self, project_path: Path) -> List[str]:
        """Detect additional tools based on project characteristics."""
        additional_tools = []
        
        # Check for specific project types
        if (project_path / "package.json").exists():
            additional_tools.append("validation")
        
        if (project_path / "pyproject.toml").exists() or (project_path / "setup.py").exists():
            additional_tools.append("validation")
        
        if (project_path / ".git").exists():
            additional_tools.append("observability")
        
        # Check for ML/AI projects
        ml_indicators = ["requirements.txt", "environment.yml", "Pipfile"]
        if any((project_path / indicator).exists() for indicator in ml_indicators):
            content_files = list(project_path.glob("**/*.py"))[:10]  # Sample files
            for file in content_files:
                try:
                    content = file.read_text(errors='ignore').lower()
                    if any(lib in content for lib in ["torch", "tensorflow", "sklearn", "pandas", "numpy"]):
                        additional_tools.extend(["embeddings", "cache_management"])
                        break
                except:
                    continue
        
        return additional_tools
    
    def remove_project(self, name: str) -> bool:
        """Remove project from configuration."""
        if name not in self.config["projects"]:
            print(f"✗ Project not found: {name}")
            return False
        
        # Remove project from config
        del self.config["projects"][name]
        
        if self._save_config():
            # Clean up project files
            mcp_config_file = Path(f".mcp.{name}.json")
            if mcp_config_file.exists():
                mcp_config_file.unlink()
                print(f"✓ Removed MCP config: {mcp_config_file}")
            
            print(f"✓ Removed project: {name}")
            return True
        
        return False
    
    def list_projects(self) -> None:
        """List all configured projects."""
        if not self.config["projects"]:
            print("ℹ️  No projects configured")
            return
        
        print("Configured ATLAS MCP Projects:")
        print("=" * 60)
        
        for name, config in self.config["projects"].items():
            print(f"\n📁 {name}")
            print(f"   Path: {config['path']}")
            print(f"   Container: {config['container_type']}")
            print(f"   Profile: {config['profile']}")
            print(f"   Tools: {', '.join(config['tools_enabled'])}")
            print(f"   Isolation: {config.get('workspace_isolation', True)}")
            
            # Check if MCP config exists
            mcp_file = Path(f".mcp.{name}.json")
            cache_dir = self.cache_root / name
            
            status_items = []
            if mcp_file.exists():
                status_items.append("✓ MCP config")
            else:
                status_items.append("✗ MCP config")
            
            if cache_dir.exists():
                status_items.append("✓ Cache dir")
            else:
                status_items.append("✗ Cache dir")
            
            if Path(config['path']).exists():
                status_items.append("✓ Project path")
            else:
                status_items.append("✗ Project path")
            
            print(f"   Status: {' | '.join(status_items)}")
    
    def generate_mcp_configs(self) -> bool:
        """Generate MCP configuration files for all projects."""
        if not self.config["projects"]:
            print("ℹ️  No projects to generate configs for")
            return True
        
        success_count = 0
        total_count = len(self.config["projects"])
        
        for name, project_config in self.config["projects"].items():
            if self._generate_project_mcp_config(name, project_config):
                success_count += 1
        
        print(f"✓ Generated {success_count}/{total_count} MCP configurations")
        return success_count == total_count
    
    def _generate_project_mcp_config(self, name: str, config: Dict[str, Any]) -> bool:
        """Generate MCP configuration for single project."""
        try:
            # Create cache directory
            cache_dir = self.cache_root / name
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Create MCP configuration
            mcp_config = {
                "mcpServers": {
                    f"atlas-{name}": {
                        "command": "docker",
                        "args": [
                            "run", "-i", "--rm",
                            "--name", f"atlas-{name}",
                            "-v", f"{config['path']}:/app/workspace",
                            "-v", f"{cache_dir}:/app/cache",
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
            
            # Write MCP config file
            config_file = Path(f".mcp.{name}.json")
            config_file.write_text(json.dumps(mcp_config, indent=2))
            
            print(f"✓ Generated MCP config: {config_file}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to generate MCP config for {name}: {e}")
            return False
    
    def status(self) -> None:
        """Show comprehensive status of ATLAS MCP setup."""
        print("ATLAS MCP Multi-Project Status")
        print("=" * 50)
        
        # Check cache directory
        print(f"\n📁 Cache Directory:")
        if self.cache_root.exists():
            try:
                # Calculate cache size
                cache_size = sum(f.stat().st_size for f in self.cache_root.rglob('*') if f.is_file())
                cache_size_mb = cache_size / (1024 * 1024)
                print(f"   ✓ {self.cache_root} ({cache_size_mb:.1f} MB)")
            except:
                print(f"   ✓ {self.cache_root}")
        else:
            print(f"   ✗ {self.cache_root} (missing)")
        
        # Check Docker and container images
        print(f"\n🐳 Docker Status:")
        try:
            # Check if Docker is running
            subprocess.run(["docker", "info"], 
                         capture_output=True, check=True, timeout=5)
            print("   ✓ Docker is running")
            
            # Check for ATLAS images
            result = subprocess.run(
                ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}", 
                 "--filter", "reference=atlas-commands-mcp"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                print("   ✓ Container images:")
                for image in result.stdout.strip().split('\n'):
                    print(f"     - {image}")
            else:
                print("   ✗ No ATLAS container images found")
                
        except subprocess.TimeoutExpired:
            print("   ⚠️  Docker command timed out")
        except subprocess.CalledProcessError:
            print("   ✗ Docker is not running or accessible")
        except FileNotFoundError:
            print("   ✗ Docker not installed")
        
        # Check running containers
        print(f"\n📦 Running Containers:")
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Image}}\t{{.Status}}", 
                 "--filter", "name=atlas-"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    name, image, status = line.split('\t', 2)
                    print(f"   ✓ {name} ({image}) - {status}")
            else:
                print("   ℹ️  No ATLAS containers running")
                
        except Exception as e:
            print(f"   ⚠️  Could not check running containers: {e}")
        
        # Project status
        print(f"\n🎯 Project Status:")
        project_count = len(self.config["projects"])
        print(f"   Configured projects: {project_count}")
        
        if project_count > 0:
            for name, config in self.config["projects"].items():
                mcp_file = Path(f".mcp.{name}.json")
                cache_dir = self.cache_root / name
                project_path = Path(config['path'])
                
                status_parts = []
                if mcp_file.exists():
                    status_parts.append("MCP✓")
                else:
                    status_parts.append("MCP✗")
                
                if cache_dir.exists():
                    status_parts.append("Cache✓")
                else:
                    status_parts.append("Cache✗")
                
                if project_path.exists():
                    status_parts.append("Path✓")
                else:
                    status_parts.append("Path✗")
                
                status_icon = "✓" if all("✓" in part for part in status_parts) else "⚠️"
                print(f"   {status_icon} {name} ({' | '.join(status_parts)})")
        
        # Configuration file status
        print(f"\n⚙️  Configuration:")
        print(f"   ✓ Config file: {self.config_file}")
        print(f"   ✓ Version: {self.config.get('metadata', {}).get('version', 'unknown')}")
        print(f"   ✓ Last updated: {self.config.get('metadata', {}).get('updated_at', 'unknown')}")
    
    def validate_setup(self) -> bool:
        """Validate the entire ATLAS MCP setup."""
        print("🔍 Validating ATLAS MCP Setup...")
        
        issues = []
        warnings = []
        
        # Check cache directory
        if not self.cache_root.exists():
            issues.append(f"Cache directory missing: {self.cache_root}")
        
        # Check Docker
        try:
            subprocess.run(["docker", "info"], 
                         capture_output=True, check=True, timeout=5)
        except:
            issues.append("Docker is not running or accessible")
        
        # Check container images
        try:
            result = subprocess.run(
                ["docker", "images", "-q", "atlas-commands-mcp"],
                capture_output=True, text=True, timeout=10
            )
            if not result.stdout.strip():
                issues.append("ATLAS container image not found")
        except:
            warnings.append("Could not check container images")
        
        # Check project configurations
        for name, config in self.config["projects"].items():
            project_path = Path(config['path'])
            if not project_path.exists():
                issues.append(f"Project path missing for '{name}': {project_path}")
            
            mcp_file = Path(f".mcp.{name}.json")
            if not mcp_file.exists():
                warnings.append(f"MCP config missing for '{name}': {mcp_file}")
        
        # Report results
        if issues:
            print("\n❌ Issues found:")
            for issue in issues:
                print(f"   - {issue}")
        
        if warnings:
            print("\n⚠️  Warnings:")
            for warning in warnings:
                print(f"   - {warning}")
        
        if not issues and not warnings:
            print("✅ All validations passed!")
            return True
        elif not issues:
            print("⚠️  Setup valid with warnings")
            return True
        else:
            print("❌ Setup has issues that need attention")
            return False


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="ATLAS MCP Project Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s add panther /path/to/panther --container=fast --tools=task_management,memory_management
  %(prog)s list
  %(prog)s generate
  %(prog)s status
  %(prog)s validate
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add project command
    add_parser = subparsers.add_parser("add", help="Add new project")
    add_parser.add_argument("name", help="Project name")
    add_parser.add_argument("path", help="Project path")
    add_parser.add_argument("--container", choices=["fast", "cached", "ml", "full"], 
                           default="fast", help="Container type")
    add_parser.add_argument("--profile", default="full", help="Project profile")
    add_parser.add_argument("--tools", help="Comma-separated list of enabled tools")
    
    # Remove project command
    remove_parser = subparsers.add_parser("remove", help="Remove project")
    remove_parser.add_argument("name", help="Project name")
    
    # List projects command
    subparsers.add_parser("list", help="List all projects")
    
    # Generate configs command
    subparsers.add_parser("generate", help="Generate MCP configurations")
    
    # Status command
    subparsers.add_parser("status", help="Show setup status")
    
    # Validate command
    subparsers.add_parser("validate", help="Validate setup")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize manager
    manager = AtlasProjectManager()
    
    # Execute command
    try:
        if args.command == "add":
            tools = args.tools.split(",") if args.tools else None
            success = manager.add_project(args.name, args.path, args.container, args.profile, tools)
            sys.exit(0 if success else 1)
            
        elif args.command == "remove":
            success = manager.remove_project(args.name)
            sys.exit(0 if success else 1)
            
        elif args.command == "list":
            manager.list_projects()
            
        elif args.command == "generate":
            success = manager.generate_mcp_configs()
            sys.exit(0 if success else 1)
            
        elif args.command == "status":
            manager.status()
            
        elif args.command == "validate":
            success = manager.validate_setup()
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()