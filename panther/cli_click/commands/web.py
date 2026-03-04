"""
Web Command - Click Implementation

Launch the PANTHER web dashboard (NiceGUI-based).
"""

import click

from panther.cli_click.core.base import (
    error_message,
    handle_errors,
    info_message,
    pass_context_and_setup_logging,
)


@click.command()
@click.option(
    "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
)
@click.option(
    "--port", "-p", default=8080, type=int, help="Port to serve on (default: 8080)"
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default=None,
    help="Preload an experiment config YAML.",
)
@click.option(
    "--output-dir",
    "-o",
    default="outputs",
    type=click.Path(),
    help="Output directory for experiment results.",
)
@click.option("--reload", is_flag=True, help="Enable auto-reload for development.")
@handle_errors
@pass_context_and_setup_logging
def web(ctx, host, port, config, output_dir, reload):
    """Launch PANTHER web dashboard.

    Starts a NiceGUI-based web interface for experiment configuration,
    launching, monitoring, and result browsing.

    \b
    Examples:
      panther web                          # Start on localhost:8080
      panther web -p 3000                  # Custom port
      panther web -c experiment.yaml       # Preload config
      panther web --reload                 # Dev mode with hot reload
    """
    try:
        from nicegui import ui
    except ImportError:
        error_message(
            "Web dependencies not installed. "
            "Install with: pip install panther-net[web]"
        )
        raise click.Abort()

    from panther.webapp.app import create_app

    info_message(f"Starting PANTHER web dashboard at http://{host}:{port}")
    create_app(config_path=config, output_dir=output_dir)
    ui.run(
        host=host,
        port=port,
        reload=reload,
        title="PANTHER Dashboard",
        show=False,
    )
