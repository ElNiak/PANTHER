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
def _reset_all_singletons():
    """Reset all singleton / global state between tests.

    Several PANTHER classes use singleton or module-level global patterns.
    Without reset, state leaks between tests (cached clients, image caches,
    observer registries, plugin registries, etc.).

    Resets (in teardown order):
    - DockerBuilder singleton
    - EventManager singleton
    - PluginManager singleton
    - StorageObserver per-path instance registry
    - ObserverFactory module-level global
    """
    yield
    # DockerBuilder
    try:
        from panther.core.docker_builder.docker_builder import DockerBuilder

        DockerBuilder.reset_singleton()
    except Exception:
        pass
    # EventManager
    try:
        from panther.core.observer.management.event_manager import EventManager

        EventManager.reset_instance()
    except Exception:
        pass
    # PluginManager
    try:
        from panther.plugins.plugin_manager import PluginManager

        PluginManager.reset_singleton()
    except Exception:
        pass
    # StorageObserver
    try:
        from panther.core.observer.impl.storage_observer import StorageObserver

        StorageObserver.clear_instances()
    except Exception:
        pass
    # ObserverFactory global
    try:
        import panther.core.observer.factory as _of_mod

        _of_mod._observer_factory = None
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
        paths={
            "output_dir": "/tmp/panther_test/outputs",
            "log_dir": "/tmp/panther_test/logs",
        },
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
# Fast-fail fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def real_fast_fail_handler():
    """Create a real FastFailHandler with fast-fail enabled.

    FastFailHandler is purely in-memory (no IO in init), so no mocking
    is needed. The handler tracks error counts, cascade detection, and
    circuit-breaker state.
    """
    from panther.core.exceptions.fast_fail import FastFailHandler

    return FastFailHandler(enabled=True)


# ---------------------------------------------------------------------------
# Workflow / state tracking fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def real_workflow_tracker():
    """Create a real WorkflowStateTracker instance.

    Purely in-memory tracker for workflow state transitions.
    No IO in __init__.
    """
    from panther.core.observer.workflow.workflow_tracker import WorkflowStateTracker

    return WorkflowStateTracker()


@pytest.fixture
def real_state_observer(real_workflow_tracker):
    """Create a real StateEventObserver wired to a real WorkflowStateTracker.

    No IO in __init__. Observes state-related events and updates the
    workflow tracker accordingly.
    """
    from panther.core.observer.impl.state_observer import StateEventObserver

    return StateEventObserver(workflow_tracker=real_workflow_tracker)


# ---------------------------------------------------------------------------
# Observer implementation fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def real_metrics_observer(tmp_path):
    """Create a real MetricsObserver with all heavyweight features disabled.

    Disables metric publishing, system metric collection, and real-time
    monitoring to keep unit tests fast and deterministic. Output is
    directed to tmp_path so no filesystem pollution occurs.
    """
    from panther.core.observer.impl.metrics_observer import MetricsObserver

    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    return MetricsObserver(
        publish_metrics=False,
        collect_system_metrics=False,
        enable_real_time_monitoring=False,
        log_level="WARNING",
        output_dir=str(metrics_dir),
    )


@pytest.fixture
def real_storage_observer(tmp_path):
    """Create a real StorageObserver with auto-backup disabled.

    Uses tmp_path for storage so tests don't write to the real
    filesystem. The per-path singleton cache is cleared by the
    autouse ``_reset_all_singletons`` fixture.
    """
    from panther.core.observer.impl.storage_observer import StorageObserver

    storage_dir = tmp_path / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return StorageObserver(
        storage_path=str(storage_dir),
        auto_backup=False,
        log_level="WARNING",
    )


@pytest.fixture
def real_command_audit_observer(tmp_path):
    """Create a real CommandAuditObserver writing audit logs to tmp_path.

    The observer tracks command generation events and writes audit
    trails to the provided output directory.
    """
    from panther.core.observer.impl.command_audit_observer import CommandAuditObserver

    audit_dir = tmp_path / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    return CommandAuditObserver(output_dir=audit_dir)


@pytest.fixture
def real_experiment_observer(tmp_path):
    """Create a real ExperimentObserver writing logs to tmp_path.

    Tracks experiment lifecycle events (phase transitions, step
    progress, service events) with timing and step tracking enabled.
    """
    from panther.core.observer.impl.experiment_observer import ExperimentObserver

    experiment_log_dir = tmp_path / "experiment_logs"
    experiment_log_dir.mkdir(parents=True, exist_ok=True)
    return ExperimentObserver(
        name="test_experiment_observer",
        output_dir=str(experiment_log_dir),
        log_level="WARNING",
    )


@pytest.fixture
def real_logger_observer(tmp_path):
    """Create a real LoggerObserver writing to a tmp_path log file.

    Provides event-aware logging with correlation tracking.
    Log level set to WARNING to reduce test output noise.
    """
    from panther.core.observer.impl.logger_observer import LoggerObserver

    log_file = tmp_path / "events.log"
    return LoggerObserver(
        log_level="WARNING",
        output_file=str(log_file),
    )


@pytest.fixture
def real_plugin_observer(real_event_manager):
    """Create a real PluginObserver connected to a real EventManager.

    Tracks plugin registrations, event interest mappings, and
    subscriber routing. No IO in __init__.
    """
    from panther.core.observer.impl.plugin_observer import PluginObserver

    return PluginObserver(event_manager=real_event_manager)


# ---------------------------------------------------------------------------
# Observer factory and emitter registry fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def real_observer_factory(real_event_manager):
    """Create a real ObserverFactory connected to a real EventManager.

    Resets the module-level global ``_observer_factory`` before creating
    a fresh instance to guarantee test isolation. The factory is
    pre-loaded with default observer type registrations.
    """
    import panther.core.observer.factory as _of_mod
    from panther.core.observer.factory import ObserverFactory

    _of_mod._observer_factory = None
    return ObserverFactory(event_manager=real_event_manager)


@pytest.fixture
def real_emitter_registry(real_event_manager):
    """Create a real EmitterRegistry connected to a real EventManager.

    Provides typed event emitters (experiment, service, environment,
    step, plugin, assertion, metrics) and manages state managers for
    each entity type. No IO in __init__.
    """
    from panther.core.events.emitter_registry import EmitterRegistry

    return EmitterRegistry(event_manager=real_event_manager)


# ---------------------------------------------------------------------------
# PluginManager fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def real_plugin_manager(
    mock_docker_client,
    minimal_global_config,
    real_event_manager,
    real_fast_fail_handler,
):
    """Create a real PluginManager with Docker daemon mocked.

    The PluginManager singleton is reset before creation. Docker is
    mocked at the IO boundary so that DockerBuilder initialization
    succeeds without a running daemon. Plugin discovery runs against
    the real plugin directories.

    Caching is disabled (``enable_cache=False``) for test isolation.
    """
    from panther.core.docker_builder.docker_builder import DockerBuilder
    from panther.plugins.plugin_manager import PluginManager

    # Ensure clean singleton state
    PluginManager.reset_singleton()
    DockerBuilder.reset_singleton()

    with patch("panther.core.docker_builder.docker_builder.docker") as mock_docker_mod:
        mock_docker_mod.from_env.return_value = mock_docker_client
        mock_docker_mod.errors = _make_docker_errors_module()

        manager = PluginManager(
            event_manager=real_event_manager,
            global_config=minimal_global_config,
            fast_fail_handler=real_fast_fail_handler,
            enable_cache=False,
        )

    assert isinstance(manager, PluginManager)
    return manager


# ---------------------------------------------------------------------------
# ExperimentManager fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def real_experiment_manager(mock_docker_client, minimal_global_config, tmp_path):
    """Create a real ExperimentManager with Docker and filesystem mocked.

    This is the most complex fixture: ExperimentManager orchestrates
    the full experiment lifecycle and touches many subsystems during
    ``__init__``.

    IO boundaries mocked:
    - Docker daemon (via ``docker.from_env``)
    - Output directory redirected to ``tmp_path``

    The manager is created with ``dry_run=True`` so that no containers
    are actually started if execution methods are called.
    """
    import panther.core.observer.factory as _of_mod
    from panther.core.docker_builder.docker_builder import DockerBuilder
    from panther.core.experiment_manager import ExperimentManager
    from panther.core.observer.management.event_manager import EventManager
    from panther.plugins.plugin_manager import PluginManager

    # Reset all singletons that ExperimentManager __init__ touches
    DockerBuilder.reset_singleton()
    EventManager.reset_instance()
    PluginManager.reset_singleton()
    _of_mod._observer_factory = None

    # Redirect output_dir to tmp_path using a proper PathsConfig object
    from panther.config.core.models.global_config import PathsConfig

    output_dir = tmp_path / "experiment_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    paths_obj = PathsConfig(
        output_dir=str(output_dir),
        log_dir=str(tmp_path / "logs"),
    )
    minimal_global_config = minimal_global_config.model_copy(
        update={"paths": paths_obj},
    )

    with patch("panther.core.docker_builder.docker_builder.docker") as mock_docker_mod:
        mock_docker_mod.from_env.return_value = mock_docker_client
        mock_docker_mod.errors = _make_docker_errors_module()

        manager = ExperimentManager(
            global_config=minimal_global_config,
            experiment_name="test_experiment",
            dry_run=True,
        )

        assert isinstance(manager, ExperimentManager)
        yield manager


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
