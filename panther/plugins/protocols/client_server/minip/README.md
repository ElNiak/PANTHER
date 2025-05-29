# MinIP Protocol Plugin

> **Plugin Type**: Client-Server Protocol
> **Verified Source Location**: `plugins/protocols/client_server/minip/`

## Overview

MinIP (Minimal Internet Protocol) is a simplified protocol designed for testing and educational purposes. It implements a minimal set of IP-based protocol features to facilitate network testing in controlled environments.

## Features

- Simplified packet structure for easy debugging and analysis
- Minimal handshake for efficient connection establishment
- Support for basic request-response communication patterns
- Configurable reliability and error handling mechanisms

## Configuration Options

The following configuration options are available for MinIP:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `version` | String | "1.0" | MinIP protocol version to use |
| `timeout` | Integer | 5000 | Connection timeout in milliseconds |
| `max_retries` | Integer | 3 | Maximum number of retry attempts |
| `packet_size` | Integer | 1024 | Maximum packet size in bytes |

## Usage Example

```yaml
protocols:
  - name: "minip"
    type: "protocol"
    implementation: "minip"
    config:
      version: "1.0"
      timeout: 3000
      max_retries: 5
      packet_size: 2048
```

## Integration

### Services

MinIP integrates with the following services:

- **MinIP IUT** - Implementation under test for MinIP protocol
- **Client Tester** - Client testing service for MinIP protocol
- **Server Tester** - Server testing service for MinIP protocol

### Dependencies

- Network Environment plugin configured for appropriate IP connectivity
- MinIP IUT service plugin

## Troubleshooting

### Common Issues

1. **Connection Timeouts**
   - Verify network environment is properly configured
   - Check timeout configuration is appropriate for the testing scenario
   - Ensure service endpoints are correctly specified

2. **Packet Size Errors**
   - Adjust `packet_size` parameter to match requirements
   - Verify that packet fragmentation is correctly handled

3. **Version Incompatibility**
   - Ensure the version specified matches the supported versions in the IUT

## Extension Points

The MinIP protocol can be extended with:

- Custom packet types by extending the packet structure
- Additional reliability mechanisms
- Enhanced error handling capabilities

## References

- MinIP Protocol Specification (internal documentation)
- [PANTHER Client-Server Protocol Interface](panther/plugins/docs/protocols/client_server/index.md)
