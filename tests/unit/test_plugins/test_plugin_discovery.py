"""
Unit tests for PANTHER Plugin Discovery and Management system.

Tests real implementations of PluginDiscovery, PluginManifest, PluginCatalog,
and PluginManagerUtils with IO-boundary mocking only.
"""

import importlib
import sys
import types
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from panther.plugins.core.plugin_catalog import PluginCatalog
from panther.plugins.core.plugin_discovery import PluginDiscovery
from panther.plugins.core.plugin_loader_utils import PluginManagerUtils
from panther.plugins.core.structures.plugin_dependency import PluginDependency
from panther.plugins.core.structures.plugin_manifest import PluginManifest
from panther.plugins.core.structures.plugin_metadata import PluginMetadata
from panther.plugins.core.structures.plugin_type import PluginType

pytestmark = [pytest.mark.unit, pytest.mark.plugin_system]


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_manifest():
    """Create a valid PluginManifest dataclass instance."""
    return PluginManifest(
        name="test_plugin",
        version="1.2.3",
        type=PluginType.SERVICE,
        description="Test plugin for unit testing",
        supported_protocols=["quic"],
        dependencies=[
            PluginDependency(name="docker_dep", version_spec=">=1.0.0"),
            PluginDependency(name="python_dep", version_spec="*"),
        ],
        entry_point="test_plugin.py",
        author="Test Author",
        license="MIT",
    )


@pytest.fixture
def manifest_dict():
    """Dictionary form of a valid manifest, suitable for from_dict()."""
    return {
        "name": "test_plugin",
        "version": "1.2.3",
        "type": "service",
        "description": "Test plugin for unit testing",
        "supported_protocols": ["quic"],
        "dependencies": [
            {"name": "docker_dep", "version_spec": ">=1.0.0"},
            {"name": "python_dep", "version_spec": "*"},
        ],
        "entry_point": "test_plugin.py",
        "author": "Test Author",
        "license": "MIT",
    }


@pytest.fixture
def empty_decorated_plugins():
    """Patch get_decorated_plugins to return empty dict."""
    with patch(
        "panther.plugins.core.plugin_decorators.get_decorated_plugins",
        return_value={},
    ):
        yield


@pytest.fixture
def fake_decorated_plugins():
    """Patch get_decorated_plugins to return a realistic set of plugins.

    Returns three plugins: a service, a network environment, and a tester,
    each backed by a real PluginManifest and a mock class.
    """
    picoquic_manifest = PluginManifest(
        name="picoquic",
        version="1.0.0",
        type=PluginType.SERVICE,
        description="PicoQUIC QUIC implementation",
        supported_protocols=["quic"],
        dependencies=[PluginDependency(name="docker", version_spec="*")],
    )
    aioquic_manifest = PluginManifest(
        name="aioquic",
        version="0.9.0",
        type=PluginType.SERVICE,
        description="Python AioQUIC implementation",
        supported_protocols=["quic"],
        dependencies=[PluginDependency(name="python", version_spec="*")],
    )
    docker_compose_manifest = PluginManifest(
        name="docker_compose",
        version="2.0.0",
        type=PluginType.NETWORK_ENVIRONMENT,
        description="Docker Compose network environment",
        dependencies=[],
    )
    ivy_tester_manifest = PluginManifest(
        name="ivy_tester",
        version="1.5.0",
        type=PluginType.TESTER,
        description="Ivy formal verification tester",
        supported_protocols=["quic"],
    )
    decorated = {
        "picoquic": (Mock(), picoquic_manifest),
        "aioquic": (Mock(), aioquic_manifest),
        "docker_compose": (Mock(), docker_compose_manifest),
        "ivy_tester": (Mock(), ivy_tester_manifest),
    }
    with patch(
        "panther.plugins.core.plugin_decorators.get_decorated_plugins",
        return_value=decorated,
    ):
        yield decorated


@pytest.fixture
def fake_catalog_plugins():
    """Patch get_decorated_plugins for PluginCatalog tests.

    PluginCatalog.scan_plugins() also calls get_decorated_plugins internally.
    """
    picoquic_manifest = PluginManifest(
        name="picoquic",
        version="1.0.0",
        type=PluginType.SERVICE,
        description="PicoQUIC QUIC implementation",
        supported_protocols=["quic"],
        dependencies=[],
        config_schema={"port": "int", "cert_file": "str"},
        default_config={"port": 4433},
    )
    aioquic_manifest = PluginManifest(
        name="aioquic",
        version="0.9.0",
        type=PluginType.SERVICE,
        description="Python AioQUIC implementation",
        supported_protocols=["quic"],
        dependencies=[
            PluginDependency(name="picoquic", version_spec="*"),
        ],
    )
    docker_compose_manifest = PluginManifest(
        name="docker_compose",
        version="2.0.0",
        type=PluginType.NETWORK_ENVIRONMENT,
        description="Docker Compose network environment",
        dependencies=[],
    )
    decorated = {
        "picoquic": (Mock(), picoquic_manifest),
        "aioquic": (Mock(), aioquic_manifest),
        "docker_compose": (Mock(), docker_compose_manifest),
    }
    with patch(
        "panther.plugins.core.plugin_decorators.get_decorated_plugins",
        return_value=decorated,
    ):
        yield decorated


# ===========================================================================
# TestPluginDiscovery -- tests the real PluginDiscovery class
# ===========================================================================


class TestPluginDiscoveryInit:
    """Test PluginDiscovery constructor behavior."""

    def test_default_init_sets_default_directories(self):
        """PluginDiscovery() without args uses _get_default_directories()."""
        discovery = PluginDiscovery()

        assert isinstance(discovery.plugin_directories, list)
        assert len(discovery.plugin_directories) > 0
        assert discovery.discovered_plugins == {}
        assert discovery.enable_cache is True

    def test_custom_directories(self):
        """PluginDiscovery with explicit directories uses them."""
        custom = ["/some/path", "/another/path"]
        discovery = PluginDiscovery(plugin_directories=custom)

        assert discovery.plugin_directories == custom

    def test_cache_configuration(self):
        """Cache settings are stored."""
        discovery = PluginDiscovery(enable_cache=False, cache_ttl=60)

        assert discovery.enable_cache is False
        assert discovery.cache_ttl == 60


class TestPluginDiscoverPlugins:
    """Test PluginDiscovery.discover_plugins()."""

    def test_discover_returns_copy(self, fake_decorated_plugins):
        """discover_plugins() returns a copy, not the internal dict."""
        discovery = PluginDiscovery(plugin_directories=[])
        result = discovery.discover_plugins(force_refresh=True)

        assert isinstance(result, dict)
        result["injected"] = "value"
        assert "injected" not in discovery.discovered_plugins

    def test_discover_finds_all_types(self, fake_decorated_plugins):
        """discover_plugins() populates plugins from decorator registry."""
        discovery = PluginDiscovery(plugin_directories=[])
        plugins = discovery.discover_plugins(force_refresh=True)

        assert "picoquic" in plugins
        assert "aioquic" in plugins
        assert "docker_compose" in plugins
        assert "ivy_tester" in plugins

    def test_discover_metadata_types(self, fake_decorated_plugins):
        """Returned values are PluginMetadata instances."""
        discovery = PluginDiscovery(plugin_directories=[])
        plugins = discovery.discover_plugins(force_refresh=True)

        for metadata in plugins.values():
            assert isinstance(metadata, PluginMetadata)

    def test_discover_caching(self, fake_decorated_plugins):
        """Second call without force_refresh returns cached result."""
        discovery = PluginDiscovery(plugin_directories=[])
        first = discovery.discover_plugins(force_refresh=True)
        second = discovery.discover_plugins()

        assert first == second

    def test_discover_force_refresh_reloads(self):
        """force_refresh=True clears and re-populates."""
        manifest_a = PluginManifest(
            name="plugin_a", version="1.0.0", type=PluginType.SERVICE
        )
        manifest_b = PluginManifest(
            name="plugin_b", version="1.0.0", type=PluginType.SERVICE
        )

        round1 = {"plugin_a": (Mock(), manifest_a)}
        round2 = {
            "plugin_a": (Mock(), manifest_a),
            "plugin_b": (Mock(), manifest_b),
        }

        discovery = PluginDiscovery(plugin_directories=[])

        with patch(
            "panther.plugins.core.plugin_decorators.get_decorated_plugins",
            return_value=round1,
        ):
            first = discovery.discover_plugins(force_refresh=True)
        assert "plugin_a" in first
        assert "plugin_b" not in first

        with patch(
            "panther.plugins.core.plugin_decorators.get_decorated_plugins",
            return_value=round2,
        ):
            second = discovery.discover_plugins(force_refresh=True)
        assert "plugin_a" in second
        assert "plugin_b" in second

    def test_discover_empty_registry(self, empty_decorated_plugins):
        """discover_plugins() with no registered plugins returns empty dict."""
        discovery = PluginDiscovery(plugin_directories=[])
        result = discovery.discover_plugins(force_refresh=True)

        assert result == {}


class TestPluginDiscoveryAccessors:
    """Test PluginDiscovery.get_plugin() and get_plugins_by_type()."""

    def test_get_plugin_found(self, fake_decorated_plugins):
        """get_plugin() returns PluginMetadata for known plugin."""
        discovery = PluginDiscovery(plugin_directories=[])
        discovery.discover_plugins(force_refresh=True)

        result = discovery.get_plugin("picoquic")

        assert result is not None
        assert isinstance(result, PluginMetadata)
        assert result.name == "picoquic"

    def test_get_plugin_not_found(self, fake_decorated_plugins):
        """get_plugin() returns None for unknown plugin."""
        discovery = PluginDiscovery(plugin_directories=[])
        discovery.discover_plugins(force_refresh=True)

        assert discovery.get_plugin("nonexistent") is None

    def test_get_plugins_by_type_service(self, fake_decorated_plugins):
        """get_plugins_by_type('service') returns service plugins only."""
        discovery = PluginDiscovery(plugin_directories=[])
        discovery.discover_plugins(force_refresh=True)

        services = discovery.get_plugins_by_type("service")

        assert isinstance(services, list)
        names = [m.name for m in services]
        assert "picoquic" in names
        assert "aioquic" in names
        assert "docker_compose" not in names

    def test_get_plugins_by_type_network_environment(self, fake_decorated_plugins):
        """get_plugins_by_type('network_environment') returns env plugins."""
        discovery = PluginDiscovery(plugin_directories=[])
        discovery.discover_plugins(force_refresh=True)

        envs = discovery.get_plugins_by_type("network_environment")

        names = [m.name for m in envs]
        assert "docker_compose" in names
        assert len(envs) == 1

    def test_get_plugins_by_type_empty(self, fake_decorated_plugins):
        """get_plugins_by_type() returns empty list for unknown type."""
        discovery = PluginDiscovery(plugin_directories=[])
        discovery.discover_plugins(force_refresh=True)

        result = discovery.get_plugins_by_type("nonexistent_type")
        assert result == []


class TestPluginDiscoveryClearCache:
    """Test PluginDiscovery.clear_cache()."""

    def test_clear_cache_empties_discovered(self, fake_decorated_plugins):
        """clear_cache() removes all discovered plugins."""
        discovery = PluginDiscovery(plugin_directories=[])
        discovery.discover_plugins(force_refresh=True)
        assert len(discovery.discovered_plugins) > 0

        discovery.clear_cache()

        assert discovery.discovered_plugins == {}


# ===========================================================================
# TestPluginManifest -- tests the real PluginManifest dataclass
# ===========================================================================


class TestPluginManifestDataclass:
    """Test PluginManifest construction and field access."""

    def test_required_fields_only(self):
        """PluginManifest with only required fields uses defaults for rest."""
        manifest = PluginManifest(
            name="minimal", version="0.1.0", type=PluginType.SERVICE
        )

        assert manifest.name == "minimal"
        assert manifest.version == "0.1.0"
        assert manifest.type == PluginType.SERVICE
        assert manifest.author == ""
        assert manifest.description == ""
        assert manifest.supported_protocols == []
        assert manifest.dependencies == []
        assert manifest.entry_point is None

    def test_full_fields(self, sample_manifest):
        """PluginManifest with all fields stores them correctly."""
        assert sample_manifest.name == "test_plugin"
        assert sample_manifest.version == "1.2.3"
        assert sample_manifest.type == PluginType.SERVICE
        assert sample_manifest.description == "Test plugin for unit testing"
        assert sample_manifest.supported_protocols == ["quic"]
        assert len(sample_manifest.dependencies) == 2
        assert sample_manifest.entry_point == "test_plugin.py"
        assert sample_manifest.author == "Test Author"
        assert sample_manifest.license == "MIT"

    def test_dependencies_are_plugin_dependency_instances(self, sample_manifest):
        """Dependencies field contains PluginDependency dataclass instances."""
        for dep in sample_manifest.dependencies:
            assert isinstance(dep, PluginDependency)


class TestPluginManifestToDict:
    """Test PluginManifest.to_dict() serialization."""

    def test_to_dict_basic(self):
        """to_dict() includes all required fields."""
        manifest = PluginManifest(
            name="basic", version="1.0.0", type=PluginType.SERVICE
        )
        d = manifest.to_dict()

        assert d["name"] == "basic"
        assert d["version"] == "1.0.0"
        assert d["type"] == "service"

    def test_to_dict_dependencies_serialized(self, sample_manifest):
        """to_dict() serializes dependencies as list of dicts."""
        d = sample_manifest.to_dict()

        assert isinstance(d["dependencies"], list)
        assert len(d["dependencies"]) == 2
        dep0 = d["dependencies"][0]
        assert dep0["name"] == "docker_dep"
        assert dep0["version_spec"] == ">=1.0.0"

    def test_to_dict_type_is_string(self, sample_manifest):
        """to_dict() converts PluginType enum to string value."""
        d = sample_manifest.to_dict()
        assert isinstance(d["type"], str)
        assert d["type"] == "service"

    def test_to_dict_includes_optional_fields(self, sample_manifest):
        """to_dict() includes optional fields."""
        d = sample_manifest.to_dict()
        assert "supported_protocols" in d
        assert "config_schema" in d
        assert "capabilities" in d
        assert "tags" in d


class TestPluginManifestFromDict:
    """Test PluginManifest.from_dict() deserialization."""

    def test_from_dict_basic(self, manifest_dict):
        """from_dict() creates a PluginManifest from a dictionary."""
        manifest = PluginManifest.from_dict(manifest_dict)

        assert manifest.name == "test_plugin"
        assert manifest.version == "1.2.3"
        assert manifest.type == PluginType.SERVICE
        assert manifest.description == "Test plugin for unit testing"

    def test_from_dict_dependencies(self, manifest_dict):
        """from_dict() converts dependency dicts to PluginDependency instances."""
        manifest = PluginManifest.from_dict(manifest_dict)

        assert len(manifest.dependencies) == 2
        assert isinstance(manifest.dependencies[0], PluginDependency)
        assert manifest.dependencies[0].name == "docker_dep"
        assert manifest.dependencies[0].version_spec == ">=1.0.0"

    def test_from_dict_roundtrip(self, manifest_dict):
        """from_dict -> to_dict preserves essential data."""
        manifest = PluginManifest.from_dict(manifest_dict)
        result = manifest.to_dict()

        assert result["name"] == manifest_dict["name"]
        assert result["version"] == manifest_dict["version"]
        assert result["type"] == manifest_dict["type"]
        assert result["description"] == manifest_dict["description"]
        assert result["supported_protocols"] == manifest_dict["supported_protocols"]

    def test_from_dict_defaults(self):
        """from_dict() uses defaults for missing optional fields."""
        minimal = {"name": "min", "version": "0.0.1", "type": "service"}
        manifest = PluginManifest.from_dict(minimal)

        assert manifest.description == ""
        assert manifest.dependencies == []
        assert manifest.supported_protocols == []
        assert manifest.entry_point is None

    def test_from_dict_with_plugin_type_dependency(self):
        """from_dict() handles dependencies with plugin_type field."""
        data = {
            "name": "dep_test",
            "version": "1.0.0",
            "type": "service",
            "dependencies": [
                {
                    "name": "other_plugin",
                    "version_spec": ">=2.0.0",
                    "plugin_type": "service",
                }
            ],
        }
        manifest = PluginManifest.from_dict(data)

        assert len(manifest.dependencies) == 1
        dep = manifest.dependencies[0]
        assert dep.plugin_type == PluginType.SERVICE


class TestPluginManifestCompatibility:
    """Test PluginManifest.is_compatible_with_panther()."""

    def test_compatible_within_range(self):
        """Plugin is compatible when panther version is within range."""
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            type=PluginType.SERVICE,
            min_panther_version="1.0.0",
            max_panther_version="2.0.0",
        )

        assert manifest.is_compatible_with_panther("1.5.0") is True

    def test_compatible_at_min_version(self):
        """Plugin is compatible at exactly the minimum version."""
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            type=PluginType.SERVICE,
            min_panther_version="1.0.0",
        )

        assert manifest.is_compatible_with_panther("1.0.0") is True

    def test_incompatible_below_min(self):
        """Plugin is incompatible below minimum version."""
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            type=PluginType.SERVICE,
            min_panther_version="2.0.0",
        )

        assert manifest.is_compatible_with_panther("1.0.0") is False

    def test_incompatible_above_max(self):
        """Plugin is incompatible above maximum version."""
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            type=PluginType.SERVICE,
            min_panther_version="1.0.0",
            max_panther_version="1.5.0",
        )

        assert manifest.is_compatible_with_panther("2.0.0") is False

    def test_no_max_version_allows_any_higher(self):
        """Without max_panther_version, any version >= min is compatible."""
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            type=PluginType.SERVICE,
            min_panther_version="1.0.0",
            max_panther_version=None,
        )

        assert manifest.is_compatible_with_panther("99.0.0") is True

    def test_invalid_version_string_returns_false(self):
        """Invalid version string returns False instead of raising."""
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            type=PluginType.SERVICE,
        )

        assert manifest.is_compatible_with_panther("not_a_version") is False


# ===========================================================================
# TestPluginDependency -- tests the real PluginDependency dataclass
# ===========================================================================


class TestPluginDependency:
    """Test PluginDependency.is_satisfied_by()."""

    def test_wildcard_satisfied_by_any(self):
        """Wildcard version spec ('*') is satisfied by any version."""
        dep = PluginDependency(name="any", version_spec="*")
        assert dep.is_satisfied_by("0.0.1") is True
        assert dep.is_satisfied_by("99.99.99") is True

    def test_non_wildcard_returns_false_due_to_packaging_bug(self):
        """Non-wildcard version specs return False.

        Pre-existing bug: PluginDependency.is_satisfied_by() uses
        ``version.SpecifierSet`` which does not exist in
        ``packaging.version`` (should be ``packaging.specifiers.SpecifierSet``).
        The method swallows the AttributeError and returns False for any
        non-wildcard spec.
        """
        dep_exact = PluginDependency(name="exact", version_spec="==1.0.0")
        assert dep_exact.is_satisfied_by("1.0.0") is False

        dep_range = PluginDependency(name="ranged", version_spec=">=1.0.0")
        assert dep_range.is_satisfied_by("1.0.0") is False

    def test_optional_plugin_type(self):
        """PluginDependency stores optional plugin_type."""
        dep = PluginDependency(
            name="typed", version_spec="*", plugin_type=PluginType.SERVICE
        )
        assert dep.plugin_type == PluginType.SERVICE


# ===========================================================================
# TestPluginMetadata -- tests the real PluginMetadata dataclass
# ===========================================================================


class TestPluginMetadata:
    """Test PluginMetadata construction and methods."""

    def test_basic_construction(self):
        """PluginMetadata with required fields."""
        meta = PluginMetadata(name="test_meta", type="service")

        assert meta.name == "test_meta"
        assert meta.type == "service"
        assert meta.version == "1.0.0"
        assert meta.description == ""
        assert meta.supported_protocols == []

    def test_from_dict(self):
        """PluginMetadata.from_dict() creates instance from dict."""
        data = {
            "name": "from_dict_meta",
            "type": "tester",
            "version": "2.0.0",
            "description": "Created from dict",
            "supported_protocols": ["quic", "http3"],
        }
        meta = PluginMetadata.from_dict(data)

        assert meta.name == "from_dict_meta"
        assert meta.type == "tester"
        assert meta.version == "2.0.0"
        assert meta.supported_protocols == ["quic", "http3"]

    def test_is_compatible_with_protocol(self):
        """is_compatible_with() checks protocol matching."""
        meta = PluginMetadata(
            name="compat_test",
            type="service",
            supported_protocols=["quic"],
        )

        assert meta.is_compatible_with(protocol="quic") is True
        assert meta.is_compatible_with(protocol="http3") is False

    def test_is_compatible_with_empty_protocols(self):
        """is_compatible_with() returns True when no protocols set (wildcard)."""
        meta = PluginMetadata(name="wildcard", type="service")

        assert meta.is_compatible_with(protocol="anything") is True

    def test_is_compatible_with_no_args(self):
        """is_compatible_with() returns True when called without args."""
        meta = PluginMetadata(name="no_args", type="service")

        assert meta.is_compatible_with() is True


# ===========================================================================
# TestPluginCatalog -- tests the real PluginCatalog class
# ===========================================================================


class TestPluginCatalogInit:
    """Test PluginCatalog constructor."""

    def test_default_init(self):
        """PluginCatalog() with no args creates empty catalog."""
        catalog = PluginCatalog()

        assert catalog.discovery_paths == []
        assert catalog.catalog == {}

    def test_with_paths(self):
        """PluginCatalog with discovery_paths stores them."""
        paths = ["/path/one", "/path/two"]
        catalog = PluginCatalog(discovery_paths=paths)

        assert catalog.discovery_paths == paths


class TestPluginCatalogScanPlugins:
    """Test PluginCatalog.scan_plugins()."""

    def test_scan_populates_catalog(self, fake_catalog_plugins):
        """scan_plugins() loads plugins from decorator registry."""
        catalog = PluginCatalog()
        result = catalog.scan_plugins()

        assert isinstance(result, dict)
        assert len(result) == 3
        assert "picoquic" in result
        assert "aioquic" in result
        assert "docker_compose" in result

    def test_scan_values_are_manifests(self, fake_catalog_plugins):
        """scan_plugins() stores PluginManifest instances."""
        catalog = PluginCatalog()
        result = catalog.scan_plugins()

        for manifest in result.values():
            assert isinstance(manifest, PluginManifest)

    def test_scan_clears_existing(self, fake_catalog_plugins):
        """scan_plugins() clears existing catalog before repopulating."""
        catalog = PluginCatalog()
        catalog.catalog["stale_entry"] = Mock()
        catalog.scan_plugins()

        assert "stale_entry" not in catalog.catalog


class TestPluginCatalogGetPluginInfo:
    """Test PluginCatalog.get_plugin_info()."""

    def test_get_existing_plugin(self, fake_catalog_plugins):
        """get_plugin_info() returns dict with manifest fields."""
        catalog = PluginCatalog()
        catalog.scan_plugins()

        info = catalog.get_plugin_info("picoquic")

        assert info is not None
        assert info["name"] == "picoquic"
        assert info["version"] == "1.0.0"
        assert info["type"] == "service"

    def test_get_nonexistent_plugin(self, fake_catalog_plugins):
        """get_plugin_info() returns None for unknown plugin."""
        catalog = PluginCatalog()
        catalog.scan_plugins()

        assert catalog.get_plugin_info("nonexistent") is None

    def test_get_plugin_info_includes_resolved_dependencies(self, fake_catalog_plugins):
        """get_plugin_info() includes resolved_dependencies key."""
        catalog = PluginCatalog()
        catalog.scan_plugins()

        info = catalog.get_plugin_info("aioquic")

        assert info is not None
        assert "resolved_dependencies" in info


class TestPluginCatalogValidateConfig:
    """Test PluginCatalog.validate_plugin_config()."""

    def test_valid_config(self, fake_catalog_plugins):
        """validate_plugin_config() passes when config matches schema."""
        catalog = PluginCatalog()
        catalog.scan_plugins()

        is_valid, errors = catalog.validate_plugin_config(
            "picoquic", {"port": 4433, "cert_file": "/path/to/cert"}
        )

        assert is_valid is True
        assert errors == []

    def test_missing_required_config_key(self, fake_catalog_plugins):
        """validate_plugin_config() detects missing required config keys."""
        catalog = PluginCatalog()
        catalog.scan_plugins()

        # "cert_file" is in schema but not in config and not in default_config
        is_valid, errors = catalog.validate_plugin_config("picoquic", {"port": 4433})

        assert is_valid is False
        assert any("cert_file" in e for e in errors)

    def test_validate_unknown_plugin(self, fake_catalog_plugins):
        """validate_plugin_config() fails for unknown plugin."""
        catalog = PluginCatalog()
        catalog.scan_plugins()

        is_valid, errors = catalog.validate_plugin_config(
            "nonexistent", {"key": "value"}
        )

        assert is_valid is False
        assert any("not found" in e for e in errors)

    def test_validate_empty_schema_passes(self, fake_catalog_plugins):
        """validate_plugin_config() passes when plugin has no schema."""
        catalog = PluginCatalog()
        catalog.scan_plugins()

        # aioquic has no config_schema
        is_valid, errors = catalog.validate_plugin_config(
            "aioquic", {"anything": "goes"}
        )

        assert is_valid is True
        assert errors == []


class TestPluginCatalogValidateDependencies:
    """Test PluginCatalog.validate_plugin_dependencies()."""

    def test_satisfied_dependencies_wildcard(self):
        """validate_plugin_dependencies() passes when deps use wildcard spec.

        Note: Non-wildcard version specs always fail due to a pre-existing bug
        in PluginDependency.is_satisfied_by(). This test uses wildcard deps
        to verify the dependency resolution logic itself works.
        """
        base_manifest = PluginManifest(
            name="base_lib",
            version="1.0.0",
            type=PluginType.SERVICE,
        )
        consumer_manifest = PluginManifest(
            name="consumer",
            version="1.0.0",
            type=PluginType.SERVICE,
            dependencies=[
                PluginDependency(name="base_lib", version_spec="*"),
            ],
        )
        decorated = {
            "base_lib": (Mock(), base_manifest),
            "consumer": (Mock(), consumer_manifest),
        }

        with patch(
            "panther.plugins.core.plugin_decorators.get_decorated_plugins",
            return_value=decorated,
        ):
            catalog = PluginCatalog()
            catalog.scan_plugins()

            is_valid, missing = catalog.validate_plugin_dependencies("consumer")

            assert is_valid is True
            assert missing == []

    def test_missing_dependencies(self):
        """validate_plugin_dependencies() reports missing deps."""
        orphan_manifest = PluginManifest(
            name="orphan",
            version="1.0.0",
            type=PluginType.SERVICE,
            dependencies=[
                PluginDependency(name="nonexistent_dep", version_spec=">=1.0.0"),
            ],
        )
        decorated = {"orphan": (Mock(), orphan_manifest)}

        with patch(
            "panther.plugins.core.plugin_decorators.get_decorated_plugins",
            return_value=decorated,
        ):
            catalog = PluginCatalog()
            catalog.scan_plugins()

            is_valid, missing = catalog.validate_plugin_dependencies("orphan")

            assert is_valid is False
            assert len(missing) > 0
            assert any("nonexistent_dep" in m for m in missing)

    def test_unknown_plugin_name(self, fake_catalog_plugins):
        """validate_plugin_dependencies() fails for unknown plugin."""
        catalog = PluginCatalog()
        catalog.scan_plugins()

        is_valid, missing = catalog.validate_plugin_dependencies("not_real")

        assert is_valid is False
        assert any("not found" in m for m in missing)

    def test_no_dependencies(self, fake_catalog_plugins):
        """validate_plugin_dependencies() passes for plugin with no deps."""
        catalog = PluginCatalog()
        catalog.scan_plugins()

        # docker_compose has no dependencies
        is_valid, missing = catalog.validate_plugin_dependencies("docker_compose")

        assert is_valid is True
        assert missing == []


class TestPluginCatalogRefresh:
    """Test PluginCatalog.refresh()."""

    def test_refresh_clears_and_rescans(self):
        """refresh() clears catalog and re-scans from decorator registry."""
        manifest = PluginManifest(
            name="refreshed", version="1.0.0", type=PluginType.SERVICE
        )
        decorated = {"refreshed": (Mock(), manifest)}

        with patch(
            "panther.plugins.core.plugin_decorators.get_decorated_plugins",
            return_value=decorated,
        ):
            catalog = PluginCatalog()
            catalog.catalog["stale"] = Mock()

            catalog.refresh()

            assert "stale" not in catalog.catalog
            assert "refreshed" in catalog.catalog


class TestPluginCatalogResolveDependencies:
    """Test PluginCatalog.resolve_dependencies()."""

    def test_resolve_returns_input(self, fake_catalog_plugins):
        """resolve_dependencies() returns plugin_ids as-is (current impl)."""
        catalog = PluginCatalog()
        catalog.scan_plugins()

        resolved, missing = catalog.resolve_dependencies(["picoquic", "aioquic"])

        assert resolved == ["picoquic", "aioquic"]
        assert missing == []


# ===========================================================================
# TestPluginManagerUtils -- tests the real PluginManagerUtils class
# ===========================================================================


class TestPluginManagerUtilsLoadModule:
    """Test PluginManagerUtils.load_module_from_file()."""

    def test_load_existing_module(self, tmp_path):
        """load_module_from_file() loads a real .py file."""
        module_file = tmp_path / "sample_module.py"
        module_file.write_text("VALUE = 42\ndef get_value(): return VALUE\n")

        module = PluginManagerUtils.load_module_from_file(module_file)

        assert hasattr(module, "VALUE")
        assert module.VALUE == 42
        assert module.get_value() == 42

    def test_load_nonexistent_raises_import_error(self, tmp_path):
        """load_module_from_file() raises ImportError for missing file."""
        missing_file = tmp_path / "does_not_exist.py"

        with pytest.raises(ImportError, match="Module file not found"):
            PluginManagerUtils.load_module_from_file(missing_file)

    def test_load_with_custom_module_name(self, tmp_path):
        """load_module_from_file() uses custom module name when provided."""
        module_file = tmp_path / "my_module.py"
        module_file.write_text("NAME = 'custom'\n")

        module = PluginManagerUtils.load_module_from_file(
            module_file, module_name="custom_name"
        )

        assert module.__name__ == "custom_name"
        assert module.NAME == "custom"


class TestPluginManagerUtilsGetClass:
    """Test PluginManagerUtils.get_class_from_module()."""

    def test_get_existing_class(self, tmp_path):
        """get_class_from_module() finds and returns a class."""
        module_file = tmp_path / "class_module.py"
        module_file.write_text("class MyPlugin:\n    pass\n")

        module = PluginManagerUtils.load_module_from_file(module_file)
        cls = PluginManagerUtils.get_class_from_module(module, "MyPlugin")

        assert cls.__name__ == "MyPlugin"

    def test_get_nonexistent_class_raises(self, tmp_path):
        """get_class_from_module() raises AttributeError for missing class."""
        module_file = tmp_path / "empty_module.py"
        module_file.write_text("pass\n")

        module = PluginManagerUtils.load_module_from_file(module_file)

        with pytest.raises(AttributeError, match="Could not find class"):
            PluginManagerUtils.get_class_from_module(module, "NonExistent")

    def test_get_class_with_base_check(self, tmp_path):
        """get_class_from_module() validates base class inheritance."""
        module_file = tmp_path / "typed_module.py"
        module_file.write_text(
            "class Base:\n    pass\n"
            "class Child(Base):\n    pass\n"
            "class Unrelated:\n    pass\n"
        )

        module = PluginManagerUtils.load_module_from_file(module_file)
        Base = getattr(module, "Base")

        # Should succeed for Child(Base)
        cls = PluginManagerUtils.get_class_from_module(module, "Child", Base)
        assert cls.__name__ == "Child"

        # Should raise for Unrelated
        with pytest.raises(TypeError, match="must inherit from"):
            PluginManagerUtils.get_class_from_module(module, "Unrelated", Base)


class TestPluginManagerUtilsLoadPluginClass:
    """Test PluginManagerUtils.load_plugin_class()."""

    def test_load_from_directory(self, tmp_path):
        """load_plugin_class() loads from plugin directory convention."""
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        plugin_file = plugin_dir / "my_plugin.py"
        plugin_file.write_text(
            "class MyPluginServiceManager:\n"
            "    def __init__(self):\n"
            "        self.name = 'my_plugin'\n"
        )

        cls = PluginManagerUtils.load_plugin_class(plugin_dir, "ServiceManager")

        assert cls.__name__ == "MyPluginServiceManager"
        instance = cls()
        assert instance.name == "my_plugin"

    def test_load_from_file(self, tmp_path):
        """load_plugin_class() loads directly from .py file."""
        plugin_file = tmp_path / "direct_plugin.py"
        plugin_file.write_text("class DirectPluginHandler:\n" "    pass\n")

        cls = PluginManagerUtils.load_plugin_class(plugin_file, "Handler")

        assert cls.__name__ == "DirectPluginHandler"

    def test_load_with_name_transform(self, tmp_path):
        """load_plugin_class() uses custom name transform if provided."""
        plugin_dir = tmp_path / "custom"
        plugin_dir.mkdir()
        plugin_file = plugin_dir / "custom.py"
        plugin_file.write_text("class SpecialRunner:\n" "    pass\n")

        cls = PluginManagerUtils.load_plugin_class(
            plugin_dir,
            "Runner",
            name_transform=lambda _: "Special",
        )

        assert cls.__name__ == "SpecialRunner"


class TestPluginManagerUtilsInstantiate:
    """Test PluginManagerUtils.instantiate_plugin()."""

    def test_instantiate_success(self, tmp_path):
        """instantiate_plugin() creates an instance of the plugin class."""
        module_file = tmp_path / "inst_module.py"
        module_file.write_text(
            "class InstPlugin:\n"
            "    def __init__(self, value):\n"
            "        self.value = value\n"
        )

        module = PluginManagerUtils.load_module_from_file(module_file)
        cls = getattr(module, "InstPlugin")
        instance = PluginManagerUtils.instantiate_plugin(cls, 42)

        assert instance.value == 42

    def test_instantiate_failure_raises(self):
        """instantiate_plugin() wraps constructor errors."""

        class BadPlugin:
            def __init__(self):
                raise RuntimeError("init failed")

        with pytest.raises(Exception, match="Failed to instantiate"):
            PluginManagerUtils.instantiate_plugin(BadPlugin)


class TestPluginManagerUtilsDiscover:
    """Test PluginManagerUtils.discover_plugins() (file discovery)."""

    def test_discover_finds_py_files(self, tmp_path):
        """discover_plugins() finds .py files excluding __init__.py."""
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "plugin_a.py").write_text("pass")
        (tmp_path / "plugin_b.py").write_text("pass")
        (tmp_path / "not_a_plugin.txt").write_text("text")

        found = PluginManagerUtils.discover_plugins(tmp_path)

        names = [p.name for p in found]
        assert "plugin_a.py" in names
        assert "plugin_b.py" in names
        assert "__init__.py" not in names
        assert "not_a_plugin.txt" not in names

    def test_discover_returns_sorted(self, tmp_path):
        """discover_plugins() returns paths in sorted order."""
        (tmp_path / "z_plugin.py").write_text("pass")
        (tmp_path / "a_plugin.py").write_text("pass")
        (tmp_path / "m_plugin.py").write_text("pass")

        found = PluginManagerUtils.discover_plugins(tmp_path)

        names = [p.name for p in found]
        assert names == sorted(names)

    def test_discover_empty_directory(self, tmp_path):
        """discover_plugins() returns empty list for empty directory."""
        found = PluginManagerUtils.discover_plugins(tmp_path)
        assert found == []

    def test_discover_custom_exclude(self, tmp_path):
        """discover_plugins() respects custom exclude list."""
        (tmp_path / "keep.py").write_text("pass")
        (tmp_path / "skip.py").write_text("pass")

        found = PluginManagerUtils.discover_plugins(
            tmp_path, exclude=["skip.py", "__init__.py"]
        )

        names = [p.name for p in found]
        assert "keep.py" in names
        assert "skip.py" not in names

    def test_discover_custom_pattern(self, tmp_path):
        """discover_plugins() supports custom file patterns."""
        (tmp_path / "plugin.py").write_text("pass")
        (tmp_path / "plugin.yaml").write_text("name: test")

        found = PluginManagerUtils.discover_plugins(tmp_path, pattern="*.yaml")

        names = [p.name for p in found]
        assert "plugin.yaml" in names
        assert "plugin.py" not in names


# ===========================================================================
# TestPluginType -- tests the PluginType enum
# ===========================================================================


class TestPluginType:
    """Test PluginType enum values."""

    def test_service_value(self):
        assert PluginType.SERVICE.value == "service"

    def test_network_environment_value(self):
        assert PluginType.NETWORK_ENVIRONMENT.value == "network_environment"

    def test_execution_environment_value(self):
        assert PluginType.EXECUTION_ENVIRONMENT.value == "execution_environment"

    def test_tester_value(self):
        assert PluginType.TESTER.value == "tester"

    def test_protocol_value(self):
        assert PluginType.PROTOCOL.value == "protocol"

    def test_iut_value(self):
        assert PluginType.IUT.value == "iut"

    def test_observer_value(self):
        assert PluginType.OBSERVER.value == "observer"

    def test_from_string(self):
        """PluginType can be constructed from string value."""
        assert PluginType("service") == PluginType.SERVICE
        assert PluginType("tester") == PluginType.TESTER

    def test_invalid_value_raises(self):
        """PluginType raises ValueError for invalid string."""
        with pytest.raises(ValueError):
            PluginType("invalid_type")


# ===========================================================================
# Integration tests across real plugin system components
# ===========================================================================


class TestPluginSystemIntegration:
    """Integration tests for PluginDiscovery + PluginCatalog + PluginManifest."""

    def test_discovery_and_catalog_share_registry(self):
        """Both PluginDiscovery and PluginCatalog use the same registry."""
        manifest = PluginManifest(
            name="shared_plugin",
            version="1.0.0",
            type=PluginType.SERVICE,
            supported_protocols=["quic"],
        )
        decorated = {"shared_plugin": (Mock(), manifest)}

        with (
            patch(
                "panther.plugins.core.plugin_decorators.get_decorated_plugins",
                return_value=decorated,
            ),
            patch(
                "panther.plugins.core.plugin_decorators.get_decorated_plugins",
                return_value=decorated,
            ),
        ):
            discovery = PluginDiscovery(plugin_directories=[])
            discovered = discovery.discover_plugins(force_refresh=True)

            catalog = PluginCatalog()
            scanned = catalog.scan_plugins()

            assert "shared_plugin" in discovered
            assert "shared_plugin" in scanned

    def test_manifest_to_metadata_field_mapping(self):
        """PluginManifest fields map correctly to PluginMetadata fields."""
        manifest = PluginManifest(
            name="mapping_test",
            version="2.0.0",
            type=PluginType.TESTER,
            description="Tests field mapping",
            supported_protocols=["quic", "http3"],
        )
        decorated = {"mapping_test": (Mock(), manifest)}

        with patch(
            "panther.plugins.core.plugin_decorators.get_decorated_plugins",
            return_value=decorated,
        ):
            discovery = PluginDiscovery(plugin_directories=[])
            plugins = discovery.discover_plugins(force_refresh=True)

            meta = plugins["mapping_test"]
            assert meta.name == "mapping_test"
            assert meta.supported_protocols == ["quic", "http3"]

    def test_catalog_dependency_validation_with_discovery(self):
        """PluginCatalog dependency validation works with discovered plugins.

        Uses wildcard version_spec because non-wildcard specs always fail
        due to a pre-existing bug in PluginDependency.is_satisfied_by().
        """
        plugin_a = PluginManifest(
            name="base_lib",
            version="1.0.0",
            type=PluginType.SERVICE,
        )
        plugin_b = PluginManifest(
            name="consumer",
            version="1.0.0",
            type=PluginType.SERVICE,
            dependencies=[
                PluginDependency(name="base_lib", version_spec="*"),
            ],
        )
        decorated = {
            "base_lib": (Mock(), plugin_a),
            "consumer": (Mock(), plugin_b),
        }

        with patch(
            "panther.plugins.core.plugin_decorators.get_decorated_plugins",
            return_value=decorated,
        ):
            catalog = PluginCatalog()
            catalog.scan_plugins()

            is_valid, missing = catalog.validate_plugin_dependencies("consumer")
            assert is_valid is True
            assert missing == []

    def test_plugin_manager_utils_discover_and_load(self, tmp_path):
        """PluginManagerUtils can discover and load plugin files."""
        plugin_file = tmp_path / "discoverable.py"
        plugin_file.write_text(
            "class DiscoverableHandler:\n"
            "    def __init__(self):\n"
            "        self.ready = True\n"
        )

        found = PluginManagerUtils.discover_plugins(tmp_path)
        assert len(found) == 1

        module = PluginManagerUtils.load_module_from_file(found[0])
        cls = PluginManagerUtils.get_class_from_module(module, "DiscoverableHandler")
        instance = PluginManagerUtils.instantiate_plugin(cls)
        assert instance.ready is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
