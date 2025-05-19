# Core Component — Code‑Level Reference 🏗️📚

> Location  `panther/core/` — last synced **May 2025**

This document is a **developer‑oriented reference** for every public
class, function, and module inside the **Core Component**.  It augments
the high‑level overview with **method signatures, data flows, and usage
snippets** so you can dive directly into the code‑base.

---

## 0  Module Map

| File                   | Public API                                     | Purpose                                                              |
| ---------------------- | ---------------------------------------------- | -------------------------------------------------------------------- |
| `experiment_manager.py`  | `ExperimentManager`                            | Top‑level orchestrator (validate → build → run → collect → teardown) |
| `test_case.py`         | `TestCase`                                     | Runtime wrapper for one `<tests[]>` entry; owns services + exec envs |
| `config_loader.py`     | `ConfigLoader`                                 | Merges plugin schemas & validates YAML                               |
| `registry.py`          | `PluginRegistry`                               | Discovers plugins; resolves them by `(category, type)`               |
| `container_builder.py` | `ContainerBuilder`                             | Build/pull Docker images; caches layers                              |
| `observer.py`          | `Observer`, `Event`                            | Publish–subscribe event bus (sync)                                   |
| `result_handler.py`    | `ResultHandler`                                | Persist artefacts/logs; can ZIP or DB‑store                          |
| `exceptions.py`        | `ConfigError`, `ContainerError`, `PluginError` | Typed error hierarchy                                                |

---

## 1  ExperimentManager

```python
class ExperimentManager:
    def __init__(self,
                 config_path: str,
                 *,
                 extra_observers: list[Observer] | None = None,
                 extra_result_handlers: list[ResultHandler] | None = None,
                 abort_on_error: bool = True):
        ...

    def run_tests(self) -> None:        # orchestrates all TestCases
    def teardown(self) -> None:         # stop containers, clean volumes
    def validate_config(self) -> None:  # raises ConfigError if invalid
```

### Key Attributes

| attr                   | type                  | description                      |
| ---------------------- | --------------------- | -------------------------------- |
| `self.cfg`             | `dict`                | Validated YAML tree              |
| `self.tests`           | `list[TestCase]`      | One object per `<tests[]>` entry |
| `self.registry`        | `PluginRegistry`      | Shared across TestCases          |
| `self.observers`       | `list[Observer]`      | Global + user‑supplied hooks     |
| `self.result_handlers` | `list[ResultHandler]` | Persist outputs                  |

### Happy‑Path Control Flow

1. `validate_config()` → `ConfigLoader.merge()` → raises on error.
2. For each YAML `test` → instantiate `TestCase(cfg, registry)`.
3. Emit `EXPERIMENT_START`.
4. Loop over `TestCase.run()`; each emits its own events.
5. Emit `EXPERIMENT_END`.
6. `teardown()` (unless `--no‑teardown`).

---

## 2  TestCase

```python
class TestCase:
    state: Literal["PENDING","RUNNING","COLLECTING","DONE","ERROR"]

    def setup(self) -> None:
        # build images (if flagged) & start containers
    def run(self) -> None:
        # honour steps & iterations; wrap commands in exec‑envs
    def collect(self) -> None:
        # ask ResultHandlers to flush artefacts
    def teardown(self) -> None:
```

### Composition Graph

```
TestCase
 ├─ NetworkEnv  (e.g. DockerComposeEnv)
 ├─ Service[]   (resolved via registry)
 ├─ ExecEnv[]   (strace, gperf, …)
 └─ Tester[]    (optional Ivy)
```

Each **step** (from YAML) is executed inside the container context; the
`iterations` field wraps the full `run()` call multiple times.

---

## 3  ConfigLoader

```python
class ConfigLoader:
    def __init__(self, path: str, registry: PluginRegistry):
    def load(self) -> dict:      # merged & validated config tree
```

* Uses **Cerberus** or **pydantic** models provided by each plugin’s
    `config_schema.py`.
* Supports `!include` and YAML anchors.

---

## 4  PluginRegistry

```python
class PluginRegistry:
    def register_dir(self, path: Path) -> None
    def resolve(self, category: str, ptype: str):  # returns plugin class
```

Categories presently known: `network_environment`, `execution_environment`,
`services/iut`, `services/testers`, `protocols`, `webapp`.

---

## 5  Observer & Event

```python
@dataclass
class Event:
    name: str           # e.g. "TEST_START"
    timestamp: float
    payload: dict[str, Any] = field(default_factory=dict)

class Observer(ABC):
    def notify(self, event: Event) -> None: ...
```

Built‑in observers: `ConsoleLogger`, `WebsocketBroadcaster` (web‑app).

---

## 6  ResultHandler

```python
class ResultHandler(ABC):
    def flush_test(self, tc: TestCase): ...   # per‑test
    def finalize(self): ...                   # end‑of‑experiment
```

Default: `FileResultHandler` writes logs to `outputs/…`; custom handlers
can push to an SQL DB or S3.

---

## 7  ContainerBuilder

```python
class ContainerBuilder:
    def build(self, image_tag: str, context: Path, dockerfile: str) -> str
    def ensure(self, image_tag: str) -> str        # pull or build
```

Uses **docker‑python SDK**; caches contexts under `.panther/cache/`.

---

## 8  Exceptions

| Exception        | Raised by                              | Typical Cause                 |
| ---------------- | -------------------------------------- | ----------------------------- |
| `ConfigError`    | `ConfigLoader`                         | Missing / invalid YAML key    |
| `ContainerError` | `ContainerBuilder`, `TestCase.setup()` | Docker build/run failure      |
| `PluginError`    | `PluginRegistry`                       | Duplicate or malformed plugin |

---

## 9  Event Sequence Diagram (Simplified)

```
ExperimentManager.run_tests()
 └─▶ EVENT: EXPERIMENT_START
     └─▶ for TestCase in self.tests:
         ├─▶ EVENT: TEST_START
         │   └─▶ TestCase.setup()
         │   └─▶ TestCase.run()
         │       ├─▶ EVENT: STEP_START
         │       └─▶ EVENT: STEP_END
         └─▶ TestCase.collect()
             └─▶ EVENT: RESULT_READY
└─▶ EVENT: EXPERIMENT_END
```

Observers *synchronously* receive events; long tasks should be off‑loaded.

---

## 10  Extending the Core

| Task                         | Hook                                                                                            |
| ---------------------------- | ----------------------------------------------------------------------------------------------- |
| New observer                 | Subclass `Observer`; pass via `extra_observers` or place in an observer dir + `--observer-dir`. |
| Alternate result backend     | Subclass `ResultHandler`; register via registry.                                                |
| Custom plugin discovery path | CLI: `--net-env-dir`, `--exec-env-dir`, `--iut-dir`, `--tester-dir`.                            |

> **Reminder:** Core never imports plugin code directly; it relies on the
> registry so adding a plugin *never* requires editing core files.

---

## 11  Quick Snippets

### Programmatic usage

```python
from panther.core.manager import ExperimentManager
mgr = ExperimentManager("experiment.yaml")
try:
    mgr.run_tests()
finally:
    mgr.teardown()
```

### Custom Observer

```python
class SlackNotifier(Observer):
    def notify(self, event):
        if event.name == "EXPERIMENT_END":
            send_slack("Experiment finished ✔️")

ExperimentManager("exp.yaml", extra_observers=[SlackNotifier()]).run_tests()
```

---

## 12  Troubleshooting Quick‑Ref

| Symptom                      | Check                                                     |
| ---------------------------- | --------------------------------------------------------- |
| `ConfigError: unknown field` | Typo in YAML, or plugin not installed.                    |
| Docker rebuilds every run    | Set `docker.build_docker_image: false` after first build. |
| Observer blocks core         | Move heavy work to a thread/async task.                   |
| Shadow sim hangs             | Topology too large; raise resources or reduce nodes.      |

---

## 13  Recap

* **ExperimentManager** drives the show; **TestCase** encapsulates each
  YAML experiment.
* Config → Build → Run → Collect → Teardown, emitting events along the
  way.
* Observers + ResultHandlers are the key extension points.
* Core never needs edits to support new protocols, services, or profilers
  — those live entirely in plugins.

Happy experimentations inside **panther/core/**!  🎉
