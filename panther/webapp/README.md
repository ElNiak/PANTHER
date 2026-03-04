# PANTHER Web Dashboard

Web interface for the PANTHER protocol testing framework, built on NiceGUI + NiceCRUD + FastAPI.

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
    docs/                   # Detailed documentation
```

## Feature Status

| Feature                          | Status       | Notes                                         |
|----------------------------------|--------------|-----------------------------------------------|
| `panther web` CLI command        | **Done**     | `panther/cli_click/commands/web.py`           |
| Shared layout (sidebar, header)  | **Done**     | `components/layout.py`                        |
| Plugin browser page              | **Done**     | `pages/plugins.py`                            |
| Dashboard with status cards      | **Done**     | `pages/dashboard.py`, `components/stat_cards.py` |
| Config builder (NiceCRUD forms)  | **Skeleton** | Placeholder forms, NiceCRUD not wired yet     |
| Dynamic plugin config discovery  | Planned      | Milestone 1 — plugins expose config schemas   |
| YAML editor with two-way sync   | **Skeleton** | Editor works, bidirectional sync not wired     |
| Experiment launch                | **Skeleton** | Threading works, status polling needed         |
| Experiment monitoring (polling)  | Planned      | Milestone 2 — ui.timer-based polling           |
| Results browser                  | **Bug**      | Detail view defined but not wired to row click |
| Error handling & UX polish       | Planned      | Milestone 3                                    |
| Tests                            | Planned      | Milestone 3 — service unit tests               |

## Development

See `docs/GETTING_STARTED.md` for first-day orientation.

See `docs/SETUP.md` for environment setup.

See `docs/TASKS.md` for the milestone-based development plan.

See `docs/ARCHITECTURE.md` for design decisions and integration patterns.

## Key PANTHER Interfaces

Files you will interact with most:

- **Config models**: `panther/config/core/models/` — GlobalConfig, TestConfig, ServiceConfig (Pydantic)
- **Plugin config base**: `panther/config/core/models/plugin.py` — BasePluginConfig hierarchy
- **Plugin configs**: `panther/plugins/*/config_schema.py` — per-plugin Pydantic config models
- **ExperimentManager**: `panther/core/experiment_manager.py` — central orchestrator
- **PluginManager**: `panther/plugins/plugin_manager.py` — plugin discovery and metadata
- **CLI entry**: `panther/cli_click/commands/web.py` — the `panther web` Click command
