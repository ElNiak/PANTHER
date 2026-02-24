# LiteSpeed QUIC (lsquic)

> **Plugin Type**: Service (IUT)
> **Source Location**: `plugins/services/iut/quic/lsquic/`

## Overview

The lsquic plugin provides integration with LiteSpeed's QUIC implementation, a high-performance C library developed by LiteSpeed Technologies. lsquic is a production-grade implementation optimized for server workloads and high-throughput scenarios, widely used in commercial web servers and CDN infrastructure.

## Configuration Options

<!-- src: config_schema.py -->

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | "lsquic" | Implementation name |
| `doc_root` | str | "/var/www" | Document root for serving files |
| `enable_push` | bool | True | Enable HTTP/3 PUSH |
| `max_conns` | Optional[int] | None | Maximum number of connections |
| `request_path` | str | "/" | Request path |
| `method` | str | "GET" | HTTP method |
| `headers` | Optional[Dict[str, str]] | {} | Request headers |
| `output_file` | Optional[str] | None | Output file path |
| `library_path` | str | "/opt/lsquic/lib" | LSQUIC library path |
| `logs_dir` | str | "/app/logs/artifacts" | Logs directory |
| `max_packet_size` | Optional[int] | None | Maximum packet size |
| `initial_max_data` | Optional[int] | None | Initial max data limit |
| `initial_max_stream_data` | Optional[int] | None | Initial max stream data |
| `quic_version` | Optional[str] | None | QUIC version to use |
| `handshake_timeout` | Optional[int] | None | Handshake timeout in seconds |
| `idle_timeout` | Optional[int] | None | Idle timeout in seconds |
| `verbose` | bool | False | Enable verbose logging |
| `debug_level` | Optional[int] | None | Debug logging level |

## Usage Example

```yaml
tests:
  - name: "lsquic Basic Test"
    network_environment:
      type: docker_compose
    services:
      server:
        implementation:
          name: lsquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
      client:
        implementation:
          name: lsquic
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
- Uses LiteSpeed's `http_server` and `http_client` executables with C-based compilation
- Docker-based deployment includes pre-built binaries with BoringSSL/OpenSSL and libevent dependencies
- Optimized for high-throughput server workloads, load testing, and CDN compatibility validation

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection drops | Check firewall UDP port configuration and certificate validity |
| Performance bottlenecks | Profile CPU usage, check memory allocation patterns, tune buffer sizes |
| TLS/security issues | Verify certificate trust chains and ALPN protocol negotiation |

## References

- [lsquic GitHub Repository](https://github.com/litespeedtech/lsquic)
- [LiteSpeed Technologies](https://www.litespeedtech.com/)
- [QUIC RFC 9000](https://tools.ietf.org/html/rfc9000)
