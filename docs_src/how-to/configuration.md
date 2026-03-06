# Configuration Guide

How to configure PANTHER experiments using YAML files.

## Configuration Structure

See the [Config System explanation](../explanation/config_system.md) for architecture details
and the [full API reference](../panther/panther/config/index.md) for all classes and fields.

## Minimal Configuration

```yaml
;--8<-- "experiment-config/base/experiment_config_example_minimal_docker.yaml:1:10"
```

## Logging Configuration

Control log verbosity per-feature:

```yaml
;--8<-- "experiment-config/base/experiment_config_example_minimal_docker.yaml:1:8"
```

## Test Definition

Each test defines a network environment and services:

```yaml
;--8<-- "experiment-config/base/experiment_config_example_minimal_docker.yaml:105:130"
```

!!! tip
    Use `type: "docker_compose"` for isolated container experiments.

## Docker Settings

```yaml
;--8<-- "experiment-config/base/experiment_config_example_minimal_docker.yaml:99:104"
```

## See Also

- [Config Schema Reference](../reference/config_schema.md) -- All Pydantic field definitions
- [Run an Experiment](run_experiment.md) -- Execute your configuration
