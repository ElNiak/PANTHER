# HTTP Protocol

> **Plugin Type**: Protocol (client_server)  
> **Verified Source Location**: `plugins/protocols/client_server/http/`  

## Purpose and Overview

The HTTP Protocol plugin provides support for the Hypertext Transfer Protocol (HTTP) in PANTHER, allowing testing of HTTP-based client-server communications. This plugin defines the configuration parameters and behavior expectations for HTTP implementations, supporting multiple versions of the protocol.

<!-- src: /panther/plugins/protocols/client_server/http/config_schema.py -->

HTTP is one of the fundamental protocols of the web, used for transmitting hypermedia documents and enabling communication between web servers and clients. This plugin supports:

- HTTP protocol versions (0.9, 2, 3)
- Client and server role configurations
- Integration with HTTP Implementation Under Test (IUT) plugins

## Requirements and Dependencies

The plugin requires:

- **Python Dependencies**:
  - dataclasses
  - enum

The plugin also integrates with:
- PANTHER service plugins implementing HTTP clients and servers
- Network environment plugins that support TCP/IP communication

## Configuration Options

The HTTP protocol plugin accepts the following configuration parameters:

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

## Usage Examples

### Basic HTTP Server Configuration

```yaml
tests:
  - name: "Basic HTTP Server Test"
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
        ports:
          - "80:80"
```

### HTTP Client Configuration

```yaml
tests:
  - name: "HTTP Client Test"
    services:
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

## Extension Points

The HTTP protocol plugin can be extended in several ways:

### Custom HTTP Version Support

You can extend the plugin to support additional HTTP versions:

```python
# Extend the version enum
from panther.plugins.protocols.client_server.http.config_schema import HttpConfig, VersionEnum

# Add new version
VersionEnum = Enum(
    "VersionEnum", ["0.9", "1.0", "1.1", "2", "3"]
)

class ExtendedHttpConfig(HttpConfig):
    """Enhanced HTTP configuration with additional versions."""
    version: VersionEnum = VersionEnum["1.1"]
```

### Protocol Extensions

Add support for HTTP extensions and features:

```python
@dataclass
class EnhancedHttpConfig(HttpConfig):
    """HTTP configuration with extension support."""
    websocket_enabled: bool = False
    compression: str = "none"  # none, gzip, deflate
    cache_control: str = "no-cache"
```

## Testing and Verification

To test the HTTP protocol plugin:

1. **Integration Tests**: Configure tests with HTTP servers and clients
2. **Validation**: Verify proper HTTP message construction and parsing
3. **Interoperability**: Test with different HTTP implementations

## Troubleshooting

### Common Issues

#### Version Compatibility

**Problem**: Incompatible HTTP versions between client and server  
**Solution**: Ensure client and server are configured with compatible HTTP versions

```yaml
# Ensure version consistency
server:
  protocol:
    version: "2"
client:
  protocol:
    version: "2"
```

#### Missing Target

**Problem**: HTTP client fails to connect because target is not specified  
**Solution**: Always specify the target service in client configuration

```yaml
client:
  protocol:
    role: "client"
    target: "http_server"  # Required for clients
```

#### Port Configuration

**Problem**: HTTP server not accessible  
**Solution**: Check port mapping configuration

```yaml
server:
  ports:
    - "80:80"  # Format is "host:container"
```

### Debugging Tips

- Use packet capture tools to inspect HTTP traffic
- Enable verbose logging in the HTTP implementations
- Check for proper protocol negotiation in HTTP/2
