---
hide:
  - navigation
  - toc
---

<div class="hero" markdown>

# PANTHER

**Protocol Analysis and Testing Harness for Extensible Research**

PANTHER is a modular framework for testing network protocol implementations
under realistic conditions. Define experiments in YAML, run them in isolated
Docker environments, and get structured results with formal verification support.

</div>

<div class="grid cards" markdown>

-   :material-test-tube:{ .lg .middle } __Protocol Testing__

    ---

    Test QUIC and custom protocol implementations under failure, jitter, or adverse timing conditions.

    [:octicons-arrow-right-24: Tutorials](tutorials/first_experiment.md)

-   :material-check-decagram:{ .lg .middle } __Formal Verification__

    ---

    Run Ivy-based conformance checks in deterministic network simulation with Shadow.

    [:octicons-arrow-right-24: How it works](explanation/plugin_system.md)

-   :material-puzzle:{ .lg .middle } __Plugin System__

    ---

    Extend PANTHER with new protocols, services, profilers, or network backends with minimal boilerplate.

    [:octicons-arrow-right-24: Write a plugin](tutorials/writing_a_plugin.md)

-   :material-docker:{ .lg .middle } __Docker Environments__

    ---

    Every experiment runs in an isolated container environment defined by a single YAML file.

    [:octicons-arrow-right-24: Run an experiment](how-to/run_experiment.md)

</div>

## Quick Start

```bash
pip install panther-net
panther run --config experiment-config/base/experiment_config_example_minimal.yaml
```

## Documentation Structure

<div class="grid cards" markdown>

-   :material-school:{ .lg .middle } __Tutorials__

    ---

    Step-by-step guides to get started with PANTHER.

    [:octicons-arrow-right-24: Start learning](tutorials/first_experiment.md)

-   :material-directions:{ .lg .middle } __How-To Guides__

    ---

    Practical recipes for common tasks.

    [:octicons-arrow-right-24: Find a guide](how-to/run_experiment.md)

-   :material-lightbulb:{ .lg .middle } __Explanation__

    ---

    Understand PANTHER's architecture and design decisions.

    [:octicons-arrow-right-24: Read more](explanation/plugin_system.md)

-   :material-book-open-variant:{ .lg .middle } __Reference__

    ---

    API docs, CLI reference, and configuration schema.

    [:octicons-arrow-right-24: Browse reference](reference/cli.md)

</div>
