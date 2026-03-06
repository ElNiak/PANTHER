# PANTHER Plugin Inventory

## Environments

### Network Environment

| Plugin | Version | Path | Description | Capabilities | Documentation | Status |
|--------|---------|------|-------------|--------------|---------------|--------|
| docker_compose | 2.0.0 | `environments/network_environment/docker_compose` | Docker Compose network environment with reduced duplication | container_orchestration, network_isolation, service_discovery | yes | ok |
| localhost_single_container | 2.0.0 | `environments/network_environment/localhost_single_container` | single container environment with reduced duplication | single_container, fast_deployment, local_testing | yes | ok |
| shadow_ns | 2.0.0 | `environments/network_environment/shadow_ns` | Shadow network simulator environment with reduced duplica... | network_simulation, deterministic_testing, scalability_testing | yes | ok |

### Execution Environment

| Plugin | Version | Path | Description | Capabilities | Documentation | Status |
|--------|---------|------|-------------|--------------|---------------|--------|
| gdb | 1.0.0 | `environments/execution_environment/gdb` | GDB debugging environment for crash analysis and stack tr... | debugging, stack_traces, crash_analysis, core_dumps | yes | ok |
| gperf_cpu | 1.0.0 | `environments/execution_environment/gperf_cpu` | Google Performance Tools CPU profiling environment | cpu_profiling, performance_analysis | yes | ok |
| gperf_heap | 1.0.0 | `environments/execution_environment/gperf_heap` | Memory heap profiling execution environment using Google ... | heap_profiling, memory_analysis, leak_detection | yes | ok |
| helgrind | 1.0.0 | `environments/execution_environment/helgrind` | Valgrind Helgrind thread error detection environment | thread_error_detection, race_condition_analysis, deadlock_detection | yes | ok |
| iterations | 1.0.0 | `environments/execution_environment/iterations` | Execution environment for running multiple test iterations | iterative_testing, statistical_analysis, performance_variance | yes | ok |
| memcheck | 1.0.0 | `environments/execution_environment/memcheck` | Valgrind Memcheck memory error detection environment | memory_error_detection, leak_detection, invalid_access_detection | yes | ok |
| strace | 1.0.0 | `environments/execution_environment/strace` | System call tracing execution environment | syscall_tracing, performance_analysis, debugging | yes | ok |

## Protocols

### Client Server

| Plugin | Version | Path | Description | Capabilities | Documentation | Status |
|--------|---------|------|-------------|--------------|---------------|--------|
| minip | flaky | `protocols/client_server/minip` | MiniP Protocol Manager (versions: flaky, fail, functional, ...) |  | yes | ok |
| quic | rfc9000 | `protocols/client_server/quic` | QUIC transport protocol - A UDP-based multiplexed and sec... | 0-rtt, connection-migration, multipath, stream-multiplexing, ... | yes | ok |

## Services

### IUT

| Plugin | Version | Path | Description | Capabilities | Documentation | Status |
|--------|---------|------|-------------|--------------|---------------|--------|
| aioquic | 2.0.0 | `services/iut/quic/aioquic` | aioquic - Python QUIC implementation with asyncio (Refact... | rfc9000, 0rtt, migration, asyncio | yes | ok |
| lsquic | 2.0.0 | `services/iut/quic/lsquic` | LSQUIC - LiteSpeed's QUIC and HTTP/3 implementation (Refa... | rfc9000, 0rtt, migration, push | yes | ok |
| mvfst | 2.0.0 | `services/iut/quic/mvfst` | MVFST - Meta's implementation of QUIC transport protocol ... | rfc9000, 0rtt, migration, congestion_control | yes | ok |
| picoquic | 1.0.0 | `services/iut/quic/picoquic` | PicoQUIC - Minimalist implementation of the QUIC protocol | tls13, 0rtt, connection_migration, multipath, ... | yes | ok |
| picoquic_shadow | 2.0.0 | `services/iut/quic/picoquic_shadow` | PicoQUIC for Shadow Network Simulator (Refactored) | rfc9000, 0rtt, migration, shadow | yes | ok |
| ping_pong | 1.0.0 | `services/iut/minip/ping_pong` | Ping-Pong implementation for MiniP protocol testing | ping_pong, basic_networking | yes | ok |
| quant | 2.0.0 | `services/iut/quic/quant` | Quant - Minimal QUIC implementation (Refactored) | rfc9000, 0rtt, migration | yes | ok |
| quic_go | 2.0.0 | `services/iut/quic/quic_go` | quic-go - Go implementation of QUIC (Refactored) | rfc9000, 0rtt, migration | yes | ok |
| quiche | 2.0.0 | `services/iut/quic/quiche` | Quiche - Cloudflare's Rust implementation of QUIC (Refact... | rfc9000, 0rtt, migration | yes | ok |
| quinn | 2.0.0 | `services/iut/quic/quinn` | Quinn - Async-friendly QUIC implementation in Rust (Refac... | rfc9000, 0rtt, migration, async | yes | ok |

### Testers

| Plugin | Version | Path | Description | Capabilities | Documentation | Status |
|--------|---------|------|-------------|--------------|---------------|--------|
| panther_ivy | 3.1.0 | `services/testers/panther_ivy` | Ivy formal verification tester using mixin-based architec... |  | yes | ok |
