"""NiceGUI application factory for PANTHER web dashboard."""

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

    Args:
        config_path: Path to a PANTHER experiment config to preload.
        output_dir: Directory where experiment outputs are stored.
    """
    # Store shared state for access across pages
    app.storage.general["config_path"] = config_path
    app.storage.general["output_dir"] = str(Path(output_dir).resolve())

    @ui.page("/")
    def index():
        create_layout("Dashboard")
        dashboard.content()

    @ui.page("/config")
    def config_page():
        create_layout("Config Builder")
        config_builder.content()

    @ui.page("/experiments")
    def experiments_page():
        create_layout("Experiments")
        experiments.content()

    @ui.page("/results")
    def results_page():
        create_layout("Results")
        results.content()

    @ui.page("/plugins")
    def plugins_page():
        create_layout("Plugins")
        plugins.content()

    @ui.page("/topology")
    def topology_page():
        create_layout("Topology")
        topology.content()

    logger.info("PANTHER web dashboard configured")
