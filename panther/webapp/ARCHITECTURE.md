# Architecture: PANTHER Web Dashboard

Design decisions and integration patterns for the NiceGUI-based webapp.

## Stack Choice

### Why NiceGUI (not Flask or Streamlit)

PANTHER already has:
1. **Pydantic models** for all configuration (GlobalConfig, TestConfig, ServiceConfig, etc.)
2. **An event/observer system** that pushes state changes (BaseEvent -> EventManager -> IObserver)
3. **Long-running experiment processes** that need real-time progress updates

NiceGUI satisfies all three constraints with minimal glue code:

| Requirement                        | Flask          | Streamlit      | NiceGUI        |
|------------------------------------|----------------|----------------|----------------|
| Forms from Pydantic models         | Manual WTForms | st.form()      | Via PydanticForm |
| WebSocket push (server -> browser) | flask-socketio | Rerun model    | Built-in       |
| Long-running background tasks      | Celery/threads | Blocking       | asyncio native |
| Pure Python (no JS build step)     | No (Jinja+JS)  | Yes            | Yes            |
| FastAPI underneath                 | No             | No             | Yes            |

NiceGUI eliminates the need for Jinja templates, WTForms, custom JavaScript, and manual WebSocket plumbing.

### PydanticForm for Config Forms

PydanticForm (`panther/webapp/components/pydantic_form.py`) is a custom recursive
form component that renders any `BaseModel` as editable NiceGUI widgets. It replaced
the external `niceguicrud` dependency.

```python
from panther.webapp.components.pydantic_form import PydanticForm, FormConfig
from panther.config.core.models.global_config import LoggingConfig

form = PydanticForm(LoggingConfig, config=FormConfig(section_style="card"))
data = form.get_value()  # Returns validated dict (falls back to raw on error)
form.set_value({"level": "DEBUG"})
```

**Three-layer architecture:**
1. **PydanticForm** — type-dispatch logic (scalar, enum, nested model, complex collections)
2. **FormConfig** — structural layout options (grouping, advanced toggle, section style)
3. **CSS classes** — every widget gets `.{prefix}-*` classes for visual theming

**Features:**
- Recursive nested BaseModel rendering (expansion panels, cards, or flat)
- Enum fields rendered as dropdowns
- Optional[BaseModel] fields with toggle switches
- Dict[str, str], Dict[str, BaseModel], List[BaseModel] via specialized widgets
- `json_schema_extra` metadata drives UI hints (widget_type, advanced, category)
- Validation through Pydantic with graceful fallback

For deeply nested config trees (TestConfig -> ServiceConfig -> ProtocolConfig),
PydanticForm handles recursion automatically.

## How NiceGUI Integrates with PANTHER Core

### Service Layer Pattern

The webapp does NOT call PANTHER core classes directly from page code. Thin service wrappers provide an async-safe interface:

```
pages/experiments.py
    -> services/experiment_service.py
        -> panther.core.experiment_manager.ExperimentManager
```

| Service           | Wraps                            | Purpose                          |
|-------------------|----------------------------------|----------------------------------|
| ExperimentService | ExperimentManager                | Launch experiments, track status |
| PluginService     | PluginManager                    | List plugins, get metadata       |
| ConfigService     | ConfigurationManager             | Load/save/validate YAML configs  |
| ResultsService    | Filesystem (`outputs/` directory)| Browse and read experiment results|

Services are instantiated once in `app.py` and passed to pages via NiceGUI's `app.storage` or function parameters.

### Page Architecture

Each page is a Python function decorated with `@ui.page('/path')`. NiceGUI calls the function on navigation and builds the UI using component calls:

```python
# pages/plugins.py
from nicegui import ui

def register(plugin_service):
    @ui.page('/plugins')
    def plugins_page():
        with layout():              # shared sidebar + header
            ui.label('Installed Plugins').classes('text-h4')
            plugins = plugin_service.list_all()
            with ui.table(columns=[...], rows=plugins):
                pass
```

No template engine, no HTML, no JavaScript. The UI is declared in Python and NiceGUI translates it to Vue/Quasar components over a WebSocket.

### Real-Time Updates: WebObserver

PANTHER's observer system (`IObserver` -> `on_event(BaseEvent)`) is the integration point for live updates.

The webapp defines a `WebObserver` that subclasses `GUIObserver` (`panther/core/observer/impl/gui_observer.py`):

```python
from panther.core.observer.impl.gui_observer import GUIObserver
from panther.core.events.base.event_base import BaseEvent

class WebObserver(GUIObserver):
    def __init__(self):
        super().__init__()
        self._subscribers = []     # NiceGUI ui.log / ui.label bindings

    def update_gui(self, event: BaseEvent):
        """Called by GUIObserver.on_event() after state tracking."""
        for callback in self._subscribers:
            callback(event)

    def subscribe(self, callback):
        self._subscribers.append(callback)
```

When an experiment runs, the `WebObserver` is registered with `EventManager`. Every event flows through `on_event()` -> `update_gui()` -> subscribed NiceGUI components. NiceGUI auto-pushes state changes over its WebSocket, so the browser updates immediately.

`GUIObserver` provides built-in:
- Event history tracking (`get_event_history()`, max 1000 events)
- GUI state dict (`get_gui_state()` with counters and timestamps per event type)
- Automatic `_update_gui_state()` on every event

Event types from `panther/core/events/`:
- `experiment.*` -- experiment lifecycle (started, completed, failed)
- `test.*` -- individual test progress
- `service.*` -- service start/stop/error
- `environment.*` -- Docker environment events
- `step.*` -- pre/post command execution
- `metrics.*` -- performance data points

### Config Builder: PydanticForm + One-Way YAML Preview

The config builder page has two panels:

1. **Left: PydanticForm forms** -- structured editing of GlobalConfig, TestConfig, ServiceConfig
2. **Right: YAML preview** -- read-only display updated from form changes

```
Form field change -> model.model_dump() -> yaml.dump() -> YAML preview
```

Two-way sync (YAML edits updating forms) is **not in scope** -- it adds significant complexity for marginal benefit. Users edit via forms and see the resulting YAML.

### Experiment Launch: asyncio.to_thread

`ExperimentManager.run_tests()` is blocking and can run for minutes. The webapp runs it via `asyncio.to_thread()`:

```python
async def run_experiment(self, config_path, on_log, on_status):
    def _run():
        manager = ExperimentManager(
            global_config=global_config,
            experiment_name=config_dict.get("name", "web_experiment"),
        )
        success = manager.run_tests()
        ...
    await asyncio.to_thread(_run)
```

The `WebObserver` receives events from the background thread and pushes them to the browser via NiceGUI's auto-sync.

### Results Data Model

The results page parses rich data structures from PANTHER's reporting system:

**ExperimentSummary** (`panther/core/reporting/status_collector.py`):
- Overall status, timing, configuration file path
- `tests: List[TestResult]` with per-test name, status, duration, error messages
- `services: List[ServiceHealthSummary]` with health, exit codes, compilation status
- `resources: ResourceUsage` with memory, disk, Docker image counts
- Computed properties: `total_tests`, `passed_tests`, `failed_tests`, `success_rate`

**Output directory structure:**
```
outputs/<experiment_date_name>/
  experiment.log                      # Main experiment log
  <test_name>/
    test.log                          # Per-test log
    logs/<service>.log                # Service logs
    analysis/
      analysis_results.json           # Tester pass/fail results
      service_health.json             # Per-service health data
    artifacts/                        # PCAPs, traces, etc.
  metrics*.json                       # Resource metrics
```

Use `StatusCollector(experiment_dir).collect_experiment_summary()` to build an `ExperimentSummary` from any experiment directory.

### Analysis Dashboard: ECharts

NiceGUI has built-in ECharts support via `ui.echart()`. The analysis dashboard uses:
- **Pie charts**: pass/fail/skip/timeout distribution per experiment
- **Bar charts**: test duration comparison
- **Line charts**: metrics over time (from `metrics*.json`)
- **Comparison tables**: side-by-side experiment results

```python
ui.echart({
    'xAxis': {'type': 'category', 'data': test_names},
    'yAxis': {'type': 'value'},
    'series': [{'data': durations, 'type': 'bar'}],
})
```

### Visual Topology Editor

The topology editor provides a drag-and-drop interface for composing experiment
configurations as a visual graph. This is **Muhammad's core thesis contribution**.

**Library Choice**: Muhammad evaluates both **vis.js Network** and **React Flow** analytically
(integration complexity, feature set, ecosystem, performance) and picks one. The comparison
becomes a thesis chapter. See `TASKS.md` Phase 1 for evaluation criteria.

**Current scaffold** uses vis.js (235 lines in `components/topology_editor.py`):

```
TopologyEditor (Python wrapper)
    ↕ JSON data: nodes, edges via ui.run_javascript()
    ↕ events: node-click, edge-click (CustomEvent dispatch)
vis.js Network (browser-side)
    → Canvas rendering, physics auto-layout, DataSet API
```

**If React Flow is chosen** instead, integration requires:
- Embedding React app via iframe or NiceGUI custom web component
- postMessage or REST API bridge for Python ↔ React communication
- npm/vite build step (breaks "no JS build" advantage of NiceGUI)
- Custom React components as graph nodes (richer UX but more complexity)

**Integration points (either library):**
- `set_graph(nodes, edges)` — Python → browser
- `get_graph()` — Browser → Python
- `on_node_click(callback)` — Click → Python handler → PydanticForm in side panel
- Export: topology graph → PANTHER YAML config (`ServiceConfig`, `TestConfig`)
- Import: PANTHER YAML config → topology graph

**Key features to implement:**
- Palette sidebar with drag-and-drop node creation (IUT, Tester, Environment)
- Edge creation with protocol labels (name, version, role)
- Properties panel: click node → PydanticForm renders ServiceConfig/ProtocolConfig
- YAML export/import matching `experiment-config/base/` format
- Validation: red borders on invalid nodes/edges
- Auto-layout via physics engine or hierarchical algorithm

**Files:**
- `components/topology_editor.py` — Python wrapper class (scaffolded, 235 lines)
- `pages/topology.py` — Topology page (scaffolded, 147 lines)
- `diagrams/04-topology-component-architecture.mmd` — Architecture diagram (Muhammad creates)
- `diagrams/05-yaml-graph-mapping.mmd` — YAML ↔ graph data mapping (Muhammad creates)

### UX Improvements (Parallel with Topology)

During topology implementation, Muhammad also improves the overall webapp UX:

- **Breadcrumbs**: All pages get breadcrumb navigation (e.g., Config > Test 1 > picoquic)
- **Workflow stepper**: Progress indicator showing Config → Topology → Launch → Results
- **"Next Step" buttons**: Contextual navigation between pages
- **Structured JSON viewer**: Replace raw JSON display with collapsible syntax-highlighted trees
- **Deep-links**: Results link back to the config that produced them

### Stretch Goals (Priority Order)

1. **CLI command integration**: Expose `panther config generate/validate`, `panther plugins params/check-deps`, `panther tools status` as webapp actions via `services/cli_service.py`
2. **Conformance matrix**: IUT × Test pass/fail grid aggregated across experiments
3. **Batch comparison**: Same test across multiple IUTs, side-by-side results
4. **Export for papers**: Charts/tables as CSV, LaTeX, SVG

See `TASKS.md` for full details and timeline.

## What Is NOT in Scope

| Feature | Reason |
|---------|--------|
| Two-way YAML sync | High complexity, one-way form-to-YAML is sufficient |
| Authentication / RBAC | Single-user tool, runs locally |
| PCAP viewer (embedded) | Would need Wireshark integration or custom parser |
| Resource monitoring (CPU/RAM) | Requires Docker stats API polling |
| Multi-user collaboration | Single-user tool |
| CI/CD integration API | CLI already serves this use case |
| Database backend | Config files + filesystem outputs are sufficient |

## How to Add a New Page

Follow this pattern when extending the webapp:

1. Create `panther/webapp/pages/my_page.py`:
```python
from nicegui import ui

def content():
    ui.label("My Page").classes("text-h5")
    # ... build UI here
```

2. Register in `panther/webapp/app.py`:
```python
from panther.webapp.pages import my_page

@ui.page('/my-page')
def my_page_route():
    with layout():
        my_page.content()
```

3. Add a sidebar link in `panther/webapp/components/layout.py`.

For pages that need data, create a service in `services/` that wraps core PANTHER classes.

## Service API Reference

Quick-reference tables for every service the webapp exposes. Use these when
wiring up a new page or component — they tell you what data is available
without reading the implementation.

### ConfigService (`services/config_service.py`)

| Method | Returns | Description |
|--------|---------|-------------|
| `get_default_yaml()` | `str` | Load default experiment config YAML template |
| `validate_yaml(yaml_content: str)` | `Optional[str]` | None if valid, error message if invalid |
| `yaml_to_dict(yaml_content: str)` | `Optional[dict]` | Parse YAML to dict, None on error |
| `dict_to_yaml(data: dict)` | `str` | Convert dict to YAML string |
| `load_config(path: str)` | `dict` | Load+parse YAML file (path-validated) |
| `save_config(path: str, data: dict)` | `None` | Save dict to YAML file (path-validated) |
| `list_configs(directory=None)` | `list[{name, path, modified}]` | List YAML files in directory |
| `list_configs_recursive(root=None)` | `list[{name, path, modified, category, summary}]` | Recursive list with summaries |
| `validate_config_detailed(data: dict)` | `list[FieldError]` | Field-level validation (path, message, severity) |
| `merge_configs(base: dict, overlay: dict)` | `dict` | Deep merge (overlay wins) |
| `resolve_interpolations(data: dict)` | `dict` | Resolve `${section.key}` templates |
| `generate_test_name(test_data: dict)` | `str` | Auto-generate test name from services/protocol |
| `generate_test_description(test_data: dict)` | `str` | Auto-generate test description |

### ExperimentService (`services/experiment_service.py`, singleton via `get_experiment_service()`)

| Method / Property | Returns | Description |
|-------------------|---------|-------------|
| `run_experiment(config_path: str)` | `async` | Run experiment in background thread |
| `stop()` | `None` | Request experiment stop |
| `status` (property) | `str` | Current status (Idle/Loading/Running/Completed/Failed/Stopped) |
| `log_lines` (property) | `list[str]` | Log buffer (max 10 000 lines) |
| `is_running` (property) | `bool` | Whether experiment is active |
| `register_callbacks(on_log, on_status)` | `None` | Register UI callbacks for live streaming |
| `unregister_callbacks(on_log, on_status)` | `None` | Unregister UI callbacks |
| `subscribe_events(callback)` | `None` | Subscribe to raw PANTHER BaseEvent objects |
| `unsubscribe_events(callback)` | `None` | Unsubscribe from events |
| `web_observer` (property) | `WebObserver` | Access the WebObserver instance |

### ResultsService (`services/results_service.py`)

| Method | Returns | Description |
|--------|---------|-------------|
| `list_experiments()` | `list[{date, name, path, test_count, status}]` | All experiments, newest first |
| `count_experiments()` | `int` | Count of experiments |
| `get_experiment_detail(name: str)` | `Optional[dict]` | Full detail: logs, report, artifacts, core_summary |
| `list_tests(experiment_path: str)` | `list[{name, status, duration, has_events, has_analysis, service_count}]` | Per-test summaries |
| `get_test_detail(experiment_path, test_name)` | `Optional[{info, services, analysis, artifacts}]` | Single test detail |
| `get_test_events(experiment_path, test_name)` | `list[dict]` | Parsed events.jsonl entries |
| `get_experiment_events(experiment_path)` | `list[dict]` | Top-level experiment events |
| `get_service_logs(experiment_path, test_name, service_name)` | `{phase: {stdout, stderr}}` | Per-phase log content |
| `get_analysis_results(experiment_path, test_name)` | `Optional[{filename: data}]` | JSON analysis files |
| `get_test_results(experiment_path)` | `list[dict]` | Chart-ready pass/fail/duration data |
| `get_service_health(experiment_path)` | `list[dict]` | Service health summaries |
| `get_aggregate_stats(experiment_path)` | `{total, passed, failed, success_rate, duration}` | Aggregate stats |
| `get_metrics_timeseries(experiment_path)` | `list[{timestamp, metric, value}]` | Normalized metrics for ECharts |

### PluginService (`services/plugin_service.py`)

| Method | Returns | Description |
|--------|---------|-------------|
| `list_plugins()` | `list[PluginMetadata]` | All discovered plugins (.name, .type, .description, .to_dict()) |
| `get_plugin_detail(name: str)` | `Optional[PluginMetadata]` | Single plugin by name |
| `get_plugin_manifest(name: str)` | `Optional[PluginManifest]` | Full manifest (license, homepage, config_schema, config_model) |

### WebObserver (`services/web_observer.py`)

| Method | Returns | Description |
|--------|---------|-------------|
| `subscribe(callback)` | `None` | Add event callback (receives BaseEvent) |
| `unsubscribe(callback)` | `None` | Remove event callback |
| Inherited: `get_event_history()` | `list[BaseEvent]` | Last 1000 events |
| Inherited: `get_gui_state()` | `dict` | Counters and timestamps per event type |

### PydanticForm Quick Reference

```python
from panther.webapp.components.pydantic_form import PydanticForm, FormConfig

# Render any Pydantic BaseModel as editable NiceGUI widgets
form = PydanticForm(LoggingConfig, config=FormConfig(section_style="card"))
data = form.get_value()      # Returns validated dict
form.set_value({"level": "DEBUG"})  # Populate from dict
```

`FormConfig` options: `section_style` (`"expansion"` / `"card"` / `"flat"`), `show_advanced` (bool), `css_prefix` (str).

### Improving the Scaffold

These services and components are a **starting scaffold** — Muhamad is expected to
improve, extend, and refine them as part of his thesis work. If something is missing,
unclear, or could be designed better, open a GitHub issue describing the gap and
proposed improvement. All changes go through GitHub pull requests with code review;
this review workflow is itself part of the thesis process. PRs should reference the
relevant issue and include a short design-rationale section so reviewers understand the
"why" behind each change.

## Future Evolution

After the thesis, potential improvements:
- **FastUI migration**: Pydantic's own `pydantic.dev/fastui` generates richer form UIs directly from models. This could complement or replace PydanticForm for more complex form scenarios.
- **Plugin UI extension**: Plugins contribute their own dashboard widgets via a registration API (e.g., `@register_plugin_widget()` decorator). Each plugin could provide a `webapp/` subdirectory with custom page components.
- **Live topology**: Real-time Docker container status visualization on the topology graph (nodes pulse when active, change color on failure).
- **Template library**: Pre-built topology templates for common test scenarios (QUIC conformance, HTTP interop).

## Key Files Reference

```
panther/config/core/models/
    global_config.py        # GlobalConfig, LoggingConfig, DockerConfig, PathsConfig
    experiment.py           # ExperimentConfig, TestConfig, StepsConfig
    service.py              # ServiceConfig, ImplementationConfig, ProtocolConfig
    environment.py          # NetworkEnvironmentConfig, ExecutionEnvironmentConfig

panther/core/
    experiment_manager.py   # ExperimentManager (central orchestrator)
    observer/
        impl/gui_observer.py        # GUIObserver base class (subclass this)
        base/observer_interface.py   # IObserver interface
        management/event_manager.py  # EventManager singleton
    events/base/event_base.py       # BaseEvent, EventType enum
    reporting/status_collector.py    # ExperimentSummary, TestResult, ServiceHealthSummary
    test_cases/analysis/output_analyzer.py  # Output collection and analysis
    metrics/                         # Metrics data model

panther/plugins/
    plugin_manager.py       # PluginManager (plugin discovery)

panther/cli_click/
    commands/web.py         # `panther web` Click command
    core/main.py            # CLI entry -- register_commands()
```
