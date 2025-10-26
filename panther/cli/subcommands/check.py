"""
Check Command - Code quality and validation checks
"""

import logging
import subprocess
import sys
from argparse import ArgumentParser, _SubParsersAction
from pathlib import Path
from typing import Any, List

from panther.cli.base import BaseCommand


class CheckCommand(BaseCommand):
    """Handle code quality checks and validation."""

    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register the check subcommand parser."""
        parser = subparsers.add_parser(
            "check",
            help="Run code quality checks",
            description="Run various code quality checks and linters",
        )

        # Check options
        parser.add_argument(
            "--fix", action="store_true", help="Automatically fix issues where possible"
        )

        parser.add_argument(
            "--all", action="store_true", help="Run all available checks"
        )

        # Individual check options
        parser.add_argument(
            "--format", action="store_true", help="Check code formatting with black"
        )

        parser.add_argument(
            "--imports", action="store_true", help="Check import sorting with isort"
        )

        parser.add_argument(
            "--lint", action="store_true", help="Run linting with flake8"
        )

        parser.add_argument(
            "--type", action="store_true", help="Run type checking with mypy"
        )

        parser.add_argument(
            "--security", action="store_true", help="Run security checks with bandit"
        )

        parser.add_argument("--test", action="store_true", help="Run tests with pytest")

        parser.add_argument(
            "--coverage", action="store_true", help="Include coverage report with tests"
        )

        parser.add_argument(
            "--path",
            type=str,
            default="panther/",
            help="Path to check (default: panther/)",
        )

        parser.add_argument(
            "--config", type=str, help="Path to configuration file for checks"
        )

        return parser

    @classmethod
    def handle(cls, args: Any) -> int:
        """Handle the check command execution."""
        # Determine which checks to run
        checks_to_run = []

        if args.all:
            checks_to_run = ["format", "imports", "lint", "type", "security"]
            if args.test:
                checks_to_run.append("test")
        else:
            if args.format:
                checks_to_run.append("format")
            if args.imports:
                checks_to_run.append("imports")
            if args.lint:
                checks_to_run.append("lint")
            if args.type:
                checks_to_run.append("type")
            if args.security:
                checks_to_run.append("security")
            if args.test:
                checks_to_run.append("test")

        if not checks_to_run:
            cls.get_instance().logger.info(
                "❌ No checks specified. Use --all or specify individual checks."
            )
            cls.get_instance().logger.info(
                "   Available checks: --format, --imports, --lint, --type, --security, --test"
            )
            return 1

        cls.get_instance().logger.info(f"🔍 Running code quality checks on: {args.path}")
        cls.get_instance().logger.info(f"   Checks to run: {', '.join(checks_to_run)}")
        if args.fix:
            cls.get_instance().logger.info("   Auto-fix: Enabled")
        cls.get_instance().logger.info("-" * 60)

        # Install required tools if needed
        cls._ensure_tools_installed(checks_to_run)

        # Run checks
        total_errors = 0
        results = []

        for check in checks_to_run:
            if check == "format":
                errors = cls._check_format(args)
            elif check == "imports":
                errors = cls._check_imports(args)
            elif check == "lint":
                errors = cls._check_lint(args)
            elif check == "type":
                errors = cls._check_type(args)
            elif check == "security":
                errors = cls._check_security(args)
            elif check == "test":
                errors = cls._run_tests(args)
            else:
                errors = 1

            results.append((check, errors))
            total_errors += errors

        # Summary
        cls.get_instance().logger.info("\n" + "=" * 60)
        cls.get_instance().logger.info("📊 Check Summary:")
        for check, errors in results:
            status = "✅ PASSED" if errors == 0 else f"❌ FAILED ({errors} issues)"
            cls.get_instance().logger.info(f"   {check:<12}: {status}")

        if total_errors == 0:
            cls.get_instance().logger.info("\n✅ All checks passed!")
            return 0
        else:
            cls.get_instance().logger.info(f"\n❌ {total_errors} total issue(s) found")
            return 1

    @classmethod
    def _ensure_tools_installed(cls, checks: List[str]) -> None:
        """Ensure required tools are installed."""
        required_tools = {
            "format": ["black"],
            "imports": ["isort"],
            "lint": ["flake8"],
            "type": ["mypy"],
            "security": ["bandit"],
            "test": ["pytest"],
        }

        tools_to_install = set()
        for check in checks:
            tools_to_install.update(required_tools.get(check, []))

        if tools_to_install:
            cls.get_instance().logger.info("📦 Checking required tools...")
            missing_tools = []

            for tool in tools_to_install:
                try:
                    subprocess.run(
                        [sys.executable, "-m", tool, "--version"],
                        capture_output=True,
                        check=True,
                    )
                except (subprocess.CalledProcessError, FileNotFoundError):
                    missing_tools.append(tool)

            if missing_tools:
                cls.get_instance().logger.info(f"   Installing missing tools: {', '.join(missing_tools)}")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install"] + missing_tools,
                    check=False,
                )

    @classmethod
    def _check_format(cls, args: Any) -> int:
        """Check code formatting with black."""
        cls.get_instance().logger.info("\n🎨 Checking code formatting with black...")

        cmd = [sys.executable, "-m", "black"]
        if args.fix:
            cmd.append(args.path)
            cls.get_instance().logger.info("   Running black to format code...")
        else:
            cmd.extend(["--check", "--diff", args.path])
            cls.get_instance().logger.info("   Running black in check mode...")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            cls.get_instance().logger.info("   ✅ Code formatting is correct")
            return 0
        else:
            if args.fix:
                cls.get_instance().logger.info("   ✅ Code has been formatted")
                return 0
            else:
                cls.get_instance().logger.info("   ❌ Code formatting issues found")
                if result.stdout:
                    cls.get_instance().logger.info("\nSuggested changes:")
                    cls.get_instance().logger.info(result.stdout)
                cls.get_instance().logger.info("\n   💡 Run with --fix to automatically format")
                return 1

    @classmethod
    def _check_imports(cls, args: Any) -> int:
        """Check import sorting with isort."""
        cls.get_instance().logger.info("\n📦 Checking import sorting with isort...")

        cmd = [sys.executable, "-m", "isort"]
        if args.fix:
            cmd.append(args.path)
            cls.get_instance().logger.info("   Running isort to sort imports...")
        else:
            cmd.extend(["--check-only", "--diff", args.path])
            cls.get_instance().logger.info("   Running isort in check mode...")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            cls.get_instance().logger.info("   ✅ Import sorting is correct")
            return 0
        else:
            if args.fix:
                cls.get_instance().logger.info("   ✅ Imports have been sorted")
                return 0
            else:
                cls.get_instance().logger.info("   ❌ Import sorting issues found")
                if result.stdout:
                    # Limit output to first 20 lines
                    lines = result.stdout.split("\n")[:20]
                    cls.get_instance().logger.info("\nSuggested changes (first 20 lines):")
                    cls.get_instance().logger.info("\n".join(lines))
                    if len(result.stdout.split("\n")) > 20:
                        cls.get_instance().logger.info("   ... and more")
                cls.get_instance().logger.info("\n   💡 Run with --fix to automatically sort imports")
                return 1

    @classmethod
    def _check_lint(cls, args: Any) -> int:
        """Run linting with flake8."""
        cls.get_instance().logger.info("\n🔍 Running flake8 linting...")

        cmd = [sys.executable, "-m", "flake8", args.path]

        # Add config file if specified
        if args.config:
            cmd.extend(["--config", args.config])
        else:
            # Use sensible defaults
            cmd.extend(["--max-line-length=100", "--extend-ignore=E203,W503"])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            cls.get_instance().logger.info("   ✅ No linting issues found")
            return 0
        else:
            cls.get_instance().logger.info("   ❌ Linting issues found:")

            # Parse and count issues
            issues = result.stdout.strip().split("\n") if result.stdout else []
            issue_count = len([i for i in issues if i])

            # Show first 10 issues
            if issues:
                cls.get_instance().logger.info("\nFirst 10 issues:")
                for issue in issues[:10]:
                    if issue:
                        cls.get_instance().logger.info(f"   {issue}")
                if len(issues) > 10:
                    cls.get_instance().logger.info(f"\n   ... and {len(issues) - 10} more issues")

            return issue_count if issue_count > 0 else 1

    @classmethod
    def _check_type(cls, args: Any) -> int:
        """Run type checking with mypy."""
        cls.get_instance().logger.info("\n🔤 Running mypy type checking...")

        cmd = [sys.executable, "-m", "mypy", args.path]

        # Add config file if specified
        if args.config:
            cmd.extend(["--config-file", args.config])
        else:
            # Use sensible defaults
            cmd.extend(
                [
                    "--ignore-missing-imports",
                    "--no-strict-optional",
                    "--warn-return-any",
                    "--warn-unused-configs",
                ]
            )

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and not result.stdout.strip():
            cls.get_instance().logger.info("   ✅ No type checking issues found")
            return 0
        else:
            cls.get_instance().logger.info("   ❌ Type checking issues found:")

            # Parse and show issues
            output = result.stdout.strip()
            if output:
                lines = output.split("\n")
                error_count = len([l for l in lines if ": error:" in l])
                warning_count = len([l for l in lines if ": warning:" in l])
                note_count = len([l for l in lines if ": note:" in l])

                cls.get_instance().logger.info(
                    f"\n   Errors: {error_count}, Warnings: {warning_count}, Notes: {note_count}"
                )

                # Show first 10 errors
                errors = [l for l in lines if ": error:" in l][:10]
                if errors:
                    cls.get_instance().logger.info("\nFirst 10 errors:")
                    for error in errors:
                        cls.get_instance().logger.info(f"   {error}")
                    if len([l for l in lines if ": error:" in l]) > 10:
                        cls.get_instance().logger.info("   ... and more errors")

            return 1

    @classmethod
    def _check_security(cls, args: Any) -> int:
        """Run security checks with bandit."""
        cls.get_instance().logger.info("\n🔒 Running bandit security checks...")

        cmd = [sys.executable, "-m", "bandit", "-r", args.path]

        # Add config file if specified
        if args.config:
            cmd.extend(["-c", args.config])
        else:
            # Use sensible defaults
            cmd.extend(["-ll", "-i"])  # Only show medium and high severity

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            cls.get_instance().logger.info("   ✅ No security issues found")
            return 0
        else:
            cls.get_instance().logger.info("   ❌ Security issues found:")

            # Parse output to show summary
            output = result.stdout
            if "Total issues" in output:
                # Extract summary line
                for line in output.split("\n"):
                    if "Total issues" in line:
                        cls.get_instance().logger.info(f"\n   {line.strip()}")
                        break

            # Show first few issues
            if output:
                lines = output.split("\n")
                issue_lines = []
                in_issue = False

                for line in lines:
                    if ">> Issue:" in line:
                        in_issue = True
                    if in_issue:
                        issue_lines.append(line)
                        if line.strip() == "":
                            in_issue = False
                            if len(issue_lines) > 50:  # Limit output
                                break

                if issue_lines:
                    cls.get_instance().logger.info("\nSecurity issues found:")
                    cls.get_instance().logger.info("\n".join(issue_lines[:50]))
                    if len(issue_lines) > 50:
                        cls.get_instance().logger.info("\n   ... and more issues")

            return 1

    @classmethod
    def _run_tests(cls, args: Any) -> int:
        """Run tests with pytest."""
        cls.get_instance().logger.info("\n🧪 Running tests with pytest...")

        cmd = [sys.executable, "-m", "pytest"]

        # Add coverage if requested
        if args.coverage:
            cmd.extend(
                ["--cov=panther", "--cov-report=term-missing", "--cov-report=html"]
            )

        # Add test path
        test_path = Path("tests")
        if test_path.exists():
            cmd.append(str(test_path))
        else:
            cls.get_instance().logger.info("   ⚠️  No tests directory found")
            return 0

        # Add config file if specified
        if args.config:
            cmd.extend(["-c", args.config])

        # Run tests
        result = subprocess.run(cmd, capture_output=False)  # Let pytest handle output

        if result.returncode == 0:
            cls.get_instance().logger.info("\n   ✅ All tests passed")
            if args.coverage:
                cls.get_instance().logger.info("   📊 Coverage report generated in htmlcov/")
            return 0
        else:
            cls.get_instance().logger.info("\n   ❌ Some tests failed")
            return 1
