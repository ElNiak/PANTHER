#!/usr/bin/env python3
"""
PANTHER Documentation Source Discovery

Automatically discovers README.md files and generates build_dict mappings
to replace manual maintenance in panther_builder.py.

This module implements Phase 1 of the PANTHER Documentation Automation:
- AST-based Python module analysis (for context)
- README file discovery and categorization
- Intelligent mapping generation based on directory structure
- Integration with existing panther_builder.py workflow

Usage:
    python discover_sources.py --generate-build-dict
    python discover_sources.py --analyze-structure
    python discover_sources.py --validate-mappings
"""

import ast
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class ReadmeInfo:
    """Information about a discovered README file."""

    source_path: str
    relative_path: str
    category: str
    suggested_doc_name: str
    priority: int
    content_preview: str
    module_context: Optional[str] = None


@dataclass
class ModuleInfo:
    """Information about a Python module for context."""

    module_path: str
    classes: List[str]
    functions: List[str]
    has_readme: bool
    readme_path: Optional[str] = None


class PantherSourceDiscovery:
    """Discovers and analyzes PANTHER documentation sources."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.panther_root = project_root / "panther"
        self.readme_files: List[ReadmeInfo] = []
        self.python_modules: List[ModuleInfo] = []
        self.category_patterns = {
            "core": ["panther/core", "panther/config"],
            "plugins_overview": ["panther/plugins/README.md"],
            "environment_plugins": ["panther/plugins/environments"],
            "execution_plugins": ["panther/plugins/environments/execution_environment"],
            "network_plugins": ["panther/plugins/environments/network_environment"],
            "protocol_plugins": ["panther/plugins/protocols"],
            "client_server_protocols": ["panther/plugins/protocols/client_server"],
            "peer_to_peer_protocols": ["panther/plugins/protocols/peer_to_peer"],
            "service_plugins": ["panther/plugins/services"],
            "iut_plugins": ["panther/plugins/services/iut"],
            "quic_iut_plugins": ["panther/plugins/services/iut/quic"],
            "tester_plugins": ["panther/plugins/services/testers"],
            "documentation": ["panther/tools/docs_gen"],
            "getting_started": ["QUICK_START.md", "INSTALL.md", "README.md"],
            "developer": ["CONTRIBUTING.md", "development.md"],
            "project_info": ["CHANGELOG.md", "LICENSE.md", "WORKFLOW.md"],
        }

    def discover_readme_files(self) -> List[ReadmeInfo]:
        """Discover all README.md files in the project."""
        print("🔍 Discovering README files...")

        readme_files = []

        # Find all README.md files, excluding virtual environments, build artifacts,
        # and the docs/ output directory (to avoid self-referencing entries)
        exclude_patterns = {
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            ".pre-commit-cache",
            "build",
            "dist",
            ".git",
            "site",
            "node_modules",
            "docs",
        }

        for readme_path in self.project_root.rglob("README.md"):
            # Skip files in excluded directories
            if any(exclude in str(readme_path) for exclude in exclude_patterns):
                continue

            relative_path = str(readme_path.relative_to(self.project_root))

            # Analyze the README file
            readme_info = self._analyze_readme_file(readme_path, relative_path)
            readme_files.append(readme_info)

        # Discover root-level documentation files (non-README)
        root_doc_files = {
            "INSTALL.md": ("getting_started", "docs/INSTALL.md", 2),
            "QUICK_START.md": ("getting_started", "docs/QUICK_START.md", 2),
            "CONTRIBUTING.md": ("developer", "docs/contributing.md", 70),
            "CHANGELOG.md": ("project_info", "docs/changelog.md", 80),
            "LICENSE.md": ("project_info", "docs/license.md", 80),
            "workflow.md": ("project_info", "docs/workflow.md", 4),
        }
        for filename, (category, doc_name, priority) in root_doc_files.items():
            file_path = self.project_root / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = file_path.read_text(encoding="latin-1")
                content_preview = content[:200].replace("\n", " ").strip()
                readme_files.append(
                    ReadmeInfo(
                        source_path=str(file_path),
                        relative_path=filename,
                        category=category,
                        suggested_doc_name=doc_name,
                        priority=priority,
                        content_preview=content_preview,
                    )
                )

        # Discover development.md files in plugin directories only
        plugins_dir = self.project_root / "panther" / "plugins"
        for dev_md_path in plugins_dir.rglob("development.md"):
            if any(exclude in str(dev_md_path) for exclude in exclude_patterns):
                continue
            relative_path = str(dev_md_path.relative_to(self.project_root))
            doc_name = self._generate_dev_doc_name(relative_path)
            try:
                content = dev_md_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = dev_md_path.read_text(encoding="latin-1")
            content_preview = content[:200].replace("\n", " ").strip()
            readme_files.append(
                ReadmeInfo(
                    source_path=str(dev_md_path),
                    relative_path=relative_path,
                    category="developer",
                    suggested_doc_name=doc_name,
                    priority=60,
                    content_preview=content_preview,
                )
            )

        # Discover plugins_inventory.md
        inventory_path = (
            self.project_root / "panther" / "plugins" / "plugins_inventory.md"
        )
        if inventory_path.exists():
            try:
                content = inventory_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = inventory_path.read_text(encoding="latin-1")
            content_preview = content[:200].replace("\n", " ").strip()
            readme_files.append(
                ReadmeInfo(
                    source_path=str(inventory_path),
                    relative_path="panther/plugins/plugins_inventory.md",
                    category="plugins_overview",
                    suggested_doc_name="docs/plugins_inventory.md",
                    priority=6,
                    content_preview=content_preview,
                )
            )

        self.readme_files = sorted(readme_files, key=lambda x: x.priority)
        print(f"  Discovered {len(readme_files)} documentation files")
        return readme_files

    def _analyze_readme_file(self, readme_path: Path, relative_path: str) -> ReadmeInfo:
        """Analyze a single README file to determine its category and mapping."""

        # Read content preview
        try:
            content = readme_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = readme_path.read_text(encoding="latin-1")
        except Exception as e:
            content = ""
        content_preview = (
            content[:200].replace("\n", " ").strip()
            if content
            else f"Error reading file"
        )

        # Determine category based on path patterns
        category = self._categorize_readme(relative_path)

        # Generate suggested documentation name
        doc_name = self._generate_doc_name(relative_path, category)

        # Assign priority (lower number = higher priority)
        priority = self._assign_priority(relative_path, category)

        # Check for associated Python module
        module_context = self._find_module_context(readme_path)

        return ReadmeInfo(
            source_path=str(readme_path),
            relative_path=relative_path,
            category=category,
            suggested_doc_name=doc_name,
            priority=priority,
            content_preview=content_preview,
            module_context=module_context,
        )

    def _categorize_readme(self, relative_path: str) -> str:
        """Categorize README based on its path."""

        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if pattern in relative_path:
                    return category

        # Default categorization based on path depth and content
        if relative_path.count("/") == 0:
            return "project_root"
        elif "plugin" in relative_path.lower():
            return "plugins_general"
        elif "test" in relative_path.lower():
            return "testing"
        else:
            return "miscellaneous"

    def _generate_doc_name(self, relative_path: str, category: str) -> str:
        """Generate appropriate documentation file name."""

        # Special cases for important files
        if relative_path == "README.md":
            return "docs/index.md"
        elif relative_path == "QUICK_START.md":
            return "docs/QUICK_START.md"
        elif relative_path == "INSTALL.md":
            return "docs/INSTALL.md"
        elif relative_path == "CONTRIBUTING.md":
            return "docs/contributing.md"
        elif relative_path == "CHANGELOG.md":
            return "docs/changelog.md"
        elif relative_path == "LICENSE.md":
            return "docs/license.md"
        elif relative_path == "WORKFLOW.md":
            return "docs/experimental_workflows.md"

        # For panther/ subdirectories, create descriptive names
        if relative_path.startswith("panther/"):
            # Remove "panther/" prefix and create doc name
            path_parts = (
                relative_path.replace("panther/", "")
                .replace("/README.md", "")
                .split("/")
            )

            if "plugins" in path_parts:
                # Special handling for plugin documentation
                return self._generate_plugin_doc_name(path_parts)
            else:
                # General module documentation
                doc_name = "_".join(path_parts) + ".md"
                return f"docs/{doc_name}"

        # For other files, use path-based naming
        path_without_readme = relative_path.replace("/README.md", "").replace(
            "README.md", ""
        )
        if path_without_readme:
            doc_name = path_without_readme.replace("/", "_") + ".md"
        else:
            doc_name = "misc.md"

        return f"docs/{doc_name}"

    def _generate_plugin_doc_name(self, path_parts: List[str]) -> str:
        """Generate documentation name for plugin README files."""

        # Remove "plugins" from path parts for cleaner names
        if "plugins" in path_parts:
            idx = path_parts.index("plugins")
            plugin_parts = path_parts[idx + 1 :]
        else:
            plugin_parts = path_parts

        if not plugin_parts:
            return "docs/plugins_overview.md"

        # Map common plugin patterns to documentation names
        if plugin_parts == ["environments"]:
            return "docs/environment_plugins.md"
        elif plugin_parts[:2] == ["environments", "execution_environment"]:
            if len(plugin_parts) == 2:
                return "docs/execution_environment.md"
            else:
                plugin_name = "_".join(plugin_parts[2:])
                return f"docs/execution_{plugin_name}.md"
        elif plugin_parts[:2] == ["environments", "network_environment"]:
            if len(plugin_parts) == 2:
                return "docs/network_environment.md"
            else:
                plugin_name = "_".join(plugin_parts[2:])
                return f"docs/network_{plugin_name}.md"
        elif plugin_parts[0] == "protocols":
            if len(plugin_parts) == 1:
                return "docs/protocol_plugins.md"
            elif plugin_parts[1] == "client_server":
                if len(plugin_parts) == 2:
                    return "docs/client_server_protocols.md"
                else:
                    protocol_name = "_".join(plugin_parts[2:])
                    return f"docs/protocol_{protocol_name}.md"
            elif plugin_parts[1] == "peer_to_peer":
                if len(plugin_parts) == 2:
                    return "docs/peer_to_peer_protocols.md"
                else:
                    protocol_name = "_".join(plugin_parts[2:])
                    return f"docs/protocol_{protocol_name}.md"
        elif plugin_parts[0] == "services":
            if len(plugin_parts) == 1:
                return "docs/service_plugins.md"
            elif plugin_parts[1] == "iut":
                if len(plugin_parts) == 2:
                    return "docs/iut_plugins.md"
                elif len(plugin_parts) >= 3 and plugin_parts[2] == "quic":
                    if len(plugin_parts) == 3:
                        return "docs/iut_quic_overview.md"
                    else:
                        impl_name = "_".join(plugin_parts[3:])
                        return f"docs/iut_quic_{impl_name}.md"
                else:
                    service_name = "_".join(plugin_parts[2:])
                    return f"docs/iut_{service_name}.md"
            elif plugin_parts[1] == "testers":
                if len(plugin_parts) == 2:
                    return "docs/testing_services.md"
                else:
                    tester_name = "_".join(plugin_parts[2:])
                    return f"docs/tester_{tester_name}.md"

        # Default: join all parts
        plugin_name = "_".join(plugin_parts)
        return f"docs/plugin_{plugin_name}.md"

    def _generate_dev_doc_name(self, relative_path: str) -> str:
        """Generate documentation name for development.md files."""
        # Remove the filename to get the directory path
        path = relative_path.rsplit("/development.md", 1)[0]
        # Remove the panther/plugins/ prefix
        if path == "panther/plugins":
            path = ""
        elif path.startswith("panther/plugins/"):
            path = path[len("panther/plugins/") :]

        mapping = {
            "": "plugin_development",
            "environments": "plugin_development_environment",
            "environments/network_environment": "plugin_development_network",
            "environments/execution_environment": "plugin_development_execution",
            "protocols": "protocol_development",
            "services": "service_development",
            "services/iut": "iut_development",
            "services/testers": "testers_development",
        }

        doc_name = mapping.get(path, path.replace("/", "_") + "_development")
        return f"docs/{doc_name}.md"

    def _assign_priority(self, relative_path: str, category: str) -> int:
        """Assign priority for documentation order."""

        # High priority (1-10): Essential project documentation
        if relative_path == "README.md":
            return 1
        elif relative_path in ["QUICK_START.md", "INSTALL.md"]:
            return 2
        elif relative_path in ["panther/config/README.md", "panther/core/README.md"]:
            return 3
        elif relative_path == "WORKFLOW.md":
            return 4
        elif relative_path == "panther/plugins/README.md":
            return 5

        # Medium priority (11-50): Plugin documentation
        elif category.endswith("_plugins"):
            return 15 + relative_path.count("/")

        # Lower priority (51+): Specific implementations and development docs
        elif "development.md" in relative_path:
            return 60
        elif category in ["developer", "testing"]:
            return 70
        elif category == "project_info":
            return 80
        else:
            return 90 + relative_path.count("/")

    def _find_module_context(self, readme_path: Path) -> Optional[str]:
        """Find associated Python module for context."""

        # Look for Python files in the same directory
        readme_dir = readme_path.parent
        python_files = list(readme_dir.glob("*.py"))

        if python_files:
            # Filter out __init__.py and get the main module
            main_modules = [f for f in python_files if f.name != "__init__.py"]
            if main_modules:
                return str(main_modules[0].relative_to(self.project_root))

        return None

    def analyze_python_modules(self) -> List[ModuleInfo]:
        """Analyze Python modules for context (optional enhancement)."""
        print("🐍 Analyzing Python modules...")

        modules = []
        python_files = list(self.panther_root.rglob("*.py"))

        # Exclude test files and virtual environments
        python_files = [
            f
            for f in python_files
            if not any(
                exclude in str(f) for exclude in [".venv", "__pycache__", "test_"]
            )
        ]

        for py_file in python_files:
            try:
                module_info = self._analyze_python_file(py_file)
                if module_info:
                    modules.append(module_info)
            except Exception as e:
                print(f"Warning: Could not analyze {py_file}: {e}")

        self.python_modules = modules
        print(f"✓ Analyzed {len(modules)} Python modules")
        return modules

    def _analyze_python_file(self, py_file: Path) -> Optional[ModuleInfo]:
        """Analyze a single Python file using AST."""

        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except Exception:
            return None

        classes = []
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):  # Skip private functions
                    functions.append(node.name)

        # Check for associated README
        readme_path = py_file.parent / "README.md"
        has_readme = readme_path.exists()

        relative_path = str(py_file.relative_to(self.project_root))

        return ModuleInfo(
            module_path=relative_path,
            classes=classes,
            functions=functions,
            has_readme=has_readme,
            readme_path=str(readme_path.relative_to(self.project_root))
            if has_readme
            else None,
        )

    def generate_build_dict(self) -> Dict[str, str]:
        """Generate the build_dict for panther_builder.py integration."""
        print("🔧 Generating build_dict...")

        if not self.readme_files:
            self.discover_readme_files()

        build_dict = {}

        for readme_info in self.readme_files:
            build_dict[readme_info.relative_path] = readme_info.suggested_doc_name

        print(f"✓ Generated {len(build_dict)} mappings")
        return build_dict

    def validate_mappings(self, build_dict: Dict[str, str]) -> List[str]:
        """Validate generated mappings for potential issues."""
        print("✅ Validating mappings...")

        issues = []
        doc_names = set()

        for source, target in build_dict.items():
            # Check for duplicate target names
            if target in doc_names:
                issues.append(f"Duplicate target: {target}")
            else:
                doc_names.add(target)

            # Check if source file exists
            source_path = self.project_root / source
            if not source_path.exists():
                issues.append(f"Source file missing: {source}")

            # Check for potential naming conflicts
            if not target.startswith("docs/"):
                issues.append(f"Target not in docs/: {target}")

            if not target.endswith(".md"):
                issues.append(f"Target not markdown: {target}")

        if issues:
            print(f"⚠️  Found {len(issues)} validation issues")
        else:
            print("✓ All mappings validated successfully")

        return issues

    def export_analysis(self, output_file: Path) -> None:
        """Export complete analysis to JSON for further processing."""

        analysis_data = {
            "project_root": str(self.project_root),
            "discovery_timestamp": str(self._get_timestamp()),
            "readme_files": [asdict(readme) for readme in self.readme_files],
            "python_modules": [asdict(module) for module in self.python_modules],
            "build_dict": self.generate_build_dict(),
            "validation_issues": self.validate_mappings(self.generate_build_dict()),
        }

        output_file.write_text(json.dumps(analysis_data, indent=2))
        print(f"📄 Analysis exported to {output_file}")

    def _get_timestamp(self) -> str:
        """Get current timestamp for analysis."""
        from datetime import datetime

        return datetime.now().isoformat()


def main():
    """Main entry point for command-line usage."""

    # Find project root (where panther_builder.py is located)
    current_dir = Path.cwd()
    project_root = None

    # Look for panther_builder.py to identify project root
    for parent in [current_dir] + list(current_dir.parents):
        if (parent / "panther_builder.py").exists():
            project_root = parent
            break

    if not project_root:
        print("❌ Error: Could not find project root (looking for panther_builder.py)")
        sys.exit(1)

    print(f"🏠 Project root: {project_root}")

    # Initialize discovery system
    discovery = PantherSourceDiscovery(project_root)

    # Parse command line arguments
    if len(sys.argv) < 2:
        command = "--generate-build-dict"
    else:
        command = sys.argv[1]

    if command == "--analyze-structure":
        # Full analysis with Python modules
        discovery.discover_readme_files()
        discovery.analyze_python_modules()

        print(f"\n📊 Analysis Summary:")
        print(f"README files: {len(discovery.readme_files)}")
        print(f"Python modules: {len(discovery.python_modules)}")

        # Export detailed analysis
        output_file = (
            project_root / "panther" / "tools" / "docs_gen" / "analysis_output.json"
        )
        discovery.export_analysis(output_file)

    elif command == "--generate-build-dict":
        # Generate and display build_dict
        discovery.discover_readme_files()
        build_dict = discovery.generate_build_dict()

        print(f"\n📚 Generated build_dict ({len(build_dict)} mappings):")
        print("build_dict = {")
        for source, target in build_dict.items():
            print(f'    "{source}": "{target}",')
        print("}")

        # Save to file for integration
        output_file = (
            project_root / "panther" / "tools" / "docs_gen" / "generated_build_dict.py"
        )
        output_file.write_text(f"# Generated build_dict\nbuild_dict = {{\n")
        for source, target in build_dict.items():
            output_file.write_text(
                output_file.read_text() + f'    "{source}": "{target}",\n'
            )
        output_file.write_text(output_file.read_text() + "}\n")

        print(f"💾 Build dict saved to: {output_file}")

    elif command == "--validate-mappings":
        # Validate existing mappings
        discovery.discover_readme_files()
        build_dict = discovery.generate_build_dict()
        issues = discovery.validate_mappings(build_dict)

        if issues:
            print("\n⚠️  Validation Issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✅ All mappings validated successfully!")

    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands:")
        print("  --analyze-structure   : Full analysis with export")
        print("  --generate-build-dict : Generate build_dict only")
        print("  --validate-mappings   : Validate generated mappings")
        sys.exit(1)


if __name__ == "__main__":
    main()
