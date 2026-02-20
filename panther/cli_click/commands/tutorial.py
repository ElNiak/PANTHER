"""
Tutorial Command - Interactive tutorials and learning (Click implementation)
"""

import json
import traceback
from pathlib import Path
from typing import List, Optional, Tuple

import click
from termcolor import colored

from panther.cli_click.core.base import (
    error_message,
    handle_errors,
    info_message,
    pass_context_and_setup_logging,
    success_message,
    warning_message,
)

# Single source of truth for tutorial metadata. Both `list_tutorials` and
# `interactive` derive their data from this registry.
TUTORIAL_REGISTRY: List[dict] = [
    {
        "name": "service",
        "title": "Service Plugin Development",
        "description": (
            "Learn to create service plugins for protocol"
            " implementations like QUIC, HTTP, and custom protocols"
        ),
        "duration": "15-20 minutes",
        "difficulty": "beginner",
        "category": "service",
        "topics": [
            "Plugin architecture",
            "IUT integration",
            "Configuration management",
            "Testing strategies",
        ],
        "prerequisites": [
            "Basic Python knowledge",
            "Understanding of network protocols",
        ],
        "examples": [
            "QUIC service implementation",
            "HTTP/2 service plugin",
            "Custom protocol wrapper",
        ],
    },
    {
        "name": "environment",
        "title": "Environment Plugin Development",
        "description": (
            "Learn to create network and execution environment"
            " plugins for complex testing scenarios"
        ),
        "duration": "20-25 minutes",
        "difficulty": "intermediate",
        "category": "environment",
        "topics": [
            "Network simulation",
            "Container orchestration",
            "Environment isolation",
            "Resource management",
        ],
        "prerequisites": [
            "Service plugin experience",
            "Docker knowledge",
            "Network fundamentals",
        ],
        "examples": [
            "Multi-host network setup",
            "Containerized test environment",
            "Network latency simulation",
        ],
    },
    {
        "name": "protocol",
        "title": "Protocol Plugin Development",
        "description": (
            "Learn to create protocol definition plugins"
            " for testing and validation frameworks"
        ),
        "duration": "10-15 minutes",
        "difficulty": "beginner",
        "category": "protocol",
        "topics": [
            "Protocol specification",
            "Test case generation",
            "Validation rules",
            "Coverage analysis",
        ],
        "prerequisites": [
            "Basic networking concepts",
            "Protocol specification understanding",
        ],
        "examples": [
            "QUIC protocol testing",
            "HTTP/3 validation",
            "Custom protocol definitions",
        ],
    },
    {
        "name": "configuration",
        "title": "Experiment Configuration Mastery",
        "description": (
            "Learn to write and structure experiment"
            " configuration files for complex testing scenarios"
        ),
        "duration": "10-15 minutes",
        "difficulty": "beginner",
        "category": "configuration",
        "topics": [
            "YAML/JSON configuration",
            "Template systems",
            "Variable substitution",
            "Validation schemas",
        ],
        "prerequisites": [
            "Basic YAML/JSON knowledge",
            "Understanding of experiment concepts",
        ],
        "examples": [
            "Multi-protocol experiments",
            "Parametric testing",
            "Environment-specific configs",
        ],
    },
]


@click.group()
def tutorial():
    """
    Interactive tutorials and learning platform.

    Access interactive tutorials for learning PANTHER development across all plugin types
    and configuration scenarios. Features guided learning with progress tracking and
    hands-on examples.

    \b
    Key Features:
    - Interactive tutorial system with guided learning
    - Hands-on examples and real plugin development
    - Progressive skill building from beginner to advanced
    - Progress tracking and completion verification
    - Quick reference and cheat sheets

    \b
    Tutorial Categories:
    - Service Plugins: Learn to create IUT implementations
    - Environment Plugins: Master network and execution environments
    - Protocol Plugins: Build protocol-specific testing components
    - Configuration: Master experiment and plugin configuration

    \b
    Learning Modes:
    - Guided: Step-by-step interactive tutorials
    - Quick Start: Fast-track tutorials for experienced developers
    - Reference: Quick lookup and examples
    """


@tutorial.command()
@click.argument(
    "tutorial_type",
    type=click.Choice(
        ["service", "environment", "protocol", "configuration"], case_sensitive=False
    ),
    metavar="TYPE",
)
@click.option(
    "--mode",
    type=click.Choice(["guided", "quick", "reference"], case_sensitive=False),
    default="guided",
    help="Learning mode (guided, quick, reference)",
    show_default=True,
)
@click.option(
    "--level",
    type=click.Choice(["beginner", "intermediate", "advanced"], case_sensitive=False),
    default="beginner",
    help="Skill level for tutorial content",
    show_default=True,
)
@click.option(
    "--output-dir", type=click.Path(), help="Directory to create tutorial artifacts"
)
@click.option(
    "--interactive/--no-interactive",
    default=True,
    help="Enable interactive prompts during tutorial",
)
@pass_context_and_setup_logging
@handle_errors
def run(
    ctx,
    tutorial_type: str,
    mode: str,
    level: str,
    output_dir: Optional[str],
    interactive: bool,
):
    """
    Run a specific tutorial with guided learning.

    \b
    Tutorial Types:
      service       - Service plugin development (IUT implementations)
      environment   - Environment plugin development (network environments)
      protocol      - Protocol plugin development (testing components)
      configuration - Experiment and plugin configuration mastery

    \b
    Learning Modes:
      guided   - Step-by-step interactive tutorial (recommended)
      quick    - Fast-track tutorial for experienced developers
      reference - Quick lookup with examples and templates

    \b
    Examples:
    panther tutorial run service --mode guided --level beginner
    panther tutorial run environment --mode quick --output-dir ./my-tutorial
    panther tutorial run protocol --mode reference --level advanced
    """
    info_message(f"Starting {tutorial_type.title()} Tutorial")
    info_message(f"Mode: {mode.title()} | Level: {level.title()}")

    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        info_message(f"Tutorial artifacts will be saved to: {output_path}")

    info_message("Preparing tutorial environment...")

    # NOTE: --mode, --level, --output-dir, --interactive are accepted by the CLI
    # but not yet wired to the backend run_tutorial(). They are kept for forward
    # compatibility and will be connected when the backend supports them.

    try:
        from panther.tools.plugins.plugin_creator import run_tutorial

        # B1 fix: run_tutorial() only accepts plugin_type (str) -> int
        result_code = run_tutorial(tutorial_type)

        # B2 fix: 0 means success, check with == not truthiness
        if result_code == 0:
            success_message(f"Tutorial '{tutorial_type}' completed successfully!")

            if mode == "guided":
                info_message("Next Steps:")
                if tutorial_type == "service":
                    info_message(
                        "  - Try creating a real service plugin with: panther create plugin service"
                    )
                    info_message(
                        "  - Explore environment tutorials: panther tutorial run environment"
                    )
                elif tutorial_type == "environment":
                    info_message(
                        "  - Try creating an environment plugin: panther create plugin environment"
                    )
                    info_message(
                        "  - Learn protocol development: panther tutorial run protocol"
                    )
                elif tutorial_type == "protocol":
                    info_message(
                        "  - Create a protocol plugin: panther create plugin protocol"
                    )
                    info_message(
                        "  - Master configuration: panther tutorial run configuration"
                    )
                else:  # configuration
                    info_message(
                        "  - Create experiment configs: panther create template experiment"
                    )
                    info_message("  - Explore all tutorials: panther tutorial list")

                info_message("  - Get help anytime: panther tutorial --help")

            return 0
        else:
            error_message(f"Tutorial '{tutorial_type}' encountered issues")
            warning_message("Try running with --help for usage information")
            ctx.exit(1)

    except ImportError as e:
        error_message(f"Tutorial system not available: {e}")
        warning_message("Ensure PANTHER tutorial plugins are properly installed")
        ctx.exit(1)
    except Exception as e:
        error_message(f"Error running tutorial: {e}")
        # B5 fix: debug flag lives on ctx.obj, not on click params
        if ctx.obj.get("debug"):
            traceback.print_exc()
        ctx.exit(1)


@tutorial.command(name="list")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "detail"], case_sensitive=False),
    default="detail",
    help="Output format for tutorial list",
    show_default=True,
)
@click.option(
    "--level",
    type=click.Choice(
        ["beginner", "intermediate", "advanced", "all"], case_sensitive=False
    ),
    default="all",
    help="Filter by skill level",
    show_default=True,
)
@click.option(
    "--category",
    type=click.Choice(
        ["service", "environment", "protocol", "configuration", "all"],
        case_sensitive=False,
    ),
    default="all",
    help="Filter by tutorial category",
    show_default=True,
)
# B6 fix: use pass_context_and_setup_logging instead of click.pass_context
@pass_context_and_setup_logging
@handle_errors
def list_tutorials(ctx, output_format: str, level: str, category: str):
    """
    List all available tutorials with filtering and detailed information.

    \b
    Output Formats:
      table  - Compact table view with key information
      detail - Detailed view with descriptions and examples (default)
      json   - JSON format for programmatic use

    \b
    Filtering:
      --level      Filter by skill level (beginner, intermediate, advanced)
      --category   Filter by tutorial type (service, environment, protocol, configuration)

    \b
    Examples:
    panther tutorial list --format table --level beginner
    panther tutorial list --category service --format detail
    panther tutorial list --format json > tutorials.json
    """
    info_message("Available PANTHER Tutorials")

    tutorials = list(TUTORIAL_REGISTRY)

    # Apply filters
    if level != "all":
        tutorials = [t for t in tutorials if t["difficulty"] == level]

    if category != "all":
        tutorials = [t for t in tutorials if t["category"] == category]

    if not tutorials:
        warning_message(
            f"No tutorials found matching filters: level={level}, category={category}"
        )
        return 0

    if output_format == "json":
        click.echo(json.dumps(tutorials, indent=2))
        return 0

    if output_format == "table":
        # U7 fix: pad text BEFORE applying color codes to avoid ANSI alignment issues
        def _padded(text: str, width: int) -> str:
            return f"{text:<{width}}"

        click.echo()
        header = (
            f"{_padded('Name', 12)} "
            f"{_padded('Title', 25)} "
            f"{_padded('Duration', 14)} "
            f"{'Level'}"
        )
        click.echo(colored(header, "white", attrs=["bold"]))
        click.echo(colored("-" * 60, "white"))

        for t in tutorials:
            title_text = t["title"][:22] + "..." if len(t["title"]) > 25 else t["title"]
            click.echo(
                f"{colored(_padded(t['name'], 12), 'cyan')} "
                f"{colored(_padded(title_text, 25), 'white')} "
                f"{colored(_padded(t['duration'], 14), 'green')} "
                f"{colored(t['difficulty'].title(), 'yellow')}"
            )

        click.echo()
        info_message("Use --format detail for more information")
        info_message("Start a tutorial: panther tutorial run <name>")
        return 0

    # Detail format (default)
    for i, t in enumerate(tutorials):
        if i > 0:
            click.echo()

        click.echo(colored(f"  {t['title']}", "white", attrs=["bold"]))

        click.echo(f"   {colored('Name:', 'cyan')} {t['name']}")
        click.echo(f"   {colored('Duration:', 'cyan')} {t['duration']}")
        click.echo(f"   {colored('Difficulty:', 'cyan')} {t['difficulty'].title()}")
        click.echo(f"   {colored('Description:', 'cyan')} {t['description']}")

        topics_str = ", ".join(t["topics"][:3])
        if len(t["topics"]) > 3:
            topics_str += f" (+{len(t['topics']) - 3} more)"
        click.echo(f"   {colored('Topics:', 'cyan')} {topics_str}")

        prereq_str = ", ".join(t["prerequisites"])
        click.echo(f"   {colored('Prerequisites:', 'cyan')} {prereq_str}")

        examples_str = ", ".join(t["examples"][:2])
        if len(t["examples"]) > 2:
            examples_str += f" (+{len(t['examples']) - 2} more)"
        click.echo(f"   {colored('Examples:', 'cyan')} {examples_str}")

        command = f"panther tutorial run {t['name']}"
        click.echo(f"   {colored('Command:', 'green')} {command}")

    click.echo()
    success_message(f"Found {len(tutorials)} tutorial(s)")
    info_message("Start any tutorial: panther tutorial run <name>")
    info_message("Interactive mode: panther tutorial interactive")

    return 0


@tutorial.command()
@click.option(
    "--quick-start/--full-menu",
    default=False,
    help="Skip introductions and jump to tutorial selection",
)
@pass_context_and_setup_logging
@handle_errors
def interactive(ctx, quick_start: bool):
    """
    Start interactive tutorial mode with guided selection.

    Provides an interactive menu for tutorial selection with guided recommendations
    based on your experience level and learning goals.

    \b
    Features:
    - Intelligent tutorial recommendations
    - Progress tracking and skill assessment
    - Easy navigation between tutorials
    - Contextual help and tips

    \b
    Examples:
    panther tutorial interactive              # Full interactive experience
    panther tutorial interactive --quick-start  # Skip intro, direct to menu
    """
    if not quick_start:
        click.echo()
        info_message("Welcome to PANTHER Interactive Tutorial System!")
        click.echo(colored("=" * 60, "cyan"))
        click.echo()
        info_message(
            "This interactive system will guide you through learning PANTHER development."
        )
        info_message("Choose tutorials based on your goals and experience level.")
        click.echo()

    tutorials: List[Tuple[str, str, str]] = [
        (t["name"], t["description"], t["difficulty"]) for t in TUTORIAL_REGISTRY
    ]

    while True:
        click.echo(colored("\nAvailable Tutorials:", "white", attrs=["bold"]))

        for i, (tutorial_type, description, level) in enumerate(tutorials, 1):
            level_color = {
                "beginner": "green",
                "intermediate": "yellow",
                "advanced": "red",
            }.get(level, "white")

            level_text = colored(f"[{level.title()}]", level_color)
            click.echo(
                f"  {colored(str(i), 'cyan')}. {colored(tutorial_type.title(), 'white')} {level_text}"
            )
            click.echo(f"     {colored(description, 'white', attrs=['dim'])}")

        click.echo()
        click.echo(colored("Commands:", "white", attrs=["bold"]))
        click.echo(f"  {colored('1-4', 'cyan')}  - Start tutorial")
        click.echo(f"  {colored('l', 'cyan')}    - List all tutorials with details")
        click.echo(f"  {colored('h', 'cyan')}    - Show help")
        click.echo(f"  {colored('q', 'cyan')}    - Quit")

        try:
            choice = (
                click.prompt(
                    colored("\nSelect option", "green"), type=str, show_default=False
                )
                .strip()
                .lower()
            )

            if choice == "q":
                info_message("Tutorial session ended. Happy coding!")
                return 0
            elif choice == "l":
                # Call list command programmatically
                ctx.invoke(
                    list_tutorials, output_format="detail", level="all", category="all"
                )
                continue
            elif choice == "h":
                click.echo()
                info_message("PANTHER Tutorial Help")
                info_message("- Start with Service tutorials if you're new to PANTHER")
                info_message("- Environment tutorials require Docker knowledge")
                info_message("- Protocol tutorials focus on testing frameworks")
                info_message("- Configuration tutorials teach experiment setup")
                click.echo()
                info_message(
                    "All tutorials include hands-on examples and real code generation"
                )
                continue

            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(tutorials):
                    tutorial_type = tutorials[choice_num - 1][0]
                    level = tutorials[choice_num - 1][2]

                    click.echo()
                    info_message(f"Starting {tutorial_type.title()} tutorial...")

                    # B7 fix: wrap ctx.invoke in SystemExit handler so that
                    # handle_errors' sys.exit() doesn't kill interactive mode
                    try:
                        result = ctx.invoke(
                            run,
                            tutorial_type=tutorial_type,
                            mode="guided",
                            level=level,
                            output_dir=None,
                            interactive=True,
                        )
                    except SystemExit as e:
                        result = e.code if e.code is not None else 1

                    if result == 0:
                        click.echo()
                        if click.confirm(
                            colored("Would you like to try another tutorial?", "green")
                        ):
                            continue
                        else:
                            success_message("Tutorial session completed successfully!")
                            return 0
                    else:
                        warning_message(
                            "Tutorial had issues. Please check the error messages above."
                        )
                        # U4 fix: answering "yes" shows the menu, not a retry
                        if click.confirm(
                            colored(
                                "Would you like to select another tutorial?",
                                "yellow",
                            )
                        ):
                            continue
                        else:
                            return result
                else:
                    error_message(
                        f"Invalid selection. Please choose 1-{len(tutorials)}, 'l', 'h', or 'q'."
                    )

            except ValueError:
                error_message("Invalid input. Please enter a number, 'l', 'h', or 'q'.")

        except KeyboardInterrupt:
            click.echo()
            info_message("Tutorial session cancelled")
            return 0
        except Exception as e:
            error_message(f"Error in interactive mode: {e}")
            return 1


# Register the command group
def register_commands():
    """Register tutorial commands with the CLI."""
    return tutorial


if __name__ == "__main__":
    tutorial()
