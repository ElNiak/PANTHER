"""Shared fixtures for tests/unit/test_core/.

Provides real PANTHER class instances with only IO-boundary mocking
(Docker daemon, subprocess, filesystem writes). Tests should exercise
real code paths, not shadow classes.
"""

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# DockerBuilder fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_docker_builder_singleton():
    """Reset DockerBuilder singleton between tests.

    DockerBuilder uses a singleton pattern. Without reset, state leaks
    between tests (cached client, image_cache, config, etc.).
    """
    yield
    try:
        from panther.core.docker_builder.docker_builder import DockerBuilder

        DockerBuilder.reset_singleton()
    except Exception:
        pass


@pytest.fixture
def mock_docker_client():
    """Create a mock Docker client that passes ping() and version checks.

    This replaces only the IO boundary — the actual Docker daemon connection.
    All DockerBuilder logic (tag generation, sanitization, cache, platform
    detection) runs as real code.
    """
    client = MagicMock()
    client.ping.return_value = True
    client.version.return_value = {
        "Version": "24.0.0",
        "ApiVersion": "1.43",
        "Os": "linux",
        "Arch": "amd64",
        "Platform": {"Name": "Docker Engine - Community"},
    }
    # images API
    client.images.list.return_value = []
    client.images.get.side_effect = Exception("Image not found")
    client.images.build.return_value = (MagicMock(id="sha256:abc123"), [])
    # containers API
    client.containers.list.return_value = []
    client.containers.get.side_effect = Exception("Container not found")
    # networks API
    client.networks.list.return_value = []
    client.networks.get.side_effect = Exception("Network not found")
    client.networks.create.return_value = MagicMock(id="net123")
    return client


@pytest.fixture
def real_docker_builder(mock_docker_client):
    """Create a real DockerBuilder with only docker.from_env() mocked.

    The returned builder is a genuine DockerBuilder instance connected
    to a mock Docker daemon. All internal logic (tag generation,
    sanitization, caching, platform detection) is real.

    Usage::

        def test_tag_generation(real_docker_builder):
            tag = real_docker_builder.generate_image_tag(
                impl_name="picoquic", version="v1.0", role="server"
            )
            assert "picoquic" in tag
    """
    from panther.core.docker_builder.docker_builder import DockerBuilder

    # Reset to guarantee fresh singleton
    DockerBuilder.reset_singleton()

    with patch("panther.core.docker_builder.docker_builder.docker") as mock_docker_mod:
        mock_docker_mod.from_env.return_value = mock_docker_client
        mock_docker_mod.errors = _make_docker_errors_module()

        builder = DockerBuilder(
            build_log_file=False,
            enable_cache=True,
        )

    # Verify we got a real instance
    assert isinstance(builder, DockerBuilder)
    return builder


@pytest.fixture
def real_docker_builder_with_config(mock_docker_client, minimal_global_config):
    """Create a real DockerBuilder with a real GlobalConfig.

    Same as real_docker_builder but also sets global_config, which
    enables testing of config-dependent methods like
    _should_use_buildx(), get_target_platform(), etc.
    """
    from panther.core.docker_builder.docker_builder import DockerBuilder

    DockerBuilder.reset_singleton()

    with patch("panther.core.docker_builder.docker_builder.docker") as mock_docker_mod:
        mock_docker_mod.from_env.return_value = mock_docker_client
        mock_docker_mod.errors = _make_docker_errors_module()

        builder = DockerBuilder(
            build_log_file=False,
            enable_cache=True,
            global_config=minimal_global_config,
        )

    return builder


# ---------------------------------------------------------------------------
# Config model fixtures (real Pydantic objects, not mocks)
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_global_config():
    """Create a minimal real GlobalConfig for testing.

    Returns a genuine Pydantic model, not a mock. Tests that need
    config-dependent behavior should use this.
    """
    from panther.config.core.models.global_config import GlobalConfig

    return GlobalConfig(
        logging={"level": "INFO", "format": "%(levelname)s - %(message)s"},
        paths={"output_dir": "/tmp/panther_test/outputs", "log_dir": "/tmp/panther_test/logs"},
        docker={
            "build_docker_image": True,
            "force_build_docker_image": False,
        },
    )


@pytest.fixture
def minimal_service_config():
    """Create a minimal real ServiceConfig for testing.

    Returns a genuine config object with real ProtocolConfig and
    ImplementationConfig sub-objects.
    """
    from panther.config.core.models.experiment import ServiceConfig

    return ServiceConfig(
        timeout=60,
        implementation={"name": "picoquic", "type": "iut"},
        protocol={
            "name": "quic",
            "version": "rfc9000",
            "role": "server",
        },
    )


@pytest.fixture
def minimal_test_config():
    """Create a minimal real TestConfig for testing."""
    from panther.config.core.models.experiment import TestConfig

    return TestConfig(
        name="test_case",
        description="Test case",
        network_environment={"type": "docker_compose"},
        services={
            "test_service": {
                "timeout": 60,
                "implementation": {"name": "picoquic", "type": "iut"},
                "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
            }
        },
    )


# ---------------------------------------------------------------------------
# CommandProcessor fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def real_command_processor():
    """Create a real CommandProcessor instance.

    CommandProcessor has no external IO in __init__, so no mocking
    is needed for instantiation. Mock subprocess only when testing
    actual command execution.
    """
    from panther.core.command_processor import CommandProcessor

    return CommandProcessor()


# ---------------------------------------------------------------------------
# Event system fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def real_event_manager():
    """Create a real EventManager instance.

    EventManager is purely in-memory (no IO in init), so no mocking needed.
    """
    from panther.core.observer.management.event_manager import EventManager

    return EventManager()


# ---------------------------------------------------------------------------
# Helpers (not fixtures)
# ---------------------------------------------------------------------------


def _make_docker_errors_module():
    """Create a mock docker.errors module with real exception types."""
    errors = MagicMock()
    errors.DockerException = type("DockerException", (Exception,), {})
    errors.ImageNotFound = type("ImageNotFound", (Exception,), {})
    errors.NotFound = type("NotFound", (Exception,), {})
    errors.APIError = type("APIError", (Exception,), {})
    errors.BuildError = type("BuildError", (Exception,), {})
    return errors
