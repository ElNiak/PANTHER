# Task 17: Scaffold panther.api Module

## Goal
Create the `panther/api/` package inside the panther repo with `__init__.py` and empty module files.

## Prerequisites
- Task 14 completed (Phase 2 verified)

## Context
`panther.api` is a thin facade API layer inside panther that panther_web (and future clients) consume. It wraps existing managers (ConfigurationManager, PluginManager, ExperimentManager, EventManager) without exposing internal complexity.

This module lives INSIDE the panther package (not a separate package) because it depends on heavy panther internals.

## Existing Foundation
Before implementing, read these files to understand what already exists:
- `panther/webapp/web_app.py` - Legacy Flask app with API endpoints (prior art)
- `panther/config/core/mixins/__init__.py` - ConfigurationManager 8-mixin composition
- `panther/plugins/core/plugin_manager.py` - PluginManager singleton
- `panther/core/experiment_manager.py` - ExperimentManager facade

## Steps

### Step 1: Create directory structure
```bash
mkdir -p panther/api
```

### Step 2: Create __init__.py

```python
# panther/api/__init__.py
"""PANTHER Public API.

This module provides a clean, stable API surface for external consumers
(panther_web, scripts, integrations) to interact with PANTHER functionality
without depending on internal implementation details.

Modules:
    config: Configuration loading, validation, saving, schema generation
    plugins: Plugin discovery, metadata, config schemas
    experiments: Experiment lifecycle (create, launch, monitor, stop, results)
    docker: Docker image and container operations
    events: Event subscription and streaming
    schemas: JSON Schema generation for frontend form building

Usage:
    from panther.api import config, plugins, experiments

    # Load and validate a config
    cfg = config.load_config("path/to/config.yaml")
    result = config.validate_config(cfg)

    # List available plugins
    available = plugins.list_plugins()

    # Launch an experiment
    exp_id = experiments.create_experiment(cfg)
    experiments.launch_experiment(exp_id)
"""
```

### Step 3: Create empty module files

```python
# panther/api/config.py
"""Configuration operations.

Wraps ConfigurationManager to provide config loading, validation,
saving, merging, and schema generation.
"""

# panther/api/plugins.py
"""Plugin discovery operations.

Wraps PluginManager to provide plugin listing, info retrieval,
config schema access, and protocol/environment enumeration.
"""

# panther/api/experiments.py
"""Experiment lifecycle operations.

Wraps ExperimentManager to provide experiment creation, launch,
monitoring, stopping, and results retrieval.
"""

# panther/api/docker.py
"""Docker operations.

Wraps Docker builder to provide image listing, building,
and container lifecycle management.
"""

# panther/api/events.py
"""Event subscription and streaming.

Wraps EventManager to provide event subscription, callback
registration, and async event streaming.
"""

# panther/api/schemas.py
"""JSON Schema generation.

Generates JSON Schemas from Pydantic models for frontend
form building and validation.
"""
```

## Verification
```bash
# Verify module structure
python -c "
import panther.api
import panther.api.config
import panther.api.plugins
import panther.api.experiments
import panther.api.docker
import panther.api.events
import panther.api.schemas
print('All modules importable: OK')
"
```

## Commit Message
```
feat: scaffold panther.api module structure

Create panther/api/ package with empty modules for config, plugins,
experiments, docker, events, and schemas. This will serve as the
public API surface for panther_web and external integrations.
```

## Files Created
- `panther/api/__init__.py`
- `panther/api/config.py`
- `panther/api/plugins.py`
- `panther/api/experiments.py`
- `panther/api/docker.py`
- `panther/api/events.py`
- `panther/api/schemas.py`
