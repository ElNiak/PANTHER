#!/usr/bin/env python3
"""Script to test the updated entrypoint template with different command types."""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Path to the template file
TEMPLATE_PATH = Path(
    "/Users/elniak/Documents/Project/PANTHER/panther/plugins/environments/network_environment/docker_compose/templates/entrypoint.sh.jinja"
)
OUTPUT_DIR = Path("/Users/elniak/Documents/Project/PANTHER/test_output")


def setup():
    """Create output directory if it doesn't exist."""
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True)


def create_test_command(cmd_type, command):
    """Create a test command object of the specified type."""
    cmd_obj = {
        "command": command,
        "description": f"Test {cmd_type} command",
        "is_critical": True,
        "is_multiline": False,
        "is_function_definition": False,
        "is_function_call": False,
        "has_control_operators": False,
        "control_operators": [],
        "working_dir": None,
        "environment": {},
        "timeout": None,
        "is_variable_assignment": False,
        "is_shell_builtin": False,
        "is_control_structure": False,
        "has_nested_quotes": False,
    }

    # Set the specific command type flag
    if cmd_type == "variable_assignment":
        cmd_obj["is_variable_assignment"] = True
    elif cmd_type == "shell_builtin":
        cmd_obj["is_shell_builtin"] = True
    elif cmd_type == "control_structure":
        cmd_obj["is_control_structure"] = True
    elif cmd_type == "nested_quotes":
        cmd_obj["has_nested_quotes"] = True
    elif cmd_type == "function_definition":
        cmd_obj["is_function_definition"] = True
    elif cmd_type == "function_call":
        cmd_obj["is_function_call"] = True
    elif cmd_type == "control_operators":
        cmd_obj["has_control_operators"] = True
        cmd_obj["control_operators"] = ["&&"]

    return cmd_obj


def render_commands():
    """Render test commands using the template."""
    # Create Environment
    try:
        print(f"Loading template from: {TEMPLATE_PATH}")
        env = Environment(loader=FileSystemLoader(TEMPLATE_PATH.parent))
        template = env.get_template(TEMPLATE_PATH.name)
    except Exception as e:
        print(f"ERROR loading template: {e}")
        return None

    # Create test commands
    test_commands = {
        "pre_run_cmds": [
            create_test_command("variable_assignment", "TARGET_IP=127.0.0.1"),
            create_test_command("shell_builtin", "set -x"),
            create_test_command(
                "control_structure",
                "while [ ! -f /app/sync_logs/ivy_ready.log ]; do sleep 1; done",
            ),
            create_test_command(
                "nested_quotes", 'export PS4="+ [${BASH_SOURCE:-sh}:${LINENO}] "'
            ),
        ]
    }

    # Additional template parameters
    additional_param = {"service_name": "test_service", "role": {"name": "server"}}

    print("Rendering template with test commands...")
    print(
        f"Command Types: {[cmd['description'] for cmd in test_commands['pre_run_cmds']]}"
    )

    # Render the template
    try:
        rendered = template.render(
            structured_commands=test_commands, additional_param=additional_param
        )
        print("Template rendered successfully!")
    except Exception as e:
        print(f"ERROR rendering template: {e}")
        return None

    # Write the rendered output
    output_path = OUTPUT_DIR / "test_entrypoint.sh"
    with open(output_path, "w") as f:
        f.write(rendered)

    print(f"Rendered test template to {output_path}")

    # Extract relevant sections for review
    summary_path = OUTPUT_DIR / "command_handling_summary.txt"
    with open(summary_path, "w") as f:
        # Find sections containing our test commands
        variable_section = re.search(
            r"TARGET_IP=127\.0\.0\.1.*?exit \$\?", rendered, re.DOTALL
        )
        builtin_section = re.search(r"set -x.*?exit \$\?", rendered, re.DOTALL)
        control_section = re.search(r"while \[ ! -f.*?exit \$\?", rendered, re.DOTALL)
        quotes_section = re.search(r"export PS4=.*?exit \$\?", rendered, re.DOTALL)

        # Write results
        f.write("COMMAND HANDLING PATTERNS:\n\n")

        f.write("1. VARIABLE ASSIGNMENT:\n")
        if variable_section:
            f.write(f"{variable_section.group(0)}\n\n")
        else:
            f.write("NOT FOUND\n\n")

        f.write("2. SHELL BUILTIN:\n")
        if builtin_section:
            f.write(f"{builtin_section.group(0)}\n\n")
        else:
            f.write("NOT FOUND\n\n")

        f.write("3. CONTROL STRUCTURE:\n")
        if control_section:
            f.write(f"{control_section.group(0)}\n\n")
        else:
            f.write("NOT FOUND\n\n")

        f.write("4. NESTED QUOTES:\n")
        if quotes_section:
            f.write(f"{quotes_section.group(0)}\n\n")
        else:
            f.write("NOT FOUND\n\n")

        # Write a section of the rendered template for context
        f.write("\n=== RENDERED TEMPLATE EXCERPT ===\n")
        excerpt_lines = rendered.splitlines()[400:600]  # Show lines 400-600
        f.write("\n".join(excerpt_lines))

    print(f"Wrote command handling summary to {summary_path}")
    return output_path


def main():
    setup()
    render_commands()
    print("Done! Test template rendered successfully.")


if __name__ == "__main__":
    main()
