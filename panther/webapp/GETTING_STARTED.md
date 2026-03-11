# Getting Started: PANTHER Web Dashboard

This guide gets you from zero to productive in your first day working on the PANTHER
web dashboard. It is designed for developers who are new to the codebase — whether
you are a thesis student, a contributor, or someone evaluating the project. Follow
it step by step.

**What you will learn:**
- How to install and run the webapp locally
- The code structure and key files to read first
- How the service layer connects the UI to PANTHER's backend
- Where to find the architecture docs and development plan

## Prerequisites

- **Python 3.10+** installed (`python --version` to check)
- **git** for version control
- **A modern browser** (Chrome or Firefox recommended)
- **Docker** — only needed to run real experiments; not required for webapp UI development
- **Familiarity with Python** — the webapp is pure Python (no JavaScript required)
- **Basic NiceGUI knowledge** recommended — see [NiceGUI documentation](https://nicegui.io/documentation)

## Step 1: Setup (30 minutes)

```bash
# Clone the repository
git clone https://github.com/ElNiak/PANTHER.git
cd PANTHER

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install PANTHER with web dependencies
pip install -e ".[web,dev]"
```

Verify:
```bash
panther --help          # Should show CLI commands including 'web'
python -c "import nicegui; print(nicegui.__version__)"   # Should print 3.x
python -c "from panther.webapp.components.forms.pydantic_form import PydanticForm; print('OK')"  # Should print OK
```

## Step 2: Run the Webapp (5 minutes)

```bash
panther web --reload
```

Open `http://localhost:8080`. You should see a sidebar with 5 navigation links.

Click through every page and note the current status:

| Page | Route | Status |
|------|-------|--------|
| Dashboard | `/` | Working -- stat cards, quick actions |
| Config Builder | `/config` | Skeleton -- placeholder forms, YAML editor works |
| Experiments | `/experiments` | Skeleton -- launch works, monitoring to build |
| Results | `/results` | Working -- table with row-click detail view |
| Plugins | `/plugins` | Working -- plugin table grouped by type |

## Step 3: Understand the Code (1 hour)

Read these files in this order:

### Webapp files (your main working area):

1. **`panther/webapp/app.py`** -- Application factory. Registers all 5 pages.
2. **`panther/webapp/components/layout.py`** -- Shared sidebar, header. Every page uses this.
3. **`panther/webapp/pages/plugins.py`** -- Simplest complete page. Shows the pattern: import service -> call method -> render.
4. **`panther/webapp/services/plugin_service.py`** -- Simplest service. Wraps `PluginManager`.
5. **`panther/webapp/pages/config_builder.py`** -- Main feature to build. Has placeholder forms and a YAML editor.

### Core PANTHER files (read, rarely edit):

6. **`panther/config/core/models/global_config.py`** -- Pydantic models (GlobalConfig, LoggingConfig, DockerConfig, PathsConfig). These are what the config builder forms generate UIs for.
7. **`panther/core/experiment_manager.py`** -- Central orchestrator. Read `__init__` carefully (lines 136-219) to understand the constructor signature.
8. **`panther/core/observer/impl/gui_observer.py`** -- GUIObserver base class. Your WebObserver will subclass this.
9. **`panther/core/reporting/status_collector.py`** -- ExperimentSummary, TestResult, ServiceHealthSummary. The results page parses these.

## Step 4: PydanticForm Exploration (1 hour)

The config builder uses `PydanticForm` — a custom component that recursively
renders any Pydantic `BaseModel` as editable NiceGUI widgets.

```python
from panther.webapp.components.forms.pydantic_form import PydanticForm, FormConfig
from panther.config.core.models.global_config import LoggingConfig

# PydanticForm handles nested models, enums, Optional fields, etc. automatically
form = PydanticForm(LoggingConfig, config=FormConfig(section_style="card"))
data = form.get_value()  # Returns validated dict
form.set_value({"level": "DEBUG"})
```

Run `panther web --reload` and navigate to `/config` to see PydanticForm in action.

See `panther/webapp/components/forms/pydantic_form.py` for the implementation and
`tests/integration/test_pydantic_form_browser.py` for comprehensive tests.

## Step 5: Verify Bug Fixes (15 minutes)

The scaffold bugs have been fixed in this commit. Verify they work:

1. **Results row-click**: Navigate to `/results`. Click a row. The detail panel should appear below the table.
2. **Config service**: The config service now resolves paths relative to the project root. Verify `panther web` starts without path errors.
3. **Experiment service**: Uses `asyncio.to_thread()` instead of a busy-loop. The experiment launch should not block the UI.

## Step 5.5: Understanding the Integration Layer

The webapp uses 4 service wrappers to talk to PANTHER core. Pages never import core classes directly — services handle error wrapping, async safety, and threading concerns. This is the key abstraction to understand before building new features.

| I want to... | Use this service | Key methods |
|-------------|-----------------|-------------|
| Load/validate a config | `ConfigService` | `load_config()`, `validate_config_detailed()`, `save_config()` |
| Run an experiment | `ExperimentService` | `run_experiment()`, `stop()`, `status`, `is_running` |
| Get live updates during a run | `ExperimentService` | `subscribe_events()`, `unsubscribe_events()`, `register_callbacks()` |
| Browse past results | `ResultsService` | `list_experiments()`, `get_experiment_detail()`, `get_test_detail()` |
| List available plugins | `PluginService` | `list_plugins()`, `get_plugin_detail()`, `get_plugin_manifest()` |

**Important patterns:**
- `ExperimentService` is a singleton — get it via `get_experiment_service()`. It persists log buffer and status across page navigations.
- All other services are stateless — instantiated once in `app.py` and passed to pages.
- Experiment execution runs in a background thread (`asyncio.to_thread`). Subscribe to events for real-time updates; unsubscribe on page disconnect to prevent stale callbacks.

For full API reference and architectural details, see `ARCHITECTURE.md` § "Service Layer Pattern" and § "Service API Reference".

## Step 6: Read the Plan

Now read your development plan and architecture docs:

- **`panther/webapp/TASKS.md`** -- 4-phase plan with code and thesis tasks per phase
- **`panther/webapp/ARCHITECTURE.md`** -- Design decisions, integration patterns, data models, scope

Run the existing test suite to make sure everything works:
```bash
pytest tests/unit/test_webapp/ -v -o "addopts=-v --tb=short"
# Should show 40 passed
```

## Key Concepts

### NiceGUI Basics
- Every UI element is a Python object: `ui.label("text")`, `ui.button("click me")`
- Layout uses context managers: `with ui.row():`, `with ui.card():`
- Styling via Quasar classes: `.classes('text-h4 text-primary')`
- Binding: `ui.input().bind_value(model, 'field_name')`
- Events: `button.on('click', handler)`
- Charts: `ui.echart({'xAxis': ..., 'series': ...})`

### Pydantic in PANTHER
- All config models inherit from `BaseConfig` (extends Pydantic `BaseModel`)
- `model.model_dump()` -> dict, `ModelClass(**data)` -> validated instance
- Validation errors are `pydantic.ValidationError` with per-field messages

### The Service Layer
- Pages never import core PANTHER classes directly
- Services wrap core classes, handle errors, provide async-safe interfaces
- Each service maps to one core component (see ARCHITECTURE.md)

### PydanticForm
- `PydanticForm(ModelClass)` renders any Pydantic BaseModel as editable widgets
- `form.get_value()` returns a validated dict; `form.set_value(data)` populates fields
- `FormConfig` controls layout: section style (expansion/card/flat), advanced toggle, CSS prefix
- Nested models are handled recursively; enums become dropdowns; Optional[BaseModel] gets a toggle
- See `panther/webapp/components/forms/pydantic_form.py` for implementation details

## Understanding Config as a Graph

PANTHER config files describe a graph: services are nodes, protocol relationships are
edges, and network environments group them. See `ARCHITECTURE.md` § "Config Model
Hierarchy" for the data model and § "Visual Topology Editor" for graph-relevant fields.

## NiceGUI JavaScript Interop

When building custom interactive components (e.g., a topology editor), you may need
to bridge between Python and browser-side JavaScript. NiceGUI provides
`ui.run_javascript()` for this:

```python
# Execute JS and get a result back
result = await ui.run_javascript('document.title')

# Dispatch custom events from JS to Python
container = ui.element('div')
container.on('my-event', lambda e: print(e.args))
ui.run_javascript(f'''
    const el = document.getElementById("{container.id}");
    el.dispatchEvent(new CustomEvent("my-event", {{
        detail: {{key: "value"}},
        bubbles: true
    }}));
''')
```

See the [NiceGUI documentation on JavaScript](https://nicegui.io/documentation)
for more patterns.


## For Thesis Students

If you are working on this codebase as part of a thesis, the following resources
will help you get started:

- **`TASKS.md`** — development roadmap with phased goals
- **`ARCHITECTURE.md`** — design decisions and integration patterns
