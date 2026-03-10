"""Implementation Under Test (IUT) service plugins.

Contains service managers for protocol implementations that PANTHER
builds, deploys, and tests. Organised by protocol:

- **quic/** -- 9 QUIC stack wrappers (picoquic, aioquic, quiche, ...)
- **http/** -- HTTP server/client implementations
- **minip/** -- Minimal Interoperability Protocol implementations

Each IUT plugin registers via ``@register_plugin()`` and provides
a service manager class plus a ``config_schema.py``.

Creating a New IUT Plugin:
    Directory structure::

        plugins/services/iut/<protocol>/<implementation>/
        +-- __init__.py
        +-- <implementation>.py # Service manager class
        +-- config_schema.py    # Pydantic configuration schema

    Choose a base class by implementation language:

    - **Python** (async/await): ``PythonQUICServiceManager`` (see ``aioquic/``)
    - **Rust** (Cargo): ``RustQUICServiceManager`` (see ``quiche/``, ``quinn/``)
    - **C / Go**: ``BaseQUICServiceManager`` directly (see ``picoquic/``, ``quic_go/``)

    Reference implementations: ``quic/picoquic/``, ``quic/aioquic/``, ``quic/quiche/``.
"""
