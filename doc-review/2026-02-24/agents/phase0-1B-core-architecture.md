# Phase 0 - Dispatch 1B: Core Architecture Documentation Evidence

**Agent:** doc-miner-evidence-gatherer
**Status:** COMPLETE
**Files Analyzed:** panther/core/README.md, DEVELOPER_GUIDE.md, api_reference.md, adr/README.md, tutorial/quickstart.md

## Confirmed Broken Links (6 total)

| Link | Source | Status |
|------|--------|--------|
| `EXPERIMENT_ENGINE.md` | core/README.md:47 | BROKEN - file does not exist |
| `../../EXPERIMENT_REPORTING.md` | core/README.md:53 | BROKEN - file does not exist |
| `../cli/adr/0001-command-pattern-architecture.md` | core/adr/README.md:18 | BROKEN - panther/cli/ deleted |
| `../cli/adr/0002-error-handling-exit-codes.md` | core/adr/README.md:19 | BROKEN - panther/cli/ deleted |
| `../cli/adr/0003-interactive-component-architecture.md` | core/adr/README.md:20 | BROKEN - panther/cli/ deleted |
| `../config/adr/0001-hybrid-pydantic-omegaconf-architecture.md` | core/adr/README.md:34 | BROKEN - panther/config/adr/ missing |

## Critical API Reference Inaccuracies

### ExperimentManager
| Documented | Actual | Severity |
|-----------|--------|----------|
| `run_tests()` returns `Dict[str, Any]` | Returns `bool` | CRITICAL |
| `add_observer(observer)` method exists | Method does not exist | CRITICAL |
| Properties `experiment_dir`, `test_cases`, etc. | Plain attributes, not @property | MAJOR |
| `ExperimentManager.from_config()` classmethod | Does not exist | MAJOR |
| Strategy pattern for plugin delegation | Code docstring says Facade pattern | MINOR |

### TestCase
| Documented | Actual | Severity |
|-----------|--------|----------|
| 6 mixin names: Configuration, Execution, Analysis, Observer, Reporting, Docker | Actual: Base, ServiceManagement, EnvironmentManagement, TestExecution, Metrics, ObserverManagement | CRITICAL |
| States: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED | Actual: PENDING, RUNNING, COLLECTING, DONE, ERROR | MAJOR |
| `TestCaseState` enum class | Does not exist; uses string literals | MAJOR |

### EventManager
| Documented | Actual | Severity |
|-----------|--------|----------|
| `emit(event)` method | Method is `notify(event)` | CRITICAL |
| `subscribe(event_type, handler)` | Method is `register_observer(...)` | CRITICAL |
| `unsubscribe(event_type, handler)` | Method is `unregister_observer(...)` | CRITICAL |

### Other
| Documented | Actual | Severity |
|-----------|--------|----------|
| `GlobalConfig` is a dataclass with `load()` | Pydantic model, no `load()` | MAJOR |
| Python >=3.9 requirement | Actually >=3.10 | MINOR |
| Coverage threshold >90% | Actually 70% (per pyproject.toml) | MINOR |
| `from panther.core.events.base import EventBase` | Actual class is `BaseEvent` | MAJOR |
| Observer base class is `Observer` with `handle_event()` | Actual is `IObserver` with `on_event()` | MAJOR |

## README Module Tree Inaccuracies
- Missing from tree: `exceptions/`, `state/`, `outputs/`, `template/`
- Listed but doesn't exist: `workflow/` (actually at `observer/workflow/`)
- command_processor flat files wrong (actual has subdirs: builders/, core/, models/, utils/, mixins/)

## Four-Phase Model Inconsistency
- README.md, experiment_manager.py docstring, and CLAUDE.md each describe different phase breakdowns
- No single authoritative version
