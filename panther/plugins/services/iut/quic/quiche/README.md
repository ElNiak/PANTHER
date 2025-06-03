# Quiche QUIC Implementation

!!! warning "Development Status"
    This plugin is currently in development phase.

> **Plugin Type**: Service (Implementation Under Test)

> **Parent Plugin**: [QUIC IUT](panther/plugins/services/iut/quic/README.md)

> **Source Location**: `plugins/services/iut/quic/quiche/`

## Overview

The Quiche plugin provides integration with Cloudflare's Quiche QUIC implementation. Quiche is a modern, high-performance QUIC library written in Rust that prioritizes security, correctness, and performance. This plugin enables comprehensive testing of Quiche's QUIC implementation within the PANTHER framework.

<!-- src: /panther/plugins/services/iut/quic/quiche/quiche.py -->

Quiche implementation features:

- **Rust-based Implementation**: Memory-safe and performance-focused implementation
- **RFC 9000 Compliance**: Full QUIC specification compliance
- **HTTP/3 Support**: Built-in HTTP/3 protocol support
- **Security Focus**: Emphasis on secure and correct implementation

## Requirements and Dependencies

The plugin requires:

- **Quiche Library**: Compiled Quiche QUIC library
- **Rust Environment**: Rust compiler and Cargo for building
- **BoringSSL**: Cryptographic library for TLS support
- **System Dependencies**:
  - Development tools (cmake, make, gcc)
  - Network libraries

Docker-based deployment installs all necessary dependencies automatically.

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

