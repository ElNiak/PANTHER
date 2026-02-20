"""Basic performance benchmarks with regression detection.

Uses pytest-benchmark for timing and adds explicit upper-bound assertions
so regressions are caught in CI even without --benchmark-compare.
"""

import time

import pytest

from panther.plugins.services.services_interface import RUN_CMD_SCHEMA, validate_structure


# Upper bounds (seconds) for regression detection.
# These are generous limits - they should only trip on severe regressions.
VALIDATION_MAX_SECONDS = 0.05  # 50ms per single validation call
IMPORT_MAX_SECONDS = 5.0  # 5s for module imports (includes first-time overhead)


@pytest.mark.benchmark
def test_validation_performance(benchmark):
    """Benchmark configuration validation performance."""
    test_config = {
        "working_dir": "/path/to/dir",
        "command_binary": "binary",
        "command_args": "args",
        "timeout": 60,
        "environment": {},
    }

    result = benchmark(validate_structure, test_config, RUN_CMD_SCHEMA)

    # Assert the validation actually completed
    assert result is not False


@pytest.mark.benchmark
def test_import_performance(benchmark):
    """Benchmark module import performance."""

    def import_modules():
        import panther.core.command_processor.command_processor  # noqa: F401
        import panther.core.events.service.emitter  # noqa: F401

        return True

    result = benchmark(import_modules)
    assert result is True


def test_validation_regression_guard():
    """Standalone regression guard: single validation call must complete fast."""
    test_config = {
        "working_dir": "/path/to/dir",
        "command_binary": "binary",
        "command_args": "args",
        "timeout": 60,
        "environment": {},
    }

    start = time.monotonic()
    for _ in range(100):
        validate_structure(test_config, RUN_CMD_SCHEMA)
    elapsed = time.monotonic() - start

    avg = elapsed / 100
    assert avg < VALIDATION_MAX_SECONDS, (
        f"Average validation time {avg:.4f}s exceeds threshold "
        f"{VALIDATION_MAX_SECONDS}s"
    )


def test_import_regression_guard():
    """Standalone regression guard: module imports must complete fast."""
    start = time.monotonic()
    import panther.core.command_processor.command_processor  # noqa: F401
    import panther.core.events.service.emitter  # noqa: F401

    elapsed = time.monotonic() - start

    assert elapsed < IMPORT_MAX_SECONDS, (
        f"Import time {elapsed:.4f}s exceeds threshold {IMPORT_MAX_SECONDS}s"
    )
