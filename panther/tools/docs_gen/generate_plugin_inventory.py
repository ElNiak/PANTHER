#!/usr/bin/env python3
"""Plugin Inventory Generator (Registry-Based).

Generates an inventory of all PANTHER plugins by querying the decorator-based
plugin registry rather than walking the filesystem. This follows the code-as-docs
principle: metadata lives in code (decorators, docstrings), not standalone markdown.

The script triggers plugin discovery (which imports plugin modules), then reads
rich metadata from the global registries populated by @register_plugin() and
@register_protocol() decorators.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _setup_import_path():
    """Ensure the project root is on sys.path for imports."""
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def _discover_all_plugins():
    """Trigger plugin discovery and return registry contents.

    Returns:
        Tuple of (plugin_manifests, protocol_metadata) where:
        - plugin_manifests: list of PluginManifest from @register_plugin
        - protocol_metadata: dict of protocol_id -> metadata from @register_protocol
    """
    from panther.plugins.core.plugin_discovery import PluginDiscovery

    # Discover plugins (triggers imports which populate the registries)
    discovery = PluginDiscovery()
    discovery.discover_plugins()

    from panther.plugins.core.plugin_decorators import (
        get_protocol_plugins,
        list_all_decorated_plugins,
    )

    return list_all_decorated_plugins(), get_protocol_plugins()


def _get_plugin_dir(file_path: Optional[str]) -> Optional[Path]:
    """Derive the plugin directory from its file_path."""
    if not file_path:
        return None
    p = Path(file_path)
    if p.is_file():
        p = p.parent
    return p


def _has_readme(plugin_dir: Optional[Path]) -> bool:
    """Check if a plugin directory has a README.md (legacy docs)."""
    if not plugin_dir:
        return False
    return (plugin_dir / "README.md").exists()


def _has_docstring(manifest) -> bool:
    """Check if the plugin class has a meaningful docstring."""
    return bool(manifest.description and len(manifest.description.strip()) > 10)


def _get_relative_path(file_path: Optional[str], plugin_root: Path) -> str:
    """Get path relative to the plugin root for display."""
    if not file_path:
        return "unknown"
    try:
        p = Path(file_path)
        if p.is_file():
            p = p.parent
        return str(p.relative_to(plugin_root))
    except ValueError:
        return str(file_path)


def _determine_dev_status(manifest, plugin_dir: Optional[Path]) -> str:
    """Determine development status from tags or README fallback.

    Checks manifest.tags for 'wip' or 'experimental' first,
    falls back to README.md warning check for backward compat.
    """
    tags = manifest.tags or []
    if "wip" in tags or "experimental" in tags:
        return "experimental"

    # Fallback: check README for development status warning
    if plugin_dir:
        readme_path = plugin_dir / "README.md"
        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding="utf-8")
                if '!!! warning "Development Status"' in content:
                    return "not totally working"
            except Exception as e:
                logger.debug("Failed to read README for plugin inventory: %s", e)
            return "ok"

    # No README and no tags — use docstring presence as proxy
    if _has_docstring(manifest):
        return "ok"
    return "unknown"


# -- Grouping helpers --

# Maps PluginType values to (category, subcategory) for inventory structure
_TYPE_TO_GROUP = {
    "execution_environment": ("Environments", "Execution Environment"),
    "network_environment": ("Environments", "Network Environment"),
    "iut": ("Services", "IUT"),
    "tester": ("Services", "Testers"),
    "observer": ("Services", "Observers"),
}


def _group_plugins(manifests, plugin_root: Path) -> Dict[str, Dict[str, list]]:
    """Group plugin manifests into category/subcategory structure."""
    grouped: Dict[str, Dict[str, list]] = {}

    for manifest in manifests:
        type_val = (
            manifest.type.value
            if hasattr(manifest.type, "value")
            else str(manifest.type)
        )
        group_info = _TYPE_TO_GROUP.get(type_val)
        if not group_info:
            continue

        category, subcategory = group_info
        if category not in grouped:
            grouped[category] = {}
        if subcategory not in grouped[category]:
            grouped[category][subcategory] = []

        plugin_dir = _get_plugin_dir(manifest.file_path)
        rel_path = _get_relative_path(manifest.file_path, plugin_root)

        grouped[category][subcategory].append(
            {
                "name": manifest.name,
                "path": rel_path,
                "version": manifest.version,
                "description": manifest.description or "",
                "capabilities": manifest.capabilities or [],
                "supported_protocols": manifest.supported_protocols or [],
                "tags": manifest.tags or [],
                "has_docs": _has_readme(plugin_dir) or _has_docstring(manifest),
                "development_status": _determine_dev_status(manifest, plugin_dir),
            }
        )

    return grouped


def _group_protocols(protocol_plugins, plugin_root: Path) -> Dict[str, list]:
    """Group protocol plugins by type (client_server, peer_to_peer)."""
    grouped: Dict[str, list] = {}

    for _, (_cls, metadata) in protocol_plugins.items():
        proto_type = metadata.get("type", "client_server")
        subcategory = proto_type.replace("_", " ").title()

        if subcategory not in grouped:
            grouped[subcategory] = []

        # Derive path from class module
        class_name = metadata.get("class_name", "")
        file_path = None
        if class_name:
            try:
                module_name = class_name.rsplit(".", 1)[0]
                import importlib

                mod = importlib.import_module(module_name)
                file_path = getattr(mod, "__file__", None)
            except Exception:
                pass

        plugin_dir = _get_plugin_dir(file_path) if file_path else None
        rel_path = (
            _get_relative_path(file_path, plugin_root) if file_path else "unknown"
        )

        grouped[subcategory].append(
            {
                "name": metadata["name"],
                "path": rel_path,
                "version": metadata.get("default_version", ""),
                "description": metadata.get("description", ""),
                "capabilities": metadata.get("capabilities", []),
                "versions": metadata.get("versions", []),
                "tags": metadata.get("tags", []),
                "has_docs": bool(plugin_dir and _has_readme(plugin_dir))
                or bool(metadata.get("description")),
                "development_status": (
                    "ok" if metadata.get("description") else "unknown"
                ),
            }
        )

    return grouped


def generate_plugin_inventory(plugin_root_str: str, output_format: str = "text"):
    """Generate plugin inventory from the decorator registries.

    Args:
        plugin_root_str: Root directory of plugins (for relative path display).
        output_format: One of 'text', 'json', 'markdown'.
    """
    plugin_root = Path(plugin_root_str).resolve()

    _setup_import_path()

    # Suppress noisy import logs during discovery
    logging.basicConfig(level=logging.WARNING)

    manifests, protocol_plugins = _discover_all_plugins()

    # Group @register_plugin plugins
    grouped = _group_plugins(manifests, plugin_root)

    # Group @register_protocol plugins into the Protocols category
    proto_groups = _group_protocols(protocol_plugins, plugin_root)
    if proto_groups:
        grouped["Protocols"] = proto_groups

    # Collect missing-docs list
    missing_docs = []
    for _cat, subcategories in grouped.items():
        for _subcat, plugins in subcategories.items():
            for plugin in plugins:
                if not plugin["has_docs"]:
                    missing_docs.append(plugin["path"])

    if output_format == "json":
        print(json.dumps(grouped, indent=2, default=str))
    elif output_format == "markdown":
        _output_markdown(grouped, missing_docs)
    else:
        _output_text(grouped, missing_docs)

    return grouped, missing_docs


def _output_text(grouped, missing_docs):
    """Output inventory in plain text format."""
    print("PANTHER Plugin Inventory")
    print("=======================")

    for category, subcategories in grouped.items():
        print(f"\n{category.upper()}")
        for subcategory, plugins in subcategories.items():
            print(f"  {subcategory}:")
            for plugin in plugins:
                doc_status = "docs" if plugin["has_docs"] else "no-docs"
                dev_status = plugin["development_status"]
                caps = ", ".join(plugin.get("capabilities", [])[:3])
                cap_str = f" [{caps}]" if caps else ""
                print(
                    f"    - {plugin['name']} v{plugin['version']} "
                    f"({plugin['path']}) [{doc_status}] [{dev_status}]{cap_str}"
                )

    if missing_docs:
        print("\nPlugins missing documentation:")
        for path in missing_docs:
            print(f"  - {path}")


def _output_markdown(grouped, missing_docs):
    """Output inventory in markdown format with enriched metadata."""
    print("# PANTHER Plugin Inventory\n")

    # Desired category order
    category_order = ["Environments", "Protocols", "Services"]

    for category in category_order:
        if category not in grouped:
            continue
        subcategories = grouped[category]
        print(f"## {category}\n")

        for subcategory, plugins in subcategories.items():
            print(f"### {subcategory}\n")

            # Richer table with version and description
            print(
                "| Plugin | Version | Path | Description | Capabilities | Documentation | Status |"
            )
            print(
                "|--------|---------|------|-------------|--------------|---------------|--------|"
            )

            for plugin in sorted(plugins, key=lambda p: p["name"]):
                doc_icon = "yes" if plugin["has_docs"] else "no"
                dev_status = plugin["development_status"]
                status_label = (
                    "warning"
                    if dev_status in ("not totally working", "experimental")
                    else "ok" if dev_status == "ok" else "?"
                )

                path_display = f"`{plugin['path']}`"
                desc = plugin.get("description", "")
                if len(desc) > 60:
                    desc = desc[:57] + "..."
                caps = ", ".join(plugin.get("capabilities", [])[:4])
                if len(plugin.get("capabilities", [])) > 4:
                    caps += ", ..."

                # Protocol-specific: show versions if available
                versions = plugin.get("versions", [])
                if versions:
                    desc_suffix = f" (versions: {', '.join(versions[:3])})"
                    if len(versions) > 3:
                        desc_suffix = desc_suffix[:-1] + ", ...)"
                    if len(desc + desc_suffix) <= 80:
                        desc += desc_suffix

                print(
                    f"| {plugin['name']} | {plugin['version']} | {path_display} "
                    f"| {desc} | {caps} | {doc_icon} | {status_label} |"
                )
            print()

    if missing_docs:
        print("## Plugins Missing Documentation\n")
        for path in missing_docs:
            print(f"- `{path}`")


def main():
    """Generate and display the PANTHER plugin inventory."""
    parser = argparse.ArgumentParser(
        description="Generate PANTHER plugin inventory from the decorator registry"
    )
    parser.add_argument(
        "--root",
        default="panther/plugins",
        help="Root directory of plugins (for relative path display)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format",
    )
    parser.add_argument("--output", help="Output file (default: stdout)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any registered plugin lacks documentation",
    )
    args = parser.parse_args()

    original_stdout = sys.stdout
    if args.output:
        sys.stdout = open(args.output, "w", encoding="utf-8")

    try:
        _grouped, missing_docs = generate_plugin_inventory(args.root, args.format)
    finally:
        if args.output:
            sys.stdout.close()
            sys.stdout = original_stdout

    if args.check and missing_docs:
        print(
            f"\nFAILED: {len(missing_docs)} plugins missing documentation",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
