# Quick Start — Your First Experiment in ≈30 min 🚀

*(Example: QUIC — but PANTHER supports **any** protocol plugin)*

This guide shows how to install **PANTHER**, spin up a simple
**client ↔ server experiment**, and inspect the results.

We use **QUIC** as a concrete example because multiple ready-made QUIC
implementations ship with PANTHER, **yet the exact same steps apply to
MiniP, HTTP/3, a custom protocol plugin, or any future protocol you add**.

> **Target platform:** Linux (x86-64) with Docker ≥ 27

> **Estimated time:** ≈ 30 minutes per test the first time (due to build times of implementation), then around 2 minutes.

---

## 1 — Install PANTHER

```bash
python -m venv .venv              # optional but recommended
source .venv/bin/activate
pip install panther_net
```

`panther_net` is the official PyPI package that bundles the core engine, all built-in plugins, and CLI entry-points.
Upgrade later with `pip install -U panther_net`.

## 2 — Write a Minimal Experiment (YAML)

Create `quic_demo.yaml` (swap `quic` for `minip` , … to test other protocols):

```yaml
logging:
  level: INFO

paths:
  output_dir: outputs

docker:
  build_docker_image: true

tests:
  - name: "QUIC Handshake (PicoQUIC)"
    description: "My first experiement"
    network_environment:
      type: docker_compose
    execution_environment:
      - type: gperf_cpu          # optional CPU profiler
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: draft29
          role: server
      client:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: draft29
          role: client
          target: server
    steps:
      wait: 15
  - name: "QUIC Version Negociation (PicoQUIC)"
    description: "My second experiement"
    network_environment:
      type: docker_compose
    execution_environment:
      - type: strace
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: draft29
          role: server
      client:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000 # trigger VN
          role: client
          target: server
    steps:
      wait: 15
```

---

## 3 — Run the Experiment

```bash
panther --experiment-config quic_demo.yaml
# Or
python -m panther  --experiment-config quic_demo.yaml
```

PANTHER validates the YAML, builds images if absent, launches the two
containers under Docker Compose, runs the handshake for 15 s, and writes
results to `outputs/`.

**Note:**
You can also test with:

```bash
python -m panther  --experiment-config experiment-config/experiment_config_example.yaml
```

---

## 4 — Inspect Results

PANTHER creates a timestamped output directory with subfolders for each test:

```
outputs/
└── 2025-…_experiment_run/
    ├── experiment.log              # high-level timeline + any errors
    ├── experiment_config.yaml      # full experiment configuration (including defaults)
    ├── QUIC_Handshake_PicoQUIC/    # first test results
    │   ├── server/                 # server container logs and artifacts
    │   │   ├── stdout.log          # server process standard output
    │   │   ├── stderr.log          # server process standard error
    │   │   └── cpu_profile.prof    # CPU profile (from gperf_cpu)
    │   └── client/                 # client container logs and artifacts
    │       ├── stdout.log          # client process standard output
    │       ├── stderr.log          # client process standard error
    │       └── cpu_profile.prof    # CPU profile (from gperf_cpu)
    └── QUIC_Version_Negociation_PicoQUIC/  # second test results
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

Enjoy experimenting—whether with QUIC **or any protocol you plug in**!

Check the existing tests configuration at `experiment-config/*.yml` !
