"""Tests for CLI override extraction utility."""

from unittest.mock import MagicMock

import click
import pytest
from click.core import ParameterSource


def _make_ctx(commandline_params: dict, default_params: dict = None):
    """Create a mock Click context with parameter sources."""
    all_params = {**(default_params or {}), **commandline_params}
    ctx = MagicMock()
    ctx.params = all_params

    sources = {}
    for k in commandline_params:
        sources[k] = ParameterSource.COMMANDLINE
    for k in default_params or {}:
        if k not in commandline_params:
            sources[k] = ParameterSource.DEFAULT

    ctx.get_parameter_source = lambda p: sources.get(p, ParameterSource.DEFAULT)
    return ctx


class TestExtractCliOverrides:
    def test_no_commandline_params(self):
        from panther.config.core.utils.cli_overrides import extract_cli_overrides

        ctx = _make_ctx({}, {"force_build": False, "output_dir": "/default"})
        result = extract_cli_overrides(ctx)
        assert result == {}

    def test_single_override(self):
        from panther.config.core.utils.cli_overrides import extract_cli_overrides

        ctx = _make_ctx({"force_build": True})
        result = extract_cli_overrides(ctx)
        assert result == {"docker.force_build_docker_image": True}

    def test_multiple_overrides(self):
        from panther.config.core.utils.cli_overrides import extract_cli_overrides

        ctx = _make_ctx({"force_build": True, "output_dir": "/custom"})
        result = extract_cli_overrides(ctx)
        assert result == {
            "docker.force_build_docker_image": True,
            "paths.output_dir": "/custom",
        }

    def test_no_docker_cache_sets_two_fields(self):
        from panther.config.core.utils.cli_overrides import extract_cli_overrides

        ctx = _make_ctx({"no_docker_cache": True})
        result = extract_cli_overrides(ctx)
        assert result["docker.no_docker_cache"] is True
        assert result["docker.force_build_docker_image"] is True

    def test_unknown_params_ignored(self):
        from panther.config.core.utils.cli_overrides import extract_cli_overrides

        ctx = _make_ctx({"unknown_param": "value"})
        result = extract_cli_overrides(ctx)
        assert result == {}  # unknown_param not in CLI_CONFIG_MAP
