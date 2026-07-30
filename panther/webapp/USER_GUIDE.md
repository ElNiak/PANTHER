# PANTHER Webapp User Guide

This guide explains how to install PANTHER from source, start the web
application, understand the main pages, and run the webapp test suites.

## Dependencies

PANTHER and the webapp require:

- Linux or macOS
- Docker v27 or higher
- Python 3.10 or higher
- pip
- Git
- A modern browser such as Chrome, Firefox, or Edge

Docker is required for running real protocol experiments. The webapp UI can be
started and explored without running an experiment.

`pyproject.toml` is the source of truth for Python dependencies and project
metadata. The webapp installation includes NiceGUI, Uvicorn, WebSocket support,
and the PANTHER core dependencies.

Install PANTHER From Source

Clone the source repository and create a virtual environment:

```bash
git clone --recurse-submodules https://github.com/umer901/PANTHER.git
cd PANTHER
git submodule update --init --recursive

python3 -m venv .venv
source .venv/bin/activate
```

Install PANTHER and the webapp dependencies in editable mode:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install --editable ".[web]"
```

If you need the Ivy tester plugin from the included submodule, install it too:

```bash
python3 -m pip install --editable panther/plugins/services/testers/panther_ivy
```

Side notes:

- Some systems provide the Python executable as `python` instead of `python3`.
  Use whichever command points to Python 3.10 or newer.
- If your shell has the current directory on `PATH`, the builder script may try
  to execute the local `panther/` package directory before the installed
  `panther` CLI. In that case, use the direct `pip install --editable ".[web]"`
  command above, or run the installed CLI explicitly as `.venv/bin/panther`.
- If dependency installation fails with DNS or connection errors, retry from an
  environment with network access to PyPI.

Run these builder commands:

```bash
python3 panther_builder.py --help
python3 panther_builder.py package-dev
python3 panther_builder.py check
python3 panther_builder.py docs
python3 panther_builder.py clean
```

Verify the CLI is available:

```bash
panther --help
panther web --help
```

## Run The Webapp

From the repository root, start the server:

```bash
panther web
```

The webapp starts at:

```text
http://localhost:8080
```


## Webapp Pages

The sidebar provides access to the main webapp pages:

- **Dashboard** (`/`): shows a high-level overview, status cards, recent
  activity, and quick navigation actions.
- **Config Builder** (`/config`): builds, loads, imports, validates, edits,
  exports, and saves PANTHER YAML experiment configurations.
- **Topology Editor** (`/topology`): loads a configuration and visualizes the
  experiment topology as either a full config overview or a per-test graph.
- **Experiments** (`/experiments`): selects a configuration, launches an
  experiment, shows progress, streams logs, and displays live events.
- **Results** (`/results`): lists experiment results, supports filtering and
  search, and opens detailed result views with summaries, tests, logs, events,
  metrics, and artifacts.
- **Plugins** (`/plugins`): browses installed plugins, filters by plugin type,
  searches plugin metadata, and opens plugin detail views.

## Run The Tests

The webapp tests are described in `panther/webapp/test_report.md`.

Run these commands from the repository root. If you are still in
`panther/webapp`, return to the root first:

```bash
cd ../..
```

Install the test dependencies once before running the test suites:

```bash
python3 -m pip install --editable ".[tests,web]"
```

Run the topology-focused unit tests:

```bash
.venv/bin/pytest tests/unit/test_webapp/test_topology_service.py tests/unit/test_webapp/test_topology_renderer_navigation.py -q -c pyproject.toml -n0 --no-cov
```

Run all webapp unit tests:

```bash
.venv/bin/pytest tests/unit/test_webapp -q -c pyproject.toml -n0 --no-cov
```

Run the browser integration tests:

```bash
.venv/bin/pytest tests/integration/test_config_builder_browser.py tests/integration/test_dashboard_browser.py tests/integration/test_experiments_browser.py tests/integration/test_plugins_browser.py tests/integration/test_pydantic_form_browser.py tests/integration/test_results_browser.py -q -c pyproject.toml -n0 --no-cov
```

Run the full webapp E2E tests:

```bash
.venv/bin/pytest tests/e2e/test_webapp_e2e.py -q -c pyproject.toml -n0 --no-cov
```

Browser integration tests require Chrome and ChromeDriver. If ChromeDriver exits
with status 127 on Ubuntu, install or extract the missing Chrome runtime
libraries before running the integration suite.
