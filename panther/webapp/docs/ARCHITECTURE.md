# Architecture: PANTHER Web Dashboard

Design decisions and integration patterns for the NiceGUI-based webapp.

## Stack Choice

### Why NiceGUI (not Flask, FastUI, or Streamlit)

PANTHER already has:
1. **Pydantic models** for all configuration (GlobalConfig, TestConfig, ServiceConfig, etc.)
2. **An event/observer system** that pushes state changes (BaseEvent -> EventManager -> IObserver)
3. **Long-running experiment processes** that need real-time progress updates

NiceGUI is the only framework in the evaluation that satisfies all three constraints with minimal glue code:

| Requirement                      | Flask         | Streamlit     | FastUI       | NiceGUI       |
|----------------------------------|---------------|---------------|--------------|---------------|
| Forms from Pydantic models       | Manual WTForms | st.form()    | Built-in     | Via NiceCRUD  |
| WebSocket push (server -> browser) | flask-socketio + JS | Rerun model | SSE only   | Built-in      |
| Long-running background tasks    | Celery/threading | Blocking    | Custom       | asyncio native|
| Pure Python (no JS build step)   | No (Jinja+JS) | Yes           | No (React)   | Yes           |
| FastAPI underneath               | No            | No            | Yes          | Yes           |

The legacy Flask webapp (`_legacy/web_app.py`) required Jinja templates, WTForms field generation from dataclasses, custom JavaScript for every dynamic UI element, and manual WebSocket plumbing. NiceGUI eliminates all of these.

### NiceCRUD for Config Forms

NiceCRUD takes a Pydantic model class and produces a complete CRUD interface (create/read/update/delete forms, table views, validation). Since PANTHER config models are already Pydantic (GlobalConfig, LoggingConfig, DockerConfig, TestConfig, ServiceConfig, ProtocolConfig, etc.), NiceCRUD generates forms with zero extra code.

Example of what this looks like in practice:

```python
from niceguicrud import NiceCRUD
from panther.config.core.models.global_config import LoggingConfig

crud = NiceCRUD(LoggingConfig, prefix="/config/logging")
# This gives you create/edit forms, validation, and a table -- all auto-generated.
```

For nested models (TestConfig contains ServiceConfig contains ProtocolConfig), you compose multiple NiceCRUD instances or use NiceGUI's `ui.expansion` to nest form sections.

## How NiceGUI Integrates with PANTHER Core

### Service Layer Pattern

The webapp does NOT call PANTHER core classes directly from page code. Instead, thin service wrappers provide an async-safe interface:

```
pages/experiments.py
    -> services/experiment_service.py
        -> panther.core.experiment_manager.ExperimentManager
```

Each service wraps exactly one core manager:

| Service               | Wraps                              | Purpose                           |
|-----------------------|------------------------------------|-----------------------------------|
| ExperimentService     | ExperimentManager                  | Launch experiments, track status   |
| PluginService         | PluginManager                      | List plugins, get metadata         |
| ConfigService         | ConfigurationManager               | Load/save/validate YAML configs    |
| ResultsService        | (filesystem: outputs/ directory)   | Browse and read experiment results |

Services are instantiated once in `app.py` and passed to pages via NiceGUI's `app.storage` or function parameters.

### Page Architecture

Each page is a Python function decorated with `@ui.page('/path')`. NiceGUI calls the function when a user navigates to that path. The function builds the UI using NiceGUI component calls.

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

There is no template engine, no HTML files, no JavaScript. The UI is declared in Python and NiceGUI translates it to Vue/Quasar components, pushing updates over a WebSocket.

### Real-Time Updates: WebObserver

PANTHER's observer system (IObserver -> on_event(BaseEvent)) is the integration point for live updates.

The webapp defines a `WebObserver` that subclasses `GUIObserver`:

```python
# services/experiment_service.py (conceptual)
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

When an experiment is running, the `WebObserver` is registered with the `EventManager`. Every event (test started, test completed, service error, etc.) flows through `on_event()` -> `update_gui()` -> subscribed NiceGUI components. Because NiceGUI auto-pushes state changes over its WebSocket, the browser updates immediately with no polling.

Event types from `panther/core/events/`:
- `experiment.*` -- experiment lifecycle (started, completed, failed)
- `test.*` -- individual test progress
- `service.*` -- service start/stop/error
- `environment.*` -- Docker environment events
- `step.*` -- pre/post command execution
- `metrics.*` -- performance data points

### Config Builder: NiceCRUD + YAML Sync

The config builder page has two panels:

1. **Left: NiceCRUD forms** -- structured editing of GlobalConfig, TestConfig, ServiceConfig
2. **Right: YAML editor** -- CodeMirror-based text editor (`ui.codemirror` with YAML mode)

Changes in the form update the YAML preview. Edits in the YAML editor parse back into the Pydantic model and update the form. This two-way sync uses NiceGUI's binding system:

```
Form field change -> Pydantic model.model_dump() -> yaml.dump() -> YAML editor value
YAML editor change -> yaml.safe_load() -> Pydantic model(**data) -> form field values
```

Validation errors from Pydantic surface immediately in the form as field-level error messages.

### Experiment Launch: Background Thread

`ExperimentManager.run_tests()` is a blocking call that can run for minutes or hours. The webapp runs it in a background thread:

```python
import threading

def launch_experiment(config, observer):
    manager = ExperimentManager(global_config=config)
    manager.event_manager.register_observer(observer)
    thread = threading.Thread(target=manager.run_tests, daemon=True)
    thread.start()
    return thread
```

The `WebObserver` receives events from the background thread and pushes them to the browser via NiceGUI's auto-sync. The experiments page shows a progress bar and log viewer that update in real time.

## What Is Explicitly NOT in Scope

These features are cut from the MVP to keep the project achievable in ~10 working weeks:

| Feature                    | Reason for cutting                                          |
|----------------------------|-------------------------------------------------------------|
| Drag-and-drop topology     | High complexity, marginal value over form-based config      |
| Authentication / RBAC      | Single-user tool, runs locally                              |
| PCAP viewer (embedded)     | Would need Wireshark integration or custom parser           |
| Resource monitoring (CPU/RAM) | Requires Docker stats API polling, out of scope           |
| Multi-user collaboration   | Single-user tool                                            |
| Custom dashboard widgets   | Nice-to-have, not core functionality                        |
| CI/CD integration API      | CLI already serves this use case                            |
| HTTPS / TLS               | Local dev tool, unnecessary complexity                       |
| Database backend           | Config files + filesystem outputs are sufficient            |
| Formal verification trace viewer | Highly specialized, would need custom renderer         |

If time permits after Week 10, the most impactful additions would be: (1) a basic results comparison view and (2) config file import/export.

## Key Files Reference

Core PANTHER files the webapp integrates with:

```
panther/config/core/models/
    global_config.py        # GlobalConfig, LoggingConfig, DockerConfig, etc.
    experiment.py           # ExperimentConfig, TestConfig, StepsConfig
    service.py              # ServiceConfig, ImplementationConfig, ProtocolConfig
    environment.py          # NetworkEnvironmentConfig, ExecutionEnvironmentConfig

panther/core/
    experiment_manager.py   # ExperimentManager -- the central orchestrator
    observer/
        impl/gui_observer.py    # GUIObserver base class (subclass this)
        base/observer_interface.py  # IObserver interface
        management/event_manager.py # EventManager singleton
    events/
        base/event_base.py  # BaseEvent, EventType enum
        experiment/          # Experiment lifecycle events
        test/                # Test execution events
        service/             # Service lifecycle events

panther/plugins/
    plugin_manager.py       # PluginManager -- plugin discovery and metadata

panther/cli_click/
    commands/web.py         # `panther web` Click command
    core/main.py            # CLI entry -- register_commands() loads commands
```
