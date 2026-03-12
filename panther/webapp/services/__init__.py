"""PANTHER webapp service layer --- thin wrappers around core components for async web usage.

Pages in ``panther.webapp.pages`` never import from ``panther.core``
directly.  Instead, every core interaction is mediated by a service
class defined in this package.  This decoupling provides three
benefits:

1. **Async safety** -- PANTHER's core is synchronous.  Services like
   ``ExperimentService`` run blocking work in background threads
   (via ``asyncio.to_thread``) so the NiceGUI event loop stays
   responsive.
2. **Caching and state management** -- Some services (``PluginService``,
   ``ResultsService``) maintain in-memory caches.
   ``ExperimentService`` is a singleton with state that persists across
   page navigations.  ``ConfigService`` is stateless.
3. **Error boundaries** -- Services catch exceptions from core
   components and translate them into user-friendly messages or
   fallback values, preventing raw tracebacks from reaching the UI.

Service inventory
-----------------

+--------------------+--------------------------------+------------------------------------+
| Service            | Core component wrapped         | Key additions                      |
+====================+================================+====================================+
| ``ConfigService``  | ``ConfigurationLoader``,       | YAML generation, deep-merge of     |
|                    | ``deep_merge``                 | form data, field-level validation,  |
|                    |                                | config file save/load              |
+--------------------+--------------------------------+------------------------------------+
| ``ExperimentService``| ``ExperimentManager``        | Background-thread execution,       |
|                    | (the central orchestrator)     | stop/cancel support, in-memory log |
|                    |                                | buffer, status callbacks           |
+--------------------+--------------------------------+------------------------------------+
| ``ResultsService`` | ``FileUtils``, output dir scan | Experiment listing with date       |
|                    |                                | parsing, summary caching, artifact |
|                    |                                | discovery (pcap, json, logs)       |
+--------------------+--------------------------------+------------------------------------+
| ``PluginService``  | ``PluginManager``              | Cached plugin discovery, detail    |
|                    | (the plugin registry)          | lookup, graceful fallback on       |
|                    |                                | discovery failure                  |
+--------------------+--------------------------------+------------------------------------+

``WebObserver`` lives in ``panther.webapp.infra``, not in this package.
It bridges PANTHER events to NiceGUI UI callbacks with per-subscriber
filtering, batching, and thread-safe dispatch.

Usage pattern
-------------
Services are instantiated as needed inside page ``content()``
functions or cached as module-level singletons (see
``get_experiment_service()`` in ``experiment_service.py``).  Pages
compose multiple services to build their UI::

    from panther.webapp.services.config_service import ConfigService
    from panther.webapp.services.results import ResultsService

    svc = ConfigService()
    results = ResultsService(output_dir="outputs")

See Also:
--------
panther.webapp.pages : Pages that consume these services.
panther.core : The core framework that services wrap.
"""
