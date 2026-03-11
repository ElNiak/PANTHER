"""PANTHER webapp pages --- top-level page modules, one per route.

Each module exposes a ``content()`` function that renders the page
body into the active NiceGUI container.  The application factory in
``panther.webapp.app`` registers routes and wraps each ``content()``
call with the shared layout shell (sidebar, header, status bar).

Routing table
-------------

+-----------------+---------------------+-------------------------------------------+
| Route           | Module              | Description                               |
+=================+=====================+===========================================+
| ``/``           | ``dashboard``       | Home page with summary stat cards, live   |
|                 |                     | experiment counters, and event feed.      |
+-----------------+---------------------+-------------------------------------------+
| ``/config``     | ``config_builder``  | PydanticForm-based config editor with     |
|                 |                     | side-by-side YAML preview and validation. |
+-----------------+---------------------+-------------------------------------------+
| ``/experiments``| ``experiments``     | Launch, monitor, and stop experiments;    |
|                 |                     | live log viewer and progress bar.         |
+-----------------+---------------------+-------------------------------------------+
| ``/results``    | ``results``         | Browse past experiment outputs with       |
|                 |                     | charts, tabbed test details, artifacts.   |
+-----------------+---------------------+-------------------------------------------+
| ``/plugins``    | ``plugins``         | Card-based plugin browser with type       |
|                 |                     | filtering and expandable detail panels.   |
+-----------------+---------------------+-------------------------------------------+
| ``/topology``   | ``topology``        | Visual topology editor using a vis.js     |
|                 |                     | network graph (scaffold for future work). |
+-----------------+---------------------+-------------------------------------------+

Composition pattern
-------------------
Pages compose **services** (from ``panther.webapp.services``) and
**components** (from ``panther.webapp.components``) but never import
from ``panther.core`` directly.  A typical page follows this
structure::

    from panther.webapp.services.results_service import ResultsService
    from panther.webapp.components.metrics_panel import metrics_panel

    def content():
        svc = ResultsService(output_dir=...)
        experiments = svc.list_experiments()
        for exp in experiments:
            metrics_panel(exp["metrics"])

See Also:
--------
panther.webapp.app : Application factory that registers these pages.
panther.webapp.services : Service layer consumed by pages.
panther.webapp.components : UI components composed within pages.
"""
