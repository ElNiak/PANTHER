"""
Unified Plugin Migration Tool for PANTHER

This module provides a comprehensive plugin migration and management utility
that combines enhanced introspection capabilities with practical migration features.
"""

import ast
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import yaml
except ImportError:
    yaml = None

from panther.plugins.plugin_manifest import PluginDependency, PluginManifest, PluginType

# Optional imports for enhanced features
try:
    from panther.tools.plugins.external_dependency_resolver import (
        ExternalDependencyResolver,
    )

    HAS_EXTERNAL_RESOLVER = True
except ImportError:
    HAS_EXTERNAL_RESOLVER = False

try:
    from panther.plugins.plugin_manager import PluginManager

    HAS_MANAGERS = True
except ImportError:
    HAS_MANAGERS = False


class PluginAnalyzer:
    """Analyze plugin code to extract metadata and dependencies."""

    # Known plugin import patterns
    IMPORT_TO_DEPENDENCY = {
        "panther.plugins.protocols": ("protocols", PluginType.PROTOCOL),
        "panther.plugins.services.services_interface": ("services", PluginType.SERVICE),
        "panther.plugins.environments.environment_interface": (
            "environments",
            PluginType.ENVIRONMENT,
        ),
        "panther.plugins.services.testers.tester_interface": (
            "testers",
            PluginType.TESTER,
        ),
    }

    # External runtime dependencies patterns
    EXTERNAL_TOOLS = {
        "docker": r"docker|container|dockerfile",
        "docker-compose": r"docker-compose|compose\.(Union[yml, yaml])",
        "valgrind": r"valgrind|memcheck|helgrind",
        "strace": r"strace|syscall|trace",
        "gperf": r"gperftools|profiling|tcmalloc",
        "shadow": r"shadow\s*simulator|network\s*simulation",
        "z3": r"z3|smt|solver",
        "ivy": r"ivy|formal|verification",
    }

    def __init__(self):
        self.logger = logging.getLogger("PluginAnalyzer")

    def analyze_plugin_directory(self, plugin_path: Path) -> Dict[str, Any]:
        """
        Analyze a plugin directory to extract comprehensive metadata.

        Returns:
            Dictionary with analysis results including decorators, dependencies, etc.
        """
        analysis = {
            "has_decorator": False,
            "decorator_info": {},
            "plugin_dependencies": [],
            "external_dependencies": [],
            "is_category": False,
            "implementations": [],
            "metadata": {},
        }

        # Analyze Python files
        for py_file in plugin_path.glob("**/*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # Check for decorator
                if "@register_plugin" in content:
                    analysis["has_decorator"] = True
                    decorator_info = self._extract_decorator_info(py_file)
                    if decorator_info:
                        analysis["decorator_info"] = decorator_info

                # Analyze imports and dependencies
                deps = self._analyze_dependencies(content)
                analysis["plugin_dependencies"].extend(deps["plugin"])
                analysis["external_dependencies"].extend(deps["external"])

            except Exception as e:
                self.logger.warning(f"Failed to analyze {py_file}: {e}")

        # Determine if this is a category plugin
        analysis["is_category"] = self._is_category_plugin(plugin_path)
        if analysis["is_category"]:
            analysis["implementations"] = self._find_implementations(plugin_path)

        # Extract additional metadata
        analysis["metadata"] = self._extract_metadata(plugin_path)

        # Check for external dependencies in Dockerfile
        dockerfile = plugin_path / "Dockerfile"
        if dockerfile.exists():
            analysis["external_dependencies"].append("docker>=20.0")
            docker_deps = self._analyze_dockerfile(dockerfile)
            analysis["external_dependencies"].extend(docker_deps)

        # Remove duplicates
        analysis["external_dependencies"] = list(set(analysis["external_dependencies"]))

        return analysis

    def _extract_decorator_info(self, py_file: Path) -> Dict[str, Any]:
        """Extract information from @register_plugin decorator using AST."""
        try:
            with open(py_file, encoding="utf-8") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for decorator in node.decorator_list:
                        if (
                            isinstance(decorator, ast.Call)
                            and hasattr(decorator.func, "id")
                            and decorator.func.id == "register_plugin"
                        ):

                            info = {"class_name": node.name}
                            for keyword in decorator.keywords:
                                if isinstance(keyword.value, ast.Constant):
                                    info[keyword.arg] = keyword.value.value
                                elif isinstance(keyword.value, ast.List):
                                    info[keyword.arg] = [
                                        elt.value
                                        for elt in keyword.value.elts
                                        if isinstance(elt, ast.Constant)
                                    ]
                            return info
        except Exception as e:
            self.logger.warning(f"Failed to parse decorator in {py_file}: {e}")

        return {}

    def _analyze_dependencies(self, content: str) -> Dict[str, List[str]]:
        """Analyze content for plugin and external dependencies."""
        deps = {"plugin": [], "external": []}

        # Check for plugin dependencies via imports
        for pattern, (dep_name, dep_type) in self.IMPORT_TO_DEPENDENCY.items():
            if pattern in content:
                deps["plugin"].append(f"{dep_name}:{dep_type.value}")

        # Check for external tool references
        for tool, pattern in self.EXTERNAL_TOOLS.items():
            if re.search(pattern, content, re.IGNORECASE):
                if tool == "docker":
                    deps["external"].append("docker>=20.0")
                elif tool == "valgrind":
                    deps["external"].append("valgrind>=3.15")
                else:
                    deps["external"].append(tool)

        return deps

    def _is_category_plugin(self, plugin_path: Path) -> bool:
        """Determine if this is a category plugin by examining structure."""
        # Check for implementation subdirectories
        subdirs = [
            d
            for d in plugin_path.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ]

        # If has subdirectories with Python files, likely a category
        for subdir in subdirs:
            if any(subdir.glob("*.py")):
                return True

        # Check if no main implementation file
        main_files = ["__init__.py", "config_schema.py", "README.md"]
        py_files = [f for f in plugin_path.glob("*.py") if f.name not in main_files]

        return not py_files and subdirs

    def _find_implementations(self, category_path: Path) -> List[str]:
        """Find implementation plugins within a category."""
        implementations = []
        for subdir in category_path.iterdir():
            if (
                subdir.is_dir()
                and not subdir.name.startswith("_")
                and any(f.name != "__init__.py" for f in subdir.glob("*.py"))
            ):
                implementations.append(subdir.name)
        return implementations

    def _extract_metadata(self, plugin_path: Path) -> Dict[str, Any]:
        """Extract metadata from README and path analysis."""
        metadata = {}

        # Read README for description
        readme_path = plugin_path / "README.md"
        if readme_path.exists():
            try:
                with open(readme_path, encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")
                    for line in lines:
                        if line.strip() and not line.startswith("#"):
                            metadata["description"] = line.strip()
                            break
            except Exception:
                pass

        # Extract type-specific metadata from path
        path_str = str(plugin_path).lower()
        if "quic" in path_str:
            metadata["supported_protocols"] = ["quic"]
            metadata["tags"] = ["quic", "transport"]

            # Implementation-specific capabilities
            impl_name = plugin_path.name.lower()
            if impl_name == "picoquic":
                metadata["capabilities"] = ["rfc9000", "0rtt", "migration", "http3"]
            elif impl_name == "aioquic":
                metadata["capabilities"] = ["rfc9000", "http3", "webtransport", "async"]

        elif "docker" in path_str:
            metadata["capabilities"] = ["container_orchestration"]
            metadata["tags"] = ["docker", "containers"]

        elif "shadow" in path_str:
            metadata["capabilities"] = ["network_simulation", "deterministic"]
            metadata["tags"] = ["shadow", "simulation"]

        elif "ivy" in path_str:
            metadata["capabilities"] = ["formal_verification", "protocol_compliance"]
            metadata["tags"] = ["testing", "formal", "ivy"]

        return metadata

    def _analyze_dockerfile(self, dockerfile: Path) -> List[str]:
        """Analyze Dockerfile for external dependencies."""
        deps = []
        try:
            with open(dockerfile, encoding="utf-8") as f:
                content = f.read()
                if "valgrind" in content.lower():
                    deps.append("valgrind>=3.15")
                if "cmake" in content.lower():
                    deps.append("cmake>=3.10")
                if "gcc" in content.lower() or "g++" in content.lower():
                    deps.append("gcc")
        except Exception:
            pass
        return deps


class PluginMigrationTool:
    """
    Unified plugin migration tool that provides comprehensive migration capabilities.
    """

    def __init__(self):
        self.logger = logging.getLogger("PluginMigrationTool")
        self.analyzer = PluginAnalyzer()

        # Optional components
        self.external_resolver = None
        if HAS_EXTERNAL_RESOLVER:
            try:
                self.external_resolver = ExternalDependencyResolver()
            except Exception:
                pass

    def scan_plugins(
        self, base_path: Path, include_manifested: bool = False
    ) -> Dict[str, Any]:
        """
        Scan for plugins and return comprehensive analysis.

        Args:
            base_path: Base path to scan
            include_manifested: Include plugins that already have manifests

        Returns:
            Scan results with plugin information
        """
        results = {
            "plugins_found": [],
            "categories": [],
            "implementations": [],
            "manifested": [],
            "unmanifested": [],
            "analysis_errors": [],
        }

        plugin_dirs = self._find_plugin_directories(base_path)

        for plugin_dir in plugin_dirs:
            try:
                # Check for existing manifest
                existing_manifest = self._find_existing_manifest(plugin_dir)
                has_manifest = existing_manifest is not None

                plugin_info = {
                    "path": str(plugin_dir),
                    "name": plugin_dir.name,
                    "has_manifest": has_manifest,
                    "manifest_path": (
                        str(existing_manifest) if existing_manifest else None
                    ),
                    "plugin_type": self._infer_plugin_type(plugin_dir),
                }

                if include_manifested or not has_manifest:
                    # Perform detailed analysis
                    analysis = self.analyzer.analyze_plugin_directory(plugin_dir)
                    plugin_info.update(analysis)

                results["plugins_found"].append(plugin_info)

                if plugin_info.get("is_category"):
                    results["categories"].append(plugin_info)
                else:
                    results["implementations"].append(plugin_info)

                if has_manifest:
                    results["manifested"].append(plugin_info)
                else:
                    results["unmanifested"].append(plugin_info)

            except Exception as e:
                results["analysis_errors"].append(
                    {"path": str(plugin_dir), "error": str(e)}
                )

        return results

    def generate_manifest(
        self, plugin_path: Path, plugin_type: Optional[PluginType] = None
    ) -> PluginManifest:
        """
        Generate a comprehensive manifest for a plugin.

        Args:
            plugin_path: Path to plugin directory
            plugin_type: Override plugin type detection

        Returns:
            Generated PluginManifest
        """
        # Analyze the plugin
        analysis = self.analyzer.analyze_plugin_directory(plugin_path)

        # Use decorator info if available, otherwise infer
        if analysis["has_decorator"] and analysis["decorator_info"]:
            return self._manifest_from_decorator(
                plugin_path, analysis["decorator_info"]
            )

        # Generate from analysis
        plugin_type = plugin_type or self._infer_plugin_type(plugin_path)
        if not plugin_type:
            raise ValueError(f"Could not determine plugin type for {plugin_path}")

        # Parse plugin dependencies
        plugin_deps = []
        for dep_str in analysis["plugin_dependencies"]:
            if ":" in dep_str:
                name, type_str = dep_str.split(":", 1)
                try:
                    dep_type = PluginType[type_str.upper()]
                    plugin_deps.append(
                        PluginDependency(name=name, plugin_type=dep_type)
                    )
                except (KeyError, ValueError):
                    pass

        # Create manifest
        manifest = PluginManifest(
            name=plugin_path.name,
            version="1.0.0",
            type=plugin_type,
            author="PANTHER Team",
            description=analysis["metadata"].get(
                "description", f"Plugin: {plugin_path.name}"
            ),
            file_path=str(plugin_path),
            dependencies=plugin_deps,
            external_dependencies=analysis["external_dependencies"],
            is_category=analysis["is_category"],
            implementations=analysis["implementations"],
            supported_protocols=analysis["metadata"].get("supported_protocols", []),
            capabilities=analysis["metadata"].get("capabilities", []),
            tags=analysis["metadata"].get("tags", []),
        )

        return manifest

    def migrate_plugins(
        self,
        base_path: Path,
        dry_run: bool = True,
        force: bool = False,
        update_existing: bool = True,
    ) -> Dict[str, Any]:
        """
        Migrate plugins by generating or updating manifests.

        Args:
            base_path: Base path to scan
            dry_run: Don't write files if True
            force: Overwrite existing manifests completely
            update_existing: Update existing manifests with new fields

        Returns:
            Migration results
        """
        if yaml is None:
            raise RuntimeError(
                "PyYAML is required for migration. Install with: pip install pyyaml"
            )

        results = {
            "success": True,
            "created": [],
            "updated": [],
            "skipped": [],
            "errors": [],
        }

        scan_results = self.scan_plugins(base_path, include_manifested=True)

        for plugin_info in scan_results["plugins_found"]:
            try:
                plugin_path = Path(plugin_info["path"])
                has_manifest = plugin_info["has_manifest"]

                if has_manifest and not force and not update_existing:
                    results["skipped"].append(plugin_info["name"])
                    continue

                # Generate new manifest
                new_manifest = self.generate_manifest(
                    plugin_path, plugin_info["plugin_type"]
                )

                if has_manifest and update_existing and not force:
                    # Update existing manifest
                    existing_path = Path(plugin_info["manifest_path"])
                    enhanced_manifest = self._enhance_existing_manifest(
                        existing_path, new_manifest
                    )

                    if not dry_run:
                        self._write_manifest(enhanced_manifest, existing_path)

                    results["updated"].append(
                        {
                            "name": enhanced_manifest.name,
                            "path": str(plugin_path),
                            "action": "updated",
                        }
                    )
                else:
                    # Create new or force overwrite
                    manifest_path = plugin_path / "plugin.yaml"
                    if has_manifest:
                        manifest_path = Path(plugin_info["manifest_path"])

                    if not dry_run:
                        self._write_manifest(new_manifest, manifest_path)

                    action = "overwritten" if has_manifest else "created"
                    results["created"].append(
                        {
                            "name": new_manifest.name,
                            "path": str(plugin_path),
                            "action": action,
                        }
                    )

            except Exception as e:
                results["errors"].append(
                    {
                        "name": plugin_info["name"],
                        "path": plugin_info["path"],
                        "error": str(e),
                    }
                )
                results["success"] = False

        return results

    def validate_external_dependencies(
        self, manifest: PluginManifest
    ) -> Dict[str, Any]:
        """Validate external dependencies if resolver is available."""
        if not self.external_resolver:
            return {
                "satisfied": [],
                "missing": [],
                "errors": [
                    {
                        "dependency": "all",
                        "error": "External dependency resolver not available",
                    }
                ],
            }

        return self.external_resolver.validate_dependencies(
            manifest.external_dependencies
        )

    def migrate_plugin_manager(self, old_manager, event_manager=None):
        """Migrate from old PluginManager to PluginManager."""
        if not HAS_MANAGERS:
            raise RuntimeError("Plugin managers not available for migration")

        # Extract plugin directories
        plugin_dirs = []
        if hasattr(old_manager, "plugin_manager") and old_manager.plugin_manager:
            base_dir = getattr(old_manager.plugin_manager, "plugins_base_dir", None)
            if base_dir:
                plugin_dirs.append(str(base_dir))

        # Create unified manager
        unified_manager = PluginManager(
            plugin_manager=old_manager.plugins_loader,
            plugin_directories=plugin_dirs,
            event_manager=event_manager or getattr(old_manager, "event_manager", None),
        )

        # Migrate cached plugins
        for attr in [
            "protocol_plugins",
            "network_environment_plugins",
            "execution_environment_plugins",
        ]:
            if hasattr(old_manager, attr):
                setattr(unified_manager, attr, getattr(old_manager, attr))

        return unified_manager

    def _manifest_from_decorator(
        self, plugin_path: Path, decorator_info: Dict[str, Any]
    ) -> PluginManifest:
        """Create manifest from decorator information."""
        plugin_type = PluginType[decorator_info.get("plugin_type", "SERVICE").upper()]

        # Parse dependencies
        plugin_deps = []
        for dep in decorator_info.get("dependencies", []):
            if isinstance(dep, str) and ":" in dep:
                name, type_str = dep.split(":", 1)
                try:
                    dep_type = PluginType[
                        type_str.split(">=")[0].split("==")[0].upper()
                    ]
                    plugin_deps.append(
                        PluginDependency(name=name, plugin_type=dep_type)
                    )
                except (KeyError, ValueError):
                    pass

        return PluginManifest(
            name=decorator_info.get("name", plugin_path.name),
            version=decorator_info.get("version", "1.0.0"),
            type=plugin_type,
            author=decorator_info.get("author", "PANTHER Team"),
            description=decorator_info.get("description", ""),
            file_path=str(plugin_path),
            dependencies=plugin_deps,
            external_dependencies=decorator_info.get("external_dependencies", []),
            supported_protocols=decorator_info.get("supported_protocols", []),
            capabilities=decorator_info.get("capabilities", []),
            tags=decorator_info.get("tags", []),
        )

    def _find_plugin_directories(self, base_path: Path) -> List[Path]:
        """Find all directories that contain plugins."""
        plugin_dirs = []

        # Auto-detect if we're in the project root or within panther directory
        if (base_path / "panther" / "plugins").exists():
            # We're in project root
            plugins_root = base_path / "panther" / "plugins"
        elif (base_path / "plugins").exists():
            # We're in panther directory
            plugins_root = base_path / "plugins"
        elif base_path.name == "plugins":
            # We're in the plugins directory
            plugins_root = base_path
        else:
            # Search for plugins directory in the current path and parents
            plugins_root = None
            current = base_path
            for _ in range(5):  # Search up to 5 levels up
                if (current / "plugins").exists():
                    plugins_root = current / "plugins"
                    break
                if (current / "panther" / "plugins").exists():
                    plugins_root = current / "panther" / "plugins"
                    break
                current = current.parent

            if not plugins_root:
                return []

        # Known plugin locations relative to plugins root
        known_paths = [
            "services/iut",
            "services/testers",
            "environments/network_environment",
            "environments/execution_environment",
            "protocols",
        ]

        for known_path in known_paths:
            full_path = plugins_root / known_path
            if full_path.exists():
                for item in full_path.iterdir():
                    if item.is_dir() and not item.name.startswith("_"):
                        plugin_dirs.append(item)
                        # Check for nested implementations
                        for subitem in item.iterdir():
                            if (
                                subitem.is_dir()
                                and not subitem.name.startswith("_")
                                and any(subitem.glob("*.py"))
                            ):
                                plugin_dirs.append(subitem)

        return plugin_dirs

    def _find_existing_manifest(self, plugin_dir: Path) -> Optional[Path]:
        """Find existing manifest file."""
        manifest_files = ["plugin.yaml", "plugin.yml", "manifest.yaml", "manifest.yml"]
        for manifest_file in manifest_files:
            manifest_path = plugin_dir / manifest_file
            if manifest_path.exists():
                return manifest_path
        return None

    def _infer_plugin_type(self, path: Path) -> Optional[PluginType]:
        """Infer plugin type from path structure."""
        path_str = str(path).lower()

        if "services" in path_str:
            if "iut" in path_str:
                return PluginType.IUT
            elif "testers" in path_str:
                return PluginType.TESTER
            else:
                return PluginType.SERVICE
        elif "environments" in path_str:
            return PluginType.ENVIRONMENT
        elif "protocols" in path_str:
            return PluginType.PROTOCOL
        elif "observers" in path_str:
            return PluginType.OBSERVER

        return None

    def _enhance_existing_manifest(
        self, existing_path: Path, new_manifest: PluginManifest
    ) -> PluginManifest:
        """Enhance existing manifest with new fields while preserving existing data."""
        with open(existing_path, encoding="utf-8") as f:
            existing_data = yaml.safe_load(f) or {}

        # Start with existing data
        enhanced_data = existing_data.copy()

        # Add enhanced fields if missing or empty
        enhancements = {
            "external_dependencies": new_manifest.external_dependencies,
            "is_category": new_manifest.is_category,
            "implementations": (
                new_manifest.implementations if new_manifest.is_category else []
            ),
        }

        # Only enhance empty fields
        for field in ["capabilities", "supported_protocols", "tags"]:
            if not existing_data.get(field) and getattr(new_manifest, field):
                enhancements[field] = getattr(new_manifest, field)

        # Update description if auto-generated
        if (
            existing_data.get("description", "").startswith("Auto-generated")
            and new_manifest.description
            and not new_manifest.description.startswith("Auto-generated")
        ):
            enhancements["description"] = new_manifest.description

        # Apply enhancements
        for key, value in enhancements.items():
            if value:
                enhanced_data[key] = value

        # Create enhanced manifest
        dependencies = []
        for dep_data in enhanced_data.get("dependencies", []):
            if isinstance(dep_data, dict):
                dependencies.append(
                    PluginDependency(
                        name=dep_data.get("name", ""),
                        plugin_type=(
                            PluginType[dep_data.get("type", "SERVICE").upper()]
                            if dep_data.get("type")
                            else None
                        ),
                        version_spec=dep_data.get("version_spec", ""),
                    )
                )

        return PluginManifest(
            name=enhanced_data.get("name", new_manifest.name),
            version=enhanced_data.get("version", new_manifest.version),
            type=PluginType[enhanced_data.get("type", new_manifest.type.value).upper()],
            author=enhanced_data.get("author", new_manifest.author),
            description=enhanced_data.get("description", new_manifest.description),
            file_path=str(existing_path.parent),
            dependencies=dependencies,
            external_dependencies=enhanced_data.get("external_dependencies", []),
            is_category=enhanced_data.get("is_category", False),
            implementations=enhanced_data.get("implementations", []),
            supported_protocols=enhanced_data.get("supported_protocols", []),
            capabilities=enhanced_data.get("capabilities", []),
            tags=enhanced_data.get("tags", []),
        )

    def _write_manifest(self, manifest: PluginManifest, path: Path):
        """Write manifest to YAML file."""
        # Convert to dict
        manifest_dict = {
            "name": manifest.name,
            "version": str(manifest.version),
            "type": manifest.type.value.lower(),
            "description": manifest.description,
            "author": manifest.author,
        }

        # Add optional fields
        if manifest.dependencies:
            manifest_dict["dependencies"] = [
                {
                    "name": dep.name,
                    "type": dep.plugin_type.value.lower() if dep.plugin_type else None,
                    "version_spec": dep.version_spec,
                }
                for dep in manifest.dependencies
            ]

        if manifest.external_dependencies:
            manifest_dict["external_dependencies"] = manifest.external_dependencies

        if manifest.is_category:
            manifest_dict["is_category"] = True
            if manifest.implementations:
                manifest_dict["implementations"] = manifest.implementations

        for field in ["supported_protocols", "capabilities", "tags"]:
            value = getattr(manifest, field)
            if value:
                manifest_dict[field] = value

        # Clean up empty values
        manifest_dict = {
            k: v for k, v in manifest_dict.items() if v not in [None, [], "", {}]
        }

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                manifest_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

        self.logger.info(
            f"{'Updated' if path.exists() else 'Created'} manifest at: {path}"
        )


def create_cli():
    """Create command-line interface for the plugin migration tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="PANTHER Plugin Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan for plugins
  panther-plugin-tool scan

  # Generate manifests (dry run)
  panther-plugin-tool migrate --dry-run

  # Actually generate manifests
  panther-plugin-tool migrate

  # Update existing manifests only
  panther-plugin-tool migrate --update-only

  # Validate specific plugin
  panther-plugin-tool validate --plugin services/iut/picoquic
        """,
    )

    parser.add_argument(
        "action",
        choices=["scan", "migrate", "validate", "check-deps"],
        help="Action to perform",
    )

    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Base path to scan (default: current directory)",
    )

    parser.add_argument(
        "--plugin", type=str, help="Specific plugin path relative to base path"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing manifests completely"
    )

    parser.add_argument(
        "--update-only",
        action="store_true",
        help="Only update existing manifests, don't create new ones",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    # Create tool
    tool = PluginMigrationTool()

    if args.action == "scan":
        results = tool.scan_plugins(args.path, include_manifested=True)

        print(f"\nPlugin Scan Results for {args.path}:")
        print(f"- Total plugins found: {len(results['plugins_found'])}")
        print(f"- With manifests: {len(results['manifested'])}")
        print(f"- Without manifests: {len(results['unmanifested'])}")
        print(f"- Categories: {len(results['categories'])}")
        print(f"- Implementations: {len(results['implementations'])}")

        if results["analysis_errors"]:
            print(f"\nAnalysis errors: {len(results['analysis_errors'])}")
            for error in results["analysis_errors"]:
                print(f"  - {error['path']}: {error['error']}")

        if args.verbose:
            print("\nDetailed results:")
            for plugin in results["plugins_found"]:
                print(
                    f"  - {plugin['name']} ({plugin.get('plugin_type', 'unknown')}) "
                    f"[{'✓' if plugin['has_manifest'] else '✗'}]"
                )

    elif args.action == "migrate":
        try:
            results = tool.migrate_plugins(
                args.path,
                dry_run=args.dry_run,
                force=args.force,
                update_existing=not args.update_only,
            )

            if args.dry_run:
                print("\nDRY RUN - No files were modified")

            print("\nMigration Results:")
            print(f"- Created/Overwritten: {len(results['created'])}")
            print(f"- Updated: {len(results['updated'])}")
            print(f"- Skipped: {len(results['skipped'])}")
            print(f"- Errors: {len(results['errors'])}")

            if results["created"]:
                print("\nCreated/Overwritten:")
                for item in results["created"]:
                    print(f"  - {item['name']} ({item['action']})")

            if results["updated"]:
                print("\nUpdated:")
                for item in results["updated"]:
                    print(f"  - {item['name']}")

            if results["errors"]:
                print("\nErrors:")
                for error in results["errors"]:
                    print(f"  - {error['name']}: {error['error']}")

        except RuntimeError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif args.action == "validate":
        if not args.plugin:
            print("Error: --plugin required for validate action")
            sys.exit(1)

        plugin_path = args.path / args.plugin
        if not plugin_path.exists():
            print(f"Error: Plugin path not found: {plugin_path}")
            sys.exit(1)

        try:
            manifest = tool.generate_manifest(plugin_path)

            print(f"\nGenerated manifest for {manifest.name}:")
            print(f"- Type: {manifest.type.value}")
            print(f"- Version: {manifest.version}")
            print(f"- Is Category: {manifest.is_category}")

            if manifest.implementations:
                print(f"- Implementations: {', '.join(manifest.implementations)}")

            if manifest.dependencies:
                print("- Plugin Dependencies:")
                for dep in manifest.dependencies:
                    print(
                        f"  - {dep.name} ({dep.plugin_type.value if dep.plugin_type else 'unknown'})"
                    )

            if manifest.external_dependencies:
                print("- External Dependencies:")
                for dep in manifest.external_dependencies:
                    print(f"  - {dep}")

        except Exception as e:
            print(f"Error validating plugin: {e}")
            sys.exit(1)

    elif args.action == "check-deps":
        if not args.plugin:
            print("Error: --plugin required for check-deps action")
            sys.exit(1)

        plugin_path = args.path / args.plugin
        manifest_path = plugin_path / "plugin.yaml"

        if not manifest_path.exists():
            print(f"Error: No manifest found at {manifest_path}")
            sys.exit(1)

        try:
            with open(manifest_path) as f:
                manifest_data = yaml.safe_load(f)

            manifest = PluginManifest(
                name=manifest_data["name"],
                version=manifest_data["version"],
                type=PluginType[manifest_data["type"].upper()],
                external_dependencies=manifest_data.get("external_dependencies", []),
            )

            results = tool.validate_external_dependencies(manifest)

            print(f"\nExternal dependency check for {manifest.name}:")

            if results["satisfied"]:
                print("\nSatisfied dependencies:")
                for dep in results["satisfied"]:
                    print(f"  ✓ {dep['dependency']}: {dep['message']}")

            if results["missing"]:
                print("\nMissing dependencies:")
                for dep in results["missing"]:
                    print(f"  ✗ {dep['dependency']}: {dep['message']}")

            if results["errors"]:
                print("\nErrors:")
                for dep in results["errors"]:
                    print(f"  ! {dep['dependency']}: {dep['error']}")

        except Exception as e:
            print(f"Error checking dependencies: {e}")
            sys.exit(1)


if __name__ == "__main__":
    create_cli()
