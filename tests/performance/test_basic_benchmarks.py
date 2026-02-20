import pytest

from panther.plugins.services.services_interface import RUN_CMD_SCHEMA, validate_structure


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

    benchmark(validate_structure, test_config, RUN_CMD_SCHEMA)


@pytest.mark.benchmark
def test_import_performance(benchmark):
    """Benchmark module import performance."""

    def import_modules():
        import panther.core.command_processor.command_processor  # noqa: F401
        import panther.core.events.service.emitter  # noqa: F401

        return True

    benchmark(import_modules)
