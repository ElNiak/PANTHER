# QUIC Protocol Implementations

**Comprehensive QUIC implementation testing for protocol research and validation**

PANTHER provides multiple production-grade QUIC implementations that can be tested individually or compared against each other. All implementations follow consistent configuration patterns and provide the same core functionality through a modern inheritance-based architecture.

> [!NOTE]
> "Inheritance Architecture"
> All QUIC implementations inherit from `BaseQUICServiceManager`, providing code reuse and consistent behavior. The template method pattern allows implementation-specific customization.

> [!TIP]
> "Getting Started with QUIC"
> For your first QUIC experiment, try the [Quick Start Guide](../../../../../QUICK_START.md) which uses PicoQUIC as an example. All QUIC implementations in PANTHER follow the same configuration patterns and inherit from the same base classes.

## Available QUIC Implementations

| Implementation | Language | Strengths | Use Cases |
|---------------|----------|-----------|-----------|
| **[PicoQUIC](picoquic/README.md)** | C | Mature, RFC-compliant | Baseline testing, interoperability |
| **[AioQUIC](aioquic/README.md)** | Python | Async/await, HTTP/3 | Python integration, async research |
| **[Quiche](quiche/README.md)** | Rust | Memory safety, performance | Security research, embedded |
| **[Quinn](quinn/README.md)** | Rust | Modern async | High-performance async testing |
| **[LsQUIC](lsquic/README.md)** | C | LiteSpeed optimized | Performance benchmarking |
| **[QUIC-Go](quic_go/README.md)** | Go | Goroutine-based | Concurrent testing scenarios |
| **[mvfst](mvfst/README.md)** | C++ | Facebook's impl | Large-scale deployment testing |
| **[Quant](quant/README.md)** | C | Research-focused | Academic research |
| **[PicoQUIC Shadow](picoquic_shadow/README.md)** | C | Shadow NS integration | Deterministic network simulation |

## Inheritance Architecture

> [!NOTE]
> "Base Class System"
> All QUIC implementations inherit from specialized base classes that provide common functionality through the template method pattern. This eliminates code duplication while maintaining implementation-specific customization.

### Base Class Hierarchy

```python
# Base inheritance structure
BaseQUICServiceManager           # Core QUIC functionality
├── PythonQUICServiceManager    # Python-specific (aioquic)
├── RustQUICServiceManager      # Rust-specific (quiche, quinn)
└── Direct inheritance          # C/Go implementations (picoquic, lsquic, etc.)
```

### What's Provided by Base Classes

**From BaseQUICServiceManager:**
- Common QUIC parameter extraction and validation
- Standardized command generation using template method pattern
- Event emission and lifecycle management
- Error handling and timeout management
- Docker integration and container build patterns
- Structured logging with correlation tracking

**Language-Specific Base Classes:**
- **PythonQUICServiceManager**: Virtual environment management, asyncio integration, Python profiling
- **RustQUICServiceManager**: Cargo build system, memory safety validation, cross-compilation support

### Template Method Pattern

Each implementation only needs to define what's unique:

```python
class PicoquicServiceManager(BaseQUICServiceManager):
    def _get_implementation_name(self) -> str:
        return "picoquic"

    def _get_binary_name(self) -> str:
        return "picoquicdemo"

    # Only implement what's specific to Picoquic
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        return ["-p", str(kwargs.get("port", 4443))]

    # All common QUIC functionality inherited!
```

### Benefits of Inheritance Architecture

- **47.2% Average Code Reduction**: Across all QUIC implementations
- **Consistent Behavior**: Common functionality shared via base classes
- **Single Point for Fixes**: Updates to base classes benefit all implementations
- **Event Integration**: Built-in event emission for monitoring and debugging
- **Command Processing**: Structured command generation through Command Processor
- **Maintainability**: Clear separation between common and implementation-specific code

## Common Configuration Pattern

All QUIC implementations use the same configuration structure:

```yaml
services:
  server:
    implementation:
      name: picoquic        # Or aioquic, quiche, quinn, etc.
      type: iut             # Implementation Under Test
    protocol:
      name: quic
      version: rfc9000      # QUIC standard version
      role: server
    timeout: 100            # Optional: service timeout in seconds

  client:
    implementation:
      name: picoquic        # Can mix different implementations
      type: iut
    protocol:
      name: quic
      version: rfc9000
      role: client
      target: server        # Connect to server service
    timeout: 100
```

## Common Features

All QUIC implementations provide:

- **RFC 9000 compliance** - Core QUIC functionality
- **TLS 1.3 encryption** - Automatic certificate generation
- **Connection migration** - IP address and port changes
- **0-RTT support** - Where implemented by the library
- **Flow control** - Stream and connection-level
- **Loss recovery** - Automatic retransmission
- **HTTP/3 support** - Where available

## Choosing an Implementation

### For Basic Protocol Testing
- **PicoQUIC**: Most stable, excellent RFC compliance
- **AioQUIC**: If you need Python integration

### For Performance Research
- **Quiche**: Rust memory safety with high performance
- **LsQUIC**: LiteSpeed's production-optimized implementation
- **mvfst**: Facebook's large-scale deployment experience

### For Advanced Research
- **Quinn**: Modern Rust async patterns
- **QUIC-Go**: Go's goroutine-based concurrency
- **Quant**: Research-focused with detailed diagnostics

### For Deterministic Testing
- **PicoQUIC Shadow**: Integrated with Shadow network simulator

## Configuration Examples

### Basic Client-Server Test
```yaml
tests:
  - name: "QUIC Handshake Test"
    services:
      server:
        implementation: {name: picoquic, type: iut}
        protocol: {name: quic, version: rfc9000, role: server}
      client:
        implementation: {name: picoquic, type: iut}
        protocol: {name: quic, version: rfc9000, role: client, target: server}
```

### Cross-Implementation Testing
```yaml
tests:
  - name: "PicoQUIC vs AioQUIC Interoperability"
    services:
      picoquic_server:
        implementation: {name: picoquic, type: iut}
        protocol: {name: quic, version: rfc9000, role: server}
      aioquic_client:
        implementation: {name: aioquic, type: iut}
        protocol: {name: quic, version: rfc9000, role: client, target: picoquic_server}
```

### Performance Comparison
```yaml
tests:
  - name: "Rust vs C Performance"
    execution_environment:
      - type: gperf_cpu     # Profile CPU usage
    services:
      quiche_server:
        implementation: {name: quiche, type: iut}
        protocol: {name: quic, version: rfc9000, role: server}
      # Test client connects and measures performance
```

## Integration with PANTHER

QUIC implementations integrate seamlessly with:

- **[Network Environments](../../../environments/network_environment/README.md)** - Docker Compose, localhost, Shadow NS
- **[Execution Environments](../../../environments/execution_environment/README.md)** - Performance profiling, system call tracing
- **[Formal Testing](../../testers/README.md)** - Ivy formal verification integration
- **[Core Framework](../../../../core/README.md)** - Event system and metrics collection

## Migration Guide

### Creating New QUIC Implementations

To create a new QUIC implementation, inherit from the appropriate base class:

```python
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager
from panther.plugins.plugin_decorators import register_plugin

@register_plugin(
    plugin_type="iut",
    name="my_quic_impl",
    version="1.0.0",
    description="My QUIC implementation",
    supported_protocols=["quic"],
    capabilities=["rfc9000"]
)
class MyQuicServiceManager(BaseQUICServiceManager):

    # Required: Implementation identification
    def _get_implementation_name(self) -> str:
        return "my_quic_impl"

    def _get_binary_name(self) -> str:
        return "my_quic_binary"

    # Required: Implementation-specific arguments
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        port = kwargs.get("port", 4443)
        return ["--listen", f"0.0.0.0:{port}"]

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 4443)
        return ["--connect", f"{host}:{port}"]

    # Required: Deployment configuration
    def generate_deployment_commands(self) -> str:
        return f"{self._get_binary_name()} --help"

    # Required: Preparation logic
    def _do_prepare(self, plugin_manager=None):
        # Implementation-specific setup
        pass
```

### Using Language-Specific Base Classes

For Python implementations:
```python
from panther.plugins.services.base.python_quic_base import PythonQUICServiceManager

class MyPythonQuicServiceManager(PythonQUICServiceManager):
    def _get_python_module(self) -> str:
        return "my_quic.server"
    # Python-specific methods automatically available
```

For Rust implementations:
```python
from panther.plugins.services.base.rust_quic_base import RustQUICServiceManager

class MyRustQuicServiceManager(RustQUICServiceManager):
    def _get_cargo_features(self) -> List[str]:
        return ["async", "crypto"]
    # Rust-specific methods automatically available
```

### Best Practices

**Do:**
- Inherit from the appropriate base class
- Override only what's specific to your implementation
- Use the template method pattern
- Leverage base class utilities for common operations
- Follow naming conventions (`<Implementation>ServiceManager`)

**Don't:**
- Reimplement common QUIC functionality
- Override main methods like `generate_run_command()`
- Skip the base class inheritance
- Implement your own event emission

### Migration from Legacy Implementations

If updating an existing implementation:

1. **Identify Base Class**: Choose BaseQUICServiceManager, PythonQUICServiceManager, or RustQUICServiceManager
2. **Extract Unique Methods**: Move implementation-specific logic to `_get_*_specific_args()` methods
3. **Remove Common Code**: Delete code that's now in the base class
4. **Update Configuration**: Ensure configuration schema matches base class expectations
5. **Test Integration**: Verify the implementation works with the inheritance system

## Getting Help

For implementation-specific questions, see the individual README files linked above. For general QUIC testing patterns, see the [Quick Start Guide](../../../../../QUICK_START.md).
