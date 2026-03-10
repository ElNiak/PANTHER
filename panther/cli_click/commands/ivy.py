"""CLI commands for Ivy formal verification and LSP integration.

Provides standalone access to panther_ivy compilation and test execution
without requiring the full experiment pipeline.
"""

import json
import sys
from pathlib import Path

import click

from panther.cli_click.core.base import featured_example
from panther.plugins.services.testers.panther_ivy.api.compiler import (
    generate_compile_commands,
    parse_compile_output,
)
from panther.plugins.services.testers.panther_ivy.api.discovery import (
    detect_from_path,
    list_tests,
)
from panther.plugins.services.testers.panther_ivy.api.runner import (
    generate_test_commands,
    parse_test_output,
)

from .ivy_executor import IvyExecutor


def _output_json(data: dict) -> None:
    """Write JSON to stdout."""
    click.echo(json.dumps(data, indent=2))


def _output_raw(text: str) -> None:
    """Write raw text to stdout."""
    click.echo(text)


@featured_example("panther ivy status")
@click.group()
@click.pass_context
def ivy(ctx):
    """Ivy formal verification and LSP integration.

    Standalone commands for compiling Ivy specifications and running
    formal verification tests. Designed for LSP integration and
    manual use without the full experiment pipeline.

    Examples:

    \b
        panther ivy compile protocol-testing/quic/quic_tests/server_tests/quic_server_test_stream.ivy
        panther ivy list-tests --protocol quic
        panther ivy build --build-mode rel-lto
        panther ivy test protocol-testing/quic/quic_tests/server_tests/quic_server_test_stream.ivy
    """
    ctx.ensure_object(dict)


@ivy.command()
@click.argument("ivy_file", type=click.Path(exists=True))
@click.option("--protocol", default=None, help="Override auto-detected protocol")
@click.option("--version", default=None, help="Override auto-detected version")
@click.option("--build-mode", default="", help="Z3 build mode")
@click.option("--test-iters", default=300, type=int, help="Internal Ivy iterations")
@click.option(
    "--target",
    type=click.Choice(["docker", "host", "compose", "auto"]),
    default="auto",
    help="Execution target",
)
@click.option(
    "--output",
    type=click.Choice(["json", "raw"]),
    default="json",
    help="Output format",
)
@click.option(
    "--compose-service",
    default=None,
    help="Docker Compose service name (for compose target)",
)
def compile(
    ivy_file, protocol, version, build_mode, test_iters, target, output, compose_service
):
    """Compile an .ivy file. Primary command for LSP integration.

    Auto-detects protocol and version from the file path.
    Outputs structured JSON diagnostics by default.
    """
    ivy_path = Path(ivy_file)

    # Resolve executor first to get base_path
    executor = IvyExecutor(target=target)
    executor._ivy_file = ivy_path
    if compose_service:
        executor._compose_service = compose_service
    base_path = executor.get_base_path()

    # Generate compilation commands
    compile_result = generate_compile_commands(
        ivy_file=ivy_path,
        protocol=protocol,
        version=version,
        build_mode=build_mode,
        test_iters=test_iters,
        base_path=base_path,
    )

    # Execute
    exec_result = executor.execute_compile(compile_result)

    if output == "raw":
        _output_raw(exec_result.stdout)
        if exec_result.stderr:
            _output_raw(exec_result.stderr)
        return

    # Parse diagnostics
    diagnostics = parse_compile_output(exec_result.stdout, exec_result.stderr)
    has_errors = any(d.severity == "error" for d in diagnostics)
    status = "error" if (exec_result.exit_code != 0 or has_errors) else "success"

    # Auto-detect metadata for output
    try:
        detected = detect_from_path(ivy_path)
        file_protocol = protocol or detected.get("protocol", "")
        file_version = version or detected.get("version", "")
    except ValueError:
        file_protocol = protocol or ""
        file_version = version or ""

    _output_json(
        {
            "status": status,
            "file": str(ivy_file),
            "protocol": file_protocol,
            "version": file_version,
            "target": exec_result.target,
            "diagnostics": [d.to_dict() for d in diagnostics],
        }
    )


@ivy.command("run-test")
@click.argument("ivy_file", type=click.Path(exists=True))
@click.option("--protocol", default=None, help="Override auto-detected protocol")
@click.option("--version", default=None, help="Override auto-detected version")
@click.option("--seed", type=int, default=None, help="Random seed")
@click.option("--iterations", type=int, default=1, help="Test repetitions")
@click.option("--target-addr", default=None, help="Target service address")
@click.option(
    "--target",
    type=click.Choice(["docker", "host", "compose", "auto"]),
    default="auto",
    help="Execution target",
)
@click.option(
    "--output",
    type=click.Choice(["json", "raw"]),
    default="json",
    help="Output format",
)
@click.option(
    "--compose-service",
    default=None,
    help="Docker Compose service name (for compose target)",
)
def run_test(
    ivy_file,
    protocol,
    version,
    seed,
    iterations,
    target_addr,
    target,
    output,
    compose_service,
):
    """Run a compiled Ivy test binary."""
    ivy_path = Path(ivy_file)

    executor = IvyExecutor(target=target)
    executor._ivy_file = ivy_path
    if compose_service:
        executor._compose_service = compose_service
    base_path = executor.get_base_path()

    test_result = generate_test_commands(
        ivy_file=ivy_path,
        protocol=protocol,
        version=version,
        seed=seed,
        iterations=iterations,
        target_addr=target_addr,
        base_path=base_path,
    )

    # Only run the test binary (skip compilation)
    exec_result = executor.execute(test_result.run_commands)

    if output == "raw":
        _output_raw(exec_result.stdout)
        if exec_result.stderr:
            _output_raw(exec_result.stderr)
        return

    verdict = parse_test_output(exec_result.stdout, exec_result.stderr)

    _output_json(
        {
            "status": "success" if verdict["passed"] else "failure",
            "file": str(ivy_file),
            "verdict": verdict["verdict"],
            "details": verdict["details"],
            "target": exec_result.target,
        }
    )


@ivy.command()
@click.argument("ivy_file", type=click.Path(exists=True))
@click.option("--protocol", default=None, help="Override auto-detected protocol")
@click.option("--version", default=None, help="Override auto-detected version")
@click.option("--seed", type=int, default=None, help="Random seed")
@click.option("--iterations", type=int, default=1, help="Test repetitions")
@click.option("--target-addr", default=None, help="Target service address")
@click.option("--build-mode", default="", help="Z3 build mode")
@click.option("--test-iters", default=300, type=int, help="Internal Ivy iterations")
@click.option(
    "--target",
    type=click.Choice(["docker", "host", "compose", "auto"]),
    default="auto",
    help="Execution target",
)
@click.option(
    "--output",
    type=click.Choice(["json", "raw"]),
    default="json",
    help="Output format",
)
@click.option(
    "--compose-service",
    default=None,
    help="Docker Compose service name (for compose target)",
)
def test(
    ivy_file,
    protocol,
    version,
    seed,
    iterations,
    target_addr,
    build_mode,
    test_iters,
    target,
    output,
    compose_service,
):
    """Full test cycle: compile + run + analyze.

    Compiles the Ivy specification, runs the test binary, and analyzes results.
    """
    ivy_path = Path(ivy_file)

    executor = IvyExecutor(target=target)
    executor._ivy_file = ivy_path
    if compose_service:
        executor._compose_service = compose_service
    base_path = executor.get_base_path()

    test_result = generate_test_commands(
        ivy_file=ivy_path,
        protocol=protocol,
        version=version,
        seed=seed,
        iterations=iterations,
        target_addr=target_addr,
        build_mode=build_mode,
        test_iters=test_iters,
        base_path=base_path,
    )

    exec_result = executor.execute_test(test_result)

    if output == "raw":
        _output_raw(exec_result.stdout)
        if exec_result.stderr:
            _output_raw(exec_result.stderr)
        return

    # Parse both compilation and test output
    compile_diags = parse_compile_output(exec_result.stdout, exec_result.stderr)
    verdict = parse_test_output(exec_result.stdout, exec_result.stderr)

    _output_json(
        {
            "status": "success" if verdict["passed"] else "failure",
            "file": str(ivy_file),
            "verdict": verdict["verdict"],
            "details": verdict["details"],
            "compile_diagnostics": [d.to_dict() for d in compile_diags],
            "target": exec_result.target,
        }
    )


@ivy.command("list-tests")
@click.option("--protocol", default=None, help="Filter by protocol")
@click.option("--version", default=None, help="Filter by version")
@click.option(
    "--output",
    type=click.Choice(["json", "raw"]),
    default="json",
    help="Output format",
)
def list_tests_cmd(protocol, version, output):
    """List available Ivy test specifications."""
    tests = list_tests(protocol=protocol, version=version)

    if output == "raw":
        for t in tests:
            _output_raw(f"{t.name}  {t.protocol}/{t.version}  [{t.role}]  {t.ivy_file}")
        if not tests:
            _output_raw("No tests found.")
        return

    _output_json(
        {
            "tests": [t.to_dict() for t in tests],
        }
    )


@ivy.command()
@click.option("--build-mode", default="", help="Z3 build mode")
@click.option("--force/--no-force", default=False, help="Force rebuild")
@click.option(
    "--output",
    type=click.Choice(["json", "raw"]),
    default="json",
    help="Output format",
)
def build(build_mode, force, output):
    """Build or ensure the panther_ivy Docker image exists."""
    executor = IvyExecutor(target="docker")

    try:
        image = executor.ensure_docker_image(build_mode=build_mode, force=force)
        if output == "raw":
            _output_raw(f"Docker image ready: {image}")
            return
        _output_json(
            {
                "status": "success",
                "image": image,
            }
        )
    except RuntimeError as e:
        if output == "raw":
            _output_raw(f"Build failed: {e}")
            sys.exit(1)
        _output_json(
            {
                "status": "error",
                "message": str(e),
            }
        )
        sys.exit(1)
