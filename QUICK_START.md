# QUIC(k) Start — Your First Experiment in ≈10(30) min 🚀

This guide shows how to install **PANTHER**, spin up a simple
**client ↔ server experiment**, and inspect the results.

We use **QUIC** as a concrete example because multiple ready-made QUIC
implementations ship with PANTHER, **yet the exact same steps apply to
MiniP, HTTP/3, a custom protocol plugin, or any future protocol you add**.

!!! info "System Requirements"
    **Target platform:** Linux (x86-64) or Mac with Docker >= 27
    **Estimated time (the first time):** ≈ 10 minutes if you do not use Ivy tester and ≈ 30 minutes (due to containers building times of implementation), then around 2 minutes. Ivy is very long to compile and depend on your computer.

---

## 1 — Install PANTHER

!!! tip "Recommended Setup"
    Using a virtual environment is highly recommended to avoid dependency conflicts:

```bash
python -m venv .venv              # optional but recommended
source .venv/bin/activate
pip install panther_net
```

`panther_net` is the official PyPI package that bundles the core engine, all built-in plugins, and CLI entry-points.
Upgrade later with `pip install -U panther_net`.

## 2 — Write a Minimal Experiment (YAML)

!!! example "Your First Experiment Configuration"
    Create `quic_demo.yaml` (swap `quic` for `minip` to test other protocols):

!!! info "Experiments vs Tests"
  In PANTHER, an **experiment** is the overall configuration file that defines what to run, while **tests** are individual scenarios within that experiment. A single experiment can contain multiple tests, each with its own configuration, network setup, and measurements.


```yaml
logging:
  level: INFO

paths:
  output_dir: outputs

docker:
  build_docker_image: true 
  # true -> Rebuild the image if already present 
  # but even at false, if the image build is done
  # if the image does not exist

tests:
  - name: "QUIC Connection (PicoQUIC)"
    description: "My first experiement"
    network_environment:
      type: docker_compose
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
      client:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: client
          target: server
    steps:
      wait: 15
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

## 3 — Run the Experiment

```bash
panther --experiment-config quic_demo.yaml --enable-metrics
# Or
python -m panther  --experiment-config quic_demo.yaml --enable-metrics
```

PANTHER validates the YAML, builds images if absent, launches the two
containers under Docker Compose, runs the handshake for 15 s, and writes
results to `outputs/`.

!!! note "Alternative Test Configuration"
    You can also test with:

    ```bash
    python -m panther  --experiment-config experiment-config/experiment_config_example.yaml --enable-metrics
    ```

---

## 4 — Inspect Results

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

## 5 — Next Steps 🧭

| Idea                      | How                                                             |
| ------------------------- | --------------------------------------------------------------- |
| **Test another protocol** | Change `protocol.name` (e.g. `minip`) and swap implementations. |
| **Use Shadow NS**         | `network_environment.type: shadow_ns` + `topology`, `duration`. |
| **Add formal testing**    | Add tester: `name: panther_ivy`, `test: quic_server_stream`.    |
| **Single-container mode** | `network_environment.type: localhost_single_container`.         |
| **Create a new plugin**   | See the [Plugin Developer Guide](panther/plugins/development.md). |
| **Enable telemetry**     | Check the [Metrics Guide](panther/core/metrics/README.md) for performance data. |


Enjoy experimenting—whether with QUIC **or any protocol you plug in**!

Check the existing tests configuration at `experiment-config/*.yml` !
