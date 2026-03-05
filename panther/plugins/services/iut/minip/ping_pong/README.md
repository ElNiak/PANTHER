# MinIP Ping-Pong Implementation

> [!NOTE]
> "Educational Protocol Implementation"
> MinIP Ping-Pong is a simplified protocol implementation designed for learning and testing basic networking concepts. It provides multiple behavioral variants for comprehensive testing scenarios.

> **Plugin Type**: Service (Implementation Under Test)

> **Parent Plugin**: [MinIP IUT](../README.md)

> **Source Location**: `plugins/services/iut/minip/ping_pong/`

## Overview

The MinIP Ping-Pong implementation provides a simple client-server protocol for testing basic network communication patterns. This lightweight implementation demonstrates the essential components of the MinIP protocol through a straightforward ping-pong request-response exchange.

<!-- src: /panther/plugins/services/iut/minip/ping_pong/ping_pong.py -->

This implementation serves as:

- **Educational Example**: Clear demonstration of IUT plugin development
- **Baseline Testing**: Reference implementation for protocol compliance testing
- **Performance Benchmark**: Minimal overhead baseline for performance comparisons
- **Development Template**: Starting point for creating new protocol implementations

## Implementation Variants

The plugin provides multiple implementation variants for different testing scenarios:

### Functional Variant

- **Purpose**: Standard, correct implementation
- **Behavior**: Follows MinIP specification exactly
- **Use Case**: Baseline conformance testing

### Vulnerable Variant

- **Purpose**: Implementation with intentional security vulnerabilities
- **Behavior**: Contains specific security flaws for testing
- **Use Case**: Security testing and penetration testing scenarios

### Flaky Variant

- **Purpose**: Intermittently unreliable implementation
- **Behavior**: Occasionally drops packets or times out
- **Use Case**: Testing fault tolerance and recovery mechanisms

### Random Variant

- **Purpose**: Implementation with non-deterministic behavior
- **Behavior**: Introduces random delays and responses
- **Use Case**: Stress testing and edge case discovery

### Fail Variant

- **Purpose**: Implementation that consistently fails
- **Behavior**: Always returns errors or fails to respond
- **Use Case**: Negative testing and error handling validation

## Configuration

<!-- src: /panther/plugins/services/iut/minip/ping_pong/config_schema.py -->

```yaml
services:
  - name: "minip_ping_pong"
    implementation:
      name: "minip/ping_pong"
      type: "iut"
      version: "functional"  # functional, vulnerable, flaky, random, fail
    protocol:
      name: "minip"
      type: "protocol"
      role: "server"  # server or client
    config:
      port: 8000
      timeout: 30
      max_connections: 10
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `version` | enum | No | "functional" | Implementation variant to use |
| `port` | integer | No | 8000 | Server listening port |
| `timeout` | integer | No | 30 | Connection timeout in seconds |
| `max_connections` | integer | No | 10 | Maximum concurrent connections |

## Usage Examples

### Basic Ping-Pong Server

```yaml
tests:
  - name: "MinIP Ping-Pong Test"
    network_environment:
      type: "docker_compose"
    services:
      ping_pong_server:
        name: "ping_pong_server"
        timeout: 60
        implementation:
          name: "minip/ping_pong"
          type: "iut"
          version: "functional"
        protocol:
          name: "minip"
          type: "protocol"
          role: "server"
```

### Vulnerability Testing

```yaml
tests:
  - name: "MinIP Security Test"
    network_environment:
      type: "docker_compose"
    services:
      vulnerable_server:
        name: "vulnerable_server"
        timeout: 60
        implementation:
          name: "minip/ping_pong"
          type: "iut"
          version: "vulnerable"
        protocol:
          name: "minip"
          type: "protocol"
          role: "server"
```

## Implementation Details

### Architecture

The ping-pong implementation consists of:

1. **Client Component**: Sends ping requests and handles pong responses
2. **Server Component**: Listens for ping requests and sends pong responses
3. **Protocol Handler**: Manages MinIP packet formatting and parsing
4. **Version Manager**: Switches between implementation variants

### Protocol Flow

```text
Client                    Server
  |                         |
  |------- PING ----------->|
  |                         |
  |<------ PONG ------------|
  |                         |
```

### File Structure

```text
ping_pong/
├── README.md                 # This documentation
├── __init__.py              # Plugin initialization
├── ping_pong.py             # Main implementation
├── config_schema.py         # Configuration schema
├── Dockerfile               # Container build instructions
├── src/                     # Source code variants
│   ├── functional/          # Standard implementation
│   ├── vulnerable/          # Vulnerable implementation
│   ├── flaky/              # Unreliable implementation
│   ├── random/             # Non-deterministic implementation
│   └── fail/               # Failing implementation
├── templates/              # Command templates
│   ├── client_command.jinja # Client command template
│   └── server_command.jinja # Server command template
└── version_configs/        # Version-specific configurations
    ├── functional.yaml
    ├── vulnerable.yaml
    ├── flaky.yaml
    ├── random.yaml
    └── fail.yaml
```

## Development

### Extending the Implementation

To add a new variant:

1. Create source code in `src/new_variant/`
2. Add configuration in `version_configs/new_variant.yaml`
3. Update `config_schema.py` to include the new variant
4. Modify `ping_pong.py` to handle the new variant

### Testing

Run unit tests for the ping-pong implementation:

```bash
python -m pytest panther/plugins/services/iut/minip/ping_pong/tests/
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | Change the port in configuration |
| Connection timeout | Increase timeout value or check network connectivity |
| Variant not found | Verify the variant name in version_configs/ |
| Build failure | Check Docker logs and ensure all dependencies are available |

For more detailed debugging, enable verbose logging in the service configuration.

## See Also

- [MinIP IUT Plugin](../README.md) - Parent plugin documentation
- [Service Plugin Development Guide](../../development.md) - General development guidelines
- IUT Plugin Development Guide - IUT-specific development guidelines
