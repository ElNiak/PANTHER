# QUIC(k) Start — Your First Experiment in ≈10(30) min 🚀

This guide shows how to install **PANTHER** with the new enhanced Click CLI, spin up a simple
**client ↔ server experiment**, and inspect the results using modern command-line tools.

We use **QUIC** as a concrete example because multiple ready-made QUIC
implementations ship with PANTHER, **yet the exact same steps apply to
MiniP, HTTP/3, a custom protocol plugin, or any future protocol you add**.

> [!NOTE]
> "System Requirements"
> **Target platform:** Linux (x86-64) or Mac with Docker >= 27
> **Estimated time (the first time):** ≈ 10 minutes if you do not use Ivy tester and ≈ 30 minutes (due to containers building times of implementation), then around 2 minutes. Ivy is very long to compile and depend on your computer.

---

## 1 — Write a Minimal Experiment (YAML)

> [!NOTE]
> "Experiments vs Tests"
> In PANTHER, an **experiment** is the overall configuration file that defines what to run, while **tests** are individual scenarios within that experiment. A single experiment can contain multiple tests, each with its own configuration, network setup, and measurements.


```yaml
# Basic logging configuration
logging:
  level: INFO  # Controls how much detail you see (DEBUG for troubleshooting)

# Where to save experiment results
paths:
  output_dir: outputs  # All results saved in 'outputs' folder

# Docker container settings
docker:
  build_docker_image: true  # Build fresh containers (set false for faster reruns)

# Tests define what protocols and implementations to run
tests:
  - name: "QUIC Connection (PicoQUIC)"
    description: "My first experiment - basic QUIC client-server test"
    network_environment:
      type: docker_compose  # Run in separate Docker containers
    services:
      server:
        implementation:
          name: picoquic      # Use PicoQUIC implementation
          type: iut           # IUT = Implementation Under Test
        protocol:
          name: quic          # Test QUIC protocol
          version: rfc9000    # Use official QUIC standard
          role: server        # This service acts as server
      client:
        implementation:
          name: picoquic      # Same implementation for client
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: client        # This service acts as client
          target: server      # Connect to the 'server' service above
    steps:
      wait: 15              # Run test for 15 seconds
  - name: "QUIC Connection Tested (PicoQUIC)"
    description: "My second experiement"
    network_environment:
      type: docker_compose
    execution_environment: # strace
      - type: strace
    services:
      server:
        timeout: 100
        implementation:
          name: panther_ivy
          type: testers
          test: quic_client_test_max
        protocol:
          name: quic
          version: rfc9000
          role: server
        ports:
          - "4443:4443"
          - "4987:4987"
      client:
        timeout: 100
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: client
          target: server
    steps:
      wait: 100
```

---

## 2 — Run the Experiment


> [!WARNING]
>  "Docker Buildkit"
> You SHOULD disable buildkit (experimental) in the config files:
> ```yaml
> docker:
>   force_build_docker_image: true
>   log_docker_image_build: true  # Enable Docker build log files
>   use_buildx: false
> ```


With the  CLI, experiment execution is more intuitive and provides better feedback (*In Progress*):

```bash
# Preview what will happen (optional dry run) without building images and running them.
panther --debug run --config quic_demo.yaml --dry-run

panther run --config quic_demo.yaml --dry-run --verbose

# Run the actual experiment with metrics
panther --debug run --config quic_demo.yaml --verbose
```

PANTHER validates the YAML, builds images if absent, launches the two
containers under Docker Compose, runs the handshake for 15 s, and writes
results to `outputs/`.

> [!NOTE]
>  "Alternative Test Configuration"
> You can also test with built-in examples:
> ```bash
> panther run --config experiment-config/experiment_config_example.yaml
> ```

---

## 3 — Inspect Results

PANTHER creates a timestamped output directory with subfolders for each test:

```text
outputs/
└── 2025-…_experiment_run/
    ├── metrics/                    # contains experiments monitored metrics
    ├── experiment.log              # high-level timeline + any errors
    ├── experiment_config.yaml      # full experiment configuration (including defaults)
    ├── QUIC_Connection_PicoQUIC/    # first test results
    │   ├── metrics/                # contains test monitored metrics
    │   ├── server/                 # server container logs and artifacts
    │   │   ├── stdout.log          # server process standard output
    │   │   ├── stderr.log          # server process standard error
    │   │   └── cpu_profile.prof    # CPU profile (from gperf_cpu)
    │   └── client/                 # client container logs and artifacts
    │       ├── stdout.log          # client process standard output
    │       ├── stderr.log          # client process standard error
    │       └── cpu_profile.prof    # CPU profile (from gperf_cpu)
    └── QUIC_Connection_Tested_PicoQUIC/  # second test results
        ├── server/                 # server container logs and artifacts
        │   ├── stdout.log          # server process standard output
        │   ├── stderr.log          # server process standard error
        │   └── strace.log          # system call trace (from strace)
        └── client/                 # client container logs and artifacts
            ├── stdout.log          # client process standard output
            ├── stderr.log          # client process standard error
            └── strace.log          # system call trace (from strace)
```

---

## 4 — Next Steps 🧭

| Idea                      | How                                                             |
| ------------------------- | --------------------------------------------------------------- |
| **Test another protocol** | Change `protocol.name` (e.g. `minip`) and swap implementations. |
| **Use Shadow NS**         | `network_environment.type: shadow_ns` + `topology`, `duration`. |
| **Add formal testing**    | Add tester: `name: panther_ivy`, `test: quic_server_stream`.    |
| **Single-container mode** | `network_environment.type: localhost_single_container`.         |
| **Create a new plugin**   | See the [Plugin Development Guide](panther/plugins/__init__.py) or run `panther --create-plugin <type> <name>`. |
| **Enable telemetry**     | Check the Metrics Guide for performance data. |


Enjoy experimenting—whether with QUIC **or any protocol you plug in**!

Check the existing tests configuration at `experiment-config/*.yml` !
