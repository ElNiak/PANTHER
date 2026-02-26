# Task 19: Implement panther.api experiments and docker Modules

## Goal
Implement `panther/api/experiments.py` and `panther/api/docker.py` as thin facades wrapping ExperimentManager and Docker builder.

## Prerequisites
- Task 17 completed (module scaffolded)

## Source Files to Read

### For experiments.py:
- `panther/core/experiment_manager.py` - ExperimentManager facade (central orchestrator)
- `panther/core/test_cases/` - Test execution logic
- `panther/webapp/web_app.py` - Existing endpoints: POST /api/run-experiment, GET /api/experiments

### For docker.py:
- `panther/core/docker_builder/` - Docker orchestration module
- `panther/plugins/services/mixins/service_manager_docker_mixin.py` - Docker build mixin

## Steps

### Step 1: Implement experiments.py

```python
# panther/api/experiments.py
"""Experiment lifecycle operations.

Wraps ExperimentManager to provide experiment creation, launch,
monitoring, stopping, and results retrieval.
"""
from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional


def create_experiment(config: Any) -> str:
    """Create an experiment from a validated configuration.

    Args:
        config: Validated ExperimentConfig object.

    Returns:
        experiment_id (str) - unique identifier for tracking.
    """
    # Read ExperimentManager and implement
    pass


def launch_experiment(experiment_id: str) -> None:
    """Launch an experiment asynchronously.

    The experiment runs in the background. Use get_status() or
    event_stream() to monitor progress.

    Args:
        experiment_id: ID returned by create_experiment().

    Raises:
        KeyError: If experiment_id not found.
        RuntimeError: If experiment already running.
    """
    pass


def get_status(experiment_id: str) -> Dict[str, Any]:
    """Get current status of an experiment.

    Args:
        experiment_id: ID returned by create_experiment().

    Returns:
        Dict with keys: status, phase, progress, started_at, elapsed,
        current_test, tests_completed, tests_total.
    """
    pass


def stop_experiment(experiment_id: str) -> None:
    """Stop a running experiment gracefully.

    Triggers cleanup and teardown of all services and environments.

    Args:
        experiment_id: ID returned by create_experiment().
    """
    pass


def list_experiments() -> List[Dict[str, Any]]:
    """List all known experiments (active and historical).

    Returns:
        List of dicts with: id, config_name, status, created_at,
        completed_at, test_count.
    """
    pass


def get_results(experiment_id: str) -> Dict[str, Any]:
    """Get results of a completed experiment.

    Args:
        experiment_id: ID returned by create_experiment().

    Returns:
        Dict with: tests (list of test results), summary,
        output_dir, duration.

    Raises:
        RuntimeError: If experiment is still running.
    """
    pass
```

### Step 2: Implement docker.py

```python
# panther/api/docker.py
"""Docker operations.

Wraps Docker builder for image listing, building, and container management.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def list_images() -> List[Dict[str, Any]]:
    """List Docker images relevant to PANTHER.

    Returns:
        List of dicts with: name, tag, size, created, id.
    """
    pass


def build_image(
    service_name: str,
    config: Any,
    force: bool = False,
    no_cache: bool = False,
) -> Dict[str, Any]:
    """Build a Docker image for a service.

    Args:
        service_name: Name of the service to build.
        config: Service configuration (for Dockerfile selection, build args).
        force: Force rebuild even if image exists.
        no_cache: Disable Docker build cache.

    Returns:
        Dict with: image_name, tag, build_time, success, logs.
    """
    pass


def get_build_status(build_id: str) -> Dict[str, Any]:
    """Get status of an ongoing Docker build.

    Args:
        build_id: Build identifier.

    Returns:
        Dict with: status, progress, current_step, logs.
    """
    pass


def remove_image(image_name: str) -> bool:
    """Remove a Docker image.

    Args:
        image_name: Full image name with tag.

    Returns:
        True if removed, False if not found.
    """
    pass


def list_containers(experiment_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List running containers, optionally filtered by experiment.

    Args:
        experiment_id: Optional experiment to filter by.

    Returns:
        List of dicts with: id, name, image, status, ports, experiment_id.
    """
    pass
```

### Step 3: Implementation Notes

For experiments.py:
- Read `ExperimentManager.run_test()` and `run_tests()` to understand the execution flow.
- The `launch_experiment()` function should be non-blocking. Consider using `threading` or `asyncio` to run the experiment in the background.
- The `get_status()` function needs a way to track running experiments. Consider a simple registry dict.
- Results are stored in `outputs/<date>/<experiment_id>/`. The `get_results()` function should read from there.

For docker.py:
- Read `ServiceManagerDockerMixin.build_docker_image()` for the build pattern.
- The Docker SDK (`docker` package) is already a panther dependency.
- Image listing can use `docker.from_env().images.list()` directly.

### Step 4: Write tests

```python
# tests/unit/test_api/test_api_experiments.py
"""Tests for panther.api.experiments module."""
import pytest


class TestCreateExperiment:
    def test_returns_id(self):
        """create_experiment should return a string ID."""
        # This is an integration test that needs a valid config
        pass


class TestListExperiments:
    def test_returns_list(self):
        """list_experiments should return a list."""
        from panther.api.experiments import list_experiments
        result = list_experiments()
        assert isinstance(result, list)


# tests/unit/test_api/test_api_docker.py
"""Tests for panther.api.docker module."""
import pytest


class TestListImages:
    @pytest.mark.requires_docker
    def test_returns_list(self):
        """list_images should return a list of image dicts."""
        from panther.api.docker import list_images
        result = list_images()
        assert isinstance(result, list)
```

## Verification
```bash
pytest tests/unit/test_api/test_api_experiments.py tests/unit/test_api/test_api_docker.py -v
```

## Important Notes
- The experiments module is the most complex API because it wraps the full experiment lifecycle.
- `launch_experiment()` must be non-blocking - this is critical for the web UI.
- Docker operations require Docker to be installed and running.
- Some tests should be marked with `@pytest.mark.requires_docker` or `@pytest.mark.integration`.

## Commit Message
```
feat(api): implement experiments and docker API modules

Add panther.api.experiments (create, launch, monitor, stop, results)
and panther.api.docker (list images, build, containers). Experiments
API is async-ready with non-blocking launch.
```

## Files Modified
- `panther/api/experiments.py` (implemented)
- `panther/api/docker.py` (implemented)
- `tests/unit/test_api/test_api_experiments.py` (new)
- `tests/unit/test_api/test_api_docker.py` (new)
