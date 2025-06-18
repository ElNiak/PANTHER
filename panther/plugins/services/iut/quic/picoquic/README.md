# Picoquic QUIC Implementation

!!! info "Production QUIC Implementation"
    Picoquic is a mature, production-ready QUIC implementation by Christian Huitema. It provides excellent conformance to QUIC specifications and is actively maintained for both research and deployment use.

> **Plugin Type**: Service (Implementation Under Test)

> **Verified Source Location**: `plugins/services/iut/quic/picoquic/`

## Purpose and Overview

The Picoquic plugin provides integration with the Picoquic QUIC implementation, developed by Christian Huitema. Picoquic is a lightweight, portable implementation of the QUIC protocol that can function as both a client and server. This plugin enables testing and analysis of Picoquic's conformance to the QUIC specifications and its performance characteristics.

<!-- src: /panther/plugins/services/iut/quic/picoquic/picoquic.py -->

The Picoquic implementation plugin is particularly valuable for:

- Conformance testing against QUIC protocol specifications
- Interoperability testing with other QUIC implementations
- Performance benchmarking of QUIC transport features
- Security analysis of Picoquic's cryptographic components

## Inheritance Architecture

!!! info "Inheritance-Based Implementation"
    The Picoquic plugin inherits directly from `BaseQUICServiceManager`, providing code reuse and consistent behavior across all QUIC implementations.

### Inheritance Architecture

The Picoquic implementation follows the template method pattern:

```python
# panther/plugins/services/iut/quic/picoquic/picoquic.py
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager

class PicoquicServiceManager(BaseQUICServiceManager):
    """Picoquic QUIC implementation with inheritance-based architecture."""
    
    def _get_implementation_name(self) -> str:
        return "picoquic"
    
    def _get_binary_name(self) -> str:
        return "picoquicdemo"
    
    # Customize only what's unique to Picoquic
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        port = kwargs.get("port", 4443)
        return ["-p", str(port)]
    
    def _get_client_specific_args(self, **kwargs) -> List[str]:
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 4443)
        return [f"{host}", str(port)]
    
    # All common QUIC functionality inherited from BaseQUICServiceManager!
```

### Benefits of Inheritance Architecture

- **66.7% Code Reduction**: From 267 lines to 89 lines of implementation code
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

### What's Customized for Picoquic

- **Binary Name**: Uses `picoquicdemo` executable
- **Command Arguments**: Picoquic-specific argument formatting
- **Build Process**: C-based compilation with CMake
- **Implementation Details**: Picoquic-specific configuration options

## Requirements and Dependencies

!!! warning "Build Dependencies"
    Picoquic requires development tools (GCC, CMake) and OpenSSL 1.1.1+ to be available on the system. Docker deployment automatically handles these requirements but manual installation requires careful dependency management.

!!! info "Base Class Dependencies"
    The Picoquic implementation automatically inherits all base class dependencies, including the Command Processor, Event System, and common QUIC utilities. No additional setup is required for these core features.

The plugin requires:

- **Picoquic Binary**: The compiled Picoquic implementation (picoquicdemo)
- **OpenSSL**: For TLS support (1.1.1 or later)
- **System Dependencies**:
  - Development tools (gcc, cmake, make)
  - TLS development libraries

Docker-based deployment installs all necessary dependencies automatically.

## Configuration

PicoQUIC uses the standard PANTHER QUIC configuration pattern:

```yaml
services:
  server:
    implementation:
      name: picoquic       # Use PicoQUIC implementation
      type: iut            # Implementation Under Test
    protocol:
      name: quic
      version: rfc9000     # QUIC standard version
      role: server         # This service acts as server
    timeout: 100           # Optional: service timeout in seconds
    
  client:
    implementation:
      name: picoquic
      type: iut
    protocol:
      name: quic
      version: rfc9000
      role: client         # This service acts as client
      target: server       # Connect to the 'server' service above
    timeout: 100
```

### Optional Configuration Parameters

PicoQUIC supports additional configuration options:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `timeout` | 100 | Service timeout in seconds |
| `ports` | auto | Custom port mapping (e.g., `["4443:4443"]`) |
| `generate_new_certificates` | true | Auto-generate TLS certificates |

<!-- TLS certificates are automatically generated and managed by PANTHER -->

## Usage Examples

### Basic Client-Server Test

```yaml
tests:
  - name: "PicoQUIC Basic Test"
    description: "Simple QUIC client-server connection test"
    network_environment:
      type: docker_compose
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
      client:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: client
          target: server
    steps:
      wait: 30
```

### Performance Testing with PicoQUIC

```yaml
tests:
  - name: "PicoQUIC Performance Analysis"
    description: "CPU and memory profiling of PicoQUIC"
    network_environment:
      type: docker_compose
    execution_environment:
      - type: gperf_cpu    # Profile CPU usage
      - type: gperf_heap   # Profile memory usage
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
        timeout: 120       # Longer timeout for profiling
      client:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: client
          target: server
        timeout: 100
    steps:
      wait: 60
```

### Interoperability Testing

```yaml
tests:
  - name: "PicoQUIC vs AioQUIC"
    description: "Test PicoQUIC server with AioQUIC client"
    network_environment:
      type: docker_compose
    services:
      picoquic_server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
      aioquic_client:
        implementation:
          name: aioquic      # Different implementation
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: client
          target: picoquic_server
    steps:
      wait: 30
```

## Why Choose PicoQUIC?

**Strengths:**
- **Mature and stable** - Extensively tested and RFC-compliant
- **Excellent interoperability** - Works well with other QUIC implementations  
- **Good performance** - Optimized C implementation
- **Well-documented** - Clear command-line interface and logging
- **Active development** - Regularly updated by Christian Huitema

**Best for:**
- **Baseline testing** - Reliable reference implementation
- **Interoperability testing** - Proven compatibility with other implementations
- **Production testing** - Mature codebase suitable for real-world scenarios
- **Educational use** - Clear, well-documented implementation

**Consider alternatives if:**
- You need Python integration → Try [AioQUIC](../aioquic/README.md)
- You want memory safety → Try [Quiche](../quiche/README.md) or [Quinn](../quinn/README.md)
- You need maximum performance → Try [LsQUIC](../lsquic/README.md)

## Getting Help

- For QUIC testing patterns, see the main [QUIC overview](../README.md)
- For general PANTHER usage, see the [Quick Start Guide](../../../../../QUICK_START.md)
- For PicoQUIC-specific issues, check the [official PicoQUIC repository](https://github.com/private-octopus/picoquic)
