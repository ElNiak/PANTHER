# Quiche QUIC Implementation

> [!WARNING]
> "Development Status"
> This plugin is currently in development phase.

> **Plugin Type**: Service (Implementation Under Test)

> **Parent Plugin**: [QUIC IUT](../README.md)

> **Source Location**: `plugins/services/iut/quic/quiche/`

## Overview

The Quiche plugin provides integration with Cloudflare's Quiche QUIC implementation. Quiche is a high-performance QUIC library written in Rust that prioritizes security, correctness, and performance. This plugin enables comprehensive testing of Quiche's QUIC implementation within the PANTHER framework.

<!-- src: /panther/plugins/services/iut/quic/quiche/quiche.py -->

Quiche implementation features:

- **Rust-based Implementation**: Memory-safe and performance-focused implementation
- **RFC 9000 Compliance**: Full QUIC specification compliance
- **HTTP/3 Support**: Built-in HTTP/3 protocol support
- **Security Focus**: Emphasis on secure and correct implementation

## Rust Inheritance Architecture

> [!NOTE]
> "Rust-Specific Inheritance"
> The Quiche plugin inherits from `RustQUICServiceManager` which extends `BaseQUICServiceManager`. This provides Rust-specific functionality including Cargo build integration and memory safety features.

### Rust Inheritance Chain

The Quiche implementation follows a specialized inheritance pattern for Rust implementations:

```python
# panther/plugins/services/iut/quic/quiche/quiche.py
from panther.plugins.services.base.rust_quic_base import RustQUICServiceManager

class QuicheServiceManager(RustQUICServiceManager):
    """Quiche QUIC implementation with Rust-specific inheritance."""

    def _get_implementation_name(self) -> str:
        return "quiche"

    def _get_binary_name(self) -> str:
        return "quiche-server"  # or quiche-client

    def _get_cargo_features(self) -> List[str]:
        return ["boring-sys", "ffi"]  # Quiche-specific Cargo features

    # Customize Rust-specific aspects
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        port = kwargs.get("port", 4443)
        return ["--listen", f"0.0.0.0:{port}"]

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 4443)
        return ["--connect-to", f"{host}:{port}"]

    # Rust compilation and memory safety handled by RustQUICServiceManager
```

### Benefits of Rust-Specific Architecture

- **69.1% Code Reduction**: From 298 lines to 92 lines of implementation code
- **Memory Safety**: Built-in Rust memory safety validation and profiling
- **Cargo Integration**: Automatic Cargo build system integration and feature management
- **Performance Optimization**: Rust-specific performance monitoring and optimization
- **Cross-compilation**: Support for multiple target architectures
- **Dependency Management**: Automatic Cargo.toml and crate dependency handling

### Rust Base Class Features

Inherited from `RustQUICServiceManager`:

- **Cargo Build System**: Automatic `cargo build` and feature flag management
- **Memory Profiling**: Integration with Rust memory profilers (Valgrind, heaptrack)
- **Performance Monitoring**: Built-in benchmarking and performance analysis
- **Cross-compilation**: Support for different target architectures
- **Dependency Validation**: Cargo.lock and dependency security scanning
- **Rust Toolchain**: Automatic Rust toolchain installation and management

### What's Provided by Base Classes

**From BaseQUICServiceManager:**
- Common QUIC parameter extraction and validation
- Standardized command generation patterns
- Event emission and lifecycle management
- Error handling and timeout management

**From RustQUICServiceManager:**
- Cargo build system integration
- Rust-specific memory safety validation
- Performance benchmarking and profiling
- Cross-compilation support
- Rust toolchain management
- Dependency security scanning

### What's Customized for Quiche

- **BoringSSL Integration**: Quiche-specific BoringSSL cryptographic backend
- **Cargo Features**: Cloudflare-specific Cargo features (`boring-sys`, `ffi`)
- **Binary Names**: Uses `quiche-server` and `quiche-client` executables
- **Memory Safety**: Leverages Rust's ownership system for zero-copy operations
- **Performance**: Optimized for Cloudflare's high-performance requirements

## Requirements and Dependencies

> [!NOTE]
> "Rust Base Class Dependencies"
> The Quiche implementation automatically inherits all Rust-specific base class dependencies, including Cargo build system integration, Rust toolchain management, and memory profiling tools. No additional setup is required for these core Rust features.

The plugin requires:

- **Quiche Library**: Compiled Quiche QUIC library (built via Cargo)
- **Rust Environment**: Rust compiler and Cargo (managed by RustQUICServiceManager)
- **BoringSSL**: Cryptographic library for TLS support
- **System Dependencies**:
  - Development tools (cmake, make, gcc)
  - Network libraries

Docker-based deployment installs all necessary dependencies automatically through the Rust base class dependency management system.

## Configuration Options

<!-- Source: config_schema.py -->

### QuicheConfig Fields

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | "quiche" | Implementation name |
| `type` | ImplementationType | IUT | Implementation type |
| `version` | QuicheVersion | (loaded from YAML) | Version configuration |

### QuicheVersion Fields

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

## Command Generation

The Quiche plugin uses structured command generation with proper argument escaping to ensure robust operation in all environments. Command arguments are handled as structured data rather than concatenated strings, avoiding issues with special characters, spaces, and quotes.

### Templates

Two command templates are provided:

- `client_command_structured.jinja`: For client-side command generation
- `server_command_structured.jinja`: For server-side command generation

These templates use the `quote_shell` Jinja filter for proper shell escaping of each argument.

### Example Usage

```python
# Build structured command arguments
command_args = []
# Add certificate parameters
command_args.append(params["certificates"]["cert_param"])
command_args.append(params["certificates"]["cert_file"])
# Add network interface if applicable
if include_interface and "network" in params and "interface" in params["network"]:
    command_args.append(params["network"]["interface"]["param"])
    command_args.append(params["network"]["interface"]["value"])

# Render template with structured arguments
render_commands(params, "client_command_structured.jinja", command_args=command_args)
```

### Handling Special Cases

- **Path arguments**: Automatically quoted if they contain spaces
- **Environment variables**: Properly escaped when rendered in scripts
- **Shell operators**: Command arguments containing operators like `|`, `&`, `>` are properly quoted
