# MinIP Protocol

> **Plugin Type**: Protocol
> **Source Location**: `plugins/protocols/client_server/minip/`

## Overview

MinIP (Minimal Internet Protocol) is a simplified protocol designed for testing and educational purposes. It implements a minimal set of IP-based protocol features to facilitate network testing in controlled environments, with support for basic request-response communication patterns and configurable reliability mechanisms.

## Configuration Options

<!-- src: config_schema.py -->

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

- Works with the MinIP IUT service plugin (`minip/ping_pong`)
- Requires a network environment plugin configured for appropriate IP connectivity
- Supports client and server tester services for MinIP protocol validation
- Provides simplified packet structure for easy debugging and analysis

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeouts | Verify network environment configuration and adjust `timeout` parameter |
| Packet size errors | Adjust `packet_size` parameter and verify fragmentation handling |
| Version incompatibility | Ensure the version matches supported versions in the IUT |

## References

- MinIP Protocol Specification (internal documentation)
