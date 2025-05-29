# PANTHER Plugin Inventory

## Environments

### Execution Environment

| Plugin | Path | Documentation |
|--------|------|---------------|
| gperf_heap | `environments/execution_environment/gperf_heap` | ✅ |
| gperf_cpu | `environments/execution_environment/gperf_cpu` | ✅ |
| memcheck | `environments/execution_environment/memcheck` | ✅ |
| helgrind | `environments/execution_environment/helgrind` | ✅ |
| strace | `environments/execution_environment/strace` | ✅ |
| iterations | `environments/execution_environment/iterations` | ✅ |

### Network Environment

| Plugin | Path | Documentation |
|--------|------|---------------|
| localhost_single_container | `environments/network_environment/localhost_single_container` | ✅ |
| shadow_ns | `environments/network_environment/shadow_ns` | ✅ |
| docker_compose | `environments/network_environment/docker_compose` | ✅ |

## Protocols

### Client Server

| Plugin | Path | Documentation |
|--------|------|---------------|
| http | `protocols/client_server/http` | ✅ |
| quic | `protocols/client_server/quic` | ✅ |
| minip | `protocols/client_server/minip` | ✅ |

### Peer To Peer

| Plugin | Path | Documentation |
|--------|------|---------------|
| bittorrent | `protocols/peer_to_peer/bittorrent` | ✅ |

## Services

### Iut

| Plugin | Path | Documentation |
|--------|------|---------------|
| http | `services/iut/http` | ✅ |
| quic | `services/iut/quic` | ✅ |
| minip | `services/iut/minip` | ✅ |

### Testers

| Plugin | Path | Documentation |
|--------|------|---------------|
| panther_ivy | `services/testers/panther_ivy` | ✅ |
