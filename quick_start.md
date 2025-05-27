# Quick Start — Your First Experiment in ≈5 min 🚀  

*(Example: QUIC — but PANTHER supports **any** protocol plugin)*

This guide shows how to install **PANTHER**, spin up a simple
**client ↔ server experiment**, and inspect the results.  

We use **QUIC** as a concrete example because multiple ready-made QUIC
implementations ship with PANTHER, **yet the exact same steps apply to
MiniP, HTTP/3, a custom protocol plugin, or any future protocol you add**.

> **Target platform:** Linux (x86-64) with Docker ≥ 27  
> **Estimated time:** ≈ 5 minutes (build times depend on network speed)

---

## 1 — Install PANTHER

### Option A — From PyPI *(easiest)*

```bash
python -m venv .venv              # optional but recommended
source .venv/bin/activate
pip install panther_net
```

`panther_net` is the official PyPI package that bundles the core engine, all built-in plugins, and CLI entry-points. 
Upgrade later with `pip install -U panther_net`.

### Option B — From Source *(for dev)*

```bash
git clone https://github.com/ElNiak/PANTHER.git
cd PANTHER
python -m venv .venv && source .venv/bin/activate
pip install -e .                   # editable install
# (Optional dev extras)
# pip install -e .[dev]
```

Both methods read dependencies from **`pyproject.toml`**—**do not
manually edit `requirements.txt`**, it’s just a frozen lock.

Verify Docker is running:

```bash
docker version   # should print Client + Server ≥ 27.x
```

## 2 — Write a Minimal Experiment (YAML)

Create `quic_demo.yaml` (swap `quic` for `minip` , … to test other protocols):

```yaml
logging: {level: INFO}
paths:   {output_dir: outputs}

docker: {build_docker_image: true}

tests:
  - name: "QUIC Handshake (PicoQUIC ↔︎ Quic-Go)"
    network_environment: {type: docker_compose}
    execution_environment:
      - {type: gperf_cpu}          # optional CPU profiler
    services:
      server:
        implementation: {name: picoquic, type: iut}
        protocol:       {name: quic, version: draft29, role: responder}
        ports: ["443:443/udp"]
      client:
        implementation: {name: quic_go, type: iut}
        protocol:       {name: quic, version: draft29, role: initiator}
    steps: {wait: 15}
```

---

## 3 — Run the Experiment

```bash
panther --experiment-config quic_demo.yaml
```

PANTHER validates the YAML, builds images if absent, launches the two
containers under Docker Compose, runs the handshake for 15 s, and writes
results to `outputs/`.

---

## 4 — Inspect Results

```
outputs/
└── 2025-…_QUIC_Handshake/
    ├── experiment.log
    ├── experiment_config.yaml
    ├── server/gperf_cpu.txt
    └── client/quic_go_stdout.log
```

* `experiment.log` — high-level timeline + any errors
* `*_stdout.log` — raw output of each service
* `gperf_cpu.txt` — CPU-usage profile (convert with `gprof2dot`)

---

## 5 — Next Steps 🧭

| Idea                      | How                                                             |
| ------------------------- | --------------------------------------------------------------- |
| **Test another protocol** | Change `protocol.name` (e.g. `minip`) and swap implementations. |
| **Use Shadow NS**         | `network_environment.type: shadow_ns` + `topology`, `duration`. |
| **Add formal testing**    | Add tester: `name: panther_ivy`, `test: quic_server_stream`.    |
| **Single-container mode** | `network_environment.type: localhost_single_container`.         |
| **Create a new plugin**   | See the [Plugin Developer Guide](plugin_guide.md).              |

Enjoy experimenting—whether with QUIC **or any protocol you plug in**!
