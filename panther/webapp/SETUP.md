# Development Setup: PANTHER Web Dashboard

How to get the webapp running locally for development. This is a companion to
[GETTING_STARTED.md](GETTING_STARTED.md) (conceptual walkthrough) and
[ARCHITECTURE.md](ARCHITECTURE.md) (design decisions).

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
- `uvicorn[standard]` -- ASGI server (used by NiceGUI internally)
- `websockets` -- WebSocket support
- Plus all PANTHER core dependencies and dev tools (pytest, black, etc.)

Config forms are rendered by the built-in `PydanticForm` component (no external form library needed).

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

### Smoke Test Verification

After installing, verify everything works:

```bash
# 1. Check CLI command exists
panther --help          # Should list 'web' command

# 2. Check NiceGUI is installed
python -c "import nicegui; print(nicegui.__version__)"   # Should print 3.x

# 3. Check PydanticForm works with PANTHER models
python -c "from panther.webapp.components.pydantic_form import PydanticForm; print('PydanticForm OK')"

# 4. Start the server and check all 5 pages load
panther web --reload
# Navigate to: /, /config, /experiments, /results, /plugins
```

## How NiceGUI Development Works

NiceGUI serves a single-page application. The Python process holds the UI state and pushes changes to the browser over a WebSocket.

**Hot reload (`--reload`):**
When you save a Python file, Uvicorn restarts and NiceGUI rebuilds the UI. The browser reconnects automatically within a few seconds.

**No build step:**
There is no `npm install`, no `webpack`, no `node_modules`. Everything is Python. NiceGUI bundles Vue.js and Quasar internally.

**Browser dev tools:**
NiceGUI renders Quasar (Material Design) components. Styling changes should be made in Python via `.classes()` and `.style()` calls, not in CSS files.

## Project Structure

Files you will work in most often:

```
panther/webapp/
    app.py                  # Start here. Application factory, page registration.
    pages/                  # One file per page. Each exports a content() function.
        dashboard.py        # /           (working)
        config_builder.py   # /config     (skeleton -- forms to build)
        experiments.py      # /experiments (skeleton -- launch works, monitoring to build)
        results.py          # /results    (working -- row-click wired, analysis to build)
        plugins.py          # /plugins    (working)
    components/             # Reusable UI pieces shared across pages.
        layout.py           # Sidebar, header, shared wrapper.
        yaml_editor.py      # CodeMirror YAML editor component.
        log_viewer.py       # Scrolling log display.
        stat_cards.py       # Stat counter cards.
        topology_editor.py  # Topology editor placeholder (student implements).
    utils/                  # Utility modules.
        form_models.py      # Type introspection utilities for PydanticForm.
    services/               # Business logic. Thin wrappers around PANTHER core.
        experiment_service.py
        plugin_service.py
        config_service.py
        results_service.py
```

Core PANTHER files you will read but rarely edit:

```
panther/config/core/models/     # Pydantic config models (GlobalConfig, TestConfig, etc.)
panther/core/experiment_manager.py          # Central experiment orchestrator
panther/core/observer/impl/gui_observer.py  # Base class for WebObserver
panther/core/observer/management/event_manager.py  # Event pub/sub
panther/core/reporting/status_collector.py  # ExperimentSummary, TestResult, ServiceHealthSummary
panther/plugins/plugin_manager.py           # Plugin discovery
```

Docs (your planning references):

```
panther/webapp/TASKS.md          # Week-by-week plan with code and thesis tasks
panther/webapp/ARCHITECTURE.md   # Design decisions, integration patterns, scope
panther/webapp/GETTING_STARTED.md # First-day walkthrough
```

## Running Tests

```bash
# Run webapp tests (40 tests covering services, form models, app factory)
pytest tests/unit/test_webapp/ -v -o "addopts=-v --tb=short"

# Run all project unit tests
pytest tests/ -n auto -m unit
```

## Code Quality

```bash
black panther/webapp/            # Format (line length 88)
isort panther/webapp/            # Sort imports
flake8 panther/webapp/           # Lint
```

Run `black` and `isort` before every commit.
