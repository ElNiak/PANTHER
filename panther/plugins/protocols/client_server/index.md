# Client-Server Protocol Plugins

> **Plugin Type**: Client-Server Protocol
> **Verified Source Location**: `plugins/protocols/client_server/`

## Overview

Client-server protocol plugins implement communication protocols following the traditional client-server model. These plugins encapsulate the logic, configuration, and behaviors of protocols where clients initiate requests to servers.

<!-- src: /panther/plugins/protocols/client_server/ -->

## Available Plugins

| Protocol | Description | Documentation |
|----------|-------------|---------------|
| HTTP | Hypertext Transfer Protocol | [Documentation](panther/plugins/protocols/client_server/http/README.md) |
| QUIC | Quick UDP Internet Connections | [Documentation](panther/plugins/protocols/client_server/quic/README.md) |
| MinIP | Minimal Internet Protocol | [Documentation](panther/plugins/protocols/client_server/minip/README.md) |

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

To create a new client-server protocol plugin, see the [Protocol Development Guide](panther/plugins/protocols/development.md) for instructions and best practices.
