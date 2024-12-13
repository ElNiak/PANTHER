# Contributing

## :open_file_folder: Project Structure


### :open_file_folder: Directory Structure


The PANTHER project is organized into the following key directories:

```
tests/                  # Unit tests
outputs/                # Experiment results and logs
panther/
├── config/              # Configuration files and schemas
├── core/                # Core experiment logic
├── plugins/             # Plugin implementations for protocols, environments, etc.
├──── services/          # Protocol implementations
├────── iut/             # Protocol-specific implementations
├────────── quic/        # QUIC protocol implementations
├──────────── picoquic/  # Picoquic implementation
├──────────── ...
├────────── minip/       # MiniP protocol implementations
├────────── ...
├────── testers/         # Testers for protocol implementations
├────────── panther_ivy/ # Ivy tester implementation
├──── environments/      # Environment configurations
├────── network_environment/    # Network environment configurations
├────────── docker_compose/     # Docker Compose configurations
├────────── shadow_ns/          # Shadow NS configurations
├────────── localhost_single_container/     # Localhost single container configurations
├────── execution_environment/  # Execution environment configurations
├────────── strace/             # Strace configurations
├────────── gperf_heap/         # Gperf Heap profiling configurations
├────────── gperf_cpu/          # Gperf CPU profiling configurations
├──── protocols/         # Protocol definitions
└── __main__.py          # Command-line interface for PANTHER
```
---
