# aioquic QUIC Implementation

!!! warning "Development Status"
    This plugin is currently in development phase.

> **Plugin Type**: Service (Implementation Under Test)

> **Verified Source Location**: `plugins/services/iut/quic/aioquic/`

## Purpose and Overview

The aioquic plugin provides integration with Python's aioquic library, a pure Python implementation of QUIC and HTTP/3. Developed by Martin Thomson and the aioquic team, this implementation is particularly valuable for Python-based testing scenarios and educational purposes due to its readable, pure-Python codebase.

<!-- src: /panther/plugins/services/iut/quic/aioquic/aioquic.py -->

The aioquic implementation plugin enables:

- QUIC protocol testing in Python environments
- HTTP/3 over QUIC implementation evaluation
- Educational analysis of QUIC protocol mechanics
- Integration testing with Python-based networking applications
- Performance evaluation of Python QUIC implementations

## Python Inheritance Architecture

!!! info "Python-Specific Inheritance"
    The aioquic plugin inherits from `PythonQUICServiceManager` which extends `BaseQUICServiceManager`. This provides Python-specific functionality and async/await integration.

### Python Inheritance Chain

The aioquic implementation follows a specialized inheritance pattern for Python implementations:

```python
# panther/plugins/services/iut/quic/aioquic/aioquic.py
from panther.plugins.services.base.python_quic_base import PythonQUICServiceManager

class AioquicServiceManager(PythonQUICServiceManager):
    """Aioquic QUIC implementation with Python-specific inheritance."""

    def _get_implementation_name(self) -> str:
        return "aioquic"

    def _get_binary_name(self) -> str:
        return "python"

    def _get_python_module(self) -> str:
        return "aioquic.quic.server"  # Python module path

    # Customize Python-specific aspects
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        port = kwargs.get("port", 4433)
        return ["-m", self._get_python_module(), "--port", str(port)]

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 4433)
        return ["-m", "aioquic.quic.client", f"{host}:{port}"]

    # Python async/await integration handled by PythonQUICServiceManager
```

### Benefits of Python-Specific Architecture

- **69.0% Code Reduction**: From 245 lines to 76 lines of implementation code
- **Async/Await Integration**: Built-in asyncio event loop management
- **Python Package Management**: Automatic virtual environment and dependency handling
- **Memory Management**: Python-specific memory profiling and garbage collection monitoring
- **Exception Handling**: Python-specific exception catching and error reporting
- **Module Loading**: Dynamic Python module loading and import management

### Python Base Class Features

Inherited from `PythonQUICServiceManager`:

- **Virtual Environment**: Automatic Python venv creation and management
- **Package Installation**: Pip-based dependency installation
- **Async Support**: Native asyncio event loop integration
- **Python Profiling**: Built-in cProfile and memory_profiler integration
- **Exception Handling**: Python-specific error catching and traceback collection
- **Module Management**: Safe Python module loading and cleanup

### What's Provided by Base Classes

**From BaseQUICServiceManager:**
- Common QUIC parameter extraction and validation
- Standardized command generation patterns
- Event emission and lifecycle management
- Error handling and timeout management

**From PythonQUICServiceManager:**
- Python virtual environment management
- Async/await execution patterns
- Python-specific logging and debugging
- Memory and performance profiling for Python
- Package dependency resolution

### What's Customized for Aioquic

- **Python Module**: Uses `aioquic.quic.server` and `aioquic.quic.client` modules
- **Async Integration**: Leverages aioquic's native asyncio support
- **HTTP/3 Support**: Aioquic-specific HTTP/3 over QUIC implementation
- **Pure Python**: No C extensions, full Python implementation
- **Educational Features**: Enhanced debugging and introspection for learning

## Requirements and Dependencies

!!! info "Python Base Class Dependencies"
    The aioquic implementation automatically inherits all Python-specific base class dependencies, including virtual environment management, asyncio integration, and Python profiling tools. No additional setup is required for these core Python features.

The plugin requires:

- **Python**: Python 3.8 or higher (managed by PythonQUICServiceManager)
- **aioquic Library**: Pure Python QUIC implementation
- **cryptography**: Python cryptographic library for TLS operations
- **asyncio**: Python async/await framework support (integrated in base class)

Docker-based deployment handles dependency installation automatically through the Python base class dependency management system.

<!-- src: /panther/plugins/services/iut/quic/aioquic/config_schema.py -->

## Configuration Options

<!-- Source: config_schema.py -->
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

Inherited from `ServicePluginConfig` / `BasePluginConfig`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | True | Whether the plugin is enabled |
| `version` | Optional[str] | None | Plugin version |
| `priority` | int | 100 | Plugin execution priority |
| `docker_image` | Optional[str] | None | Docker image name |
| `build_from_source` | bool | True | Build from source |
| `source_repository` | Optional[str] | None | Source repository URL |

## Usage Examples

### Basic Server Configuration

```yaml
services:
  iut:
    type: "aioquic"
    role: "server"
    port: 4433
    certificate: "/certs/server.crt"
    private_key: "/certs/server.key"
    alpn_protocols: ["h3", "hq-interop"]
```

### Client Configuration

```yaml
services:
  iut:
    type: "aioquic"
    role: "client"
    host: "server.example.com"
    port: 4433
    alpn_protocols: ["h3"]
    keylog_file: "/logs/keylog.txt"
```

### Performance Testing Setup

```yaml
services:
  iut:
    type: "aioquic"
    role: "server"
    port: 4433
    max_stream_data: 16777216  # 16MB
    max_data: 167772160        # 160MB
    http3_enabled: true
    logging_level: "WARNING"   # Reduced logging for performance
```

### Educational/Debug Configuration

```yaml
services:
  iut:
    type: "aioquic"
    role: "server"
    port: 4433
    keylog_file: "/debug/aioquic-keys.log"
    logging_level: "DEBUG"
    idle_timeout: 300  # Extended for analysis
```

## Features

### QUIC Protocol Support

- **RFC 9000**: Full QUIC transport protocol implementation
- **Stream Management**: Multiple concurrent streams with flow control
- **Connection Migration**: Transparent connection endpoint changes
- **0-RTT**: Zero Round Trip Time connection establishment
- **Path MTU Discovery**: Automatic maximum transmission unit detection

### HTTP/3 Integration

- **HTTP/3 Semantics**: HTTP over QUIC with multiplexing
- **Server Push**: HTTP/3 server-initiated streams
- **Header Compression**: QPACK header compression
- **WebTransport**: Bidirectional communication over HTTP/3

### Security Features

- **TLS 1.3**: Integrated TLS 1.3 encryption
- **Certificate Validation**: X.509 certificate chain verification
- **ALPN Support**: Application Layer Protocol Negotiation
- **Key Logging**: TLS key extraction for debugging

### Python Integration

- **Asyncio Native**: Full async/await support
- **Pure Python**: No C extensions required
- **Educational Value**: Readable implementation for learning
- **Extensible**: Easy customization and extension

## Performance Characteristics

### Strengths

- **Ease of Use**: Simple Python API and integration
- **Debugging**: Excellent debugging and introspection capabilities
- **Portability**: Runs on any Python-supported platform
- **Educational**: Clear, readable implementation

### Considerations

- **Performance**: Python implementation may be slower than C/Rust equivalents
- **Memory Usage**: Higher memory footprint than native implementations
- **CPU Overhead**: Increased CPU usage for cryptographic operations

## Testing and Validation

### Conformance Testing

- QUIC protocol conformance against RFC specifications
- HTTP/3 compatibility with other implementations
- TLS 1.3 security validation

### Interoperability Testing

- Cross-implementation compatibility verification
- ALPN protocol negotiation testing
- Connection migration scenario validation

### Performance Testing

- Throughput measurement under various conditions
- Latency analysis for different stream patterns
- Memory usage profiling during sustained operations

## Development and Extension

### Customization Points

- Protocol parameter tuning through configuration
- Custom stream handling logic
- Extended logging and metrics collection
- Application-specific ALPN protocol support

### Integration Guidelines

- Use asyncio event loops for concurrent operations
- Implement proper exception handling for network errors
- Configure appropriate timeouts for test scenarios
- Enable key logging for protocol analysis

### Common Extension Patterns

```python
# Custom stream handler
class CustomStreamHandler:
    async def handle_stream(self, stream):
        # Custom stream processing logic
        pass

# Extended logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Troubleshooting

### Common Issues

**Connection Timeouts**

- Verify network connectivity and firewall rules
- Check certificate validity and trust chain
- Increase idle timeout for slow networks

**Certificate Errors**

- Ensure certificate matches hostname/IP
- Verify certificate chain is complete
- Check certificate expiration dates

**Performance Issues**

- Monitor Python garbage collection overhead
- Consider using PyPy for improved performance
- Profile CPU usage during cryptographic operations

### Debug Configuration

```yaml
services:
  iut:
    type: "aioquic"
    logging_level: "DEBUG"
    keylog_file: "/debug/keys.log"
    idle_timeout: 300
```

## Related Documentation

- [QUIC Protocol Overview](panther/plugins/services/iut/quic/README.md): General QUIC testing guide
- [Performance Testing](panther/plugins/services/iut/quic/docs/performance.md): Optimization strategies
- [Integration Examples](panther/plugins/services/iut/quic/docs/integration.md): Usage patterns

## References

- [aioquic GitHub Repository](https://github.com/aiortc/aioquic)
- [QUIC RFC 9000](https://tools.ietf.org/html/rfc9000)
- [HTTP/3 RFC 9114](https://tools.ietf.org/html/rfc9114)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
