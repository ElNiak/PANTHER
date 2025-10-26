"""
Tools Command - Install and manage development/runtime tools
"""

import logging
import subprocess
import sys
from argparse import ArgumentParser, _SubParsersAction
from pathlib import Path
from typing import Any

from panther.cli.base import BaseCommand, CLIActionDispatchMixin


class ToolsCommand(BaseCommand, CLIActionDispatchMixin):
    """Handle tools installation and management."""

    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register the tools subcommand parser."""
        parser = subparsers.add_parser(
            "tools",
            help="Install and manage development/runtime tools",
            description="Install and manage various tools used by PANTHER",
        )

        subcommands = parser.add_subparsers(
            dest="tools_action", help="Tool management actions", metavar="ACTION"
        )

        # Install slim
        slim_parser = subcommands.add_parser(
            "install-slim",
            help="Install slim tool for Docker image optimization",
            description="Install the slim tool used for optimizing Docker images",
        )
        slim_parser.add_argument(
            "--force",
            action="store_true",
            help="Force reinstallation even if already present",
        )

        # Install pre-commit
        precommit_parser = subcommands.add_parser(
            "install-precommit",
            help="Install and configure pre-commit hooks",
            description="Install pre-commit framework and configure hooks for the project",
        )
        precommit_parser.add_argument(
            "--update", action="store_true", help="Update hooks to latest versions"
        )

        # List installed tools
        list_parser = subcommands.add_parser(
            "list",
            help="List installed tools",
            description="Show status of various tools",
        )

        return parser

    @classmethod
    def handle(cls, args: Any) -> int:
        """Handle the tools command execution."""
        action_handlers = {
            "install-slim": cls._install_slim,
            "install-precommit": cls._install_precommit,
            "list": cls._list_tools,
        }

        return cls.dispatch_action(args, "tools_action", action_handlers, "tools")

    @classmethod
    def _install_slim(cls, args: Any) -> int:
        """Install slim tool for Docker image optimization."""
        cls.get_instance().logger.info("Installing slim tool for Docker image optimization...")

        # Check if slim is already installed
        if not args.force:
            result = subprocess.run(["which", "slim"], capture_output=True)
            if result.returncode == 0:
                cls.get_instance().logger.info(
                    "✅ slim is already installed at: " + result.stdout.decode().strip()
                )
                return 0

        # Install slim using the official installation script
        cls.get_instance().logger.info("Downloading and installing slim...")
        try:
            # Use subprocess.Popen to chain commands securely without shell=True
            curl_cmd = [
                "curl",
                "-sL",
                "https://raw.githubusercontent.com/slimtoolkit/slim/master/scripts/install-slim.sh",
            ]
            bash_cmd = ["sudo", "-E", "bash", "-"]

            # Create the pipe between curl and bash
            curl_proc = subprocess.Popen(curl_cmd, stdout=subprocess.PIPE)
            bash_proc = subprocess.Popen(
                bash_cmd, stdin=curl_proc.stdout, stdout=subprocess.PIPE
            )

            # Allow curl_proc to receive SIGPIPE if bash_proc exits
            curl_proc.stdout.close()

            # Wait for the process to complete
            output, error = bash_proc.communicate()
            result = bash_proc

            # Verify installation was successful
            verify_result = subprocess.run(["which", "slim"], capture_output=True)

            if verify_result.returncode == 0:
                cls.get_instance().logger.info(
                    "✅ slim installed successfully at: "
                    + verify_result.stdout.decode().strip()
                )
                return 0
            else:
                cls.get_instance().logger.info("❌ slim installation failed. Could not find slim in PATH.")
                return 1

        except subprocess.CalledProcessError as e:
            cls.get_instance().logger.info(f"❌ Error installing slim: {e}")
            return 1
        except Exception as e:
            cls.get_instance().logger.info(f"❌ Unexpected error during slim installation: {e}")
            return 1

    @classmethod
    def _install_precommit(cls, args: Any) -> int:
        """Install and configure pre-commit hooks."""
        cls.get_instance().logger.info("Installing and configuring pre-commit hooks...")

        # Install pre-commit
        cls.get_instance().logger.info("Installing pre-commit package...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pre-commit"], capture_output=True
        )
        if result.returncode != 0:
            cls.get_instance().logger.info("❌ Failed to install pre-commit package")
            cls.get_instance().logger.info(result.stderr.decode())
            return result.returncode

        # Find project root (where .git directory is)
        current_path = Path.cwd()
        project_root = None

        while current_path != current_path.parent:
            if (current_path / ".git").exists():
                project_root = current_path
                break
            current_path = current_path.parent

        if not project_root:
            cls.get_instance().logger.info(
                "❌ Not in a git repository. Please run from within a git repository."
            )
            return 1

        # Check if .pre-commit-config.yaml exists in root
        precommit_config = project_root / ".pre-commit-config.yaml"

        if not precommit_config.exists():
            cls.get_instance().logger.info("No .pre-commit-config.yaml found in root. Creating one...")

            # Create a basic pre-commit config
            basic_config = """# See https://pre-commit.com for more information
# See https://pre-commit.com/hooks.html for more hooks
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files
    -   id: check-ast
    -   id: check-json
    -   id: check-merge-conflict
    -   id: check-toml
    -   id: pretty-format-json
        args: ["--autofix", "--no-sort-keys"]

-   repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
    -   id: black

-   repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
    -   id: isort

-   repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
    -   id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]
"""
            with open(precommit_config, "w") as f:
                f.write(basic_config)
            cls.get_instance().logger.info("✅ Created basic .pre-commit-config.yaml")
        else:
            cls.get_instance().logger.info("✅ .pre-commit-config.yaml already exists in root")

        # Install the pre-commit hooks
        cls.get_instance().logger.info("Installing pre-commit hooks into .git/hooks/...")
        result = subprocess.run(
            ["pre-commit", "install"], cwd=project_root, capture_output=True
        )
        if result.returncode != 0:
            cls.get_instance().logger.info("❌ Failed to install pre-commit hooks")
            cls.get_instance().logger.info(result.stderr.decode())
            return result.returncode

        # Update hooks if requested
        if args.update:
            cls.get_instance().logger.info("Updating pre-commit hooks to latest versions...")
            result = subprocess.run(
                ["pre-commit", "autoupdate"], cwd=project_root, capture_output=True
            )
            if result.returncode != 0:
                cls.get_instance().logger.info(
                    "⚠️  Warning: Failed to update pre-commit hooks, but installation was successful"
                )

        cls.get_instance().logger.info("✅ Pre-commit hooks installed and configured successfully!")
        cls.get_instance().logger.info("💡 To run pre-commit on all files: pre-commit run --all-files")

        return 0

    @classmethod
    def _list_tools(cls, args: Any) -> int:
        """List installed tools and their status."""
        cls.get_instance().logger.info("🔍 PANTHER Tools Status")
        cls.get_instance().logger.info("=" * 40)

        tools = [
            ("slim", "Docker image optimizer"),
            ("pre-commit", "Git hooks framework"),
            ("docker", "Container platform"),
            ("mkdocs", "Documentation generator"),
            ("pytest", "Testing framework"),
            ("black", "Code formatter"),
            ("isort", "Import sorter"),
            ("flake8", "Code linter"),
            ("mypy", "Type checker"),
        ]

        for tool_name, description in tools:
            result = subprocess.run(
                ["which", tool_name], capture_output=True, text=True
            )

            if result.returncode == 0:
                location = result.stdout.strip()

                # Try to get version
                version = "unknown"
                try:
                    if tool_name in ["python", "pip"]:
                        ver_result = subprocess.run(
                            [tool_name, "--version"], capture_output=True, text=True
                        )
                    else:
                        # Try common version flags
                        for flag in ["--version", "-v", "version"]:
                            ver_result = subprocess.run(
                                [tool_name, flag], capture_output=True, text=True
                            )
                            if ver_result.returncode == 0:
                                break

                    if ver_result.returncode == 0:
                        version_output = ver_result.stdout.strip()
                        # Extract version number (basic pattern)
                        import re

                        ver_match = re.search(r"(\d+\.\d+\.\d+)", version_output)
                        if ver_match:
                            version = ver_match.group(1)
                except Exception:
                    pass

                cls.get_instance().logger.info(f"✅ {tool_name:<12} {version:<10} - {description}")
            else:
                cls.get_instance().logger.info(f"❌ {tool_name:<12} {'not found':<10} - {description}")

        return 0
