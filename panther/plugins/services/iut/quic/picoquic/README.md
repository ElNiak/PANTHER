# Picoquic

> **Plugin Type**: Service (IUT)
> **Source Location**: `plugins/services/iut/quic/picoquic/`

## Overview

The Picoquic plugin provides integration with the Picoquic QUIC implementation, developed by Christian Huitema. Picoquic is a lightweight, portable C implementation of the QUIC protocol that can function as both a client and server. It is mature, RFC-compliant, and actively maintained for both research and deployment use.

## Configuration Options

<!-- src: config_schema.py -->

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | "picoquic" | Implementation name |
| `type` | ImplementationType | IUT | Implementation type |
| `version` | PicoquicVersion | (loaded from YAML) | Version configuration |
| `alpn` | Optional[str] | None | ALPN protocol identifier |
| `initial_rtt` | Optional[int] | None | Initial RTT in milliseconds |
| `max_stream_data` | Optional[int] | None | Maximum stream data in bytes |
| `max_data` | Optional[int] | None | Maximum connection data in bytes |

**PicoquicVersion Fields:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `version` | str | "" | Version string |
| `commit` | str | "" | Git commit hash |
| `dependencies` | List[Dict[str, str]] | [] | List of dependencies |
| `client` | Optional[dict] | {} | Client-specific configuration |
| `server` | Optional[dict] | {} | Server-specific configuration |

## Usage Example

```yaml
tests:
  - name: "Picoquic Basic Test"
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
      wait: 30
```

## Integration

- Inherits from `BaseQUICServiceManager` using the template method pattern for consistent QUIC behavior
- Uses the `picoquicdemo` binary with C-based compilation via CMake
- Docker-based deployment automatically handles all build dependencies (GCC, CMake, OpenSSL 1.1.1+)
- Supports conformance, interoperability, and performance testing scenarios

## References

- [Picoquic GitHub Repository](https://github.com/private-octopus/picoquic)
- [QUIC RFC 9000](https://tools.ietf.org/html/rfc9000)
