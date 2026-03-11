"""PluginService -- plugin discovery and metadata browsing for the web UI.

This module wraps PANTHER's PluginManager (the central registry that
discovers, validates, and catalogues all installed plugins) to provide
a simple, web-friendly API for listing plugins and inspecting their
metadata.

PANTHER's plugin system uses decorator-based registration
(``@register_plugin()``, ``@register_protocol()``) and an
inheritance-based template-method pattern.  Each plugin ships a
``PluginManifest`` that describes its name, version, supported protocols,
capabilities, license, config schema, and more.  The discovery pipeline
walks the ``panther/plugins/services/`` package tree, imports modules,
and collects the manifests deposited by decorators.

Caching strategy:
    ``PluginService`` caches the discovery result after the first
    successful call to ``list_plugins()``.  If discovery fails (e.g.
    because a plugin has an import error), the failure is **not** cached
    so that a subsequent call can retry.  Since plugins are filesystem
    artifacts that do not change at runtime, the cache never needs
    invalidation during a single server process.
"""

import logging

logger = logging.getLogger(__name__)


class PluginService:
    """Web-friendly facade over PluginManager (PANTHER's central plugin registry).

    PluginService delegates to ``PluginManager.discover_plugins()`` to walk
    the ``panther/plugins/services/`` package tree, import plugin modules,
    and collect the ``PluginMetadata`` dataclass instances deposited by
    ``@register_plugin()`` decorators.

    The class uses a simple *cache-on-first-success* strategy: after a
    successful discovery run, results are stored in ``_plugins_cache`` and
    returned on all subsequent calls.  If discovery fails (e.g. due to an
    import error in a plugin module), the failure is **not** cached, allowing
    the next call to retry.

    All returned objects are ``PluginMetadata`` dataclass instances from
    ``panther.plugins.core.structures.plugin_metadata`` with fields:
    ``name``, ``type``, ``version``, ``description``,
    ``supported_protocols``, ``capabilities``, ``tags``, ``status``,
    ``path``; and a ``.to_dict()`` method for JSON serialisation.

    Attributes:
        _plugins_cache: Cached list of ``PluginMetadata``, or ``None`` if
            discovery has not yet succeeded.

    Example::

        svc = PluginService()
        for plugin in svc.list_plugins():
            print(plugin.name, plugin.version, plugin.supported_protocols)
    """

    def __init__(self):  # noqa: D107
        self._plugins_cache = None

    def list_plugins(self):
        """Discover and return all registered plugins as ``PluginMetadata`` instances.

        On first call, triggers full plugin discovery via ``PluginManager``.
        Subsequent calls return the cached result.  If discovery raises an
        exception, an empty list is returned and the failure is logged as a
        warning; the next call will retry discovery.

        Returns:
            A list of ``PluginMetadata`` instances representing all
            discovered plugins.  Returns an empty list on failure.
        """
        if self._plugins_cache is not None:
            return self._plugins_cache

        try:
            from panther.plugins.plugin_manager import PluginManager

            pm = PluginManager()
            discovered = pm.discover_plugins()
            self._plugins_cache = list(discovered.values())
        except Exception as e:
            logger.warning("Failed to discover plugins: %s", e)
            return []  # Don't cache failure — allow retry on next call

        return self._plugins_cache

    def get_plugin_detail(self, name: str):
        """Look up a single plugin by name and return its ``PluginMetadata``.

        Args:
            name: The plugin name to search for (exact, case-sensitive
                match against ``PluginMetadata.name``).

        Returns:
            The matching ``PluginMetadata`` instance, or ``None`` if no
            plugin with that name is found.
        """
        for p in self.list_plugins():
            if p.name == name:
                return p
        return None

    def get_plugin_manifest(self, name: str):
        """Retrieve the full ``PluginManifest`` for a plugin by name.

        Unlike ``get_plugin_detail`` (which returns the lightweight
        ``PluginMetadata`` dataclass), this method returns the original
        ``PluginManifest`` stored in the decorator registry
        (``get_decorated_plugins``).  The manifest includes all fields
        that are lost during catalog re-creation, such as ``license``,
        ``homepage``, ``config_schema``, and ``config_model``.

        This method triggers a full plugin discovery to ensure that all
        decorator registrations have been executed.

        Args:
            name: The plugin name to search for (exact, case-sensitive
                match against ``PluginManifest.name``).

        Returns:
            The matching ``PluginManifest`` instance, or ``None`` if the
            plugin is not found or discovery fails.
        """
        try:
            from panther.plugins.plugin_manager import PluginManager

            # Ensure plugins are imported and decorators have run
            pm = PluginManager()
            pm.discover_plugins()

            from panther.plugins.core.plugin_decorators import get_decorated_plugins

            for _plugin_id, (_cls, manifest) in get_decorated_plugins().items():
                if manifest.name == name:
                    return manifest
        except Exception as e:
            logger.warning("Failed to get plugin manifest for %s: %s", name, e)
        return None
