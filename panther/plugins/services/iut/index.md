# Implementation Under Test (IUT) Plugins

> **Plugin Type**: IUT Service
> **Verified Source Location**: `plugins/services/iut/`

## Overview

Implementation Under Test (IUT) plugins represent the actual protocol implementations being evaluated within the PANTHER framework. These implementations can be tested for standards conformance, performance characteristics, or security vulnerabilities.

<!-- src: /panther/plugins/services/iut/ -->

## Available Plugins

| Plugin | Description | Documentation |
|--------|-------------|---------------|
| picoquic | QUIC protocol implementation in C | [Documentation](panther/plugins/services/iut/quic/picoquic/README.md) |
| ping_pong | Simple ping-pong service for basic testing | [Documentation](panther/plugins/services/iut/minip/ping_pong/README.md) |

## Common Configuration

IUT plugins typically share these configuration patterns:

```yaml
services:
  - name: "quic_implementation"
    type: "iut"
    implementation: "quic/picoquic"
    config:
      binary_path: "/usr/local/bin/picoquicdemo"
      server_port: 4443
      certificate_file: "cert.pem"
      private_key_file: "key.pem"
```

## Integration Points

IUT plugins integrate with:

1. **Protocol plugins**: They implement specific protocol versions/behaviors
2. **Environment plugins**: They run within specific execution and network environments
3. **Tester plugins**: They are validated by tester plugins

## Development

To create a new IUT plugin, see the [Adding IUT](panther/plugins/ADDING_IUT.md) guide.
