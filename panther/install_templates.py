"""
Script to install plugin templates during package installation.

This script ensures that the plugin templates are correctly installed
when the PANTHER package is installed, so they can be accessed in
production mode.

It supports both top-level plugin templates and subplugin templates,
and can process Jinja2 templates for dynamic content generation.
"""

import shutil
from pathlib import Path
import site

try:
    import jinja2

    JINJA_AVAILABLE = True
except ImportError:
    JINJA_AVAILABLE = False
    print("Warning: Jinja2 not installed. Will use static templates only.")

# Plugin type definitions
PLUGIN_HIERARCHY = {
    "services": ["iut", "tester"],
    "environments": ["network_environment", "execution_environment"],
    "protocols": ["client", "server", "peer_to_peer"],
}


def install_templates():
    """
    Install plugin templates to the site-packages directory.
    Handles both top-level plugin templates and specialized subplugin templates.
    """
    # Plugin types
    plugin_types = list(PLUGIN_HIERARCHY.keys())

    plugins_base = Path(__file__).parent.resolve() / "plugins"
    site_packages = site.getsitepackages()[0]

    # Process each plugin type
    for plugin_type in plugin_types:
        # Source directory in development mode
        src_dir = plugins_base / plugin_type / "tutorials"
        src_template = src_dir / "template"

        # Target directory in site-packages
        target_dir = (
            Path(site_packages) / "panther" / "plugins" / plugin_type / "tutorials"
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        target_template = target_dir / "template"

        if not src_template.exists():
            print(f"Template directory does not exist: {src_template}")
            # Skip if template doesn't exist
            continue

        # Create target template directory
        target_template.mkdir(parents=True, exist_ok=True)

        # Copy top-level plugin template files
        print(f"Installing {plugin_type} top-level templates to {target_template}")
        for item in src_template.glob("*"):
            if item.is_dir():
                # Skip subplugin folders as they'll be handled separately
                if item.name not in PLUGIN_HIERARCHY.get(plugin_type, []):
                    shutil.copytree(
                        item, target_template / item.name, dirs_exist_ok=True
                    )
            else:
                shutil.copy2(item, target_template / item.name)

        # Process subplugin templates if they exist
        for subplugin_type in PLUGIN_HIERARCHY.get(plugin_type, []):
            subplugin_src = src_template / subplugin_type
            subplugin_target = target_template / subplugin_type

            if subplugin_src.exists():
                print(
                    f"  Installing {plugin_type}/{subplugin_type} templates to {subplugin_target}"
                )
                subplugin_target.mkdir(parents=True, exist_ok=True)

                for item in subplugin_src.glob("*"):
                    if item.is_dir():
                        shutil.copytree(
                            item, subplugin_target / item.name, dirs_exist_ok=True
                        )
                    else:
                        shutil.copy2(item, subplugin_target / item.name)

    # Process any Jinja templates if available
    if JINJA_AVAILABLE:
        process_jinja_templates(target_dir, plugin_types)

    print("Plugin templates installed successfully")
    return True


def process_jinja_templates(target_dir, plugin_types):
    """
    Process any .j2 template files found in the target directory.

    Args:
        target_dir: Path to the target directory where templates are installed
        plugin_types: List of plugin types to process
    """
    if not JINJA_AVAILABLE:
        return

    print("Processing Jinja2 templates...")

    # For each plugin type
    for plugin_type in plugin_types:
        plugin_dir = target_dir / plugin_type / "tutorials"
        if not plugin_dir.exists():
            continue

        # Create Jinja environment for the plugin type
        template_loader = jinja2.FileSystemLoader(str(plugin_dir))
        template_env = jinja2.Environment(loader=template_loader)

        # Find all .j2 files in the template directory and its subdirectories
        for j2_file in plugin_dir.rglob("*.j2"):
            relative_path = j2_file.relative_to(plugin_dir)
            output_file = plugin_dir / relative_path.with_suffix("")

            try:
                # Get template from the environment
                template = template_env.get_template(str(relative_path))

                # Determine context based on the template file location
                context = {
                    "plugin_type": plugin_type,
                }

                # Add subplugin type to context if applicable
                path_parts = list(relative_path.parts)
                if len(path_parts) >= 2 and path_parts[0] == "template":
                    if path_parts[1] in PLUGIN_HIERARCHY.get(plugin_type, []):
                        context["subplugin_type"] = path_parts[1]

                # Render template
                rendered = template.render(**context)

                # Write the rendered template to the output file
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, "w") as f:
                    f.write(rendered)

                print(f"  Processed template: {relative_path}")
            except Exception as e:
                print(f"  Error processing template {relative_path}: {e}")


if __name__ == "__main__":
    install_templates()
