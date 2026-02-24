# BitTorrent Protocol

> **Plugin Type**: Protocol
> **Source Location**: `plugins/protocols/peer_to_peer/bittorrent/`

## Overview

The BitTorrent Protocol plugin provides a peer-to-peer file sharing protocol implementation for PANTHER testing environments. It enables evaluation of distributed content delivery, tracker communication, piece selection strategies, and tit-for-tat bandwidth allocation in controlled network scenarios. This plugin is currently in development.

## Configuration Options

<!-- src: config_schema.py -->

```yaml
protocols:
  - name: "bt_protocol"
    type: "protocol"
    implementation: "peer_to_peer/bittorrent"
    config:
      max_peers: 10             # Maximum number of peer connections
      download_rate: 100        # Download rate limit in KB/s
      upload_rate: 50           # Upload rate limit in KB/s
      piece_size: 262144        # Size of each piece in bytes (default: 256 KB)
      trackers:                 # List of trackers to use
        - "udp://tracker.example.com:80"
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_peers` | integer | 10 | Maximum number of peer connections |
| `download_rate` | integer | 100 | Download rate limit in KB/s |
| `upload_rate` | integer | 50 | Upload rate limit in KB/s |
| `piece_size` | integer | 262144 | Size of each piece in bytes |
| `trackers` | list | [] | List of tracker URLs |

## Usage Example

```yaml
protocols:
  - name: "bt_client"
    type: "protocol"
    implementation: "peer_to_peer/bittorrent"
    config:
      max_peers: 15
      download_rate: 200
      upload_rate: 100
```

## Integration

- Integrates with PANTHER network environments for testing in varied network scenarios (high latency, limited bandwidth, partitions)
- Supports peer churn simulation (peers joining and leaving rapidly)
- Requires UDP/TCP traffic on configured ports for tracker communication
- Can operate in both client and tracker modes

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeouts | Ensure trackers are accessible and the network environment allows UDP/TCP traffic on required ports |
| Poor download speeds | Check bandwidth limits and ensure sufficient peers with the complete file are available |
| Tracker errors | Verify tracker URLs and ensure correct protocol (HTTP, HTTPS, or UDP) |

## References

- [BitTorrent Specification (BEP 3)](https://www.bittorrent.org/beps/bep_0003.html)
- [BitTorrent Metadata Extension (BEP 9)](https://www.bittorrent.org/beps/bep_0009.html)
