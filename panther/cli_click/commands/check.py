"""
Check Command - Click Implementation

Code quality and validation checks with enhanced user experience.
"""

import logging
from pathlib import Path

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


@click.command()
@click.option("--fix", is_flag=True, help="Automatically fix issues where possible")
@click.option("--all", is_flag=True, help="Run all available checks")
# Individual check options
@click.option("--format", is_flag=True, help="Check code formatting with black")
@click.option("--imports", is_flag=True, help="Check import sorting with isort")
@click.option("--lint", is_flag=True, help="Run linting with flake8")
@click.option("--type", is_flag=True, help="Run type checking with mypy")
@click.option("--security", is_flag=True, help="Run security checks with bandit")
@click.option("--test", is_flag=True, help="Run tests with pytest")
@click.option("--coverage", is_flag=True, help="Include coverage report with tests")
# Configuration options
@click.option(
    "--path",
    type=click.Path(exists=True),
    default="panther/",
    help="Path to check (default: panther/)",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to configuration file for checks",
)
@handle_errors
@pass_context_and_setup_logging
def check(
    ctx, fix, all, format, imports, lint, type, security, test, coverage, path, config
):
    """
    Run comprehensive code quality checks and linters.

    Provides multiple code quality analysis tools:
    • Code formatting (black)
    • Import sorting (isort)
    • Linting (flake8)
    • Type checking (mypy)
    • Security analysis (bandit)
    • Test execution (pytest)

    \b
    Key Features:
    🎨 Automated code formatting
    📎 Import organization
    🔍 Comprehensive linting
    📝 Type safety validation
    🔒 Security vulnerability scanning
    🧪 Test execution with coverage

    \b
    Check Types:
    • --format: Code formatting with black
    • --imports: Import sorting with isort
    • --lint: Linting with flake8
    • --type: Type checking with mypy
    • --security: Security checks with bandit
    • --test: Test execution with pytest

    \b
    Examples:
      # Run all checks
      panther check --all

      # Run specific checks
      panther check --format --lint

      # Auto-fix issues where possible
      panther check --all --fix

      # Check specific path
      panther check --all --path src/

      # Include test coverage
      panther check --test --coverage

      # Use custom config
      panther check --lint --config setup.cfg

    \b
    Auto-Fix Support:
    When using --fix flag:
    • black: Automatically formats code
    • isort: Automatically sorts imports
    • Other tools: Show suggestions only

    \b
    Configuration:
    Each tool can be configured using:
    • Command-line --config option
    • Tool-specific config files (pyproject.toml, setup.cfg, etc.)
    • Built-in sensible defaults
    """
    # Determine which checks to run
    checks_to_run = []

    if all:
        checks_to_run = ["format", "imports", "lint", "type", "security"]
        if test:
            checks_to_run.append("test")
    else:
        if format:
            checks_to_run.append("format")
        if imports:
            checks_to_run.append("imports")
        if lint:
            checks_to_run.append("lint")
        if type:
            checks_to_run.append("type")
        if security:
            checks_to_run.append("security")
        if test:
            checks_to_run.append("test")

    if not checks_to_run:
        error_message("No checks specified")
        info_message(
            "Available checks: --format, --imports, --lint, --type, --security, --test"
        )
        info_message("Use --all to run all checks, or specify individual checks")
        raise click.Abort()

    # Enhanced logging setup
    verbose = ctx.obj.get("verbose", False)

    if verbose:
        info_message(f"Running code quality checks on: {path}")
        info_message(f"Checks to run: {', '.join(checks_to_run)}")
        if fix:
            info_message("Auto-fix: Enabled")
        if config:
            info_message(f"Config file: {config}")
        click.echo()

    # Native Click implementation for code quality checks
    try:
        import subprocess
        import sys

        # Show configuration summary
        if verbose:
            click.echo(colored("📋 Check Configuration:", "blue", attrs=["bold"]))
            click.echo(f"   📁 Target path: {path}")
            click.echo(f"   🔧 Checks: {', '.join(checks_to_run)}")
            if fix:
                click.echo(
                    f"   ⚙️ Mode: {colored('AUTO-FIX', 'green', attrs=['bold'])}"
                )
            else:
                click.echo(
                    f"   ⚙️ Mode: {colored('CHECK-ONLY', 'yellow', attrs=['bold'])}"
                )
            if config:
                click.echo(f"   📄 Config: {config}")
            click.echo()

        check_results = []

        # Run checks with progress tracking
        with click.progressbar(
            checks_to_run, label="Running checks", show_eta=True, show_percent=True
        ) as bar:
            for check_type in bar:
                click.echo(f"\n🔍 Running {check_type} check...")

                if check_type == "format":
                    # Black formatting check
                    cmd = ["black", "--check" if not fix else "", str(path)]
                    if not fix:
                        cmd.remove("")
                elif check_type == "imports":
                    # isort import sorting
                    cmd = ["isort", "--check-only" if not fix else "", str(path)]
                    if not fix:
                        cmd.remove("")
                elif check_type == "lint":
                    # flake8 linting
                    cmd = ["flake8", str(path)]
                    if config:
                        cmd.extend(["--config", str(config)])
                elif check_type == "type":
                    # mypy type checking
                    cmd = ["mypy", str(path)]
                elif check_type == "security":
                    # bandit security check
                    cmd = ["bandit", "-r", str(path)]
                elif check_type == "test":
                    # pytest testing
                    cmd = ["pytest", str(path)]
                    if coverage:
                        cmd.extend(["--cov", str(path), "--cov-report", "term-missing"])
                else:
                    click.echo(f"  ⚠️ Unknown check type: {check_type}")
                    continue

                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=120
                    )

                    if result.returncode == 0:
                        click.echo(f"  ✅ {check_type}: PASSED")
                        check_results.append((check_type, True, ""))
                    else:
                        click.echo(f"  ❌ {check_type}: FAILED")
                        if verbose and result.stdout:
                            click.echo(f"     Output: {result.stdout[:200]}...")
                        check_results.append((check_type, False, result.stdout))

                except subprocess.TimeoutExpired:
                    click.echo(f"  ⏰ {check_type}: TIMEOUT")
                    check_results.append((check_type, False, "Command timed out"))
                except FileNotFoundError:
                    click.echo(f"  ❓ {check_type}: TOOL NOT FOUND")
                    check_results.append(
                        (check_type, False, f"Tool for {check_type} not installed")
                    )

        # Show summary
        click.echo("\n📊 Check Summary:")
        passed = sum(1 for _, success, _ in check_results if success)
        total = len(check_results)

        for check_type, success, output in check_results:
            status = "✅ PASSED" if success else "❌ FAILED"
            click.echo(f"  {check_type}: {status}")

        if passed == total:
            success_message(f"All {total} checks passed successfully")
            if fix:
                info_message("Code has been automatically formatted where possible")
        else:
            error_message(f"{total - passed} of {total} checks failed")
            if not fix:
                info_message(
                    "Run with --fix to automatically resolve formatting issues"
                )

            # Show failed checks details in verbose mode
            if verbose:
                click.echo("\n🔍 Failed Check Details:")
                for check_type, success, output in check_results:
                    if not success and output:
                        click.echo(f"\n{check_type}:")
                        click.echo(
                            output[:500] + "..." if len(output) > 500 else output
                        )

            raise click.Abort()

    except Exception as e:
        error_message(f"Check execution failed: {e}")
        if ctx.obj.get("debug", False):
            import traceback

            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


# Add convenience commands for individual checks
@click.group()
def check_group():
    """Code quality check commands."""
    pass


# Add the main check command to the group
check_group.add_command(check)


@check_group.command("format")
@click.option("--fix", is_flag=True, help="Auto-format code")
@click.option(
    "--path", type=click.Path(exists=True), default="panther/", help="Path to check"
)
@handle_errors
@pass_context_and_setup_logging
def format_only(ctx, fix, path):
    """
    Run only code formatting checks with black.

    Convenience command for quick formatting checks.
    """
    ctx.invoke(check, format=True, fix=fix, path=path)


@check_group.command("lint")
@click.option(
    "--path", type=click.Path(exists=True), default="panther/", help="Path to check"
)
@click.option("--config", type=click.Path(exists=True), help="Configuration file")
@handle_errors
@pass_context_and_setup_logging
def lint_only(ctx, path, config):
    """
    Run only linting checks with flake8.

    Convenience command for quick linting.
    """
    ctx.invoke(check, lint=True, path=path, config=config)


@check_group.command("security")
@click.option(
    "--path", type=click.Path(exists=True), default="panther/", help="Path to check"
)
@handle_errors
@pass_context_and_setup_logging
def security_only(ctx, path):
    """
    Run only security checks with bandit.

    Convenience command for security scanning.
    """
    ctx.invoke(check, security=True, path=path)


@check_group.command("test")
@click.option("--coverage", is_flag=True, help="Include coverage report")
@handle_errors
@pass_context_and_setup_logging
def test_only(ctx, coverage):
    """
    Run only tests with pytest.

    Convenience command for test execution.
    """
    ctx.invoke(check, test=True, coverage=coverage)


if __name__ == "__main__":
    check_group()
