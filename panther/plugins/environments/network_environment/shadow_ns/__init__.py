"""Shadow network simulator environment plugin.

Provides deterministic network simulation using the Shadow
discrete-event network simulator. Enables reproducible experiments
with configurable latency, bandwidth, and packet loss.

Key features:
    - Deterministic replay of network conditions
    - Configurable topology (latency, bandwidth, jitter)
    - Shadow YAML configuration generation
    - Compatible with `picoquic_shadow` service plugin
"""
