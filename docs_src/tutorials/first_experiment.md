---
status: new
---

# Your First Experiment

This tutorial walks you through running your first PANTHER experiment using Docker Compose.

## Prerequisites

- Docker installed and running
- PANTHER installed (`pip install panther-net`)

## The Experiment Configuration

PANTHER experiments are defined in YAML files. Here's a minimal Docker-based experiment:

```yaml
;--8<-- "experiment-config/base/experiment_config_example_minimal_docker.yaml:1:30"
```

!!! tip "Configuration Structure"
    Every experiment config has three main sections: `logging`, `tests`, and optional `paths`.

## Running the Experiment

```bash
panther run --config experiment-config/base/experiment_config_example_minimal_docker.yaml
```

## Understanding the Output

PANTHER follows a **four-phase execution model**:

1. **Initialization** -- Loads and validates your configuration
2. **Plugin Loading** -- Discovers plugins, creates service managers
3. **Environment Deployment** -- Builds Docker images, sets up networks
4. **Test Execution** -- Runs scenarios, collects results

Results are stored in `outputs/<date>/<experiment_id>/`.

## Next Steps

- [Configuration Guide](../how-to/configuration.md) -- Customize your experiments
- [Write a Plugin](writing_a_plugin.md) -- Extend PANTHER
- [Architecture](../explanation/plugin_system.md) -- Understand the internals
