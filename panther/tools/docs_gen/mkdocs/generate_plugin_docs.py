#!/usr/bin/env python3
"""
Generate plugin documentation by extracting information from README.md files
and organizing them into a coherent documentation structure.
"""

import argparse
import glob
import os
import re
import sys
from pathlib import Path

# Configure paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PLUGINS_DIR = ROOT_DIR / "panther" / "plugins"
DOCS_OUTPUT_DIR = ROOT_DIR / "docs"

# Plugin categories to document
PLUGIN_CATEGORIES = ["services", "protocols", "environments"]


def ensure_dir(directory):
    """Ensure directory exists."""
    os.makedirs(directory, exist_ok=True)


def copy_readme_with_relative_links(src_path, dest_path, base_path):
    """
    Copy README file, adjusting any relative links to work in the docs structure.
    """
    if not os.path.exists(src_path):
        print(f"Warning: {src_path} does not exist")
        return False  # Indicate a warning occurred

    with open(src_path, encoding="utf-8") as f:
        content = f.read()

    # Adjust relative links for images and other resources
    # This is a simple example and may need enhancement for your specific README structure
    def adjust_link(match):
        link_path = match.group(1)
        if link_path.startswith("http") or link_path.startswith("#"):
            return match.group(0)  # Don't change absolute or fragment links

        # Calculate relative path from the destination to the resource
        src_dir = os.path.dirname(src_path)
        abs_link_path = os.path.abspath(os.path.join(src_dir, link_path))
        rel_to_base = os.path.relpath(abs_link_path, base_path)

        return f"({rel_to_base})"

    # Adjust markdown links [text](link)
    content = re.sub(r"\]\((.*?)\)", lambda m: adjust_link(m), content)

    # Create parent directories if they don't exist
    ensure_dir(os.path.dirname(dest_path))

    # Write adjusted content
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True  # Indicate success


def generate_plugin_docs():
    """Generate documentation for all plugins.

    Returns:
        bool: True if no warnings occurred, False otherwise
    """
    ensure_dir(DOCS_OUTPUT_DIR)

    # Track warnings to potentially exit with error in strict mode
    warnings_found = False

    # We don't create a new index file as it would override the main documentation index
    # Instead, we'll just ensure each plugin category directory exists and has proper content
    print("Generating plugin documentation in main docs directory...")

    # Process each plugin category
    for category in PLUGIN_CATEGORIES:
        category_dir = PLUGINS_DIR / category
        output_category_dir = DOCS_OUTPUT_DIR / category
        ensure_dir(output_category_dir)

        # Create subcategory directories and index files if they don't exist
        if category == "environments":
            subcategories = ["execution_environment", "network_environment"]
        elif category == "protocols":
            subcategories = ["client_server", "peer_to_peer"]
        elif category == "services":
            subcategories = ["iut", "testers"]
        else:
            subcategories = []

        for subcategory in subcategories:
            subcat_dir = output_category_dir / subcategory
            ensure_dir(subcat_dir)

            # Create subcategory index if it doesn't exist
            if not os.path.exists(subcat_dir / "index.md"):
                with open(subcat_dir / "index.md", "w", encoding="utf-8") as f:
                    subcategory_title = subcategory.replace("_", " ").title()
                    f.write(
                        f"""# {subcategory_title}

This section contains documentation for all {subcategory_title.lower()} plugins.

"""
                    )
                    print(f"Created subcategory index for {category}/{subcategory}")

        # Don't override existing category index.md files that were already created
        if not os.path.exists(output_category_dir / "index.md"):
            # Create category index
            with open(output_category_dir / "index.md", "w", encoding="utf-8") as f:
                f.write(
                    f"""# {category.capitalize()} Plugins

This section contains documentation for all {category} plugins.

"""
                )

                # List all plugin directories in this category
                plugin_dirs = [
                    d
                    for d in os.listdir(category_dir)
                    if os.path.isdir(os.path.join(category_dir, d))
                    and not d.startswith("__")
                ]

                for plugin in sorted(plugin_dirs):
                    f.write(f"- [{plugin}]({plugin}/)\n")

        # Process each plugin in the category
        for plugin_dir in glob.glob(str(category_dir / "*")):
            plugin_name = os.path.basename(plugin_dir)

            if plugin_name.startswith("__") or not os.path.isdir(plugin_dir):
                continue

            # Determine the correct subdirectory based on category and plugin type
            subcategory = ""
            if category == "services":
                if "tester" in plugin_name.lower():
                    subcategory = "testers"
                else:
                    subcategory = "iut"
                plugin_output_dir = output_category_dir / subcategory / plugin_name
            elif category == "protocols":
                if "peer" in plugin_name.lower():
                    subcategory = "peer_to_peer"
                else:
                    subcategory = "client_server"
                plugin_output_dir = output_category_dir / subcategory / plugin_name
            elif category == "environments":
                if "network" in plugin_name.lower():
                    subcategory = "network_environment"
                else:
                    subcategory = "execution_environment"
                plugin_output_dir = output_category_dir / subcategory / plugin_name
            else:
                plugin_output_dir = output_category_dir / plugin_name

            ensure_dir(plugin_output_dir)

            # Copy main README for the plugin
            readme_path = os.path.join(plugin_dir, "README.md")
            if os.path.exists(readme_path):
                output_path = plugin_output_dir / "index.md"
                result = copy_readme_with_relative_links(
                    readme_path, output_path, ROOT_DIR
                )
                if not result:
                    warnings_found = True
                print(f"Generated docs for {category}/{subcategory}/{plugin_name}")
            else:
                # Create placeholder if no README exists
                with open(plugin_output_dir / "index.md", "w", encoding="utf-8") as f:
                    f.write(
                        f"""# {plugin_name}

*This plugin does not have documentation yet.*

"""
                    )
                print(
                    f"Warning: No README found for {category}/{subcategory}/{plugin_name}"
                )
                warnings_found = True

            # Look for additional documentation in the plugin directory
            for md_file in glob.glob(os.path.join(plugin_dir, "*.md")):
                if os.path.basename(md_file) == "README.md":
                    continue  # Skip README as we've already processed it

                output_path = plugin_output_dir / os.path.basename(md_file)
                result = copy_readme_with_relative_links(md_file, output_path, ROOT_DIR)
                if not result:
                    warnings_found = True

    # Return False if any warnings were found, otherwise True
    return not warnings_found


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate plugin documentation")
    parser.add_argument(
        "--strict", action="store_true", help="Exit with error code on warnings"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    try:
        success = generate_plugin_docs()

        if not success and args.strict:
            print(
                "❌ Strict mode enabled: Warnings were detected during plugin documentation generation."
            )
            sys.exit(1)

        print("Plugin documentation generation complete.")
    except Exception as e:
        print(f"Error generating plugin documentation: {e}")
        if args.strict:
            sys.exit(1)  # Exit with error code in strict mode
