# PANTHER Plugin Inventory

## Environments

### Execution Environment

| Plugin | Path | Documentation | Development Status |
|--------|------|---------------|-------------------|
| gperf_heap | [`environments/execution_environment/gperf_heap`](panther/plugins/environments/execution_environment/gperf_heap/README.md) | ✅ | ✅ |
| gperf_cpu | [`environments/execution_environment/gperf_cpu`](panther/plugins/environments/execution_environment/gperf_cpu/README.md) | ✅ | ✅ |
| memcheck | [`environments/execution_environment/memcheck`](panther/plugins/environments/execution_environment/memcheck/README.md) | ✅ | ✅ |
| helgrind | [`environments/execution_environment/helgrind`](panther/plugins/environments/execution_environment/helgrind/README.md) | ✅ | ✅ |
| strace | [`environments/execution_environment/strace`](panther/plugins/environments/execution_environment/strace/README.md) | ✅ | ✅ |
| iterations | [`environments/execution_environment/iterations`](panther/plugins/environments/execution_environment/iterations/README.md) | ✅ | ✅ |

### Network Environment

| Plugin | Path | Documentation | Development Status |
|--------|------|---------------|-------------------|
| localhost_single_container | [`environments/network_environment/localhost_single_container`](panther/plugins/environments/network_environment/localhost_single_container/README.md) | ✅ | ✅ |
| shadow_ns | [`environments/network_environment/shadow_ns`](panther/plugins/environments/network_environment/shadow_ns/README.md) | ✅ | ✅ |
| docker_compose | [`environments/network_environment/docker_compose`](panther/plugins/environments/network_environment/docker_compose/README.md) | ✅ | ✅ |

## Protocols

### Client Server

| Plugin | Path | Documentation | Development Status |
|--------|------|---------------|-------------------|
| http | [`protocols/client_server/http`](panther/plugins/protocols/client_server/http/README.md) | ✅ | ⚠️ |
| quic | [`protocols/client_server/quic`](panther/plugins/protocols/client_server/quic/README.md) | ✅ | ✅ |
| minip | [`protocols/client_server/minip`](panther/plugins/protocols/client_server/minip/README.md) | ✅ | ✅ |

### Peer To Peer

| Plugin | Path | Documentation | Development Status |
|--------|------|---------------|-------------------|
| bittorrent | [`protocols/peer_to_peer/bittorrent`](panther/plugins/protocols/peer_to_peer/bittorrent/README.md) | ✅ | ⚠️ |

## Services

### Iut

| Plugin | Path | Documentation | Development Status |
|--------|------|---------------|-------------------|
| quant | [`services/iut/quic/quant`](panther/plugins/services/iut/quic/quant/README.md) | ✅ | ⚠️ |
| picoquic_shadow | [`services/iut/quic/picoquic_shadow`](panther/plugins/services/iut/quic/picoquic_shadow/README.md) | ✅ | ✅ |
| aioquic | [`services/iut/quic/aioquic`](panther/plugins/services/iut/quic/aioquic/README.md) | ✅ | ⚠️ |
| lsquic | [`services/iut/quic/lsquic`](panther/plugins/services/iut/quic/lsquic/README.md) | ✅ | ⚠️ |
| quinn | [`services/iut/quic/quinn`](panther/plugins/services/iut/quic/quinn/README.md) | ✅ | ⚠️ |
| quic_go | [`services/iut/quic/quic_go`](panther/plugins/services/iut/quic/quic_go/README.md) | ✅ | ⚠️ |
| mvfst | [`services/iut/quic/mvfst`](panther/plugins/services/iut/quic/mvfst/README.md) | ✅ | ⚠️ |
| quiche | [`services/iut/quic/quiche`](panther/plugins/services/iut/quic/quiche/README.md) | ✅ | ⚠️ |
| picoquic | [`services/iut/quic/picoquic`](panther/plugins/services/iut/quic/picoquic/README.md) | ✅ | ✅ |
| ping_pong | [`services/iut/minip/ping_pong`](panther/plugins/services/iut/minip/ping_pong/README.md) | ✅ | ✅ |

### Testers

| Plugin | Path | Documentation | Development Status |
|--------|------|---------------|-------------------|
| panther_ivy | [`services/testers/panther_ivy`](panther/plugins/services/testers/panther_ivy/README.md) | ✅ | ✅ |

