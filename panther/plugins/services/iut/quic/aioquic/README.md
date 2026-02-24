# aioquic

> **Plugin Type**: Service (IUT)
> **Source Location**: `plugins/services/iut/quic/aioquic/`

## Overview

The aioquic plugin provides integration with Python's aioquic library, a pure Python implementation of QUIC and HTTP/3. Developed by the aioquic team, this implementation is particularly valuable for Python-based testing scenarios and educational purposes due to its readable, pure-Python codebase with native asyncio support.

## Configuration Options

<!-- src: config_schema.py -->

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | "aioquic" | Implementation name |
| `server_root` | str | "/var/www" | Document root for serving files |
| `server_certificate` | Optional[str] | "/certs/cert.pem" | Server certificate path |
| `server_private_key` | Optional[str] | "/certs/key.pem" | Server private key path |
| `session_ticket_store` | Optional[str] | None | Session ticket store path |
| `client_output_dir` | str | "/app/logs/artifacts" | Client output directory |
| `client_insecure` | bool | True | Skip certificate verification |
| `client_legacy_http` | bool | False | Enable legacy HTTP support |
| `verbose` | bool | False | Enable verbose logging |
| `secrets_log` | Optional[str] | None | Path to secrets log file |
| `python_path` | str | "/opt/aioquic" | Python path for aioquic |
| `examples_dir` | str | "/opt/aioquic/examples" | Examples directory |
| `enable_http3` | bool | True | Enable HTTP/3 support |
| `enable_websockets` | bool | True | Enable WebSocket support |
| `enable_priority` | bool | True | Enable stream priority |
| `enable_push` | bool | True | Enable server push |
| `enable_datagram` | bool | True | Enable datagram support |

## Usage Example

```yaml
tests:
  - name: "aioquic Basic Test"
    network_environment:
      type: docker_compose
    services:
      server:
        implementation:
          name: aioquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
      client:
        implementation:
          name: aioquic
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

- Inherits from `PythonQUICServiceManager` which extends `BaseQUICServiceManager`, providing Python-specific async/await integration
- Docker-based deployment handles Python dependency installation automatically through the base class
- Supports HTTP/3, WebSocket, server push, and datagram features over QUIC
- Pure Python implementation with no C extensions, suitable for educational and debugging use

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeouts | Verify network connectivity, check certificate validity, increase idle timeout |
| Certificate errors | Ensure certificate matches hostname/IP and chain is complete |
| Performance issues | Monitor Python GC overhead; consider PyPy for improved performance |

## References

- [aioquic GitHub Repository](https://github.com/aiortc/aioquic)
- [QUIC RFC 9000](https://tools.ietf.org/html/rfc9000)
- [HTTP/3 RFC 9114](https://tools.ietf.org/html/rfc9114)
