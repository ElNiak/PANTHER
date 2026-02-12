#!/usr/bin/env python3
"""
PANTHER Click CLI - Main entry point

Modern CLI implementation using Click framework with enhanced user experience,
improved error handling, and better maintainability compared to argparse version.

Key improvements over argparse:
- Colored output and emojis for better visual feedback
- Enhanced error messages with context
- Built-in bash completion support
- Cleaner command organization with groups
- Better help text formatting
- Progress bars for long operations
"""

import sys
from pathlib import Path

import click
from termcolor import colored

from panther import __version__
from panther.cli_click.core.base import setup_logging


@click.group()
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Enable debug logging with detailed output",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.version_option(version=__version__, prog_name="panther")
@click.pass_context
def cli(ctx, debug, verbose):
    """
    PANTHER - Protocol Analysis and Testing for Heterogeneous Execution and Research

    Modern CLI for network protocol testing, formal verification, and automated
    analysis of protocol implementations across multiple environments.

    \b
    Key Features:
    🔬 Protocol formal analysis and verification
    🐋 Docker-based isolated testing environments
    🌐 Network simulation and testing
    📊 Comprehensive metrics and reporting
    🔧 Extensible plugin architecture

    \b
    Examples:
      panther run --config experiment.yaml          # Run experiment
      panther config validate --config config.yaml # Validate configuration
      panther plugins list                          # List available plugins
      panther create plugin service my_service      # Create new service plugin
      panther tutorial run service                  # Run service tutorial
      panther tutorial interactive                  # Interactive tutorial mode
      panther check --all                           # Run all code quality checks
      panther metrics list                          # List available metrics
      panther admin status                          # Show system status
      panther admin docker --images-all             # Clean Docker images
      panther tools install-slim                    # Install Docker optimization tool

    Use 'panther COMMAND --help' for detailed information on each command.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["verbose"] = verbose

    # Setup logging based on flags
    setup_logging(debug, verbose)

    if debug:
        click.echo(colored("🐛 Debug mode enabled", "yellow"))
    elif verbose:
        click.echo(colored("🔍 Verbose mode enabled", "blue"))


@cli.command()
@click.option(
    "--output", "-o", type=click.Path(), help="Output format for shell completion"
)
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]), required=False)
def completion(output, shell):
    """
    Setup shell completion for PANTHER CLI.

    Enables tab completion for commands, options, and arguments in your shell.
    Supports bash, zsh, and fish shells.

    \b
    Examples:
      panther completion bash              # Show bash completion script
      panther completion bash > ~/.panther-complete.bash
      echo 'source ~/.panther-complete.bash' >> ~/.bashrc
    """
    if not shell:
        # Auto-detect shell
        shell_path = (
            Path("/proc/self/comm").read_text().strip()
            if Path("/proc/self/comm").exists()
            else "bash"
        )
        if "zsh" in shell_path:
            shell = "zsh"
        elif "fish" in shell_path:
            shell = "fish"
        else:
            shell = "bash"

    # Generate completion script
    if shell == "bash":
        completion_script = f"""
# PANTHER bash completion
_panther_completion() {{
    local IFS=$'\\t'
    COMPREPLY=( $( env COMP_WORDS="${{COMP_WORDS[*]}}" \\
                   COMP_CWORD=${{COMP_CWORD}} \\
                   _PANTHER_COMPLETE=complete $1 ) )
    return 0
}}

complete -F _panther_completion -o default panther;
"""
    elif shell == "zsh":
        completion_script = f"""
# PANTHER zsh completion
#compdef panther

_panther_completion() {{
    local -a completions
    local -a completions_with_descriptions
    local -a response
    response=("${{(@f)$( env COMP_WORDS="${{words[*]}}" \\
                        COMP_CWORD=${{#words[@]}} \\
                        _PANTHER_COMPLETE="complete_zsh" panther )}}")

    for key descr in ${{(kv)response}}; do
        if [[ "$key" == "$descr" ]]; then
            completions+=("$key")
        else
            completions_with_descriptions+=("$key":"$descr")
        fi
    done

    if [ "$#completions_with_descriptions" -eq "0" ]; then
        compadd -Q -S '' -a completions
    else
        _describe -V unsorted completions_with_descriptions -U -Q -S ''
    fi
}}

compdef _panther_completion panther;
"""
    else:  # fish
        completion_script = f"""
# PANTHER fish completion
complete -c panther -f -a "(env _PANTHER_COMPLETE=complete_fish panther)"
"""

    if output:
        with open(output, "w") as f:
            f.write(completion_script)
        click.echo(colored(f"✅ Completion script written to {output}", "green"))
        click.echo(f"Add 'source {output}' to your shell config file")
    else:
        click.echo(completion_script)


# Import and register command groups
def register_commands():
    """
    Register all command groups with the main CLI.

    This function imports and registers command groups, allowing for
    lazy loading of command modules to improve startup performance.

    BEHAVIORAL EQUIVALENCE: Provides better error reporting for missing
    commands to match legacy CLI behavior.
    """
    commands_to_register = [
        ("tools", "panther.cli_click.commands.tools", "tools"),
        ("run", "panther.cli_click.commands.run", "run"),
        ("config", "panther.cli_click.commands.config", "config"),
        ("plugins", "panther.cli_click.commands.plugins", "plugins"),
        ("create", "panther.cli_click.commands.create", "create"),
        ("tutorial", "panther.cli_click.commands.tutorial", "tutorial"),
        ("admin", "panther.cli_click.commands.admin", "admin"),
        ("check", "panther.cli_click.commands.check", "check"),
        ("metrics", "panther.cli_click.commands.metrics", "metrics"),
    ]

    missing_commands = []

    for cmd_name, module_path, attr_name in commands_to_register:
        try:
            module = __import__(module_path, fromlist=[attr_name])
            command = getattr(module, attr_name)
            cli.add_command(command)
        except ImportError as e:
            missing_commands.append(f"{cmd_name} ({e})")
        except AttributeError as e:
            missing_commands.append(f"{cmd_name} (missing attribute {attr_name})")

    # BEHAVIORAL EQUIVALENCE: Report missing commands clearly
    if missing_commands:
        ctx = click.get_current_context(silent=True)
        if ctx:
            click.echo(
                colored(
                    f"⚠️  Some commands not available: {', '.join(missing_commands)}",
                    "yellow",
                ),
                err=True,
            )


def main():
    """
    Main entry point for PANTHER CLI.

    This function is called when the CLI is invoked and handles
    command registration and execution.

    BEHAVIORAL EQUIVALENCE: Preserves legacy CLI return code patterns
    and error handling for shell script compatibility.

    Returns:
        int: Exit code following Unix conventions:
             0 = success
             1 = general error
             130 = terminated by Control-C
    """
    try:
        # Register commands
        register_commands()

        # Execute CLI - Click handles the exit codes internally now
        cli()

        # If we reach here, execution was successful
        return 0

    except KeyboardInterrupt:
        # BEHAVIORAL EQUIVALENCE: Preserve legacy exit code 130 for Ctrl+C
        click.echo(colored("⚠️  Operation cancelled by user", "yellow"), err=True)
        return 130
    except SystemExit as e:
        # Let Click's SystemExit through (preserves Click's exit code handling)
        return e.code if e.code is not None else 0
    except Exception as e:
        # BEHAVIORAL EQUIVALENCE: Top-level error handling matches legacy
        debug_mode = "--debug" in sys.argv
        if debug_mode:
            import logging

            logging.error(f"❌ Fatal error: {e}", exc_info=True)
        else:
            click.echo(colored(f"❌ Fatal error: {e}", "red"), err=True)
        return 1


# Register commands when module is imported
register_commands()

if __name__ == "__main__":
    # BEHAVIORAL EQUIVALENCE: Match legacy CLI exit code behavior
    sys.exit(main() or 0)
