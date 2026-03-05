# Getting Started: PANTHER Web Dashboard

Muhammad, this guide gets you from zero to productive in your first day. Follow it step by step.

## Prerequisites

- Python 3.10+ installed
- git
- A modern browser (Chrome or Firefox)
- Docker (only needed to run real experiments -- not required for webapp development)

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
python -c "from niceguicrud import NiceCRUD; print('OK')"  # Should print OK
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

## Step 4: NiceCRUD Spike (2 hours)

Before building the full config builder, test if NiceCRUD works with PANTHER's models.

Create a temporary test file `test_nicecrud_spike.py` in the repo root:

```python
"""NiceCRUD spike: test with PANTHER config models."""
from nicegui import ui
from panther.config.core.models.global_config import LoggingConfig, DockerConfig

@ui.page('/')
def main():
    ui.label("NiceCRUD Spike").classes('text-h4')

    # Test 1: Simple flat model with id_field
    ui.label("LoggingConfig:").classes('text-h6')
    try:
        from niceguicrud import NiceCRUD
        crud = NiceCRUD(LoggingConfig, id_field='level')
        ui.label("LoggingConfig: NiceCRUD works!").classes('text-green')
    except Exception as e:
        ui.label(f"LoggingConfig FAILED: {e}").classes('text-red')

    # Test 2: Nested model with id_field
    ui.label("DockerConfig:").classes('text-h6')
    try:
        crud2 = NiceCRUD(DockerConfig, id_field='force_build')
        ui.label("DockerConfig: NiceCRUD works!").classes('text-green')
    except Exception as e:
        ui.label(f"DockerConfig FAILED: {e}").classes('text-red')

ui.run(port=9999)
```

Run: `python test_nicecrud_spike.py`

Document what happens:
- Does LoggingConfig render correctly?
- Does DockerConfig (with nested sub-models) render?
- Are Optional fields handled?
- Are Enum fields rendered as dropdowns?

**Write a 1-page spike report.** This determines your fallback strategy for Week 2.

## Step 5: Verify Bug Fixes (15 minutes)

The scaffold bugs have been fixed in this commit. Verify they work:

1. **Results row-click**: Navigate to `/results`. Click a row. The detail panel should appear below the table.
2. **Config service**: The config service now resolves paths relative to the project root. Verify `panther web` starts without path errors.
3. **Experiment service**: Uses `asyncio.to_thread()` instead of a busy-loop. The experiment launch should not block the UI.

## Step 6: Read the Plan

Now read your development plan and architecture docs:

- **`panther/webapp/TASKS.md`** -- 8-week plan with code and thesis tasks per week
- **`panther/webapp/ARCHITECTURE.md`** -- Design decisions, integration patterns, data models, scope

## Key Concepts

### NiceGUI Basics
- Every UI element is a Python object: `ui.label("text")`, `ui.button("click me")`
- Layout uses context managers: `with ui.row():`, `with ui.card():`
- Styling via Quasar classes: `.classes('text-h4 text-primary')`
- Binding: `ui.input().bind_value(model, 'field_name')`
- Events: `button.on('click', handler)`
- Charts: `ui.echart({'xAxis': ..., 'series': ...})`

### Pydantic in PANTHER
- All config models inherit from `BaseUnifiedModel` (extends `BaseModel`)
- `model.model_dump()` -> dict, `ModelClass(**data)` -> validated instance
- Validation errors are `pydantic.ValidationError` with per-field messages

### The Service Layer
- Pages never import core PANTHER classes directly
- Services wrap core classes, handle errors, provide async-safe interfaces
- Each service maps to one core component (see ARCHITECTURE.md)

### NiceCRUD with PANTHER Models
- Always pass `id_field` parameter (PANTHER models don't have an `id` field)
- Use a field that's unique per instance (e.g., `id_field='level'` for LoggingConfig)
- For nested models, compose multiple NiceCRUD instances in `ui.expansion` panels

## Your First Week Deliverables

By end of Week 1, you should have:
1. All 5 pages loading without errors (verified)
2. NiceCRUD spike report (1 page)
3. Background chapter outline for thesis
4. Related work research notes (web-based testing tools, framework comparisons)

## Thesis Writing Tips (UCLouvain EPL)

Your thesis should be 40-60 pages. Suggested chapter structure:

1. **Introduction** (5-7 pages): Problem statement, contributions, structure
2. **Background & Related Work** (8-12 pages): Protocol testing, PANTHER framework, web UI frameworks, comparison
3. **Architecture & Design** (8-12 pages): Stack choice, service layer, observer integration, NiceCRUD pipeline
4. **Implementation** (10-15 pages): Config builder, experiment launch, results dashboard, charts
5. **Evaluation** (5-8 pages): Testing methodology, usability comparison with CLI, demo walkthrough
6. **Conclusion & Future Work** (3-5 pages)

Start writing in Week 1. Each week has thesis writing tasks alongside code tasks.
