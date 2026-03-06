# Run an Experiment

How to execute PANTHER experiments and inspect results.

## Quick Run

```bash
panther run --config experiment-config/base/experiment_config_example_minimal_docker.yaml
```

## Validate Before Running

```bash
panther config validate --config your_config.yaml
```

## Execution Phases

PANTHER experiments follow a four-phase model:

1. **Initialization** -- Config loading and validation
2. **Plugin Loading** -- Service discovery and command generation
3. **Environment Deployment** -- Docker image builds and network setup
4. **Test Execution** -- Scenario execution with metrics collection

## Inspecting Results

Results are stored in `outputs/<date>/<experiment_id>/`:

```bash
ls outputs/          # List experiment runs
```

## Common Options

| Option | Description |
|--------|-------------|
| `--config` | Path to experiment YAML |
| `--debug` | Enable debug logging |
| `--verbose` | Verbose output |

## Troubleshooting

!!! warning "Docker Required"
    Most experiments require Docker. Ensure Docker is running before starting.

!!! tip "Force Rebuild"
    Set `docker.force_build_docker_image: true` in config to rebuild images.
