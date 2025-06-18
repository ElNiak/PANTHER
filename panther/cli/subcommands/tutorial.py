"""
Tutorial Command - Interactive tutorials and learning
"""

from argparse import ArgumentParser, _SubParsersAction
from typing import Any

from ..base import BaseCommand


class TutorialCommand(BaseCommand):
    """Handle tutorial and learning commands."""

    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register the tutorial subcommand parser."""
        parser = subparsers.add_parser(
            "tutorial",
            help="Interactive tutorials and learning",
            description="Access interactive tutorials for learning PANTHER development",
        )

        subcommands = parser.add_subparsers(
            dest="tutorial_action", help="Tutorial actions", metavar="ACTION"
        )

        # Run subcommand
        run_parser = subcommands.add_parser(
            "run",
            help="Run specific tutorial",
            description="Run a specific tutorial by type",
        )
        run_parser.add_argument(
            "tutorial_type",
            choices=["service", "environment", "protocol", "configuration"],
            help="Type of tutorial to run",
        )

        # Interactive subcommand
        interactive_parser = subcommands.add_parser(
            "interactive",
            help="Start interactive tutorial mode",
            description="Start interactive tutorial selection and guidance",
        )

        # List subcommand
        list_parser = subcommands.add_parser(
            "list",
            help="List available tutorials",
            description="List all available tutorials",
        )

        return parser

    @classmethod
    def handle(cls, args: Any) -> int:
        """Handle the tutorial command execution."""
        if not hasattr(args, "tutorial_action") or args.tutorial_action is None:
            logging.info(
                "❌ No tutorial action specified. Use 'panther tutorial --help' for options."
            )
            return 1

        if args.tutorial_action == "run":
            return cls._handle_run_tutorial(args)
        elif args.tutorial_action == "interactive":
            return cls._handle_interactive_tutorial(args)
        elif args.tutorial_action == "list":
            return cls._handle_list_tutorials(args)
        else:
            logging.info(f"❌ Unknown tutorial action: {args.tutorial_action}")
            return 1

    @classmethod
    def _handle_run_tutorial(cls, args: Any) -> int:
        """Handle running specific tutorial."""
        try:
            from ...tools.plugins.plugin_creator import run_tutorial

            tutorial_type = args.tutorial_type
            logging.info(f"📚 Starting {tutorial_type} tutorial...")

            success = run_tutorial(tutorial_type)

            if success:
                logging.info(f"✅ Tutorial '{tutorial_type}' completed successfully")
                return 0
            else:
                logging.info(f"❌ Tutorial '{tutorial_type}' failed")
                return 1

        except Exception as e:
            logging.info(f"❌ Error running tutorial: {e}")
            if hasattr(args, "debug") and args.debug:
                import traceback

                traceback.print_exc()
            return 1

    @classmethod
    def _handle_interactive_tutorial(cls, args: Any) -> int:
        """Handle interactive tutorial mode."""
        try:
            logging.info("🎓 Welcome to PANTHER Interactive Tutorials!")
            logging.info("=" * 50)

            tutorials = [
                ("service", "Learn to create service plugins"),
                ("environment", "Learn to create environment plugins"),
                ("protocol", "Learn to create protocol plugins"),
                ("configuration", "Learn to write experiment configurations"),
            ]

            logging.info("\nAvailable tutorials:")
            for i, (tutorial_type, description) in enumerate(tutorials, 1):
                logging.info(f"  {i}. {tutorial_type.title()} - {description}")

            logging.info(
                "\nSelect a tutorial by number (1-{}), or 'q' to quit:".format(
                    len(tutorials)
                )
            )

            try:
                choice = input("> ").strip()

                if choice.lower() == "q":
                    logging.info("👋 Tutorial session ended")
                    return 0

                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(tutorials):
                        tutorial_type = tutorials[choice_num - 1][0]

                        # Create args object for run_tutorial
                        tutorial_args = type(
                            "Args", (), {"tutorial_type": tutorial_type}
                        )()
                        return cls._handle_run_tutorial(tutorial_args)
                    else:
                        logging.info(
                            "❌ Invalid selection. Please choose 1-{}.".format(
                                len(tutorials)
                            )
                        )
                        return 1
                except ValueError:
                    logging.info("❌ Invalid input. Please enter a number or 'q'.")
                    return 1

            except KeyboardInterrupt:
                logging.info("\n👋 Tutorial session cancelled")
                return 0

        except Exception as e:
            logging.info(f"❌ Error in interactive tutorial: {e}")
            return 1

    @classmethod
    def _handle_list_tutorials(cls, args: Any) -> int:
        """Handle listing available tutorials."""
        try:
            logging.info("📚 Available PANTHER Tutorials")
            logging.info("=" * 40)

            tutorials = [
                {
                    "name": "service",
                    "title": "Service Plugin Development",
                    "description": "Learn to create service plugins for protocol implementations",
                    "duration": "15-20 minutes",
                    "difficulty": "Beginner",
                },
                {
                    "name": "environment",
                    "title": "Environment Plugin Development",
                    "description": "Learn to create network and execution environment plugins",
                    "duration": "20-25 minutes",
                    "difficulty": "Intermediate",
                },
                {
                    "name": "protocol",
                    "title": "Protocol Plugin Development",
                    "description": "Learn to create protocol definition plugins",
                    "duration": "10-15 minutes",
                    "difficulty": "Beginner",
                },
                {
                    "name": "configuration",
                    "title": "Experiment Configuration",
                    "description": "Learn to write and structure experiment configuration files",
                    "duration": "10-15 minutes",
                    "difficulty": "Beginner",
                },
            ]

            for tutorial in tutorials:
                logging.info(f"\n🎯 {tutorial['title']}")
                logging.info(f"   Name: {tutorial['name']}")
                logging.info(f"   Description: {tutorial['description']}")
                logging.info(f"   Duration: {tutorial['duration']}")
                logging.info(f"   Difficulty: {tutorial['difficulty']}")
                logging.info(f"   Command: panther tutorial run {tutorial['name']}")

            logging.info(f"\nTo start a tutorial, use: panther tutorial run <name>")
            logging.info(f"For interactive mode, use: panther tutorial interactive")

            return 0

        except Exception as e:
            logging.info(f"❌ Error listing tutorials: {e}")
            return 1
