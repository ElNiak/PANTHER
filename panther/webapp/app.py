"""PANTHER webapp application factory --- page registration and shared state setup.

This module implements the application factory pattern for the PANTHER
web dashboard.  The single public function ``create_app()`` configures
NiceGUI's shared storage, registers all page routes, and wires each
route to its corresponding page module through the shared layout shell.

Page registration works by decorating inner functions with
``@ui.page(route)``.  Each decorated function calls ``create_layout()``
(which renders the sidebar, header, and status bar) and then delegates
to the page module's ``content()`` function for the page body.

This module is imported lazily by ``panther.webapp.__init__.create_app``
so that web dependencies (NiceGUI, FastAPI) are only required when the
dashboard is actually started.

Example:
-------
::

    from panther.webapp.app import create_app
    from nicegui import ui

    create_app(config_path="my_config.yaml", output_dir="outputs")
    ui.run(title="PANTHER", port=8080)

See Also:
--------
panther.webapp.__init__ : Lazy entry point that wraps this factory.
panther.webapp.pages : Page modules registered by this factory.
panther.webapp.components.layout : Shared layout shell used by every page.
"""

import logging
from pathlib import Path
from typing import Optional

from nicegui import app, ui

from panther.webapp.components.layout import create_layout
from panther.webapp.pages import (
    config_builder,
    dashboard,
    experiments,
    plugins,
    results,
    topology,
)

logger = logging.getLogger(__name__)


def create_app(
    config_path: Optional[str] = None,
    output_dir: str = "outputs",
):
    """Create and configure the NiceGUI application.

    Seeds ``app.storage.general`` with the config path and resolved
    output directory so that all pages can access shared state without
    passing arguments through the call chain.  Then registers one
    ``@ui.page`` route per dashboard page, each wrapped in the common
    layout shell (sidebar navigation, header, experiment status bar).

    This function does **not** call ``ui.run()`` --- the caller is
    responsible for starting the NiceGUI server after invoking this
    factory.

    Args:
        config_path: Path to a PANTHER experiment config YAML file to
            preload into the config builder on startup.  When ``None``,
            the config builder starts empty.
        output_dir: Directory where experiment outputs are stored.
            Resolved to an absolute path before being stored.
    """
    # Store shared state for access across pages
    app.storage.general["config_path"] = config_path
    app.storage.general["output_dir"] = str(Path(output_dir).resolve())

    @ui.page("/")
    def index():
        """Serve the dashboard home page with summary stats and live event feed."""
        create_layout("Dashboard")
        dashboard.content()

    @ui.page("/config")
    def config_page():
        """Serve the config builder with PydanticForm editors and YAML preview."""
        create_layout("Config Builder")
        config_builder.content()

    @ui.page("/experiments")
    def experiments_page():
        """Serve the experiment runner with live log viewer and progress bar."""
        create_layout("Experiments")
        experiments.content()

    @ui.page("/results")
    def results_page():
        """Serve the results browser with charts, test details, and artifacts."""
        create_layout("Results")
        results.content()

    @ui.page("/plugins")
    def plugins_page():
        """Serve the plugin browser with type filtering and detail panels."""
        create_layout("Plugins")
        plugins.content()

    @ui.page("/topology")
    def topology_page():
        """Serve the visual topology editor for experiment configuration."""
        create_layout("Topology")
        topology.content()

    logger.info("PANTHER web dashboard configured")
