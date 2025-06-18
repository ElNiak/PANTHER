"""
Hatch build hook to ensure all plugin files are included.
This hook helps maintain backward compatibility when migrating from setuptools.
"""

import os
from pathlib import Path
from typing import Any, Dict

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    """
    Custom build hook to ensure all PANTHER plugin files are included in the wheel.
    
    This is necessary because Hatchling's default behavior might miss some
    non-Python files in deeply nested plugin directories.
    """
    
    PLUGIN_NAME = "custom"
    
    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        """
        Initialize the build hook and ensure all plugin files are included.
        
        Args:
            version: The version being built
            build_data: Build configuration data
        """
        print("PANTHER custom build hook: Ensuring all plugin files are included...")
        
        # Get the project root
        project_root = Path(self.root)
        
        # Define patterns for files to include
        plugin_patterns = [
            "**/*.yaml",
            "**/*.yml",
            "**/*.jinja",
            "**/*.j2",
            "**/*.sh",
            "**/Dockerfile*",
            "**/*.txt",
            "**/*.key",
            "**/*.pem",
            "**/*.cert",
            "**/*.ivy",
            "**/*.h",
            "**/*.c",
            "**/*.html",
        ]
        
        # Critical directories to scan
        critical_dirs = [
            "panther/plugins/services",
            "panther/plugins/environments",
            "panther/plugins/protocols",
            "panther/webapp",
        ]
        
        # Collect all files that match patterns
        force_include = build_data.setdefault("force_include", {})
        artifacts = build_data.setdefault("artifacts", [])
        
        for dir_path in critical_dirs:
            full_dir = project_root / dir_path
            if not full_dir.exists():
                print(f"Warning: Directory {dir_path} not found")
                continue
            
            # Scan for files matching patterns
            for pattern in plugin_patterns:
                for file_path in full_dir.rglob(pattern):
                    if file_path.is_file():
                        # Get relative path from project root
                        rel_path = file_path.relative_to(project_root)
                        
                        # Add to artifacts to ensure inclusion
                        artifact_path = str(rel_path)
                        if artifact_path not in artifacts:
                            artifacts.append(artifact_path)
        
        # Special handling for Ivy tester files
        ivy_dir = project_root / "panther/plugins/services/testers/panther_ivy"
        if ivy_dir.exists():
            # Include all subdirectories of Ivy
            for subdir in ["ivy", "submodules", "scripts", "protocol-testing", "lib", "version_configs", "templates"]:
                full_subdir = ivy_dir / subdir
                if full_subdir.exists():
                    # Force include entire directory
                    force_include[str(full_subdir)] = f"panther/plugins/services/testers/panther_ivy/{subdir}"
        
        # Ensure py.typed is included
        py_typed = project_root / "panther/py.typed"
        if py_typed.exists():
            force_include[str(py_typed)] = "panther/py.typed"
        
        print(f"PANTHER custom build hook: Added {len(artifacts)} artifact patterns")
        print(f"PANTHER custom build hook: Force including {len(force_include)} paths")
    
    def finalize(self, version: str, build_data: Dict[str, Any], artifact_path: str) -> None:
        """
        Finalize the build and validate that critical files were included.
        
        Args:
            version: The version that was built
            build_data: Build configuration data
            artifact_path: Path to the built artifact
        """
        print(f"PANTHER custom build hook: Finalizing build for {artifact_path}")
        
        # Validate that critical files exist in the artifact
        if artifact_path.endswith('.whl'):
            import zipfile
            
            critical_files = [
                "panther/py.typed",
                "panther/plugins/services/iut/quic/picoquic/Dockerfile",
                "panther/plugins/environments/network_environment/docker_compose/docker_compose.py",
                "panther/webapp/templates/base.html",
            ]
            
            with zipfile.ZipFile(artifact_path, 'r') as wheel:
                wheel_files = wheel.namelist()
                
                missing_files = []
                for critical_file in critical_files:
                    if not any(critical_file in f for f in wheel_files):
                        missing_files.append(critical_file)
                
                if missing_files:
                    print(f"Warning: Critical files missing from wheel: {missing_files}")
                else:
                    print("PANTHER custom build hook: All critical files included ✓")