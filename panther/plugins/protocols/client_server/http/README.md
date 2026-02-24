# HTTP Protocol

> **Plugin Type**: Protocol
> **Source Location**: `plugins/protocols/client_server/http/`

## Overview

The HTTP Protocol plugin provides support for the Hypertext Transfer Protocol (HTTP) in PANTHER, allowing testing of HTTP-based client-server communications. It defines configuration parameters and behavior expectations for HTTP implementations, supporting multiple versions of the protocol (0.9, 2, 3).

## Configuration Options

<!-- src: config_schema.py -->

```yaml
protocol:
  name: "HTTP"               # Protocol name
  version: "2"               # HTTP version (0.9, 2, 3)
  role: "server"             # Role (server, client)
  target: "http_client"      # Target service (for clients)
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | No | "HTTP" | Protocol identifier |
| `version` | string | No | "random" | HTTP version (0.9, 2, 3) |
| `role` | string | No | "server" | Role in communication (server, client) |
| `target` | string | No | None | Target service name (required for clients) |

## Usage Example

```yaml
tests:
  - name: "HTTP Server Test"
    services:
      server:
        name: "http_server"
        implementation:
          name: "nginx"
          type: "iut"
        protocol:
          name: "HTTP"
          version: "2"
          role: "server"
      client:
        name: "http_client"
        implementation:
          name: "curl"
          type: "iut"
        protocol:
          name: "HTTP"
          version: "2"
          role: "client"
          target: "http_server"
```

## Integration

- Works with PANTHER service plugins implementing HTTP clients and servers
- Requires network environment plugins that support TCP/IP communication
- Client role requires the `target` field to specify which server service to connect to
- Supports HTTP/2 and HTTP/3 protocol negotiation between endpoints

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Version incompatibility | Ensure client and server are configured with compatible HTTP versions |
| Missing target | Always specify the `target` service in client configuration |
| Server not accessible | Check port mapping configuration (format: `"host:container"`) |
