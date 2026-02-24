# Quant QUIC Implementation

!!! warning "Development Status"
    This plugin is currently in development phase.

> **Plugin Type**: Service (Implementation Under Test)

> **Verified Source Location**: `plugins/services/iut/quic/quant/`

## Purpose and Overview

The Quant plugin provides integration with the Quant QUIC implementation, a research-oriented C library developed for academic and experimental QUIC protocol evaluation. Quant focuses on protocol correctness, extensibility, and research applications rather than production performance, making it ideal for protocol research and educational purposes.

<!-- src: /panther/plugins/services/iut/quic/quant/quant.py -->

The Quant implementation plugin enables:

- Academic research and protocol experimentation
- QUIC specification conformance validation
- Educational protocol analysis and learning
- Experimental feature development and testing
- Protocol extension and modification research

## Inheritance Architecture

!!! info "Inheritance-Based Implementation"
    The Quant plugin uses PANTHER's inheritance architecture, inheriting directly from `BaseQUICServiceManager`. This provides benefits through code reuse and consistent behavior across all QUIC implementations while maintaining Quant's research-focused patterns and extensibility.

### Inheritance Architecture

The Quant implementation follows the template method pattern:

```python
# panther/plugins/services/iut/quic/quant/quant.py
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager

class QuantServiceManager(BaseQUICServiceManager):
    """Quant QUIC implementation with inheritance-based architecture."""

    def _get_implementation_name(self) -> str:
        return "quant"

    def _get_binary_name(self) -> str:
        return "client"  # or server

    # Customize only what's unique to Quant
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        port = kwargs.get("port", 4433)
        return ["-p", str(port)]

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 4433)
        return ["-h", host, "-p", str(port)]

    # All common QUIC functionality inherited from BaseQUICServiceManager!
```

### Benefits of Inheritance Architecture

- **Code Reduction**: From extensive manual implementation to focused research-specific patterns
- **Consistent Behavior**: Common QUIC functionality shared with all implementations
- **Automatic Updates**: New features in base class automatically available
- **Event Integration**: Built-in event emission for monitoring and debugging
- **Command Processing**: Structured command generation through Command Processor
- **Research Focus**: Allows focus on protocol innovation rather than infrastructure

### What's Provided by Base Class

- **Common Parameter Extraction**: Port, host, certificate handling
- **Standard Command Building**: Template method pattern for command generation
- **Event Emission**: Service lifecycle and status events
- **Error Handling**: Timeout management and failure recovery
- **Docker Integration**: Standardized container build patterns
- **Logging Integration**: Structured logging with correlation tracking

### What's Customized for Quant

- **Binary Name**: Uses Quant's research-focused `client` and `server` executables
- **Command Arguments**: Quant-specific argument formatting (`-p`, `-h`)
- **Build Process**: Academic C compilation with research extensions
- **Research Features**: Extensible architecture for protocol experimentation

## Requirements and Dependencies

!!! info "Base Class Dependencies"
    The Quant implementation automatically inherits all base class dependencies, including the Command Processor, Event System, and common QUIC utilities. No additional setup is required for these core features.

The plugin requires:

- **Quant Library**: Academic QUIC implementation in C
- **OpenSSL**: Cryptographic operations and TLS 1.3
- **libev**: Event loop library for network operations
- **Build Tools**: GCC/Clang, make, cmake, pkg-config

Docker-based deployment includes all necessary dependencies and build environment.

<!-- src: /panther/plugins/services/iut/quic/quant/config_schema.py -->

## Configuration Options

<!-- Source: config_schema.py -->

### QuantConfig Fields

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | "quant" | Implementation name |
| `type` | ImplementationType | IUT | Implementation type |
| `version` | QuantVersion | (loaded from YAML) | Version configuration |

### QuantVersion Fields

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `version` | str | "" | Version string |
| `commit` | str | "" | Git commit hash |
| `dependencies` | List[Dict[str, str]] | [] | Dependencies list |
| `client` | Optional[dict] | {} | Client configuration |
| `server` | Optional[dict] | {} | Server configuration |

Inherited from `ServicePluginConfig` / `BasePluginConfig`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | True | Whether the plugin is enabled |
| `priority` | int | 100 | Plugin execution priority |
| `docker_image` | Optional[str] | None | Docker image name |
| `build_from_source` | bool | True | Build from source |
| `source_repository` | Optional[str] | None | Source repository URL |

## Usage Examples

### Basic Research Setup

```yaml
services:
  iut:
    type: "quant"
    role: "server"
    port: 4433
    cert_file: "/certs/test.crt"
    key_file: "/certs/test.key"
    debug_level: 2
    qlog_enabled: true
    qlog_file: "/logs/quant-trace.qlog"
```

### Protocol Conformance Testing

```yaml
services:
  iut:
    type: "quant"
    role: "server"
    port: 4433
    quic_version: "1"
    alpn_protocols: ["hq-interop", "h3"]
    initial_max_data: 1048576
    max_streams_bidi: 10
    keylog_file: "/debug/quant-keys.log"
    packet_trace: true
```

### Experimental Features Testing

```yaml
services:
  iut:
    type: "quant"
    role: "server"
    port: 4433
    # Enable experimental features
    enable_0rtt: true
    connection_migration: true
    multipath: true
    spin_bit: true
    debug_level: 3
```

### Client Testing Configuration

```yaml
services:
  iut:
    type: "quant"
    role: "client"
    server_addr: "research.example.com"
    port: 4433
    alpn_protocols: ["hq-interop"]
    qlog_enabled: true
    qlog_file: "/logs/client-trace.qlog"
    debug_level: 1
```

## Features

### Research-Oriented Design

- **Clean Implementation**: Readable, well-documented code
- **Modular Architecture**: Easy modification and extension
- **Extensive Logging**: Detailed protocol event tracing
- **Debugging Support**: Rich debugging and analysis tools

### QUIC Protocol Support

- **RFC 9000 Compliance**: Full QUIC transport implementation
- **Version Negotiation**: Multi-version support for compatibility
- **Stream Management**: Bidirectional and unidirectional streams
- **Flow Control**: Connection and stream-level flow control
- **Loss Recovery**: Configurable loss detection algorithms

### Experimental Features

- **0-RTT Connections**: Zero Round Trip Time establishment
- **Connection Migration**: Transparent endpoint changes
- **Multipath QUIC**: Multiple network path utilization
- **Spin Bit**: Latency measurement support
- **Custom Extensions**: Framework for protocol extensions

### Analysis and Debugging

- **qlog Integration**: Detailed protocol event logging
- **Packet Tracing**: Complete packet-level analysis
- **TLS Key Logging**: Cryptographic key extraction
- **Performance Metrics**: Connection and stream statistics

## Research Applications

### Protocol Analysis

- QUIC specification conformance verification
- Interoperability testing with other implementations
- Protocol behavior analysis under various conditions
- Security property validation and testing

### Performance Research

- Congestion control algorithm evaluation
- Flow control mechanism analysis
- Loss recovery strategy comparison
- Network path utilization studies

### Educational Use Cases

- Protocol implementation learning
- Network programming education
- Cryptographic protocol analysis
- Distributed systems research

## Development and Extension

### Custom Protocol Extensions

```c
// Example: Custom frame type implementation
typedef struct custom_frame {
    quant_frame_type_t type;
    uint64_t custom_data;
    uint8_t flags;
} custom_frame_t;

// Register custom frame handler
int register_custom_frame(quant_conn_t *conn,
                         custom_frame_handler_t handler);
```

### Research Hooks

```c
// Connection event callbacks
struct research_callbacks {
    void (*on_packet_sent)(quant_conn_t *, quant_pkt_t *);
    void (*on_packet_received)(quant_conn_t *, quant_pkt_t *);
    void (*on_loss_detected)(quant_conn_t *, quant_pkt_t *);
    void (*on_rtt_updated)(quant_conn_t *, uint64_t rtt);
};
```

### Experimental Configuration

```yaml
services:
  iut:
    type: "quant"
    role: "server"
    # Research-specific settings
    custom_frame_types: [0x40, 0x41]  # Experimental frame types
    loss_detection_algo: "custom"      # Custom algorithm
    cc_algorithm: "experimental"       # Research congestion control
    debug_level: 5                     # Maximum verbosity
```

## Testing and Validation

### Conformance Testing

- QUIC specification compliance verification
- Cross-implementation interoperability testing
- Protocol state machine validation
- Error handling correctness verification

### Research Validation

- Custom extension functionality testing
- Performance characteristic measurement
- Protocol behavior analysis under stress
- Security property verification

### Educational Testing

```yaml
# Simple educational setup
services:
  iut:
    type: "quant"
    role: "server"
    port: 4433
    debug_level: 3
    qlog_enabled: true
    # Simplified parameters for learning
    max_streams_bidi: 1
    initial_max_data: 65536
```

## Troubleshooting

### Common Issues

**Build Problems**

- Ensure all development dependencies are installed
- Check OpenSSL version compatibility
- Verify libev library availability
- Review compiler version requirements

**Protocol Issues**

- Enable debug logging to trace protocol events
- Use qlog files for detailed protocol analysis
- Check certificate configuration and validity
- Verify network connectivity and firewall rules

**Research Setup Issues**

- Configure appropriate debug levels for analysis
- Enable packet tracing for detailed examination
- Use keylog files for cryptographic analysis
- Set up proper qlog visualization tools

### Debug Configuration

```yaml
services:
  iut:
    type: "quant"
    debug_level: 5          # Maximum debugging
    qlog_enabled: true
    qlog_file: "/debug/trace.qlog"
    keylog_file: "/debug/keys.log"
    packet_trace: true
```

### Analysis Tools Integration

```bash
# qlog analysis with qvis
qvis /debug/trace.qlog

# Wireshark analysis with keylog
wireshark -o tls.keylog_file:/debug/keys.log capture.pcap

# Custom analysis scripts
python analyze_quant_logs.py /debug/trace.qlog
```

## Related Documentation

- [QUIC Protocol Overview](panther/plugins/services/iut/quic/README.md): General QUIC implementation guide
- [Research Methodologies](panther/plugins/services/iut/quic/docs/research.md): Research best practices
- [Protocol Extensions](panther/plugins/services/iut/quic/docs/extensions.md): Extension development guide

## References

- [Quant QUIC Implementation](https://github.com/NTAP/quant)
- [QUIC RFC 9000](https://tools.ietf.org/html/rfc9000)
- [qlog Specification](https://tools.ietf.org/html/draft-ietf-quic-qlog)
- [QUIC Protocol Analysis](https://quicwg.org/)
- [Academic QUIC Research](https://scholar.google.com/scholar?q=QUIC+protocol+research)
