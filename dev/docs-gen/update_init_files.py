#!/usr/bin/env python3
"""Script to update all __init__.py files with appropriate module docstrings."""

import os
from pathlib import Path
import re

# Base directory
base_dir = (
    Path(__file__).resolve().parent.parent
)  # Changed to parent.parent to get project root
print(f"Base directory: {base_dir}")


# Function to generate appropriate docstring based on module path
def generate_docstring(module_path):
    """Generate an appropriate docstring based on module path."""
    path_parts = module_path.parts
    # Get relative path to base directory
    try:
        rel_path = module_path.relative_to(base_dir)
        rel_parts = rel_path.parts
    except ValueError:
        # Handle paths outside base_dir
        rel_parts = path_parts

    # Generate module name from path
    if len(rel_parts) == 1:
        # This is the top-level PANTHER package
        return '''"""PANTHER package.

PANTHER (Protocol Analysis and Network Testing Harness for Extensive Research) is a
framework for network protocol testing and research.
"""'''

    # For modules inside panther/
    if len(rel_parts) > 0 and rel_parts[0] == "panther":
        if len(rel_parts) == 1:
            # Main panther package
            return '''"""PANTHER package.

PANTHER (Protocol Analysis and Network Testing Harness for Extensive Research) is a
framework for network protocol testing and research.
"""'''

        # Second level packages
        if len(rel_parts) >= 2:
            package_name = rel_parts[1]

            # Handle specific packages
            if package_name == "config":
                return '''"""PANTHER configuration package.

This package contains configuration management for the PANTHER framework.
"""'''

            elif package_name == "core":
                return '''"""PANTHER core package.

This package contains the core functionality of the PANTHER framework.
"""'''

            elif package_name == "plugins":
                if len(rel_parts) == 2:
                    return '''"""PANTHER plugins package.

This package contains all plugins for the PANTHER framework.
"""'''

                # Handle plugin subpackages
                if len(rel_parts) >= 3:
                    plugin_type = rel_parts[2]

                    if plugin_type == "environments":
                        return '''"""PANTHER environment plugins.

This package contains environment plugins for different testing environments.
"""'''

                    elif plugin_type == "services":
                        if len(rel_parts) == 3:
                            return '''"""PANTHER service plugins.

This package contains service plugins for different network services.
"""'''

                        # Service subpackages
                        if len(rel_parts) >= 4:
                            service_type = rel_parts[3]

                            if service_type == "iut":
                                if len(rel_parts) == 4:
                                    return '''"""PANTHER Implementation Under Test (IUT) services.

This package contains services that can be used as implementations under test.
"""'''

                                # IUT specific protocols
                                if len(rel_parts) >= 5:
                                    protocol = rel_parts[4]

                                    if protocol == "quic":
                                        if len(rel_parts) == 5:
                                            return '''"""PANTHER QUIC protocol implementations.

This package contains QUIC protocol implementations that can be used as IUT.
"""'''

                                        # Specific QUIC implementation
                                        if len(rel_parts) >= 6:
                                            impl_name = rel_parts[5]
                                            return f'''"""PANTHER {impl_name.capitalize()} QUIC implementation.

This package contains the {impl_name.capitalize()} implementation of the QUIC protocol.
"""'''

                                    elif protocol == "http":
                                        return '''"""PANTHER HTTP protocol implementations.

This package contains HTTP protocol implementations that can be used as IUT.
"""'''

                                    elif protocol == "minip":
                                        if len(rel_parts) == 5:
                                            return '''"""PANTHER Mini Protocol implementations.

This package contains Mini Protocol implementations that can be used for testing.
"""'''

                                        # Specific mini protocol
                                        if len(rel_parts) >= 6:
                                            mini_protocol = rel_parts[5]
                                            return f'''"""PANTHER {mini_protocol.replace("_", " ").title()} protocol.

This package contains the {mini_protocol.replace("_", " ").title()} protocol implementation.
"""'''

            elif package_name == "webapp":
                return '''"""PANTHER web application.

This package contains the web interface for PANTHER.
"""'''

    # Handle dev/docs-gen directory
    if "dev/docs-gen" in rel_parts:
        if len(rel_parts) == 1 and rel_parts[0] == "dev/docs-gen":
            return '''"""PANTHER documentation generation tools.

This package contains tools for generating and maintaining PANTHER's documentation.
"""'''
        elif len(rel_parts) >= 2:
            submodule = rel_parts[1]
            return f'''"""PANTHER documentation {submodule} tools.

This module contains {submodule}-related documentation tools.
"""'''

    # Handle tests directory
    if "tests" in rel_parts:
        if len(rel_parts) == 1 and rel_parts[0] == "tests":
            return '''"""PANTHER test suite.

This package contains tests for the PANTHER framework.
"""'''
        elif len(rel_parts) >= 2:
            test_type = rel_parts[1]
            return f'''"""PANTHER {test_type} tests.

This package contains {test_type} tests for the PANTHER framework.
"""'''

    # Default docstring if no specific match
    module_name = rel_parts[-1] if len(rel_parts) > 0 else "module"
    return f'''"""{module_name} package.

This package is part of the PANTHER framework.
"""'''


# Function to update an __init__.py file
def update_init_file(init_file):
    """Update an __init__.py file with an appropriate docstring."""
    # Generate appropriate docstring
    docstring = generate_docstring(init_file.parent)

    # Read current content
    try:
        with open(init_file) as f:
            content = f.read()
    except Exception:
        # If file is not readable, create a new one
        content = ""

    # Check if file already has a docstring
    docstring_pattern = r'""".*?"""'
    if re.match(docstring_pattern, content, re.DOTALL):
        # Replace existing docstring
        updated_content = re.sub(docstring_pattern, docstring, content, 1, re.DOTALL)
    else:
        # Add docstring to beginning of file
        updated_content = docstring + "\n\n" + content if content.strip() else docstring

    # Write updated content
    with open(init_file, "w") as f:
        f.write(updated_content)

    print(f"Updated {init_file}")


# Find all __init__.py files
def find_init_files(directory):
    """Find all __init__.py files in the given directory."""
    for root, dirs, files in os.walk(directory):
        if "__init__.py" in files:
            yield Path(root) / "__init__.py"


# Main execution
if __name__ == "__main__":
    # Get all __init__.py files in the project
    project_dir = base_dir  # Use base_dir directly (which is now project root)

    print(f"Updating __init__.py files in the project: {project_dir}...")

    count = 0
    for init_file in find_init_files(project_dir):
        update_init_file(init_file)
        count += 1

    print(f"Updated {count} __init__.py files.")
