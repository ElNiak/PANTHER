"""PANTHER webapp --- NiceGUI-based web dashboard for protocol testing experiment management.

This package provides a browser-based UI for configuring, launching,
monitoring, and reviewing PANTHER (Protocol ANalyzer and THreat
Evaluator for Research) experiments.  The stack is built on NiceGUI
(which itself wraps FastAPI + Vue.js) and uses a strict service-layer
architecture so that pages never import ``panther.core`` directly.

Architecture overview
---------------------
The webapp follows three design principles:

1. **Service-layer pattern** -- Every interaction with the PANTHER core
   passes through a service class in ``services/``.  Services add
   async safety, caching, error boundaries, and NiceGUI-specific
   adaptations on top of core components.
2. **Event bridge** -- ``WebObserver`` (a GUIObserver subclass) bridges
   PANTHER's event system into NiceGUI UI callbacks, enabling live
   dashboards that react to experiment progress in real time.
3. **Pydantic form rendering** -- The ``PydanticForm`` component
   introspects Pydantic config models and renders them as editable
   NiceGUI widgets, so that new config sections are automatically
   surfaced in the UI without hand-written forms.

Directory structure
-------------------
::

    webapp/
    +-- __init__.py          # Package entry point (this file); lazy create_app
    +-- app.py               # Application factory; page registration
    +-- services/            # Service layer (ConfigService, ExperimentService,
    |                        #   ResultsService, PluginService, WebObserver)
    +-- components/          # Reusable NiceGUI UI components (forms, cards,
    |                        #   badges, viewers, topology editor, ...)
    +-- pages/               # Top-level page modules, one per route
    |                        #   (dashboard, config_builder, experiments,
    |                        #   results, plugins, topology)
    +-- models/              # Webapp-specific Pydantic models for API
    |                        #   responses and display aggregates
    +-- utils/               # Form-model introspection helpers and
    |                        #   plugin-to-form bridging utilities
    +-- static/              # CSS, images, and other static assets

Quick start
-----------
From the CLI (after ``pip install panther-net[web]``)::

    panther web                           # starts on http://localhost:8080
    panther web --config my_config.yaml   # preloads a config file

Programmatically::

    from panther.webapp import create_app

    create_app(config_path="experiment.yaml", output_dir="outputs")
    # then start NiceGUI: ui.run(...)

See Also:
--------
panther.core : Core experiment execution framework.
panther.config : OmegaConf + Pydantic configuration system.
panther.plugins : Plugin discovery and registration system.
"""

__all__ = ["create_app"]


def create_app(**kwargs):
    """Create and configure the NiceGUI web application.

    Lazy import to avoid requiring web dependencies when not using the webapp.
    """
    try:
        from panther.webapp.app import create_app as _create_app
    except ImportError as e:
        raise ImportError(
            "Web dependencies not installed. "
            "Install with: pip install panther-net[web]"
        ) from e
    return _create_app(**kwargs)
