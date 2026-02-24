# Client-Server Protocols Index

**Traditional request-response protocol architectures for network testing**

This section covers protocol plugins that implement traditional client-server communication patterns, where clients initiate connections and requests to servers.

## Available Client-Server Protocols

### Core Protocols

* **[HTTP](http/README.md)** - Hypertext Transfer Protocol
  * Support for HTTP/1.1, HTTP/2, and HTTP/3
  * TLS encryption and certificate management
  * RESTful API testing capabilities

* **[QUIC](quic/README.md)** - Quick UDP Internet Connections
  * Modern transport protocol with built-in encryption
  * 0-RTT connection establishment
  * Connection migration and multiplexing

* **[MiniP](minip/README.md)** - Minimal Internet Protocol
  * Simplified protocol for educational and testing purposes
  * Lightweight implementation for basic connectivity testing
  * Ideal for formal verification scenarios

## Protocol Selection Guide

| Use Case | Recommended Protocol | Notes |
|----------|---------------------|-------|
| Web application testing | HTTP | Traditional web protocols |
| Modern transport research | QUIC | Latest networking innovations |
| Educational/Formal testing | MiniP | Simplified protocol semantics |
| Performance benchmarking | QUIC, HTTP | Production-grade implementations |

## Configuration Pattern

All client-server protocols follow this configuration structure:

```yaml
services:
  server:
    protocol:
      name: quic  # or http, minip
      version: rfc9000
      role: server
    implementation:
      name: picoquic
      type: iut

  client:
    protocol:
      name: quic
      version: rfc9000
      role: client
      target: server  # References server service
    implementation:
      name: picoquic
      type: iut
```

## Integration with PANTHER

Client-server protocols integrate with:

- **[Service Plugins](../../services/README.md)** - Implementation under test (IUT) and tester services
- **[Environment Plugins](../../environments/README.md)** - Network and execution environments
- **[Core Framework](../../../core/README.md)** - Event system and metrics collection

## Getting Started

1. **Choose a protocol** based on your testing requirements
2. **Select implementations** from available service plugins
3. **Configure environment** (Docker Compose, localhost, or Shadow NS)
4. **Run experiments** using PANTHER's 4-phase execution model

For detailed examples, see [Quick Start Guide](../../../../QUICK_START.md).

## Development

To create new client-server protocol plugins, see the [Protocol Development Guide](../development.md).
