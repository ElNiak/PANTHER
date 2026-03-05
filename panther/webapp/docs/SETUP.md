# Development Setup: PANTHER Web Dashboard

How to get the webapp running locally for development.

## Prerequisites

- Python 3.10 or later
- pip (comes with Python)
- git
- A modern browser (Chrome, Firefox, Edge)
- Docker (needed only if you want to actually run experiments, not for webapp development)

## Install

```bash
# 1. Clone the repo (if you have not already)
git clone https://github.com/ElNiak/PANTHER.git
cd PANTHER

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# 3. Install PANTHER with web + dev dependencies
pip install -e ".[web,dev]"
```

This installs:
- `nicegui>=3.0.0` -- the UI framework
- `niceguicrud` -- auto-generated CRUD forms from Pydantic models
- `uvicorn[standard]` -- ASGI server (used by NiceGUI internally)
- `websockets` -- WebSocket support
- Plus all PANTHER core dependencies and dev tools (pytest, black, etc.)

## Run the Dev Server

```bash
# Start with hot reload (recommended during development)
panther web --reload

# Start on a custom port
panther web --port 9000 --reload

# Start without reload (more stable, use if hot reload causes issues)
panther web
```

The server starts at `http://localhost:8080` by default. The browser does NOT auto-open; navigate there manually.

## How NiceGUI Development Works

NiceGUI serves a single-page application. The Python process holds the UI state and pushes changes to the browser over a WebSocket.

**Hot reload (`--reload`):**
When you save a Python file, Uvicorn restarts and NiceGUI rebuilds the UI. The browser reconnects automatically within a few seconds. You do not need to manually refresh.

**No build step:**
There is no `npm install`, no `webpack`, no `node_modules`. Everything is Python. NiceGUI bundles Vue.js and Quasar internally.

**Browser dev tools:**
NiceGUI renders Quasar (Material Design) components. You can inspect elements in the browser dev tools, but styling changes should be made in Python via `.classes()` and `.style()` calls, not in CSS files.

## Project Structure Orientation

Files you will work in most often:

```
panther/webapp/
    app.py                  # Start here. Application factory, page registration.
    # CLI command lives at panther/cli_click/commands/web.py
    pages/                  # One file per page. Each exports a register() function.
        dashboard.py        # /
        config_builder.py   # /config
        experiments.py      # /experiments
        results.py          # /results
        plugins.py          # /plugins
    components/             # Reusable UI pieces shared across pages.
        layout.py           # Sidebar, header, shared wrapper.
        yaml_editor.py      # CodeMirror YAML editor component.
        log_viewer.py       # Scrolling log display.
        stat_cards.py       # Stat counter cards.
    services/               # Business logic. Thin wrappers around PANTHER core.
        experiment_service.py
        plugin_service.py
        config_service.py
        results_service.py
```

Core PANTHER files you will read but rarely edit:

```
panther/config/core/models/     # Pydantic config models (GlobalConfig, TestConfig, etc.)
panther/core/experiment_manager.py   # Central experiment orchestrator
panther/core/observer/impl/gui_observer.py  # Base class for the web observer
panther/core/observer/management/event_manager.py  # Event pub/sub
panther/plugins/plugin_manager.py    # Plugin discovery
panther/cli_click/core/main.py       # CLI entry point (register your command here)
```

## Running Tests

```bash
# Run webapp tests only
pytest tests/unit/test_webapp/ -v

# Run with coverage
pytest tests/unit/test_webapp/ --cov=panther/webapp --cov-report=term-missing

# Run all project tests (slow, needs Docker for integration tests)
pytest tests/ -n auto -m unit
```

The test directory `tests/unit/test_webapp/` does not exist yet. Create it in Week 10 (see TASKS.md).

## Code Quality

PANTHER uses these tools (configured in `pyproject.toml`):

```bash
# Format code (line length 88, Black default)
black panther/webapp/

# Sort imports
isort panther/webapp/

# Lint
flake8 panther/webapp/

# Type check (optional, PANTHER has pre-existing pyright issues)
mypy panther/webapp/
```

Run `black` and `isort` before every commit. The project uses 88-character line length (Black default).

## Troubleshooting

**`ModuleNotFoundError: No module named 'nicegui'`**
You installed without the `[web]` extra. Run: `pip install -e ".[web]"`

**`panther web` command not found**
Either the command has not been implemented yet (see Week 1 in TASKS.md), or you need to reinstall: `pip install -e ".[web]"`

**Port already in use**
Another process is using port 8080. Either kill it (`lsof -ti:8080 | xargs kill`) or use a different port: `panther web --port 9000`

**NiceGUI hot reload causes import errors on restart**
This happens occasionally with circular imports. Restart the server manually. If it persists, run without `--reload`.

**Browser shows "Disconnected" after saving a file**
This is normal during hot reload. Wait 2-3 seconds for the server to restart. The browser reconnects automatically.

**`ImportError` when importing PANTHER core modules**
Make sure you are in the virtual environment (`source .venv/bin/activate`) and have installed with `pip install -e ".[web]"`. PANTHER must be installed in editable mode for imports to work.

**Plugin list is empty on the /plugins page**
PluginManager needs the plugin directory to be available. Make sure you are running from the repo root (where `panther/plugins/` exists). If installed via pip, plugins are bundled in the package.
