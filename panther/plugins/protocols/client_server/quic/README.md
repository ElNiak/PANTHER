# QUIC Protocol

> **Plugin Type**: Protocol
> **Source Location**: `plugins/protocols/client_server/quic/`

## Overview

The QUIC Protocol plugin implements the QUIC (Quick UDP Internet Connections) transport layer protocol within the PANTHER framework. QUIC provides encrypted, multiplexed connections between endpoints with reduced connection establishment latency. This plugin supports testing different QUIC protocol versions (RFC 9000, Draft 29, Draft 27), conformance testing, performance benchmarking, and security analysis.

## Configuration Options

<!-- src: config_schema.py -->

```yaml
protocol:
  name: "quic"
  version: "rfc9000"         # QUIC version (rfc9000, draft29, draft27)
  role: "server"             # Role (server or client)
  target: "client_service"   # Optional target service name
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | "QUIC" | Protocol name |
| `version` | enum | No | "rfc9000" | QUIC version (rfc9000, draft29, draft27) |
| `role` | enum | No | "server" | Protocol role (server, client) |
| `target` | string | No | None | Target service name |
| `protocol_type` | enum | No | "client_server" | Protocol type |

## Usage Example

```yaml
tests:
  - name: "QUIC Server Test"
    network_environment:
      type: "docker_compose"
    services:
      quic_server:
        name: "quic_server"
        timeout: 100
        implementation:
          name: "picoquic"
          type: "iut"
        protocol:
          name: "quic"
          version: "rfc9000"
          role: "server"
      quic_client:
        name: "quic_client"
        timeout: 100
        implementation:
          name: "picoquic"
          type: "iut"
        protocol:
          name: "quic"
          version: "rfc9000"
          role: "client"
          target: "quic_server"
```

## Integration

- Works with all QUIC IUT service plugins (picoquic, aioquic, quiche, quinn, lsquic, mvfst, quic-go, quant)
- Requires network environments that support UDP traffic (docker_compose, shadow_ns)
- Depends on certificate management tools for TLS handshake configuration
- Supports interoperability testing across different QUIC implementations

## Troubleshooting

| Issue | Solution |
|-------|----------|
| TLS handshake failures | Check certificate validity and configuration |
| Connection establishment timeouts | Verify UDP connectivity between endpoints |
| Version negotiation issues | Ensure both endpoints support the configured version |
| Performance issues | Check for network congestion and adjust buffer sizes |
