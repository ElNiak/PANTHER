"""Client-server protocol plugins.

Contains protocol definitions for traditional client-server architectures:

- **quic** – QUIC transport protocol (RFC 9000 and draft versions)
- **http** – HTTP/1.1 and HTTP/3 protocol testing
- **minip** – Minimal Interoperability Protocol for testing infrastructure

Each sub-package registers itself via `@register_protocol()` and
provides a `config_schema.py` with Pydantic validation.
"""
