"""Peer-to-peer protocol plugins.

Contains protocol definitions for peer-to-peer architectures:

- **bittorrent** – BitTorrent protocol testing

Each sub-package registers itself via `@register_protocol()` and
provides a `config_schema.py` with Pydantic validation.
"""
