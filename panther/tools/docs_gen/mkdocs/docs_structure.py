"""Improved documentation structure manager for PANTHER."""

import os
import shutil
from pathlib import Path

import yaml


def ensure_dir_exists(dir_path):
    """Ensure directory exists."""
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def copy_markdown_file(source, destination):
    """Copy markdown file from source to destination."""
    dest_dir = os.path.dirname(destination)
    ensure_dir_exists(dest_dir)

    # Create parent directories if they don't exist
    if not os.path.exists(source):
        print(f"Warning: Source file not found: {source}")
        return False

    print(f"Copying {source} to {destination}")
    shutil.copy2(source, destination)
    return True


def organize_docs():
    """Create an organized documentation structure."""
    repo_dir = Path.cwd()
    docs_dir = repo_dir / "docs"

    # Ensure docs directory exists and is clean
    ensure_dir_exists(docs_dir)

    # Copy index template to docs directory
    index_template = (
        repo_dir
        / "panther"
        / "tools"
        / "docs_gen"
        / "mkdocs"
        / "template"
        / "index_template.md"
    )
    if index_template.exists():
        copy_markdown_file(index_template, docs_dir / "index.md")
    else:
        print("Warning: index template not found at", index_template)

    # Create documentation structure
    structure = {
        "getting_started": [
            {"source": "QUICK_START.md", "dest": "docs/getting_started/QUICK_START.md"},
            {"source": "README.md", "dest": "docs/getting_started/index.md"},
            {"source": "INSTALL.md", "dest": "docs/getting_started/INSTALL.md"},
        ],
        "user_guide": [
            {"source": "WORKFLOW.md", "dest": "docs/user_guide/WORKFLOW.md"},
            {"source": "panther/README.md", "dest": "docs/user_guide/overview.md"},
            {"source": "TODO.md", "dest": "docs/user_guide/todo.md", "optional": True},
        ],
        "developer_guide": [
            {
                "source": "CONTRIBUTING.md",
                "dest": "docs/developer_guide/contributing.md",
            },
            {
                "source": "panther/tools/docs_gen/README.md",
                "dest": "docs/developer_guide/documentation.md",
            },
            # development.md removed; plugin dev docs now in code docstrings
        ],
        "reference": [
            {"source": "PACKAGING.md", "dest": "docs/reference/packaging.md"},
            {
                "source": "tests/README.md",
                "dest": "docs/reference/testing.md",
                "optional": True,
            },
        ],
        "project": [
            {"source": "CHANGELOG.md", "dest": "docs/project/changelog.md"},
            {
                "source": "LICENSE.md",
                "dest": "docs/project/license.md",
                "optional": True,
            },
        ],
    }

    # Copy all plugin READMEs
    plugin_dirs = [
        "panther/plugins",
        "panther/plugins/environments",
        "panther/plugins/protocols",
        "panther/plugins/services",
    ]

    # Copy main markdown files
    for section, files in structure.items():
        section_dir = docs_dir / section
        ensure_dir_exists(section_dir)

        for file_info in files:
            source = repo_dir / file_info["source"]
            dest = repo_dir / file_info["dest"]

            # Skip if marked optional and doesn't exist
            if not source.exists() and file_info.get("optional", False):
                continue

            copy_markdown_file(source, dest)

    # Copy plugin documentation
    for plugin_dir in plugin_dirs:
        # Find all README.md files in the plugin directories
        for path in Path(repo_dir / plugin_dir).glob("**/*.md"):
            # Skip submodules and any documentation that might cause duplication issues
            if any(skip_dir in str(path) for skip_dir in ["submodules/", "/.venv/"]):
                continue

            if path.name == "README.md" or path.name.endswith(".md"):
                relative_path = path.relative_to(repo_dir)

                # Determine destination path
                if "plugins/environments" in str(relative_path):
                    dest_category = "plugins/environments"
                elif "plugins/protocols" in str(relative_path):
                    dest_category = "plugins/protocols"
                elif "plugins/services" in str(relative_path):
                    dest_category = "plugins/services"
                else:
                    dest_category = "plugins"

                # Create destination path
                dest_path = (
                    docs_dir
                    / dest_category
                    / path.relative_to(
                        repo_dir / plugin_dir.split("/")[0] / plugin_dir.split("/")[1]
                    )
                )

                # Ensure parent directory exists
                ensure_dir_exists(dest_path.parent)

                # Copy the file
                copy_markdown_file(path, dest_path)

    # Add core files from panther directory
    panther_core_dirs = [
        "panther/config",
        "panther/core",
        "panther/webapp",
    ]

    # Copy core panther documentation
    for core_dir in panther_core_dirs:
        for path in Path(repo_dir / core_dir).glob("**/*.md"):
            if path.name.endswith(".md"):
                relative_path = path.relative_to(repo_dir)
                dest_path = docs_dir / str(relative_path).replace(".md", ".md")

                # Ensure parent directory exists
                ensure_dir_exists(dest_path.parent)

                # Copy the file
                copy_markdown_file(path, dest_path)

    # Create the navigation structure for mkdocs.yml
    nav = [
        {"Home": "index.md"},
        {
            "Getting Started": {
                "Overview": "getting_started/index.md",
                "Quick Start": "getting_started/QUICK_START.md",
                "Installation": "getting_started/INSTALL.md",
            }
        },
        {
            "User Guide": {
                "Overview": "user_guide/overview.md",
                "Workflow": "user_guide/WORKFLOW.md",
                "To-Do List": "user_guide/todo.md",
            }
        },
        {
            "Developer Guide": {
                "Contributing": "developer_guide/contributing.md",
                "Documentation": {
                    "Overview": "developer_guide/documentation.md",
                    "Workflow": "developer_guide/documentation_WORKFLOW.md",
                    "Style Guide": "developer_guide/style_guide.md",
                    "Integration": "developer_guide/documentation_integration.md",
                    "Links": "developer_guide/documentation_links.md",
                    "Enhancements": "developer_guide/documentation_enhancements.md",
                },
                "Plugin Development": "developer_guide/plugin_development.md",  # sourced from panther/plugins/__init__.py docstring
            }
        },
        {
            "Plugins": {
                "Overview": "plugins/plugins_overview.md",
                "Environments": {
                    "Overview": "plugins/environments/README.md",
                    "Network Environments": "plugins/environments/network_environment/README.md",
                    "Execution Environments": "plugins/environments/execution_environment/README.md",
                },
                "Protocols": {
                    "Overview": "plugins/protocols/README.md",
                    "Client-Server": "plugins/protocols/client_server/README.md",
                    "Peer-to-Peer": "plugins/protocols/peer_to_peer/README.md",
                },
                "Services": {
                    "Overview": "plugins/services/README.md",
                    "Implementations": "plugins/services/iut/README.md",
                    "Testers": "plugins/services/testers/README.md",
                },
            }
        },
        {
            "Panther Core": {
                "Overview": "panther/README.md",
                "Web Interface": "panther/webapp/webapp_interface.md",
            }
        },
        {
            "Reference": {
                "Packaging": "reference/packaging.md",
                "Testing": "reference/testing.md",
            }
        },
        {
            "Project": {
                "Changelog": "project/changelog.md",
                "License": "project/license.md",
            }
        },
    ]

    # Generate updated mkdocs.yml
    update_mkdocs_nav(repo_dir / "mkdocs.yml", nav)

    print("Documentation structure organized successfully!")


def update_mkdocs_nav(mkdocs_file, nav):
    """Update the navigation section in mkdocs.yml."""
    with open(mkdocs_file) as f:
        config = yaml.safe_load(f)

    # Update navigation
    config["nav"] = nav

    with open(mkdocs_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":
    organize_docs()
