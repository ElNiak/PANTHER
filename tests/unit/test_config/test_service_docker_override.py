"""
Unit tests for per-service Docker build configuration overrides.

Tests cover:
- ServiceDockerOverrideConfig model creation and defaults
- resolve_docker_build_config() resolution logic
- build_args merging semantics
- ServiceConfig integration with docker field
- Backward compatibility (no docker field = no change)
"""

import pytest

from panther.config.core.models.global_config import (
    DockerConfig,
    ServiceDockerOverrideConfig,
    resolve_docker_build_config,
)
from panther.config.core.models.service import (
    ImplementationConfig,
    ProtocolConfig,
    ServiceConfig,
)


class TestServiceDockerOverrideConfig:
    """Test suite for ServiceDockerOverrideConfig model."""

    def test_all_none_defaults(self):
        """All fields default to None (inherit from global)."""
        cfg = ServiceDockerOverrideConfig()
        assert cfg.force_build_docker_image is None
        assert cfg.no_docker_cache is None
        assert cfg.use_buildx is None
        assert cfg.target_platform is None
        assert cfg.build_args is None

    def test_partial_override(self):
        """Setting some fields leaves others as None."""
        cfg = ServiceDockerOverrideConfig(
            force_build_docker_image=False,
            no_docker_cache=True,
        )
        assert cfg.force_build_docker_image is False
        assert cfg.no_docker_cache is True
        assert cfg.use_buildx is None
        assert cfg.target_platform is None
        assert cfg.build_args is None

    def test_full_override(self):
        """All fields can be set explicitly."""
        cfg = ServiceDockerOverrideConfig(
            force_build_docker_image=True,
            no_docker_cache=False,
            use_buildx=False,
            target_platform="linux/amd64",
            build_args={"MY_ARG": "value"},
        )
        assert cfg.force_build_docker_image is True
        assert cfg.no_docker_cache is False
        assert cfg.use_buildx is False
        assert cfg.target_platform == "linux/amd64"
        assert cfg.build_args == {"MY_ARG": "value"}

    def test_build_args_empty_dict(self):
        """build_args can be an empty dict (distinct from None)."""
        cfg = ServiceDockerOverrideConfig(build_args={})
        assert cfg.build_args == {}
        assert cfg.build_args is not None


class TestResolveBuildConfig:
    """Test suite for resolve_docker_build_config() function."""

    def setup_method(self):
        """Create a standard global DockerConfig for tests."""
        self.global_docker = DockerConfig(
            force_build_docker_image=True,
            no_docker_cache=False,
            use_buildx=True,
            target_platform="linux/arm64",
            build_args={"A": "1", "B": "2"},
        )

    def test_no_service_override_returns_global(self):
        """With no service override, resolved config equals global."""
        resolved = resolve_docker_build_config(self.global_docker, None)
        assert resolved["force_build_docker_image"] is True
        assert resolved["no_docker_cache"] is False
        assert resolved["use_buildx"] is True
        assert resolved["target_platform"] == "linux/arm64"
        assert resolved["build_args"] == {"A": "1", "B": "2"}

    def test_single_field_override(self):
        """Override a single field, rest comes from global."""
        service = ServiceDockerOverrideConfig(force_build_docker_image=False)
        resolved = resolve_docker_build_config(self.global_docker, service)
        assert resolved["force_build_docker_image"] is False
        # Rest unchanged
        assert resolved["no_docker_cache"] is False
        assert resolved["use_buildx"] is True
        assert resolved["target_platform"] == "linux/arm64"
        assert resolved["build_args"] == {"A": "1", "B": "2"}

    def test_multiple_field_overrides(self):
        """Override multiple fields."""
        service = ServiceDockerOverrideConfig(
            force_build_docker_image=False,
            use_buildx=False,
            target_platform="linux/amd64",
        )
        resolved = resolve_docker_build_config(self.global_docker, service)
        assert resolved["force_build_docker_image"] is False
        assert resolved["use_buildx"] is False
        assert resolved["target_platform"] == "linux/amd64"
        # Unchanged
        assert resolved["no_docker_cache"] is False

    def test_build_args_merge_service_wins(self):
        """Service build_args merge over global; service wins on key collision."""
        service = ServiceDockerOverrideConfig(
            build_args={"B": "3", "C": "4"},
        )
        resolved = resolve_docker_build_config(self.global_docker, service)
        assert resolved["build_args"] == {"A": "1", "B": "3", "C": "4"}

    def test_build_args_empty_service_dict_no_change(self):
        """Service build_args={} merges nothing, global unchanged."""
        service = ServiceDockerOverrideConfig(build_args={})
        resolved = resolve_docker_build_config(self.global_docker, service)
        assert resolved["build_args"] == {"A": "1", "B": "2"}

    def test_build_args_none_no_merge(self):
        """Service build_args=None means no merge, global stays."""
        service = ServiceDockerOverrideConfig(build_args=None)
        resolved = resolve_docker_build_config(self.global_docker, service)
        assert resolved["build_args"] == {"A": "1", "B": "2"}

    def test_resolved_does_not_mutate_global(self):
        """Resolving must not mutate the original global DockerConfig."""
        original_build_args = dict(self.global_docker.build_args)
        service = ServiceDockerOverrideConfig(build_args={"X": "99"})
        resolve_docker_build_config(self.global_docker, service)
        # Global should be untouched
        assert self.global_docker.build_args == original_build_args

    def test_global_with_defaults(self):
        """Resolve with a default DockerConfig (all defaults)."""
        default_docker = DockerConfig()
        resolved = resolve_docker_build_config(default_docker, None)
        assert resolved["force_build_docker_image"] is True
        assert resolved["no_docker_cache"] is False
        assert resolved["use_buildx"] is True
        assert resolved["target_platform"] is None
        assert resolved["build_args"] == {}


class TestServiceConfigDockerField:
    """Test ServiceConfig integration with the docker override field."""

    def _make_service_config(self, docker_override=None):
        """Helper to create a minimal ServiceConfig."""
        kwargs = {
            "implementation": ImplementationConfig(name="picoquic", type="iut"),
            "protocol": ProtocolConfig(name="quic", role="server"),
        }
        if docker_override is not None:
            kwargs["docker"] = docker_override
        return ServiceConfig(**kwargs)

    def test_no_docker_field(self):
        """ServiceConfig without docker field parses fine (backward compat)."""
        sc = self._make_service_config()
        assert sc.docker is None

    def test_docker_field_none(self):
        """ServiceConfig with docker=None works."""
        sc = self._make_service_config(docker_override=None)
        assert sc.docker is None

    def test_docker_field_empty_dict(self):
        """ServiceConfig with docker={} parses to all-None overrides."""
        sc = ServiceConfig(
            implementation=ImplementationConfig(name="picoquic", type="iut"),
            protocol=ProtocolConfig(name="quic", role="server"),
            docker=ServiceDockerOverrideConfig(),
        )
        assert sc.docker is not None
        assert sc.docker.force_build_docker_image is None

    def test_docker_field_with_override(self):
        """ServiceConfig with docker overrides parses correctly."""
        override = ServiceDockerOverrideConfig(
            force_build_docker_image=False,
            build_args={"DEBUG": "1"},
        )
        sc = self._make_service_config(docker_override=override)
        assert sc.docker is not None
        assert sc.docker.force_build_docker_image is False
        assert sc.docker.build_args == {"DEBUG": "1"}

    def test_docker_from_dict(self):
        """ServiceConfig can be constructed from a dict with docker block."""
        data = {
            "implementation": {"name": "picoquic", "type": "iut"},
            "protocol": {"name": "quic", "role": "server"},
            "docker": {
                "force_build_docker_image": False,
                "no_docker_cache": True,
            },
        }
        sc = ServiceConfig(**data)
        assert sc.docker is not None
        assert sc.docker.force_build_docker_image is False
        assert sc.docker.no_docker_cache is True
        assert sc.docker.use_buildx is None

    def test_docker_from_dict_without_docker_key(self):
        """ServiceConfig from dict without docker key -> backward compat."""
        data = {
            "implementation": {"name": "picoquic", "type": "iut"},
            "protocol": {"name": "quic", "role": "server"},
        }
        sc = ServiceConfig(**data)
        assert sc.docker is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
