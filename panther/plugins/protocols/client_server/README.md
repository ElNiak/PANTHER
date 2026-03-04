# Client-Server Protocol Plugins

!!! info "Traditional Protocol Architecture"
    Client-server protocol plugins implement protocols where clients initiate requests to servers in a traditional request-response pattern. These are the most common network protocol architectures.

> **Plugin Type**: Client-Server Protocol

> **Verified Source Location**: `plugins/protocols/client_server/`

## Overview

Client-server protocol plugins implement communication protocols following the traditional client-server model. These plugins encapsulate the logic, configuration, and behaviors of protocols where clients initiate requests to servers.

<!-- src: /panther/plugins/protocols/client_server/ -->

## Available Plugins

| Protocol | Description | Documentation |
|----------|-------------|---------------|
| HTTP | Hypertext Transfer Protocol | [Documentation](http/README.md) |
| QUIC | Quick UDP Internet Connections | [Documentation](quic/README.md) |
| MinIP | Minimal Internet Protocol | [Documentation](minip/README.md) |

## Common Configuration

Client-server protocol plugins typically share these configuration patterns:

```yaml
protocols:
  - name: "http_protocol"
    type: "protocol"
    implementation: "client_server/http"
    config:
      version: "1.1"  # HTTP version
      tls: true       # Enable TLS
```

## Integration Points

Client-server protocol plugins integrate with:

1. **Service plugins**: Services implement specific protocol versions/behaviors
2. **Environment plugins**: Network environments affect protocol behavior
3. **Core framework**: Protocol metrics and analysis feed into the framework

## Development

To create a new client-server protocol plugin, see the [Protocol Development Guide](../development.md) for instructions and best practices.
