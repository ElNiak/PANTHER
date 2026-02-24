# PANTHER Test Suite

## Overview

Tests for the PANTHER framework covering core functionality, plugin system, CLI,
configuration parsing, event handling, and Docker-based experiment execution.
Tests are organized by type (unit, integration, e2e, property-based, performance)
with the bulk of active tests under `tests/unit/`.

## Test Structure

```text
tests/
├── conftest.py                          # Root fixtures
├── unit/                                # Fast tests, no external dependencies
│   ├── observers/                       # Observer pattern tests
│   ├── plugins/                         # Plugin system tests
│   │   ├── environments/                # Network & execution environment plugins
│   │   │   ├── execution_environment/   # Helgrind, memcheck, strace, gperf, iterations
│   │   │   └── network_environment/     # Localhost, Shadow NS resolvers
│   │   └── services/                    # Service template & command generation
│   ├── test_cli/                        # CLI command tests
│   ├── test_config/                     # Configuration parsing & validation
│   ├── test_core/                       # Core framework (docker builder, commands, etc.)
│   ├── test_events/                     # Event system tests
│   ├── test_plugins/                    # Plugin discovery & registration
│   ├── test_refactoring/                # Refactoring regression tests
│   ├── test_config_inheritance.py
│   ├── test_docker_version.py
│   ├── test_event_manager_singleton.py
│   ├── test_import_health.py
│   ├── test_non_critical_commands.py
│   ├── test_plugin_manager_singleton.py
│   └── test_structure_debug.py
├── cli_click/                           # Click CLI unit & integration tests
│   ├── unit/core/                       # CLI base & main entry
│   └── unit/commands/                   # Individual command tests
├── functional/                          # Placeholder resolution & failure scenarios
├── integration/                         # Tests requiring Docker
├── e2e/                                 # End-to-end workflow tests
├── property_based/                      # Hypothesis property-based tests
├── performance/                         # Benchmark & performance tests
├── builder/                             # Build system tests
├── config/                              # Additional config tests
├── core/                                # Additional core tests
├── documentation/                       # CLI help output tests
├── fixtures/                            # Shared test utilities
├── load/                                # Concurrent experiment tests
├── mutation/                            # Mutation testing
├── plugins/                             # Additional plugin tests
├── test_packaging/                      # Packaging & migration tests
├── tests_ressources/                    # Test data files
└── visual/                              # Visual regression tests
```

Standalone test files at the `tests/` root cover specific areas such as
Docker Compose environments, network protocols, Ivy commands, security,
metrics, and filesystem operations.

## Running Tests

```bash
# Unit tests (fast, no external dependencies)
pytest tests/ -m unit

# Integration tests (requires Docker)
pytest tests/ -m integration

# With coverage enforcement
pytest tests/ --cov=panther --cov-fail-under=70

# Specific directory
pytest tests/unit/test_core/ -v

# Single test file
pytest tests/unit/test_core/test_docker_builder_tag_generation.py -v

# Property-based tests
pytest tests/ -m property

# Click CLI tests
pytest tests/cli_click/ -v
```

## Test Markers

Defined in `pyproject.toml` under `[tool.pytest.ini_options]`:

| Marker             | Description                              |
|--------------------|------------------------------------------|
| `unit`             | Fast, no external dependencies           |
| `integration`      | May require Docker                       |
| `e2e`              | Full workflow tests                      |
| `property`         | Property-based tests using Hypothesis    |
| `requires_docker`  | Tests that require Docker to be running  |
| `requires_network` | Tests that require network access        |
| `requires_ivy`     | Tests that require Ivy tester            |
| `slow`             | Tests that take more than 10 seconds     |
| `critical`         | Critical functionality tests             |

## Coverage

- **Minimum threshold**: 70% (configured via `--cov-fail-under=70` in `pyproject.toml`)
- **Source**: `panther/` package with branch coverage enabled
- **Reports**: terminal (with missing lines), HTML, and XML

Coverage configuration is in `pyproject.toml` under `[tool.coverage.run]` and
`[tool.coverage.report]`.

## Writing New Tests

- Place unit tests in `tests/unit/` under the appropriate subdirectory.
- Use `@pytest.mark.unit` for fast tests with no external dependencies.
- Use `@pytest.mark.requires_docker` for tests that need Docker.
- Use `@pytest.mark.property` for Hypothesis-based tests.
- Follow existing naming convention: `test_<module_name>.py`.
- Use fixtures from `conftest.py` files in each directory.
- Keep unit tests isolated -- mock external services and Docker calls.

## Known Issues

- Some test collection errors exist for modules referencing the legacy
  `panther.config.config_manager` or old `panther.cli` (pre-Click migration).
- Shadow resolver tests may fail due to positional argument handling with
  Pydantic BaseModel.
- `test_command_generation_utils.py` has pre-existing failures related to
  logger format assertions.
