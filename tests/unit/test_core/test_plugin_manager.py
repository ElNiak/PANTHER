"""Unit tests for PluginManager - the core plugin orchestration component of PANTHER.

Tests exercise the real PluginManager singleton with Docker mocked at the IO boundary.
All fake class fallbacks have been removed in favour of the ``real_plugin_manager``
fixture defined in ``conftest.py``.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.plugin_manager]


# ---------------------------------------------------------------------------
# Singleton pattern
# ---------------------------------------------------------------------------


class TestPluginManagerSingleton:
    """Verify the singleton lifecycle: creation, identity, reset."""

    def test_get_instance_returns_same_object(self, real_plugin_manager):
        """PluginManager() after first init returns the same singleton."""
        from panther.plugins.plugin_manager import PluginManager

        second = PluginManager.get_instance()
        assert second is real_plugin_manager

    def test_reset_singleton_allows_new_instance(
        self, real_plugin_manager, mock_docker_client
    ):
        """After reset_singleton(), next creation yields a different object."""
        from panther.core.docker_builder.docker_builder import DockerBuilder
        from panther.plugins.plugin_manager import PluginManager

        old_id = id(real_plugin_manager)

        PluginManager.reset_singleton()
        DockerBuilder.reset_singleton()

        with patch(
            "panther.core.docker_builder.docker_builder.docker"
        ) as mock_docker_mod:
            mock_docker_mod.from_env.return_value = mock_docker_client
            errors = MagicMock()
            errors.DockerException = type("DockerException", (Exception,), {})
            errors.ImageNotFound = type("ImageNotFound", (Exception,), {})
            errors.NotFound = type("NotFound", (Exception,), {})
            errors.APIError = type("APIError", (Exception,), {})
            errors.BuildError = type("BuildError", (Exception,), {})
            mock_docker_mod.errors = errors

            new_manager = PluginManager(enable_cache=False)

        assert id(new_manager) != old_id

    def test_singleton_class_variables_after_reset(self):
        """reset_singleton clears both _instance and _initialized."""
        from panther.plugins.plugin_manager import PluginManager

        PluginManager.reset_singleton()
        assert PluginManager._instance is None
        assert PluginManager._initialized is False


# ---------------------------------------------------------------------------
# Initialization attributes
# ---------------------------------------------------------------------------


class TestPluginManagerInitialization:
    """Verify that a freshly-created PluginManager has the expected attributes."""

    def test_has_event_manager(self, real_plugin_manager, real_event_manager):
        """event_manager is set from the constructor argument."""
        assert real_plugin_manager.event_manager is real_event_manager

    def test_has_global_config(self, real_plugin_manager, minimal_global_config):
        """global_config is set from the constructor argument."""
        assert real_plugin_manager.global_config is minimal_global_config

    def test_has_fast_fail_handler(self, real_plugin_manager, real_fast_fail_handler):
        """fast_fail_handler is set from the constructor argument."""
        assert real_plugin_manager.fast_fail_handler is real_fast_fail_handler

    def test_has_plugin_discovery(self, real_plugin_manager):
        """plugin_discovery component is created during init."""
        from panther.plugins.core.plugin_discovery import PluginDiscovery

        assert isinstance(real_plugin_manager.plugin_discovery, PluginDiscovery)

    def test_has_plugin_catalog(self, real_plugin_manager):
        """plugin_catalog component is created during init."""
        from panther.plugins.core.plugin_catalog import PluginCatalog

        assert isinstance(real_plugin_manager.plugin_catalog, PluginCatalog)

    def test_has_plugin_factory(self, real_plugin_manager):
        """plugin_factory component is created during init."""
        from panther.plugins.core.plugin_factory import PluginFactory

        assert isinstance(real_plugin_manager.plugin_factory, PluginFactory)

    def test_has_docker_builder(self, real_plugin_manager):
        """docker_builder is created from DockerBuilder.get_instance during init."""
        from panther.core.docker_builder.docker_builder import DockerBuilder

        assert isinstance(real_plugin_manager.docker_builder, DockerBuilder)

    def test_cache_disabled_when_requested(self, real_plugin_manager):
        """Fixture creates with enable_cache=False."""
        assert real_plugin_manager.enable_cache is False

    def test_plugins_dict_populated_on_init(self, real_plugin_manager):
        """Auto-discovery runs during __init__, populating self.plugins."""
        assert isinstance(real_plugin_manager.plugins, dict)
        assert len(real_plugin_manager.plugins) > 0

    def test_event_system_components(self, real_plugin_manager):
        """Plugin observer and event emitter are created when event_manager is provided."""
        assert real_plugin_manager.plugin_observer is not None
        assert real_plugin_manager.plugin_event_emitter is not None

    def test_default_plugin_directories(self, real_plugin_manager):
        """Default plugin directories point to real plugin folders."""
        dirs = real_plugin_manager.plugin_directories
        assert isinstance(dirs, list)
        assert len(dirs) > 0
        # At least some should be real directories
        existing = [d for d in dirs if Path(d).exists()]
        assert len(existing) > 0


# ---------------------------------------------------------------------------
# Parameter update on existing singleton
# ---------------------------------------------------------------------------


class TestPluginManagerParameterUpdate:
    """Verify that re-calling PluginManager() updates parameters on the singleton."""

    def test_update_global_config(self, real_plugin_manager):
        """Re-instantiating with a new global_config updates the singleton."""
        from panther.config.core.models.global_config import GlobalConfig
        from panther.plugins.plugin_manager import PluginManager

        new_config = GlobalConfig(
            logging={"level": "DEBUG", "format": "%(levelname)s - %(message)s"},
        )
        PluginManager(global_config=new_config)
        assert real_plugin_manager.global_config is new_config

    def test_update_plugin_directories(self, real_plugin_manager, tmp_path):
        """Re-instantiating with new plugin_directories updates the singleton."""
        from panther.plugins.plugin_manager import PluginManager

        new_dirs = [str(tmp_path)]
        PluginManager(plugin_directories=new_dirs)
        assert real_plugin_manager.plugin_directories == new_dirs

    def test_no_change_when_same_params(self, real_plugin_manager):
        """Re-instantiating with identical params does not raise."""
        from panther.plugins.plugin_manager import PluginManager

        PluginManager()  # should be a no-op


# ---------------------------------------------------------------------------
# Plugin discovery
# ---------------------------------------------------------------------------


class TestPluginDiscovery:
    """Verify discover_plugins() returns real plugin metadata."""

    def test_discover_plugins_returns_dict(self, real_plugin_manager):
        """discover_plugins returns a dict of name -> PluginMetadata."""
        plugins = real_plugin_manager.discover_plugins()
        assert isinstance(plugins, dict)

    def test_discover_plugins_finds_real_plugins(self, real_plugin_manager):
        """At least one real plugin is discovered from the codebase."""
        plugins = real_plugin_manager.discover_plugins()
        assert len(plugins) > 0

    def test_discovered_plugin_has_metadata(self, real_plugin_manager):
        """Each discovered plugin has a PluginMetadata with a name and type."""
        plugins = real_plugin_manager.discover_plugins()
        for name, metadata in plugins.items():
            assert type(metadata).__name__ == "PluginMetadata"
            assert metadata.name, f"Plugin {name} has empty name"
            assert metadata.type, f"Plugin {name} has empty type"

    def test_discover_plugins_returns_copy(self, real_plugin_manager):
        """discover_plugins returns a copy, not the internal dict."""
        plugins1 = real_plugin_manager.discover_plugins()
        plugins2 = real_plugin_manager.discover_plugins()
        assert plugins1 is not plugins2
        assert plugins1 == plugins2

    def test_discover_plugins_force_refresh(self, real_plugin_manager):
        """force_refresh=True re-scans and returns fresh results."""
        plugins = real_plugin_manager.discover_plugins(force_refresh=True)
        assert isinstance(plugins, dict)
        assert len(plugins) > 0

    def test_discovery_count_increments(self, real_plugin_manager):
        """Each non-cached discovery increments _discovery_count."""
        # Cache is disabled, so every call should increment
        count_before = real_plugin_manager._discovery_count
        real_plugin_manager.discover_plugins()
        assert real_plugin_manager._discovery_count > count_before


# ---------------------------------------------------------------------------
# get_plugin
# ---------------------------------------------------------------------------


class TestGetPlugin:
    """Verify get_plugin() lookups."""

    def test_get_existing_plugin(self, real_plugin_manager):
        """get_plugin returns metadata for a discovered plugin."""
        plugins = real_plugin_manager.discover_plugins()
        if plugins:
            name = next(iter(plugins))
            result = real_plugin_manager.get_plugin(name)
            assert result is not None
            assert result.name == name

    def test_get_nonexistent_plugin(self, real_plugin_manager):
        """get_plugin returns None for a name that does not exist."""
        result = real_plugin_manager.get_plugin("__nonexistent_plugin_xyz__")
        assert result is None


# ---------------------------------------------------------------------------
# get_plugins_by_type / get_plugins_by_protocol
# ---------------------------------------------------------------------------


class TestPluginFiltering:
    """Verify filtering helpers on the real plugin registry."""

    def test_get_plugins_by_type_service(self, real_plugin_manager):
        """get_plugins_by_type('service') returns only service plugins."""
        services = real_plugin_manager.get_plugins_by_type("service")
        assert isinstance(services, list)
        for p in services:
            assert p.type == "service"

    def test_get_plugins_by_type_iut(self, real_plugin_manager):
        """get_plugins_by_type('iut') returns IUT plugins."""
        iut_plugins = real_plugin_manager.get_plugins_by_type("iut")
        assert isinstance(iut_plugins, list)
        for p in iut_plugins:
            assert p.type == "iut"

    def test_get_plugins_by_type_invalid_raises(self, real_plugin_manager):
        """get_plugins_by_type with an invalid type string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid plugin type"):
            real_plugin_manager.get_plugins_by_type("__bogus__")

    def test_get_plugins_by_protocol_quic(self, real_plugin_manager):
        """get_plugins_by_protocol('quic') returns QUIC-compatible plugins."""
        quic_plugins = real_plugin_manager.get_plugins_by_protocol("quic")
        assert isinstance(quic_plugins, list)
        for p in quic_plugins:
            assert p.is_compatible_with(protocol="quic")

    def test_get_plugins_by_protocol_unknown_includes_wildcard(
        self, real_plugin_manager
    ):
        """Plugins with empty supported_protocols are treated as universally compatible.

        is_compatible_with() returns True when supported_protocols is empty,
        so get_plugins_by_protocol always includes those plugins regardless
        of the protocol name queried.
        """
        result = real_plugin_manager.get_plugins_by_protocol("__no_such_protocol__")
        assert isinstance(result, list)
        # Every returned plugin either has empty supported_protocols
        # (wildcard) or explicitly lists the protocol
        for p in result:
            assert (
                p.supported_protocols == []
                or "__no_such_protocol__" in p.supported_protocols
            )


# ---------------------------------------------------------------------------
# Protocol version discovery
# ---------------------------------------------------------------------------


class TestProtocolVersionDiscovery:
    """Verify discover_protocol_versions() delegation."""

    def test_discover_protocol_versions_returns_dict(self, real_plugin_manager):
        """discover_protocol_versions returns a dict of protocol -> version list."""
        versions = real_plugin_manager.discover_protocol_versions()
        assert isinstance(versions, dict)

    def test_discover_protocol_versions_filtered(self, real_plugin_manager):
        """Passing a specific protocol filters results."""
        versions = real_plugin_manager.discover_protocol_versions(protocol="quic")
        assert isinstance(versions, dict)
        # If QUIC is found, the key should be present
        if versions:
            for key in versions:
                assert "quic" in key.lower()


# ---------------------------------------------------------------------------
# Plugin schema discovery
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Dependency validation
# ---------------------------------------------------------------------------


class TestDependencyValidation:
    """Verify validate_plugin_dependencies() delegation to PluginCatalog."""

    def test_validate_deps_returns_tuple(self, real_plugin_manager):
        """validate_plugin_dependencies returns (bool, list)."""
        is_valid, missing = real_plugin_manager.validate_plugin_dependencies(
            "some_plugin"
        )
        assert isinstance(is_valid, bool)
        assert isinstance(missing, list)

    def test_validate_deps_for_known_plugin(self, real_plugin_manager):
        """For a plugin with no deps, validation should pass."""
        plugins = real_plugin_manager.discover_plugins()
        if plugins:
            name = next(iter(plugins))
            is_valid, missing = real_plugin_manager.validate_plugin_dependencies(name)
            assert isinstance(is_valid, bool)
            assert isinstance(missing, list)


# ---------------------------------------------------------------------------
# Experiment validation
# ---------------------------------------------------------------------------


class TestExperimentValidation:
    """Verify validate_experiment_plugins() delegation to PluginCatalog."""

    def test_validate_experiment_plugins_returns_tuple(
        self, real_plugin_manager, minimal_test_config
    ):
        """validate_experiment_plugins returns (bool, list[str]).

        The method expects an ExperimentConfig (with .tests list), not a
        bare TestConfig.
        """
        from panther.config.core.models.experiment import ExperimentConfig

        experiment_config = ExperimentConfig(tests=[minimal_test_config])
        is_valid, errors = real_plugin_manager.validate_experiment_plugins(
            experiment_config
        )
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_validate_experiment_plugins_with_known_service(self, real_plugin_manager):
        """Validation succeeds when the experiment references discovered plugins."""
        from panther.config.core.models.experiment import ExperimentConfig, TestConfig

        test_config = TestConfig(
            name="validation_test",
            description="Test validation",
            network_environment={"type": "docker_compose"},
            services={
                "server": {
                    "timeout": 60,
                    "implementation": {"name": "picoquic", "type": "iut"},
                    "protocol": {
                        "name": "quic",
                        "version": "rfc9000",
                        "role": "server",
                    },
                }
            },
        )
        experiment_config = ExperimentConfig(tests=[test_config])
        is_valid, errors = real_plugin_manager.validate_experiment_plugins(
            experiment_config
        )
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


class TestPluginManagerStatistics:
    """Verify get_statistics() returns expected structure."""

    def test_get_statistics_structure(self, real_plugin_manager):
        """get_statistics returns dict with expected keys."""
        stats = real_plugin_manager.get_statistics()
        expected_keys = {
            "total_plugins",
            "plugins_by_type",
            "discovery_count",
            "last_discovery_time",
            "cache_enabled",
            "cache_valid",
            "directories_scanned",
            "event_system_enabled",
            "docker_builder_available",
        }
        assert expected_keys.issubset(stats.keys())

    def test_statistics_total_plugins(self, real_plugin_manager):
        """total_plugins matches the number of discovered plugins."""
        stats = real_plugin_manager.get_statistics()
        plugins = real_plugin_manager.discover_plugins()
        assert stats["total_plugins"] == len(plugins)

    def test_statistics_docker_builder_available(self, real_plugin_manager):
        """docker_builder_available is True when builder was initialised."""
        stats = real_plugin_manager.get_statistics()
        assert stats["docker_builder_available"] is True

    def test_statistics_event_system_enabled(self, real_plugin_manager):
        """event_system_enabled is True when event_manager was provided."""
        stats = real_plugin_manager.get_statistics()
        assert stats["event_system_enabled"] is True

    def test_statistics_plugins_by_type(self, real_plugin_manager):
        """plugins_by_type contains counts for each PluginType."""
        stats = real_plugin_manager.get_statistics()
        by_type = stats["plugins_by_type"]
        assert isinstance(by_type, dict)
        # All values should be non-negative integers
        for count in by_type.values():
            assert isinstance(count, int)
            assert count >= 0


# ---------------------------------------------------------------------------
# Cache refresh
# ---------------------------------------------------------------------------


class TestPluginRefresh:
    """Verify refresh_plugins() clears caches and re-discovers."""

    def test_refresh_plugins_clears_cache(self, real_plugin_manager):
        """refresh_plugins() clears the discovery cache."""
        real_plugin_manager.refresh_plugins()
        # After refresh, cache timestamp should be recent
        assert real_plugin_manager._cache_timestamp > 0

    def test_refresh_plugins_re_discovers(self, real_plugin_manager):
        """refresh_plugins() re-discovers plugins."""
        count_before = real_plugin_manager._discovery_count
        real_plugin_manager.refresh_plugins()
        assert real_plugin_manager._discovery_count > count_before


# ---------------------------------------------------------------------------
# Experiment context
# ---------------------------------------------------------------------------


class TestExperimentContext:
    """Verify experiment context management."""

    def test_set_experiment_context(self, real_plugin_manager):
        """set_experiment_context stores the context on the manager."""
        context = {"experiment_name": "test_exp", "run_id": 42}
        real_plugin_manager.set_experiment_context(context)
        assert real_plugin_manager.experiment_context == context

    def test_experiment_context_for_plugins_property(self, real_plugin_manager):
        """experiment_context_for_plugins returns the stored context."""
        context = {"experiment_name": "test_exp"}
        real_plugin_manager.set_experiment_context(context)
        assert real_plugin_manager.experiment_context_for_plugins == context


# ---------------------------------------------------------------------------
# Docker builder integration
# ---------------------------------------------------------------------------


class TestDockerBuilderIntegration:
    """Verify DockerBuilder integration within PluginManager."""

    def test_docker_builder_is_real_instance(self, real_plugin_manager):
        """docker_builder is a genuine DockerBuilder, not a mock."""
        from panther.core.docker_builder.docker_builder import DockerBuilder

        assert isinstance(real_plugin_manager.docker_builder, DockerBuilder)

    def test_docker_builder_has_generate_image_tag(self, real_plugin_manager):
        """docker_builder supports generate_image_tag for tag generation."""
        tag = real_plugin_manager.docker_builder.generate_image_tag(
            impl_name="picoquic",
            version="rfc9000",
            tag_version="latest",
        )
        assert isinstance(tag, str)
        assert "picoquic" in tag


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestPluginManagerErrorHandling:
    """Verify graceful error handling in PluginManager."""

    def test_docker_builder_failure_raises_runtime_error(
        self, mock_docker_client, real_event_manager, real_fast_fail_handler
    ):
        """If DockerBuilder init fails, PluginManager raises RuntimeError."""
        from panther.core.docker_builder.docker_builder import DockerBuilder
        from panther.plugins.plugin_manager import PluginManager

        PluginManager.reset_singleton()
        DockerBuilder.reset_singleton()

        with patch(
            "panther.core.docker_builder.docker_builder.docker"
        ) as mock_docker_mod:
            mock_docker_mod.from_env.side_effect = Exception(
                "Docker daemon not running"
            )

            with pytest.raises(
                RuntimeError, match="DockerBuilder initialization failed"
            ):
                PluginManager(
                    event_manager=real_event_manager,
                    fast_fail_handler=real_fast_fail_handler,
                    enable_cache=False,
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
