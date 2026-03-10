"""Tests for unified environment config hierarchy."""

import pytest

from panther.config.core.models.environment import (
    EnvironmentConfig,
    ExecutionEnvironmentConfig,
    NetworkEnvironmentConfig,
)


class TestNetworkEnvironmentHierarchy:
    """NetworkEnvironmentConfig is the base for all network env plugin configs."""

    def test_docker_compose_isinstance(self):
        from panther.plugins.environments.network_environment.docker_compose.config_schema import (
            DockerComposeConfig,
        )

        dc = DockerComposeConfig()
        assert isinstance(dc, NetworkEnvironmentConfig)
        assert isinstance(dc, EnvironmentConfig)

    def test_shadow_ns_isinstance(self):
        from panther.plugins.environments.network_environment.shadow_ns.config_schema import (
            ShadowNSConfig,
        )

        sn = ShadowNSConfig()
        assert isinstance(sn, NetworkEnvironmentConfig)
        assert isinstance(sn, EnvironmentConfig)

    def test_localhost_isinstance(self):
        from panther.plugins.environments.network_environment.localhost_single_container.config_schema import (
            LocalhostSingleContainerConfig,
        )

        lc = LocalhostSingleContainerConfig()
        assert isinstance(lc, NetworkEnvironmentConfig)
        assert isinstance(lc, EnvironmentConfig)

    def test_network_env_has_network_fields(self):
        """NetworkEnvironmentConfig should have network_name, subnet, enable_ipv6."""
        nec = NetworkEnvironmentConfig(type="test")
        assert nec.network_name == "panther_network"
        assert nec.subnet is None
        assert nec.enable_ipv6 is False

    def test_docker_compose_inherits_monitoring_fields(self):
        """DockerComposeConfig should inherit monitoring fields, not duplicate them."""
        from panther.plugins.environments.network_environment.docker_compose.config_schema import (
            DockerComposeConfig,
        )

        dc = DockerComposeConfig()
        assert dc.enable_background_monitoring is True
        # DockerCompose overrides this default (10 vs base 5)
        assert dc.monitoring_interval_seconds == 10
        assert dc.failure_threshold_count == 1

    def test_docker_compose_no_plugin_config(self):
        """No plugin_config dict on environment configs."""
        from panther.plugins.environments.network_environment.docker_compose.config_schema import (
            DockerComposeConfig,
        )

        dc = DockerComposeConfig()
        assert (
            not hasattr(dc, "plugin_config") or "plugin_config" not in dc.model_fields
        )


class TestExecutionEnvironmentHierarchy:
    """ExecutionEnvironmentConfig is the base for all exec env plugin configs."""

    def test_gdb_isinstance(self):
        from panther.plugins.environments.execution_environment.gdb.config_schema import (
            GdbConfig,
        )

        gdb = GdbConfig()
        assert isinstance(gdb, ExecutionEnvironmentConfig)
        assert isinstance(gdb, EnvironmentConfig)

    def test_strace_isinstance(self):
        from panther.plugins.environments.execution_environment.strace.config_schema import (
            StraceConfig,
        )

        st = StraceConfig()
        assert isinstance(st, ExecutionEnvironmentConfig)
        assert isinstance(st, EnvironmentConfig)

    def test_exec_env_has_exec_fields(self):
        """ExecutionEnvironmentConfig should have output_format, collect_metrics."""
        eec = ExecutionEnvironmentConfig(type="test")
        assert eec.output_format == "json"
        assert eec.collect_metrics is True

    def test_strace_inherits_monitoring_and_overrides(self):
        """Strace overrides failure_threshold_count default to 3."""
        from panther.plugins.environments.execution_environment.strace.config_schema import (
            StraceConfig,
        )

        st = StraceConfig()
        assert st.enable_background_monitoring is True
        assert st.failure_threshold_count == 3  # strace override


class TestOldClassesRemoved:
    """The old plugin base classes should no longer exist."""

    def test_no_network_environment_plugin_config(self):
        from panther.config.core.models import plugin

        assert not hasattr(plugin, "NetworkEnvironmentPluginConfig")

    def test_no_execution_environment_plugin_config(self):
        from panther.config.core.models import plugin

        assert not hasattr(plugin, "ExecutionEnvironmentPluginConfig")
