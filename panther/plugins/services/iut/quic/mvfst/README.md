# mvfst QUIC Implementation

!!! warning "Development Status"
    This plugin is currently in development phase.

> **Plugin Type**: Service (Implementation Under Test)

> **Parent Plugin**: [QUIC IUT](panther/plugins/services/iut/quic/README.md)

> **Source Location**: `plugins/services/iut/quic/mvfst/`

## Overview

The mvfst plugin provides integration with Meta's mvfst QUIC implementation. mvfst is a high-performance, production-ready QUIC transport library written in C++ and developed by Meta (formerly Facebook). This plugin enables comprehensive testing of mvfst's QUIC implementation within the PANTHER framework.

<!-- src: /panther/plugins/services/iut/quic/mvfst/mvfst.py -->

mvfst implementation features:

- **Production-Grade Performance**: Optimized for high-throughput applications
- **C++ Implementation**: High-performance native implementation
- **Facebook Scale**: Battle-tested in Meta's production environments
- **Congestion Control Innovation**: Advanced congestion control algorithms
- **HTTP/3 Support**: Full HTTP/3 implementation support

## Inheritance Architecture

!!! info "Inheritance-Based Implementation"
    The mvfst plugin uses PANTHER's inheritance architecture, inheriting directly from `BaseQUICServiceManager`. This provides benefits through code reuse and consistent behavior across all QUIC implementations while maintaining Meta's production-optimized patterns.

### Inheritance Architecture

The mvfst implementation follows the template method pattern:

```python
# panther/plugins/services/iut/quic/mvfst/mvfst.py
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager

class MvfstServiceManager(BaseQUICServiceManager):
    """Meta's mvfst QUIC implementation with inheritance-based architecture."""

    def _get_implementation_name(self) -> str:
        return "mvfst"

    def _get_binary_name(self) -> str:
        return "echo"  # Meta's echo server/client

    # Customize only what's unique to mvfst
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        port = kwargs.get("port", 6666)
        return ["--mode=server", f"--port={port}"]

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 6666)
        return ["--mode=client", f"--host={host}", f"--port={port}"]

    # All common QUIC functionality inherited from BaseQUICServiceManager!
```

### Benefits of Inheritance Architecture

- **Code Reduction**: From extensive manual implementation to focused Meta-specific patterns
- **Consistent Behavior**: Common QUIC functionality shared with all implementations
- **Automatic Updates**: New features in base class automatically available
- **Event Integration**: Built-in event emission for monitoring and debugging
- **Command Processing**: Structured command generation through Command Processor
- **Error Handling**: Comprehensive error handling and recovery mechanisms

### What's Provided by Base Class

- **Common Parameter Extraction**: Port, host, certificate handling
- **Standard Command Building**: Template method pattern for command generation
- **Event Emission**: Service lifecycle and status events
- **Error Handling**: Timeout management and failure recovery
- **Docker Integration**: Standardized container build patterns
- **Logging Integration**: Structured logging with correlation tracking

### What's Customized for mvfst

- **Binary Name**: Uses Meta's `echo` server/client executables
- **Command Arguments**: mvfst-specific argument formatting (`--mode`, `--port`)
- **Build Process**: C++ compilation with Folly and Fizz dependencies
- **Facebook Patterns**: Production-optimized configuration for large-scale deployment

## Requirements and Dependencies

!!! info "Base Class Dependencies"
    The mvfst implementation automatically inherits all base class dependencies, including the Command Processor, Event System, and common QUIC utilities. No additional setup is required for these core features.

The plugin requires:

- **mvfst Library**: Compiled mvfst QUIC library
- **C++ Environment**: Modern C++ compiler (C++17 or later)
- **Folly Library**: Facebook's C++ library collection
- **Fizz**: Facebook's TLS 1.3 implementation
- **System Dependencies**:
  - CMake build system
  - Boost libraries
  - OpenSSL or BoringSSL

Docker-based deployment installs all necessary dependencies automatically.

## Configuration Options

<!-- Source: config_schema.py -->

### MvfstConfig Fields

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | "mvfst" | Implementation name |
| `type` | ImplementationType | IUT | Implementation type |
| `version` | MvfstVersion | (loaded from YAML) | Version configuration |

### MvfstVersion Fields

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `version` | str | "" | Git tag or release version string |
| `commit` | str | "" | Git commit hash for reproducible builds |
| `dependencies` | List[Dict[str, str]] | [] | Build-time dependency specifications |
| `client` | Optional[dict] | {} | Client-specific configuration |
| `server` | Optional[dict] | {} | Server-specific configuration |

Inherited from `ServicePluginConfig` / `BasePluginConfig`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | True | Whether the plugin is enabled |
| `priority` | int | 100 | Plugin execution priority |
| `docker_image` | Optional[str] | None | Docker image name |
| `build_from_source` | bool | True | Build from source |
| `source_repository` | Optional[str] | None | Source repository URL |

## Version Support

The plugin supports multiple QUIC specification versions and testing variants:

### RFC 9000

- **Description**: Final QUIC specification
- **Features**: Complete QUIC 1.0 implementation
- **Use Case**: Production and conformance testing

### Draft 29

- **Description**: QUIC draft-29 implementation
- **Features**: Near-final draft specification
- **Use Case**: Legacy compatibility testing

### Draft 27 Vulnerabilities

- **draft27-vuln1**: Implementation with specific vulnerability for security testing
- **draft27-vuln2**: Alternative vulnerability variant for security analysis
- **Use Case**: Security testing and penetration testing scenarios

## Usage Examples

### Basic mvfst Server

```yaml
tests:
  - name: "mvfst Server Test"
    network_environment:
      type: "docker_compose"
    services:
      mvfst_server:
        name: "mvfst_server"
        timeout: 100
        implementation:
          name: "quic/mvfst"
          type: "iut"
          version: "rfc9000"
        protocol:
          name: "quic"
          type: "protocol"
          role: "server"
        config:
          server_port: 6666
          congestion_control: "cubic"
```

### High-Performance Configuration

```yaml
tests:
  - name: "mvfst Performance Test"
    network_environment:
      type: "docker_compose"
    execution_environment:
      - type: "gperf_cpu"
    services:
      mvfst_server:
        name: "mvfst_server"
        timeout: 120
        implementation:
          name: "quic/mvfst"
          type: "iut"
          version: "rfc9000"
        protocol:
          name: "quic"
          type: "protocol"
          role: "server"
        config:
          server_port: 6666
          congestion_control: "bbr"
          max_data: 1073741824  # 1GB for high-throughput testing
          max_streams_bidi: 10000
          transport_params:
            max_idle_timeout: 60000
            max_udp_payload_size: 1452
```

### Security Vulnerability Testing

```yaml
tests:
  - name: "mvfst Security Analysis"
    network_environment:
      type: "docker_compose"
    services:
      mvfst_vulnerable:
        name: "mvfst_vulnerable"
        timeout: 180
        implementation:
          name: "quic/mvfst"
          type: "iut"
          version: "draft27-vuln1"
        protocol:
          name: "quic"
          type: "protocol"
          role: "server"
        config:
          server_port: 6666
          certificate_file: "/certs/test-cert.pem"
          private_key_file: "/certs/test-key.pem"
```

## Implementation Details

### Architecture

The mvfst implementation provides:

1. **Transport Layer**: Core QUIC protocol implementation
2. **Congestion Control**: Multiple advanced algorithms (BBR, COPA, etc.)
3. **Flow Control**: Sophisticated stream and connection management
4. **Security Layer**: Integration with Fizz TLS 1.3
5. **Performance Optimization**: Zero-copy networking and efficient data structures

### Advanced Features

- **Zero-RTT Support**: 0-RTT connection establishment
- **Connection Migration**: IP address and port migration support
- **Multipath QUIC**: Experimental multipath support
- **Advanced Loss Recovery**: Sophisticated packet loss detection and recovery

### File Structure

```text
mvfst/
├── README.md                 # This documentation
├── __init__.py              # Plugin initialization
├── mvfst.py                 # Main implementation
├── config_schema.py         # Configuration schema
├── Dockerfile               # Container build instructions
├── templates/              # Command templates
│   ├── client_command.jinja # Client command template
│   └── server_command.jinja # Server command template
├── version_configs/        # Version-specific configurations
│   ├── rfc9000.yaml        # RFC 9000 configuration
│   ├── draft29.yaml        # Draft 29 configuration
│   ├── draft27-vuln1.yaml  # Vulnerability variant 1
│   └── draft27-vuln2.yaml  # Vulnerability variant 2
└── file_to_change/         # Source modifications for testing
    └── rfc9000/            # Version-specific modifications
```

## Extension Points

### Custom Congestion Control Algorithms

Extend the plugin to test Meta's advanced congestion control:

```python
from panther.plugins.services.iut.quic.mvfst.mvfst import MvfstServiceManager

class EnhancedMvfstServiceManager(MvfstServiceManager):
    """Enhanced mvfst service manager with advanced CC algorithms."""

    def configure_copa_cc(self):
        """Configure COPA congestion control algorithm."""
        # Implementation for COPA-specific testing
        pass

    def configure_bbr_settings(self, variant: str):
        """Configure BBR algorithm variants."""
        # Implementation for BBR tuning
        pass
```

### Performance Monitoring

Extend for detailed performance analysis:

```python
def setup_performance_monitoring(self):
    """Configure mvfst performance monitoring."""
    # Implementation for performance metrics collection
    pass

def analyze_throughput_metrics(self):
    """Analyze mvfst throughput characteristics."""
    # Implementation for throughput analysis
    pass
```

### Zero-RTT Testing

Add support for 0-RTT connection testing:

```python
def configure_zero_rtt_testing(self):
    """Configure 0-RTT connection establishment testing."""
    # Implementation for 0-RTT testing scenarios
    pass
```

## Testing and Verification

### Unit Tests

Run mvfst-specific tests:

```bash
python -m pytest panther/plugins/services/iut/quic/mvfst/tests/
```

### Integration Tests

Test interoperability with other QUIC implementations:

```bash
# Test against Picoquic
python -m pytest tests/integration/test_mvfst_picoquic_interop.py

# Test against Quiche
python -m pytest tests/integration/test_mvfst_quiche_interop.py
```

### Performance Benchmarks

```bash
# Run high-performance benchmarks
python -m pytest tests/performance/test_mvfst_performance.py --benchmark

# Test congestion control algorithms
python -m pytest tests/performance/test_mvfst_congestion_control.py
```

### Security Testing

```bash
# Test vulnerability variants
python -m pytest tests/security/test_mvfst_vulnerabilities.py

# Test security features
python -m pytest tests/security/test_mvfst_security.py
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Build failures | Ensure C++17 compiler and all Meta dependencies are available |
| Folly dependency issues | Verify Folly library installation and version compatibility |
| Performance issues | Tune congestion control and transport parameters |
| Memory usage concerns | Adjust max_data and stream limits for available memory |
| Connection failures | Check network configuration and firewall settings |
| Certificate issues | Verify TLS certificate and key file validity |

### Debugging

Enable comprehensive logging for debugging:

```yaml
logging:
  level: DEBUG
  format: "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
  mvfst_debug: true
  congestion_control_debug: true
```

For C++ level debugging, compile mvfst with debug symbols and use gdb or lldb:

```bash
# Debug with gdb
gdb --args mvfst_server --config server.json

# Debug with lldb
lldb -- mvfst_server --config server.json
```

## Performance Tuning

### High-Throughput Configuration

For maximum throughput:

```yaml
config:
  congestion_control: "bbr"
  max_data: 1073741824  # 1GB
  max_streams_bidi: 10000
  transport_params:
    max_udp_payload_size: 1452  # Optimal for most networks
    max_idle_timeout: 60000
```

### Low-Latency Configuration

For minimum latency:

```yaml
config:
  congestion_control: "copa"
  transport_params:
    max_udp_payload_size: 1200
    max_idle_timeout: 10000
```

## See Also

- [QUIC IUT Plugin](panther/plugins/services/iut/quic/README.md) - Parent plugin documentation
- [QUIC Protocol Plugin](panther/plugins/services/protocols/client_server/quic/README.md) - QUIC protocol implementation
- [Picoquic Plugin](panther/plugins/services/iut/quic/picoquic/README.md) - Alternative QUIC implementation
- [Quiche Plugin](panther/plugins/services/iut/quic/quiche/README.md) - Rust-based QUIC implementation
- [Service Plugin Development Guide](panther/plugins/services/iut/development.md) - General development guidelines
