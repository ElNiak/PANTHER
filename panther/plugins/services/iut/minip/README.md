# MinIP Ping-Pong Implementation

> **Plugin Type**: Service (Implementation Under Test)
> **Verified Source Location**: `plugins/services/iut/minip/ping_pong/`

## Purpose and Overview

The MinIP Ping-Pong plugin provides an implementation of the MinIP (Minimal Internet Protocol) for testing client-server communication patterns. This lightweight protocol implementation focuses on basic ping-pong style request-response exchanges, making it ideal for baseline testing and educational purposes.

<!-- src: /panther/plugins/services/iut/minip/ping_pong/ping_pong.py -->

The MinIP Ping-Pong implementation is particularly valuable for:
- Testing basic client-server communication patterns
- Providing a lightweight reference implementation
- Benchmarking minimal network overhead
- Demonstrating protocol implementation concepts

## Requirements and Dependencies

The plugin requires:

- **C Compiler**: GCC or compatible compiler
- **Standard C Libraries**: For socket communications and basic functionality
- **Network**: Functional IP networking between client and server

Docker-based deployment installs all necessary dependencies automatically.

## Configuration Options

The MinIP Ping-Pong implementation accepts the following configuration parameters:

```yaml
services:
  my_minip_service:
    name: "minip_service"
    implementation:
      name: "minip/ping_pong"
      type: "iut"
    protocol:
      name: "minip"
      version: "standard"
      role: "server"  # or "client"
    ports:
      - "8000:8000"  # Format: "host:container"
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | - | Service name |
| `implementation.name` | string | Yes | "minip/ping_pong" | Implementation path |
| `implementation.type` | string | Yes | "iut" | Implementation type |
| `protocol.role` | string | Yes | - | Either "client" or "server" |
| `protocol.version` | string | No | "standard" | MinIP protocol version |

## Server Configuration

When configured as a server, the MinIP Ping-Pong implementation listens for incoming connections and responds to client requests:

```yaml
services:
  minip_server:
    name: "minip_server"
    implementation:
      name: "minip/ping_pong"
      type: "iut"
    protocol:
      name: "minip"
      version: "standard"
      role: "server"
    ports:
      - "8000:8000"
```

## Client Configuration

When configured as a client, the MinIP Ping-Pong implementation initiates connections to a server and sends ping requests:

```yaml
services:
  minip_client:
    name: "minip_client"
    implementation:
      name: "minip/ping_pong"
      type: "iut"
    protocol:
      name: "minip"
      version: "standard"
      role: "client"
      target: "minip_server"  # Target server service name
```

## Supported Versions

| Version | Description |
|---------|-------------|
| `standard` | Standard implementation with basic ping-pong functionality |
| `functional` | Enhanced implementation with advanced reliability features |
| `random` | Implementation with randomized message timing |
| `vulnerable` | Implementation with deliberate vulnerabilities for security testing |
| `flaky` | Implementation with intermittent failures for resilience testing |
| `fail` | Implementation that demonstrates failure modes |

## Usage Examples

### Basic Client-Server Test

```yaml
tests:
  - name: "minip_basic_test"
    description: "Basic MinIP client-server ping-pong test"
    network_environment: "docker_compose"
    services:
      minip_server:
        name: "minip_server"
        implementation:
          name: "minip/ping_pong"
          type: "iut"
        protocol:
          name: "minip"
          version: "standard"
          role: "server"
        ports:
          - "8000:8000"
      minip_client:
        name: "minip_client"
        implementation:
          name: "minip/ping_pong"
          type: "iut"
        protocol:
          name: "minip"
          version: "standard"
          role: "client"
          target: "minip_server"
    steps:
      wait: 5  # Wait 5 seconds for connection
    assertions:
      - type: "log_contains"
        service: "minip_client"
        pattern: "Connection successful"
```

## Troubleshooting

### Common Issues

1. **Connection Failures**:
   - Ensure the server is running before the client attempts to connect
   - Verify that network ports are correctly mapped in the configuration
   - Check network environment configuration for proper routing

2. **Timeout Errors**:
   - Increase the timeout value in service configuration
   - Check for network congestion or latency issues
   - Verify that the server is properly handling client requests

3. **Version Mismatches**:
   - Ensure client and server use compatible protocol versions
   - Check for any specific version requirements in test configuration

## References

- [MinIP Protocol Documentation](../../../../../docs/protocols/client_server/minip/README.md)
- [PANTHER Service Development Guide](../../../../../docs/services/development.md)
