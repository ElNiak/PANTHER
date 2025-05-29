# Quant QUIC Implementation

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

## Requirements and Dependencies

The plugin requires:

- **Quant Library**: Academic QUIC implementation in C
- **OpenSSL**: Cryptographic operations and TLS 1.3
- **libev**: Event loop library for network operations
- **Build Tools**: GCC/Clang, make, cmake, pkg-config

Docker-based deployment includes all necessary dependencies and build environment.

<!-- src: /panther/plugins/services/iut/quic/quant/config_schema.py -->

## Configuration Options

### Version Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `version` | String | "" | Quant library version/branch |
| `commit` | String | "" | Specific git commit hash |
| `dependencies` | List | [] | Additional library dependencies |

### Basic Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `role` | String | "server" | Service role: "server" or "client" |
| `port` | Integer | 4433 | QUIC port number |
| `bind_addr` | String | "0.0.0.0" | Address to bind (server mode) |
| `server_addr` | String | "" | Server address (client mode) |
| `cert_file` | String | "" | X.509 certificate file path |
| `key_file` | String | "" | Private key file path |

### Protocol Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `quic_version` | String | "1" | QUIC version to use |
| `alpn_protocols` | List | ["hq-interop"] | ALPN protocol negotiation list |
| `initial_max_data` | Integer | 1048576 | Initial connection data limit |
| `initial_max_stream_data` | Integer | 262144 | Initial stream data limit |
| `max_streams_bidi` | Integer | 100 | Maximum bidirectional streams |
| `max_streams_uni` | Integer | 100 | Maximum unidirectional streams |

### Research and Debug Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `debug_level` | Integer | 0 | Debug verbosity (0-5) |
| `qlog_enabled` | Boolean | false | Enable qlog tracing |
| `qlog_file` | String | "" | qlog output file path |
| `keylog_file` | String | "" | TLS keylog file for analysis |
| `packet_trace` | Boolean | false | Enable packet-level tracing |

### Experimental Features

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_0rtt` | Boolean | false | Enable 0-RTT connection establishment |
| `connection_migration` | Boolean | false | Enable connection migration |
| `multipath` | Boolean | false | Enable multipath QUIC (experimental) |
| `spin_bit` | Boolean | false | Enable spin bit for latency measurement |
| `loss_detection_algo` | String | "rfc" | Loss detection algorithm variant |

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
