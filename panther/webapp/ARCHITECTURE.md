# Architecture: PANTHER Web Dashboard

Design decisions and integration patterns for the NiceGUI-based webapp.

## Concepts Glossary

| Term | Definition |
|------|-----------|
| **Experiment** | A complete test run defined by a YAML config file. Contains one or more test scenarios, network setup, and service definitions. |
| **Test (scenario)** | A single test case within an experiment. Specifies which services participate, their protocol roles, and execution steps. |
| **IUT** | Implementation Under Test — the software being tested (e.g., a QUIC library like picoquic or aioquic). |
| **Tester** | A verification tool that checks IUT behavior (e.g., panther_ivy for formal verification). |
| **Service** | A running process in the experiment (either an IUT or a tester), typically deployed as a Docker container. |
| **Plugin** | A PANTHER extension that provides an IUT, tester, protocol, or environment implementation. Discovered at runtime via decorators. |
| **Protocol** | The network protocol being tested (e.g., QUIC, HTTP/3). Each service declares its protocol name, version, and role (server/client/peer). |
| **Network Environment** | The infrastructure layer for an experiment: Docker Compose (containers on a shared network), Shadow (network simulation), or localhost. |
| **EventManager** | PANTHER's central event bus. All experiment lifecycle events (test started, service crashed, metrics collected) flow through it. |
| **Observer** | A subscriber to EventManager events. The webapp's WebObserver bridges these events to browser components. |
| **PydanticForm** | A custom NiceGUI component that recursively renders any Pydantic BaseModel as editable form widgets. |
| **ExperimentManager** | The core orchestrator that runs the four-phase experiment lifecycle: initialization, plugin loading, deployment, execution. |

## Stack Choice

### Why NiceGUI (not Flask or Streamlit)

**Why this design?** The web framework choice was driven by three constraints that
PANTHER already imposes. Rather than building adapter layers for a general-purpose
framework, we chose the framework that natively satisfies all three:

1. **Pydantic models** for all configuration — GlobalConfig, TestConfig, ServiceConfig, etc. are Pydantic BaseModel subclasses that define the experiment YAML schema
2. **An event/observer system** that pushes state changes — BaseEvent objects flow through EventManager (the central event bus) to registered IObserver subscribers
3. **Long-running experiment processes** that need real-time progress updates — experiments can run for minutes with continuous event emission

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

PydanticForm (`panther/webapp/components/forms/pydantic_form.py`) is a custom recursive
form component that renders any `BaseModel` as editable NiceGUI widgets. It replaced
the external `niceguicrud` dependency.

```python
from panther.webapp.components.forms.pydantic_form import PydanticForm, FormConfig
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

**Why this design?** PANTHER's core classes (ExperimentManager, PluginManager,
ConfigurationManager) are designed for CLI usage — they block the calling thread,
raise raw exceptions, and assume single-threaded execution. The service layer
translates these into web-friendly interfaces: non-blocking calls, structured error
responses, and thread-safe state management. This separation also means page code
never needs to understand PANTHER internals — it only talks to services.

The webapp does NOT call PANTHER core classes directly from page code. Thin service wrappers provide an async-safe interface:

```
pages/experiments.py
    -> services/experiment_service.py
        -> panther.core.experiment_manager.ExperimentManager
```

| Service           | Wraps                            | Purpose                          |
|-------------------|----------------------------------|----------------------------------|
| ExperimentService | ExperimentManager (the central orchestrator that runs the four-phase experiment lifecycle) | Launch experiments in background threads, track status, stream live events |
| PluginService     | PluginManager (discovers and loads plugin implementations at runtime) | List available plugins, retrieve metadata and configuration schemas |
| ConfigService     | ConfigurationLoader, deep_merge (PANTHER's YAML loading and merge utilities) | Load/save/validate experiment YAML configs with path safety |
| ResultsService    | Filesystem (`outputs/` directory) | Browse past experiment results, parse logs, extract metrics for charts |

Stateless services (ConfigService, PluginService, ResultsService) are instantiated per-page-load. ExperimentService is a module-level singleton accessed via `get_experiment_service()`.

**Data flow through the service layer:**

```
┌─────────┐    ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐    ┌─────────────┐    ┌────┐
│  Page   │───>│   Service    │───>│   PANTHER Core   │───>│    Events    │───>│ WebObserver │───>│ UI │
│ (async) │    │  (thin wrap) │    │ (ExperimentMgr)  │    │ (EventMgr)  │    │ (callbacks) │    │    │
└─────────┘    └──────────────┘    └──────────────────┘    └──────────────┘    └─────────────┘    └────┘
  NiceGUI         async-safe            blocking              push-based          bridges           auto
  event loop      interface             (background           to observers        thread gap        WebSocket
  (main thread)                          thread)                                                    push
```

**Threading model:**
- **Main thread**: NiceGUI's asyncio event loop. All UI code runs here. Never block this thread.
- **Background thread**: Experiment execution runs via `asyncio.to_thread()` in `ExperimentService.run_experiment()`. The `ExperimentManager.run_tests()` call is blocking and can run for minutes.
- **Thread bridge**: `WebObserver.update_gui()` is called from the background thread. It iterates a copy of the subscription list (`list(self._subscriptions)`) under a lock to avoid race conditions. NiceGUI auto-pushes state changes to the browser over its WebSocket.

**Service composition:**
- **ConfigService**: Stateless. Load/validate/save YAML configs. Used by the config builder page and experiment launch.
- **ExperimentService**: Singleton (via `get_experiment_service()`). Manages experiment lifecycle, holds log buffer and status across page navigations. The only stateful service.
- **ResultsService**: Stateless. Reads from the `outputs/` filesystem. Used by the results and analysis pages.
- **PluginService**: Stateless. Wraps `PluginManager` for plugin discovery. Used by the plugins page and config builder (for implementation dropdowns).

Services do not call each other. Pages compose them: e.g., the experiment page uses both `ConfigService` (to validate before launch) and `ExperimentService` (to run).

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

**Why this design?** Experiments emit dozens of events per second (test started, service
health check, metrics collected, assertion passed). Rather than polling for status,
the webapp subscribes to PANTHER's existing observer system and receives push
notifications. This reuses the same event infrastructure that the CLI uses for
progress display, avoiding any duplication. The WebObserver adds filtering and
batching on top to prevent UI flooding.

PANTHER's observer system (`IObserver` -> `on_event(BaseEvent)`) is the integration point for live updates.

The webapp defines a `WebObserver` that subclasses `GUIObserver` (`panther/core/observer/impl/gui_observer.py`):

```python
# Simplified for illustration; see panther/webapp/infra/web_observer.py for the full API.
from panther.webapp.infra.web_observer import WebObserver, Subscription

observer = WebObserver()

# subscribe() returns a Subscription handle and supports per-subscriber filtering:
sub = observer.subscribe(
    callback,
    event_types={"test", "experiment"},  # optional: only these event categories
    importance=EventImportance.HIGH,     # optional: minimum importance threshold
    predicate=lambda e: ...,             # optional: arbitrary filter function
    batched=True,                        # default: participates in event batching
)

observer.unsubscribe(sub)  # remove by Subscription handle
```

When an experiment runs, the `WebObserver` is registered with `EventManager`. Every event flows through `on_event()` -> `update_gui()` -> subscribed NiceGUI components. NiceGUI auto-pushes state changes over its WebSocket, so the browser updates immediately.

`GUIObserver` provides built-in:
- Event history tracking (`get_event_history()`, max 1000 events)
- GUI state dict (`get_gui_state()` with counters and timestamps per event type)
- Automatic `_update_gui_state()` on every event

**Subscription lifecycle** for a NiceGUI page (actual pattern used by pages):
```python
# 1. Subscribe on page load via web_observer directly
experiment_svc = get_experiment_service()
sub = experiment_svc.web_observer.subscribe(
    handle_event,
    event_types={"test", "experiment"},
    importance=EventImportance.HIGH,
)

# 2. Filter and update UI using string-based event types
def handle_event(event: BaseEvent):
    event_type = event.get_type()  # returns e.g. "test.started", "experiment.completed"
    if event_type == "test.completed":
        update_test_progress(event)     # NiceGUI auto-pushes via WebSocket

# 3. Unsubscribe on client disconnect (prevent stale callbacks)
client.on_disconnect(
    lambda: experiment_svc.web_observer.unsubscribe(sub)
)
```

### Config Builder: PydanticForm + YAML Preview

**Why this design?** PANTHER experiment configurations are deeply nested YAML files
with cross-references between services. Editing raw YAML is error-prone; users forget
field names, misspell enum values, or create structurally invalid configs. PydanticForm
auto-generates type-safe forms from the same Pydantic models that validate the YAML,
ensuring the UI and validation logic are always in sync.

The config builder page has two panels:

1. **Left: PydanticForm forms** -- structured editing of GlobalConfig, TestConfig, ServiceConfig
2. **Right: YAML preview** -- live display updated from form changes via a periodic timer

**Sync directions:**
- **Forms -> YAML** (automatic): A timer periodically collects form values and updates the YAML preview.
- **YAML/file -> Forms** (on import/load): Users can import YAML text or load a config file, which populates forms via `_populate_forms_from_dict()`.

```
Form field change -> timer -> model.model_dump() -> yaml.dump() -> YAML preview
Import/Load YAML  -> parse -> _populate_forms_from_dict() -> form.set_value()
```

### Config Model Hierarchy

The Pydantic models form a tree that maps directly to the YAML structure. Understanding this hierarchy is essential for the config builder and topology editor.

```
ExperimentConfig                          # Top-level: one YAML file
├── metadata: ExperimentMetadata          # name, author, version, tags
└── tests: List[TestConfig]               # Each test = independent scenario
    ├── name: str                         # Test identifier
    ├── network_environment: NetworkEnvironmentConfig
    │   └── type: str                     # "docker_compose" | "shadow" | "localhost"
    ├── execution_environment: List[ExecutionEnvironmentConfig]
    ├── services: Dict[str, ServiceConfig]    # Key = service name (= container name)
    │   ├── implementation: ImplementationConfig
    │   │   ├── name: str                 # Plugin name (e.g., "picoquic")
    │   │   └── type: ImplementationType  # "iut" or "testers"
    │   ├── protocol: ProtocolConfig
    │   │   ├── name: str                 # e.g., "quic"
    │   │   ├── version: str              # e.g., "rfc9000"
    │   │   ├── role: ProtocolRole        # "server" | "client" | "peer"
    │   │   └── target: Optional[str]     # References another services dict key
    │   ├── network: Optional[NetworkConfig]  # interface, port, host
    │   └── depends_on: List[str]         # Startup ordering
    ├── steps: StepsConfig                # pre_commands, wait, post_commands
    └── iterations: int                   # How many times to repeat
```

**Graph-relevant fields** (for the topology editor):

| Config field | Graph concept | Notes |
|-------------|--------------|-------|
| `TestConfig` | Independent subgraph/group | Each test is a separate topology |
| `TestConfig.services[key]` | Node (key = label) | Dict key = Docker container name |
| `ImplementationType` | Node category (color/shape) | IUT = green, Tester = orange |
| `ProtocolConfig.role` | Node role badge | server/client/peer |
| `ProtocolConfig.target` | Directed edge (source→target) | Client points to server |
| `ProtocolConfig.name` + `version` | Edge label | e.g., "quic / rfc9000" |
| `NetworkEnvironmentConfig.type` | Group property or background | docker_compose, shadow, localhost |
| `ServiceConfig.depends_on` | Dashed dependency edge | Startup ordering |

These mapping rules are invariant regardless of which graph approach is chosen for the topology editor. The conversion logic between graph and config models is the core thesis contribution — see "Topology Design Reference" below for research context.

**Source files:** `panther/config/core/models/experiment.py`, `panther/config/core/models/service.py`

### Experiment Launch: asyncio.to_thread

`ExperimentManager.run_tests()` is blocking and can run for minutes. The webapp runs it via `asyncio.to_thread()`:

```python
async def run_experiment(self, config_path):
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
  experiment_events.log               # Main experiment event log
  <test_name>/
    test.log                          # Per-test log
    logs/<service_name>/<phase>/stdout.log  # Service logs (per phase)
    analysis/
      analysis_results.json           # Tester pass/fail results
      service_health.json             # Per-service health data
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

Protocol testing experiments are inherently graph-structured: services (nodes)
communicate via protocols (edges) within network environments (groups). A visual
editor makes this structure explicit. The topology editor is the **core thesis
contribution**.

The developer evaluates at least 3 visualization approaches and implements one:

1. **vis.js Network** — Mature JS graph library with built-in physics and manipulation
   API. Requires CDN + JavaScript bridge.
2. **React Flow** — React-based node editor with rich custom node support. Requires npm
   build step + iframe/webcomponent embedding.
3. **NiceGUI Native** — Pure SVG/ECharts approach using only NiceGUI built-in
   capabilities. Zero external dependencies but requires custom drag-and-drop
   implementation. Sub-options include SVG + custom JS for full editing, or
   `ui.echart()` Graph type for read-only visualization with force-directed layout.

The evaluation criteria, methodology, and final recommendation are the developer's
to define. This comparison becomes an analytical thesis chapter.

**Graph-relevant config fields** (see "Config Model Hierarchy" above for the full tree):

| Config field | Graph concept |
|-------------|--------------|
| `TestConfig.services[key]` | Node (key = label) |
| `ImplementationType` | Node category |
| `ProtocolConfig.target` | Directed edge (source→target) |
| `ProtocolConfig.name` + `version` | Edge label |
| `NetworkEnvironmentConfig.type` | Group property |
| `ServiceConfig.depends_on` | Dependency edge |

### UX Improvements (Parallel with Topology)

During topology implementation, the developer also improves the overall webapp UX:

- **Breadcrumbs**: All pages get breadcrumb navigation (e.g., Config > Test 1 > picoquic)
- **Workflow stepper**: Progress indicator showing Config → Topology → Launch → Results
- **"Next Step" buttons**: Contextual navigation between pages
- **Structured JSON viewer**: Replace raw JSON display with collapsible syntax-highlighted trees
- **Deep-links**: Results link back to the config that produced them
- **Polishing**: The scaffold is functional; remaining work involves edge-case handling, error message refinement, and responsive layout optimization.

### Stretch Goals (Priority Order)

1. **CLI command integration**: Expose `panther config generate/validate`, `panther plugins params/check-deps`, `panther tools status` as webapp actions via `services/cli_service.py`
2. **Conformance matrix**: IUT × Test pass/fail grid aggregated across experiments
3. **Batch comparison**: Same test across multiple IUTs, side-by-side results
4. **Export for papers**: Charts/tables as CSV, LaTeX, SVG

See `TASKS.md` for full details and timeline.

## Other Features Considered but HARD

| Feature | Reason |
|---------|--------|
| Full bidirectional YAML sync (keystroke-level) | Import/load covers most use cases; live keystroke sync adds complexity for marginal benefit |
| Authentication / RBAC | Single-user tool, runs locally |
| PCAP viewer (embedded) | Would need Wireshark integration or custom parser |
| Resource monitoring (CPU/RAM) | Requires Docker stats API polling |
| Multi-user collaboration | Single-user tool |
| CI/CD integration API | CLI already serves this use case |
| Database backend | Config files + filesystem outputs are sufficient |
