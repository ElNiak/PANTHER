# Configuration Guide — Writing & Validating PANTHER YAML 📜

```yaml
[configuration_guide]
- Purpose : describe every knob in an experiment YAML and how to validate it
- Target  : newcomers designing their own tests; plugin authors adding schemas
- Files   : arbitrary `*.yaml` passed via --experiment-config CLI flag
- Schemas : merged from each plugin’s config_schema.py at runtime
```

A **PANTHER configuration** is a single YAML file that tells the core
engine **what to run, where to run it, and how to instrument it**.

This tutorial walks you through:
1. the **global section** (`logging`, `paths`, `docker`),
2. the **tests array** (one object per experiment),
3. nested **network / execution / service / tester** blocks,
4. **validation & error-checking**, and
5. **advanced tricks** (overrides, templates, re-use).

> **Tip:** Every plugin ships its own `config_schema.py`; PANTHER merges
> them automatically.  Missing keys or wrong types raise an error **before
> any container is built** (with `omegaconf`).

## Why YAML?

PANTHER treats **one YAML file** as the *ground-truth specification* of an
experiment. YAML’s human-readable nesting maps naturally onto PANTHER’s
hierarchy:

```
logging/paths/docker  ──► global behaviour
tests:                ──► list of experiments
└─ network_environment ──► where containers run
   └─ services        ──► what binaries run
      └─ protocol     ──► which protocol model
```

Key points:

| Feature                                           | How it helps in PANTHER                                                                                                   |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Indentation = scope**                           | Easier to see which service uses which protocol or port.                                                                  |
| **Anchors & aliases** (`&default`, `*default`)    | Re-use common blocks (handy in large suites).                                                                             |
| **Inline maps & arrays** (`{key: val}`, `[a, b]`) | Keep small values concise.                                                                                                |
| **Strict schema validation**                      | Each plugin provides a `config_schema.py`; the core merges them and rejects invalid keys *before* any container is built. |
| **Evolutive and plugin-adapted architecture**     | Seamlessly integrates new plugins while maintaining compatibility with existing configurations.                           |

---

## 1 — Minimal Skeleton

```yaml
# my_experiment.yaml
logging: {level: INFO}
paths:   {output_dir: outputs}
docker:  {build_docker_image: true}

tests:
  - name:  "Ping-Pong (MiniP)"
    network_environment: {type: localhost_single_container}
    services:
      srv:
        implementation: {name: ping_pong, type: iut}
        protocol:       {name: minip, version: "1.0", role: responder}
      cli:
        implementation: {name: ping_pong, type: iut}
        protocol:       {name: minip, version: "1.0", role: initiator}
    steps: {wait: 10}
```

Validate in one command:

```bash
panther --experiment-config my_experiment.yaml --validate-config
```

> **Note:** Validation is always performed, even without the `--validate-config` argument. This flag is used to validate the configuration **only**, without executing the experiment.

If the schema passes, re-run **without** `--validate-config` to execute.

> **Tip:** Use `panther --validate-config my.yaml` in CI to fail fast on
> schema errors or typos.

---

## 2 — Global Keys


For more details on the global configuration schema, refer to the [config_global_schema.py](https://github.com/ElNiak/PANTHER/blob/main/panther/config/config_global_schema.py) file in the PANTHER repository. This file defines the structure and validation rules for the global keys used in the configuration.

| Key                         | Type      | Required | Description                                           |   |                              |
| --------------------------- | --------- | -------- | ----------------------------------------------------- | - | ---------------------------- |
| `logging.level`             | enum(INFO | DEBUG    | …)                                                    | ✓ | Console & file log verbosity |
| `logging.format`            | str       | ×        | Python‐style log-format string                        |   |                              |
| `paths.output_dir`          | str       | ✓        | Base folder for artefacts                             |   |                              |
| `paths.log_dir`             | str       | ×        | Separate log folder (default `paths.output_dir/logs`) |   |                              |
| `docker.build_docker_image` | bool      | ✓        | Auto-build missing images                             |   |                              |
| `docker.compose_template`   | str       | ×        | Custom Jinja2 template for Docker Compose             |   |                              |

---

## 3 — The `tests:` Array

Each entry is an **independent experiment**.

Required sub-blocks:

| Sub-block             | Purpose                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------ |
| `network_environment` | Picks one env plugin (`localhost_single_container`, `docker_compose`, `shadow_ns`, custom) |
| `services`            | Map of **named endpoints** (client, server, …)                                             |
| `steps`               | Timing instructions (e.g. `{wait: 30}`) or a list of scripted actions                      |

Optional:

* `execution_environment` — profiling / tracing plugins
* `testers` — Ivy or future fuzzers
* `iterations` — repeat the whole test N times

### Example (Docker Compose w/ profiler)

```yaml
tests:
  - name: "QUIC Throughput"
    network_environment: {type: docker_compose}
    execution_environment:
      - {type: gperf_cpu, sample_freq: 99}
    services:
      h3srv:
        implementation: {name: quiche, type: iut}
        protocol:       {name: quic, version: rfc9000, role: responder}
      h3cli:
        implementation: {name: quic_go, type: iut}
        protocol:       {name: quic, version: rfc9000, role: initiator}
    steps: {wait: 60}
```

---

## 4 — Service Definition Cheat-Sheet

| Key                   | Location    | Meaning                                       |
| --------------------- | ----------- | --------------------------------------------- |
| `implementation.name` | services.\* | Points to a **service plugin** folder         |
| `implementation.type` | services.\* | Always `iut` (implementation-under-test)      |
| `protocol.name`       | services.\* | Protocol plugin (`quic`, `minip`, …)          |
| `protocol.version`    | services.\* | Draft / spec version string                   |
| `protocol.role`       | services.\* | `initiator` / `responder` / custom            |
| `ports`               | services.\* | Docker port-mapping array (`["443:443/udp"]`) |

Services run in the container(s) generated by the **network environment**
plugin.  Extra fields (cert paths, flags) come from that service
plugin’s `config_schema.py`.

---

## 5 — Network Environment Block

| `type` value                 | Extra keys                                     | Notes                                          |
| ---------------------------- | ---------------------------------------------- | ---------------------------------------------- |
| `localhost_single_container` | —                                              | Light & fast; all services share one PID space |
| `docker_compose`             | `compose_template`, `links`, `networks`        | Multi-container; customise with Jinja template |
| `shadow_ns`                  | `topology`, `duration`, `bandwidth`, `latency` | Deterministic network simulation               |

Shadow example:

```yaml
network_environment:
  type: shadow_ns
  topology: topo/torus.gml
  duration: 300
  bandwidth: 100Mbit
```

---

## 6 — Execution Environment Block

List of profiling/tracing wrappers.  Each item must at least specify
`type:`; all other keys come from the plugin schema.

```yaml
execution_environment:
  - {type: strace, filters: "read,write,connect"}
  - {type: gperf_heap}
```

---

## 7 — Tester Block

Attach Ivy (or future fuzzers) to verify behaviour.

```yaml
testers:
  - name: panther_ivy
    test: quic_server_stream
    timeout: 120
```

---

## 8 — Iterations, Steps & Timing

* **`steps:`** can be a map (`{wait: 10}`) or a list:

  ```yaml
  steps:
    - wait: 5
    - command: "killall -SIGUSR1 my_srv"
    - wait: 20
  ```
* **`iterations:`** wraps the whole test N times (with tear-down):

  ```yaml
  iterations: 3
  ```

Execution plugins (`iterations`) take precedence if both are present.

---

## 9 — Advanced Tricks

### A. Override Paths via CLI

```bash
panther --experiment-config exp.yaml --output-dir /tmp/artefacts
```

CLI overrides always win over YAML.

### B. Jinja-Template Variables

In Docker Compose mode the file `docker-compose.j2` can reference
variables defined in `network_environment`:

```jinja
services:
  {{ service.name }}:
    image: {{ service.image }}
    networks:
      default:
        ipv4_address: {{ service.ip }}
```

### C. Sharing Parts with `!include`

For large suites, split YAML and include with the built-in `!include`
directive (PANTHER extends PyYAML):

```yaml
tests: !include tests/quic_suite.yaml
```

---

## 10 — Common Validation Errors 🐞

| Message                           | Likely Cause              | Fix                            |
| --------------------------------- | ------------------------- | ------------------------------ |
| `Unknown field 'typoe'`           | Misspelled `type` key     | Correct spelling               |
| `Unallowed value 'ftp'`           | Plugin not installed      | Add/enable plugin              |
| `Missing required key 'protocol'` | Service block incomplete  | Add `protocol.*` keys          |
| `Port already allocated`          | Two tests share host port | Use distinct `ports:` mappings |

---

## 11 — Recap

1. **Global keys** set log paths & Docker behaviour.
2. **tests\[]** defines what to run — one object ⇒ one experiment.
3. Nest **network / execution / service / tester** blocks.
4. Use `--validate-config` to catch errors early.
5. Plugin schemas keep YAML declarative and self-documenting.

Armed with this guide, you can craft anything from a one-liner ping test
to a 100-node Shadow simulation — all reproducible, version-controlled,
and shareable.
