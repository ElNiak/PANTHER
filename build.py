#!/usr/bin/env python3
"""
PANTHER Build Script

This script replaces the Makefile and provides a more portable, 
Python-based build system for the PANTHER project.

Usage:
    python build.py [command] [options]

Commands:
    package        - Build and install the package
    package-dev    - Build and install in development mode
    package-test   - Run tests after building
    clean          - Clean build artifacts
    install-local  - Install locally in editable mode
    docs           - Build documentation
    check          - Run code quality checks
    help           - Show this help message
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class BuildManager:
    """Manages the build process for PANTHER."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.build_dirs = ["build", "dist"]
        self.package_name = "panther_net"
        # Check Python version and virtual environment
        self.min_python_version = (3, 10)
        self.is_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

        if sys.version_info < self.min_python_version:
            print(f"Error: Python {'.'.join(map(str, self.min_python_version))} or higher is required.")
            print(f"Current Python version: {sys.version.split()[0]}")
            sys.exit(1)

        if not self.is_venv:
            print("Warning: It is recommended to run this script in a Python virtual environment.")

    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> int:
        """Run a command and return the exit code."""
        print(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd or self.project_root, 
                check=True,
                capture_output=False
            )
            return result.returncode
        except subprocess.CalledProcessError as e:
            print(f"Error: Command failed with exit code {e.returncode}")
            return e.returncode
        except FileNotFoundError:
            print(f"Error: Command not found: {cmd[0]}")
            return 1
    
    def clean(self) -> int:
        """Clean build artifacts."""
        print("Cleaning build artifacts...")
        
        # Remove build directories
        for dir_name in self.build_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                print(f"Removing {dir_path}")
                shutil.rmtree(dir_path)
        
        # Remove egg-info directories
        for egg_info in self.project_root.glob("*.egg-info"):
            print(f"Removing {egg_info}")
            shutil.rmtree(egg_info)
        
        # Remove __pycache__ directories
        for pycache in self.project_root.rglob("__pycache__"):
            print(f"Removing {pycache}")
            shutil.rmtree(pycache)
        
        # Remove .pyc files
        for pyc_file in self.project_root.rglob("*.pyc"):
            print(f"Removing {pyc_file}")
            pyc_file.unlink()
        
        print("Clean completed.")
        return 0
    
    def install_dependencies(self) -> int:
        """Install build dependencies."""
        print("Installing build dependencies...")
        return self.run_command([
            sys.executable, "-m", "pip", "install", 
            "build", "wheel", "setuptools"
        ])
    
    def uninstall_package(self) -> int:
        """Uninstall existing package."""
        print(f"Uninstalling existing {self.package_name}...")
        return self.run_command([
            sys.executable, "-m", "pip", "uninstall", 
            "--yes", self.package_name
        ])
    
    def build_wheel(self) -> int:
        """Build the wheel package."""
        print("Building wheel...")
        return self.run_command([
            sys.executable, "-m", "build", 
            "--wheel", "--no-isolation"
        ])
    
    def install_wheel(self) -> int:
        """Install the built wheel."""
        print("Installing wheel...")
        dist_dir = self.project_root / "dist"
        wheel_files = list(dist_dir.glob(f"{self.package_name}-*.whl"))
        
        if not wheel_files:
            print("Error: No wheel file found in dist/")
            return 1
        
        wheel_file = wheel_files[0]  # Use the first (should be only) wheel file
        return self.run_command([
            sys.executable, "-m", "pip", "install", str(wheel_file)
        ])
    
    def install_editable(self) -> int:
        """Install in editable/development mode."""
        print("Installing in editable mode...")
        return self.run_command([
            sys.executable, "-m", "pip", "install", 
            "--force-reinstall", "--editable", "."
        ])
    
    def run_tests(self) -> int:
        """Run the test suite."""
        print("Running tests...")
        # Install test dependencies
        result = self.run_command([
            sys.executable, "-m", "pip", "install", ".[tests]"
        ])
        if result != 0:
            return result
        
        # Run pytest
        return self.run_command([sys.executable, "-m", "pytest", "tests/"])
    
    def build_docs(self) -> int:
        """Build documentation."""
        
        # Create a backup of mkdocs.yml
        mkdocs_file = self.project_root / "mkdocs.yml"
        if mkdocs_file.exists():
            backup_file = self.project_root / "mkdocs.yml.bak"
            if backup_file.exists():
                print(f"Restoring backup of mkdocs.yml from {backup_file}")
                shutil.copy2(backup_file, mkdocs_file)
            print(f"Creating backup of mkdocs.yml -> {backup_file}")
            shutil.copy2(mkdocs_file, backup_file)
        else:
            print("Warning: mkdocs.yml not found, no backup created")

        print("Building documentation...")

        build_dict = {
            # Home
            "README.md": "docs/index.md",
            
            # Getting Started
            "quick_start.md": "docs/quick_start.md",
            "install.md": "docs/install.md",
            "panther/config/README.md": "docs/configuration.md",
            "panther/core/README.md": "docs/core.md",
            "workflow.md": "docs/experimental_workflows.md",
            "panther/core/README.md": "docs/core_workflows.md",
            "panther/webapp/README.md": "docs/web_application_workflows.md",
            
            
            # Plugins Overview
            "panther/plugins/README.md": "docs/plugins_overview.md",
            "docs-gen/plugins_inventory.md": "docs/plugins_inventory.md",
            
            # Developer Guide
            "CONTRIBUTING.md": "docs/contributing.md",
            "panther/plugins/development.md": "docs/plugin_development.md",
           
        
            # Environment Plugins
            "panther/plugins/environments/README.md": "docs/environment_plugins.md",
            "panther/plugins/environments/development.md": "docs/plugin_development_environment.md",
            "panther/plugins/environments/network_environment/README.md": "docs/network_environment.md",
            "panther/plugins/environments/network_environment/development.md": "docs/plugin_development_network.md",
            "panther/plugins/environments/network_environment/docker_compose/README.md": "docs/network_docker_compose.md",
            "panther/plugins/environments/network_environment/localhost_single_container/README.md": "docs/network_localhost_container.md",
            "panther/plugins/environments/network_environment/shadow_ns/README.md": "docs/network_shadow_ns.md",
            
            # Execution Environment Plugins
            "panther/plugins/environments/execution_environment/README.md": "docs/execution_environment.md",
            "panther/plugins/environments/execution_environment/development.md": "docs/plugin_development_execution.md",
            "panther/plugins/environments/execution_environment/gperf_cpu/README.md": "docs/execution_gperf_cpu.md",
            "panther/plugins/environments/execution_environment/gperf_heap/README.md": "docs/execution_gperf_heap.md",
            "panther/plugins/environments/execution_environment/helgrind/README.md": "docs/execution_helgrind.md",
            "panther/plugins/environments/execution_environment/iterations/README.md": "docs/execution_iterations.md",
            "panther/plugins/environments/execution_environment/memcheck/README.md": "docs/execution_memcheck.md",
            "panther/plugins/environments/execution_environment/strace/README.md": "docs/execution_strace.md",
            
            # Protocol Plugins
            "panther/plugins/protocols/README.md": "docs/protocol_plugins.md",
            "panther/plugins/protocols/development.md": "docs/protocol_development.md",
            
            # Client-Server Protocol Plugins
            "panther/plugins/protocols/client_server/README.md": "docs/client_server_protocols.md",
            "panther/plugins/protocols/client_server/index.md": "docs/client_server_index.md",
            "panther/plugins/protocols/client_server/http/README.md": "docs/protocol_http.md",
            "panther/plugins/protocols/client_server/minip/README.md": "docs/protocol_minip.md",
            "panther/plugins/protocols/client_server/quic/README.md": "docs/protocol_quic.md",
            
            # Peer-to-Peer Protocol Plugins
            "panther/plugins/protocols/peer_to_peer/README.md": "docs/peer_to_peer_protocols.md",
            "panther/plugins/protocols/peer_to_peer/index.md": "docs/peer_to_peer_index.md",
            "panther/plugins/protocols/peer_to_peer/bittorrent/README.md": "docs/protocol_bittorrent.md",
            
            # Service Plugins
            "panther/plugins/services/README.md": "docs/service_plugins.md",
            "panther/plugins/services/development.md": "docs/service_development.md",
            
            # IUT (Implementation Under Test) Plugins
            "panther/plugins/services/iut/README.md": "docs/iut_plugins.md",
            "panther/plugins/services/iut/development.md": "docs/iut_development.md",
            "panther/plugins/services/iut/http/README.md": "docs/iut_http.md",
            "panther/plugins/services/iut/minip/README.md": "docs/iut_minip.md",
            "panther/plugins/services/iut/minip/ping_pong/README.md": "docs/iut_minip_ping_pong.md",
            
            # QUIC IUT Plugins
            "panther/plugins/services/iut/quic/README.md": "docs/iut_quic_overview.md",
            "panther/plugins/services/iut/quic/aioquic/README.md": "docs/iut_quic_aioquic.md",
            "panther/plugins/services/iut/quic/lsquic/README.md": "docs/iut_quic_lsquic.md",
            "panther/plugins/services/iut/quic/mvfst/README.md": "docs/iut_quic_mvfst.md",
            "panther/plugins/services/iut/quic/picoquic/README.md": "docs/iut_quic_picoquic.md",
            "panther/plugins/services/iut/quic/picoquic_shadow/README.md": "docs/iut_quic_picoquic_shadow.md",
            "panther/plugins/services/iut/quic/quant/README.md": "docs/iut_quic_quant.md",
            "panther/plugins/services/iut/quic/quic_go/README.md": "docs/iut_quic_go.md",
            "panther/plugins/services/iut/quic/quiche/README.md": "docs/iut_quic_quiche.md",
            "panther/plugins/services/iut/quic/quinn/README.md": "docs/iut_quic_quinn.md",
            
            # Tester Service Plugins
            "panther/plugins/services/testers/README.md": "docs/testing_services.md",
            "panther/plugins/services/testers/development.md": "docs/testers_development.md",
            "panther/plugins/services/testers/panther_ivy/README.md": "docs/tester_panther_ivy.md",
            
            # Documentation
            "docs-gen/README.md": "docs/documentation_readme.md",
            "docs-gen/documentation_workflow.md": "docs/documentation_workflow.md",
            "docs-gen/style_guide.md": "docs/style_guide.md",
            "docs-gen/documentation_integration.md": "docs/documentation_integration.md",
            "docs-gen/documentation_links.md": "docs/documentation_links.md",
            "docs-gen/documentation_enhancements.md": "docs/documentation_enhancements.md",
            
            # Project Information
            "CHANGELOG.md": "docs/changelog.md",
            "LICENSE.md": "docs/license.md",
        }

        self.clean()  # Clean before building docs

        # Clean documentation build artifacts
        print("Cleaning documentation build artifacts...")
        doc_artifacts = ["site"]  # MkDocs default output directory
        for artifact in doc_artifacts:
            artifact_path = self.project_root / artifact
            if artifact_path.exists():
                print(f"Removing {artifact_path}")
                shutil.rmtree(artifact_path)
        
        # Install documentation dependencies
        print("Installing documentation dependencies...")
        result = self.run_command([
            sys.executable, "-m", "pip", "install", ".[doc]"
        ])
        if result != 0:
            print("Warning: Could not install documentation dependencies")
        
        # Ensure docs directory exists and is empty
        docs_dir = self.project_root / "docs"
        if docs_dir.exists():
            print(f"Clearing {docs_dir} directory...")
            shutil.rmtree(docs_dir)
        docs_dir.mkdir(exist_ok=True)

        # Run the MkDocs automation script
        print("Running MkDocs automation script...")
        mkdocs_script = self.project_root / "docs-gen" / "mkdocs" / "automate_mkdocs.py"
        if mkdocs_script.exists():
            result = self.run_command([sys.executable, str(mkdocs_script)])
            if result != 0:
                print("Warning: MkDocs automation script failed")
        else:
            print(f"Warning: MkDocs automation script not found at {mkdocs_script}")

        # Run gendocs with the mkgendocs.yml config
        print("Running gendocs with custom configuration...")
        result = self.run_command(["gendocs", "--config", "mkgendocs.yml"])
        if result != 0:
            print("Warning: gendocs command failed")

        # Generate plugin inventory
        print("Generating plugin inventory...")
        inventory_script = self.project_root / "docs-gen" / "generate_plugin_inventory.py"
        if inventory_script.exists():
            result = self.run_command([
                sys.executable, str(inventory_script), 
                "--format", "markdown", 
                "--output", "docs/plugins_inventory.md"
            ])
            if result != 0:
                print("Warning: Plugin inventory generation failed")
        
        # Copy files according to build_dict
        print("Copying documentation files...")
        for source, destination in build_dict.items():
            source_path = self.project_root / source
            dest_path = self.project_root / destination
            
            # Create destination directory if it doesn't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            if source_path.exists():
                print(f"Copying {source} -> {destination}")
                shutil.copy2(source_path, dest_path)
            else:
                print(f"Warning: Source file {source} not found, creating placeholder")
                # Create a placeholder file
                with open(dest_path, 'w') as f:
                    f.write(f"# {dest_path.stem.replace('_', ' ').title()}\n\n")
                    f.write("This documentation is under development.\n")

        # Copy all markdown files from panther to docs/panther
        panther_docs_dir = self.project_root / "docs" / "panther"
        panther_src_dir = self.project_root / "panther"
        if not panther_docs_dir.exists():
            print(f"Creating directory {panther_docs_dir}")
            panther_docs_dir.mkdir(parents=True, exist_ok=True)
        for md_file in panther_src_dir.rglob("*.md"):
            if md_file.is_file():
                relative_path = md_file.relative_to(panther_src_dir)
                dest_path = panther_docs_dir / relative_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"Copying {md_file} to {dest_path}")
                shutil.copy2(md_file, dest_path)
                
        
        # Check if MkDocs is available
        try:
            result = self.run_command(["mkdocs", "--version"])
            if result != 0:
                print("Installing MkDocs...")
                self.run_command([
                    sys.executable, "-m", "pip", "install", 
                    "mkdocs", "mkdocs-material", "mkdocstrings"
                ])
        except FileNotFoundError:
            print("Installing MkDocs...")
            self.run_command([
                sys.executable, "-m", "pip", "install", 
                "mkdocs", "mkdocs-material", "mkdocstrings"
            ])
        
        # Build documentation with MkDocs
        print("Building documentation with MkDocs...")
        return self.run_command([
            "mkdocs", "build", "--verbose", "--config-file", "mkdocs.yml"
        ])

    def serve_docs(self) -> int:
        """Serve the documentation locally."""
        self.build_docs()  # Ensure docs are built first
        print("Serving documentation locally...")
        
        # Ensure MkDocs is installed
        result = self.run_command(["mkdocs", "--version"])
        if result != 0:
            print("Installing MkDocs...")
            self.run_command([
                sys.executable, "-m", "pip", "install", 
                "mkdocs", "mkdocs-material", "mkdocstrings"
            ])
        
        # Serve the documentation
        return self.run_command(["mkdocs", "serve", "--config-file", "mkdocs.yml"])
    
    def check_code_quality(self) -> int:
        """Run code quality checks."""
        print("Running code quality checks...")
        
        # Install check dependencies
        result = self.run_command([
            sys.executable, "-m", "pip", "install", 
            "flake8", "black", "isort", "mypy"
        ])
        if result != 0:
            print("Warning: Could not install quality check tools")
        
        # Run checks
        checks = [
            # Check formatting with black
            ([sys.executable, "-m", "black", "--check", "."], "Black formatting check"),
            # Check imports with isort
            ([sys.executable, "-m", "isort", "--check-only", "."], "Import sorting check"),
            # Check with flake8
            ([sys.executable, "-m", "flake8", "panther/"], "Flake8 linting"),
        ]
        
        total_errors = 0
        for cmd, description in checks:
            print(f"\n{description}...")
            result = self.run_command(cmd)
            if result != 0:
                total_errors += 1
                print(f"❌ {description} failed")
            else:
                print(f"✅ {description} passed")
        
        return total_errors
    
    def package(self, dev_mode: bool = False) -> int:
        """Build and install the package."""
        steps = [
            ("Installing dependencies", self.install_dependencies),
            ("Uninstalling existing package", self.uninstall_package),
            ("Cleaning", self.clean),
            ("Building wheel", self.build_wheel),
        ]
        
        if dev_mode:
            steps.append(("Installing in editable mode", self.install_editable))
        else:
            steps.append(("Installing wheel", self.install_wheel))
        
        for description, func in steps:
            print(f"\n{description}...")
            result = func()
            if result != 0:
                print(f"❌ {description} failed")
                return result
            print(f"✅ {description} completed")
        
        print("\n🎉 Package build completed successfully!")
        return 0
    
    def package_test(self) -> int:
        """Build package and run tests."""
        result = self.package()
        if result != 0:
            return result
        
        return self.run_tests()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PANTHER Build Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "command",
        choices=[
            "package", "package-dev", "package-test", 
            "clean", "install-local", "docs", "check", "help"
        ],
        help="Build command to execute"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Serve documentation locally (only with 'docs' command)"
    )
    
    args = parser.parse_args()
    
    if args.command == "help":
        parser.print_help()
        return 0
    
    builder = BuildManager()
    
    try:
        if args.command == "package":
            return builder.package()
        elif args.command == "package-dev":
            return builder.package(dev_mode=True)
        elif args.command == "package-test":
            return builder.package_test()
        elif args.command == "clean":
            return builder.clean()
        elif args.command == "install-local":
            return builder.install_editable()
        elif args.command == "docs":
            if args.serve:
                return builder.serve_docs()
            else:
                return builder.build_docs()
        elif args.command == "check":
            return builder.check_code_quality()
        else:
            print(f"Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\n❌ Build interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Build failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
