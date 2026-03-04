# PANTHER Web Dashboard

Web interface for the PANTHER protocol testing framework, built on NiceGUI + NiceCRUD + FastAPI.

This replaces the legacy Flask webapp. The old code lives in `_legacy/` for reference only.

## Quick Start

```bash
# From the repo root, with the venv active:
pip install -e ".[web]"
panther web                    # http://localhost:8080
panther web --port 9000        # custom port
panther web --reload           # dev mode with hot reload
```

## Tech Stack

| Layer       | Technology | Why                                                        |
|-------------|------------|------------------------------------------------------------|
| UI framework | NiceGUI 3.x | Pure Python, auto-pushes state to browser via WebSocket, no JS/HTML templates to maintain |
| CRUD forms  | NiceCRUD   | Auto-generates forms from Pydantic models -- PANTHER config is already Pydantic |
| Server      | Uvicorn + FastAPI | Comes free with NiceGUI; async, WebSocket-native          |
| Styling     | Quasar (via NiceGUI) | Material Design components out of the box              |

**Why not Flask?** The legacy webapp required Jinja templates, WTForms, custom JS for every form, and manual WebSocket wiring. NiceGUI removes all of that -- UI is declared in Python, and state changes push to the browser automatically. NiceCRUD eliminates the form-generation boilerplate since PANTHER already uses Pydantic models for configuration.

**Why not FastUI / Streamlit / Gradio?** FastUI is React-heavy (extra build step). Streamlit reruns the entire script on every interaction (bad for long-running experiments). Gradio targets ML demos, not dashboards. NiceGUI is the best fit for a stateful dashboard that wraps an existing Python backend.

## File Structure

```
panther/webapp/
    __init__.py
    app.py                  # NiceGUI application factory, page registration
    _legacy/                # Old Flask code -- reference only, do not import
    pages/
        dashboard.py        # Home: experiment status cards, quick actions
        config_builder.py   # Config editor: NiceCRUD forms + YAML preview
        experiments.py      # Launch & monitor running experiments
        results.py          # Browse output directories, view reports
        plugins.py          # Plugin browser: protocols, IUTs, testers, envs
    components/
        layout.py           # Shared sidebar, header, theme
        yaml_editor.py      # CodeMirror YAML editor (ui.codemirror)
        log_viewer.py       # Scrolling log panel (ui.log)
        stat_cards.py       # Reusable stat/counter cards
    services/
        experiment_service.py   # Wraps ExperimentManager for async use
        plugin_service.py       # Wraps PluginManager for plugin discovery
        results_service.py      # Reads output directories
        config_service.py       # Config loading, validation, YAML I/O
    models/
        api_models.py       # Pydantic models for API request/response
    docs/                   # Detailed documentation (you are here)
    static/                 # Custom CSS, images if needed
```

## Feature Status

| Feature                          | Status       | Notes                                         |
|----------------------------------|--------------|-----------------------------------------------|
| `panther web` CLI command        | **Done**     | `panther/cli_click/commands/web.py`           |
| Shared layout (sidebar, header)  | **Done**     | `components/layout.py`                        |
| Plugin browser page              | **Done**     | `pages/plugins.py`                            |
| Dashboard with status cards      | **Done**     | `pages/dashboard.py`, `components/stat_cards.py` |
| Config builder (NiceCRUD forms)  | **Skeleton** | `pages/config_builder.py` — form wiring TBD  |
| YAML editor with live sync       | **Skeleton** | `components/yaml_editor.py` — sync TBD       |
| Experiment launch                | Planned      | Week 6 task                                   |
| Real-time monitoring (WebObserver) | Planned    | Week 7 task                                   |
| Results browser                  | **Done**     | `pages/results.py`, `services/results_service.py` |
| Error handling & UX polish       | Planned      | Week 9 task                                   |
| Tests                            | Planned      | Week 10 task                                  |

## Legacy Code (`_legacy/`)

The `_legacy/` directory contains the original Flask-based webapp:
- `web_app.py` -- Flask app factory with API endpoints
- `experiment_setup.py` -- Blueprint with WTForms-based config forms
- `templates/` -- Jinja2 HTML templates
- `static/` -- CSS, JS, fonts

This code is kept as reference for understanding what the old webapp did. It is not imported by the new code and will be deleted once the new webapp reaches feature parity.

## Development

See `docs/SETUP.md` for environment setup and `docs/TASKS.md` for the full task breakdown.

See `docs/ARCHITECTURE.md` for design decisions and integration patterns.

## Key PANTHER Interfaces

Files you will interact with most:

- **Config models**: `panther/config/core/models/` -- GlobalConfig, TestConfig, ServiceConfig (Pydantic)
- **ExperimentManager**: `panther/core/experiment_manager.py` -- central orchestrator
- **GUIObserver**: `panther/core/observer/impl/gui_observer.py` -- base class to subclass for web events
- **EventManager**: `panther/core/observer/management/event_manager.py` -- event pub/sub system
- **PluginManager**: `panther/plugins/plugin_manager.py` -- plugin discovery and metadata
- **CLI entry**: `panther/cli_click/commands/web.py` -- the `panther web` Click command
