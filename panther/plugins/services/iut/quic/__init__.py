"""QUIC IUT service plugins.

Each sub-package wraps a third-party QUIC stack so that PANTHER
can build, deploy, and test it uniformly. Language-specific base
classes provide common parameter extraction, command generation
(template method), Docker integration, and event emission.

Inheritance Architecture:
    ```
    BaseQUICServiceManager               ← core QUIC functionality
    ├── PythonQUICServiceManager          ← venv, asyncio, profiling
    │   └── aioquic
    ├── RustQUICServiceManager            ← Cargo, memory-safety
    │   ├── quiche
    │   └── quinn
    └── (direct subclasses)               ← C / Go implementations
        ├── picoquic
        ├── picoquic_shadow   (Shadow NS)
        ├── lsquic
        ├── mvfst
        ├── quant
        └── quic_go
    ```

Template Method Hooks:
    Concrete implementations only override four methods:
    `_get_implementation_name()`, `_get_binary_name()`,
    `_get_server_specific_args()`, `_get_client_specific_args()`.

Implementation Selection:
    - **Basic testing** – picoquic, aioquic
    - **Performance** – quiche, lsquic, mvfst
    - **Advanced research** – quinn, quic-go, quant
    - **Deterministic replay** – picoquic_shadow (Shadow NS)

Common Features:
    RFC 9000 compliance, TLS 1.3, connection migration, 0-RTT,
    flow control, loss recovery, HTTP/3 support.
"""
