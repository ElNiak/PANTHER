# HTTP Implementation Under Test

The HTTP IUT plugin provides HTTP protocol implementations for testing web server and client behavior within the PANTHER framework. This plugin enables testing of HTTP/1.1 and HTTP/2 implementations for compliance, performance, and security analysis.

!!! info "Plugin Information"
    **Plugin Type**: Service (Implementation Under Test)
    **Source Location**: `plugins/services/iut/http/`

!!! warning "Development Status"
    HTTP implementations are currently in development. Most functionality is planned for future releases. For immediate protocol testing, consider using the QUIC plugins which are production-ready.

<!-- src: /panther/plugins/services/iut/http/__init__.py -->

This implementation supports:

- **HTTP/1.1 Protocol Testing**: Standard HTTP protocol compliance testing
- **HTTP/2 Protocol Testing**: Modern HTTP protocol features and performance
- **Security Testing**: Analysis of HTTP security mechanisms and vulnerabilities
- **Performance Benchmarking**: HTTP server and client performance evaluation

## Available Implementations

The HTTP IUT plugin serves as a base for specific HTTP implementation plugins:

### Planned Implementations

- **Apache HTTP Server**: Industry-standard web server implementation
- **Nginx**: High-performance web server and reverse proxy
- **Node.js HTTP**: JavaScript-based HTTP server implementation
- **Custom HTTP**: Minimal HTTP implementation for educational purposes

## Configuration Schema

<!-- src: /panther/plugins/services/iut/http/config_schema.py -->

```yaml
services:
  - name: "http_server"
    implementation:
      name: "http/{specific_implementation}"
      type: "iut"
    protocol:
      name: "http"
      type: "protocol"
      version: "1.1"  # 1.1 or 2.0
      role: "server"  # server or client
    config:
      port: 8080
      ssl_enabled: false
      document_root: "/var/www/html"
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `port` | integer | No | 8080 | HTTP server port |
| `ssl_enabled` | boolean | No | false | Enable HTTPS |
| `document_root` | string | No | "/var/www/html" | Document root directory |
| `max_connections` | integer | No | 100 | Maximum concurrent connections |

## Usage Examples

### Basic HTTP Server Test

```yaml
tests:
  - name: "HTTP Server Test"
    network_environment:
      type: "docker_compose"
    services:
      http_server:
        name: "http_server"
        timeout: 60
        implementation:
          name: "http/apache"
          type: "iut"
        protocol:
          name: "http"
          type: "protocol"
          version: "1.1"
          role: "server"
        config:
          port: 8080
          document_root: "/var/www/html"
```

### HTTPS Security Testing

```yaml
tests:
  - name: "HTTPS Security Test"
    network_environment:
      type: "docker_compose"
    services:
      https_server:
        name: "https_server"
        timeout: 60
        implementation:
          name: "http/nginx"
          type: "iut"
        protocol:
          name: "http"
          type: "protocol"
          version: "1.1"
          role: "server"
        config:
          port: 443
          ssl_enabled: true
          certificate_file: "/certs/server.crt"
          private_key_file: "/certs/server.key"
```

## Directory Structure

```
http/
├── README.md                 # This documentation
├── __init__.py              # Plugin initialization and base classes
├── config_schema.py         # HTTP IUT configuration schema
├── apache/                  # Apache HTTP Server implementation
├── nginx/                   # Nginx implementation
├── nodejs/                  # Node.js HTTP implementation
└── custom/                  # Custom minimal HTTP implementation
```

## Development

### Adding New HTTP Implementations

To add a new HTTP implementation:

1. Create a subdirectory for the implementation (e.g., `lighttpd/`)
2. Implement the IUT interface with HTTP-specific functionality
3. Add configuration schema for the implementation
4. Create Dockerfile for containerized deployment
5. Add comprehensive documentation and examples

### Base Classes

The HTTP IUT plugin provides base classes for implementation development:

```python
from panther.plugins.services.iut.http import HTTPImplementationBase

class MyHTTPImplementation(HTTPImplementationBase):
    """Custom HTTP implementation."""

    def start_server(self):
        """Start the HTTP server."""
        pass

    def stop_server(self):
        """Stop the HTTP server."""
        pass
```

## Integration Testing

Test HTTP implementations with various protocols and environments:

```bash
# Run HTTP conformance tests
python -m pytest panther/plugins/services/iut/http/tests/

# Run security tests
python -m pytest panther/plugins/services/iut/http/tests/security/

# Run performance benchmarks
python -m pytest panther/plugins/services/iut/http/tests/performance/
```

## See Also

- [Services Plugin Documentation](panther/plugins/services/README.md) - Parent plugin system
- [IUT Development Guide](panther/plugins/services/iut/development.md) - IUT-specific development guidelines
- [HTTP Protocol Plugin](panther/plugins/protocols/client_server/http/README.md) - HTTP protocol implementation
