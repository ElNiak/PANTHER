# Service Modules (IUT) 🛠️

> **Purpose:** Comprehensive guide to PANTHER's Implementation Under Test (IUT) services and protocol implementations  
> **Target:** Protocol developers; QA engineers; researchers testing protocol implementations  

Service modules in PANTHER define **what implementations you're testing**. They provide containerized protocol implementations, configuration management, and standardized interfaces for testing various protocol stacks.

---

## Architecture Overview

PANTHER's service system uses a **plugin-based architecture** where each service provides:

1. **Protocol Implementation**: Containerized implementations of network protocols
2. **Configuration Management**: Standardized configuration interfaces
3. **Runtime Control**: Start, stop, monitor, and control services
4. **Result Collection**: Gather logs, metrics, and artifacts

### Service Types

| Service Type | Purpose | Examples |
|-------------|---------|----------|
| **IUT (Implementation Under Test)** | Protocol implementations being tested | QUIC servers/clients, HTTP implementations |
| **Tester** | Testing and verification tools | Formal verifiers, load generators, conformance checkers |

---

## Available IUT Implementations

### QUIC Protocol Implementations

#### 1. Quiche (Cloudflare)

**Overview:** Rust-based QUIC implementation by Cloudflare, focusing on performance and security.

**Service Configuration:**
```yaml
services:
  quiche_server:
    name: "quiche_server"
    implementation:
      name: "quiche"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "server"
    ports:
      - "4443:4443"
    generate_new_certificates: true

  quiche_client:
    name: "quiche_client"
    implementation:
      name: "quiche"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "client"
      target: "quiche_server"
    ports:
      - "4444:4444"
```

**Version Configuration (rfc9000.yaml):**
```yaml
# Automatically loaded from panther/plugins/services/iut/quic/quiche/version_configs/
version: "rfc9000"
commit: "4bda0917dd5aa535f39214063ee85c2cad00ceb2"
server:
  initial_version: "00000001"
  protocol:
    alpn:
      param: ""
      value: ""
    additional_parameters: "--no-grease --no-retry"
  binary:
    dir: "/opt/quiche/"
    name: "cargo run --bin quiche-server -- --root ."
  network:
    port: 4443
    destination:
      param: "--listen"
      value: "10.0.0.1"
  certificates:
    cert:
      param: "--cert"
      file: "/opt/certs/cert.pem"
    key:
      param: "--key"
      file: "/opt/certs/key.pem"
  logging:
    qlog:
      param: "--dump-packets"
      path: "/app/logs/server.qlog"

client:
  initial_version: "00000001"
  protocol:
    additional_parameters: "--dump-json --no-verify --body / -n 5"
  binary:
    dir: "/opt/quiche/"
    name: "cargo run --bin quiche-client --"
  network:
    port: 4443
    destination:
      value: "11.0.0.1"
```

#### 2. Picoquic (Microsoft Research)

**Overview:** Educational QUIC implementation focusing on protocol conformance and research.

**Service Configuration:**
```yaml
services:
  picoquic_server:
    name: "picoquic_server"
    implementation:
      name: "picoquic"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "server"
    ports:
      - "4443:4443"
    generate_new_certificates: true

  picoquic_client:
    name: "picoquic_client"
    implementation:
      name: "picoquic"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "client"
      target: "picoquic_server"
    ports:
      - "4444:4444"
```

**Version Configuration (rfc9000.yaml):**
```yaml
# Automatically loaded from panther/plugins/services/iut/quic/picoquic/version_configs/
version: "rfc9000"
commit: "bb67995f2d7c0e577c2c8788313c3b580d3df9a7"
dependencies:
  - name: "picotls"
    url: "https://github.com/h2o/picotls.git"
    commit: "047c5fe20bb9ea91c1caded8977134f19681ec76"

server:
  initial_version: "00000001"
  protocol:
    alpn:
      param: "-a"
      value: "hq-interop"
    additional_parameters: "-l - -n servername -D -L"
  binary:
    dir: "/opt/picoquic"
    name: "./picoquicdemo"
  network:
    interface:
      param: "-e"
      value: "eth0"
    port: 4443
    destination: "11.0.0.1"
  certificates:
    cert:
      param: "-c"
      file: "/opt/certs/cert.pem"
    key:
      param: "-k"
      file: "/opt/certs/key.pem"
  ticket_file:
    param: "-T"
    file: "/opt/ticket/ticket.key"
  logging:
    qlog:
      param: "-q"
      path: "/app/logs/server.qlog"

client:
  initial_version: "00000001"
  protocol:
    alpn:
      param: "-a"
      value: "hq-interop"
    additional_parameters: "-z -l - -D -L"
  binary:
    dir: "/opt/picoquic"
    name: "./picoquicdemo"
  network:
    port: 4443
    destination: "10.0.0.1"
```
        qlog_dir: "/app/logs/qlogs/"
```

#### 3. Aioquic (Python)

**Overview:** Python async QUIC implementation with HTTP/3 support.

**Configuration:**
```yaml
services:
  aioquic_server:
    name: "aioquic_server"
    implementation:
      name: "aioquic"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "server"
    ports:
      - "4433:4433"
    generate_new_certificates: true

  aioquic_client:
    name: "aioquic_client"
    implementation:
      name: "aioquic"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "client"
      target: "aioquic_server"
    ports:
      - "4434:4434"
```

#### 4. MVfst (Meta)

**Overview:** Facebook's high-performance QUIC implementation in C++.

**Service Configuration:**

```yaml
services:
  mvfst_server:
    name: "mvfst_server"
    implementation:
      name: "mvfst"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "server"
    ports:
      - "6666:6666"
    generate_new_certificates: true

  mvfst_client:
    name: "mvfst_client"
    implementation:
      name: "mvfst"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "client"
      target: "mvfst_server"
    ports:
      - "6667:6667"
```

#### 5. LsQUIC (LiteSpeed)

**Overview:** LiteSpeed's high-performance QUIC implementation optimized for web servers.

**Service Configuration:**

```yaml
services:
  lsquic_server:
    name: "lsquic_server"
    implementation:
      name: "lsquic"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "server"
    ports:
      - "4443:4443"
    generate_new_certificates: true

  lsquic_client:
    name: "lsquic_client"
    implementation:
      name: "lsquic"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "client"
      target: "lsquic_server"
    ports:
      - "4444:4444"
```
    config:
      binary:
        path: "/opt/lsquic/bin/http_server"
        args: ["-D", "-s", "0.0.0.0:4433"]
      
      network:
        port: 4433
        interface: "0.0.0.0"
        bind_address: "0.0.0.0:4433"
      
      protocol:
        versions: ["Q046", "Q050", "h3-29", "h3-32"]
        congestion_control: "cubic"
        enable_ech: false
        delayed_acks: true
        pace_packets: true
      
      certificates:
        cert_file: "/certs/server.crt" 
        key_file: "/certs/server.key"
        cert_chain_file: "/certs/chain.pem"
      
      performance:
        engine_settings:
          max_connections: 1000
          max_streams_in: 100
          cfcw: 16777216  # Connection flow control window
          sfcw: 1048576   # Stream flow control window
          max_header_list_size: 65536
      
      logging:
        log_level: "debug"
        log_file: "/app/logs/lsquic.log"
        qlog_dir: "/app/logs/qlogs/"
```

#### 6. QUANT

**Overview:** Academic QUIC implementation focusing on protocol research and conformance.

**Service Configuration:**

```yaml
services:
  quant_server:
    name: "quant_server"
    implementation:
      name: "quant"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "server"
    ports:
      - "4443:4443"
    generate_new_certificates: true

  quant_client:
    name: "quant_client"
    implementation:
      name: "quant"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "client"
      target: "quant_server"
    ports:
      - "4444:4444"
```

#### 7. QUIC-GO

**Overview:** Go implementation of QUIC with excellent performance and HTTP/3 support.

**Configuration:**
```yaml
services:
  quic_go_server:
    name: "quic_go_server"
    implementation:
      name: "quic_go"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "server"
    ports:
      - "4433:4433"
    generate_new_certificates: true

  quic_go_client:
    name: "quic_go_client"
    implementation:
      name: "quic_go"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "client"
      target: "quic_go_server"
    ports:
      - "4434:4434"
```

#### 8. Quinn (Rust)

**Overview:** Pure Rust QUIC implementation focusing on async performance and safety.

**Configuration:**
```yaml
services:
  quinn_server:
    name: "quinn_server"
    implementation:
      name: "quinn"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "server"
    ports:
      - "4433:4433"
    generate_new_certificates: true

  quinn_client:
    name: "quinn_client"
    implementation:
      name: "quinn"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "client"
      target: "quinn_server"
    ports:
      - "4434:4434"
```

#### 9. Picoquic Shadow NS

**Overview:** Picoquic implementation adapted for Shadow Network Simulator testing environments.

**Configuration:**
```yaml
services:
  picoquic_shadow_server:
    name: "picoquic_shadow_server"
    implementation:
      name: "picoquic_shadow"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "server"
    ports:
      - "4433:4433"
    generate_new_certificates: true

  picoquic_shadow_client:
    name: "picoquic_shadow_client"
    implementation:
      name: "picoquic_shadow"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "client"
      target: "picoquic_shadow_server"
    ports:
      - "4434:4434"
      
      logging:
        log_level: "info"
        performance_log: "/app/logs/performance.csv"
        connection_log: "/app/logs/connections.log"
```

### HTTP Protocol Implementations

#### HTTP/1.1 and HTTP/2 Services

**Configuration:**
```yaml
services:
  nginx_http2_server:
    name: "nginx_http2_server"
    implementation:
      name: "nginx"
      type: "iut"
    protocol:
      name: "http"
      version: "2.0"
      role: "server"
    ports:
      - "443:443"
      - "80:80"
    generate_new_certificates: true
```

### MiniP Protocol Implementation

**Overview:** Simple ping-pong protocol for basic connectivity testing.

**Configuration:**
```yaml
services:
  minip_server:
    name: "minip_server"
    implementation:
      name: "ping_pong"
      type: "iut"
    protocol:
      name: "minip"
      version: "1.0"
      role: "server"
    ports:
      - "8888:8888"

  minip_client:
    name: "minip_client"
    implementation:
      name: "ping_pong"
      type: "iut"
    protocol:
      name: "minip"
      version: "1.0"
      role: "client"
      target: "minip_server"
    ports:
      - "8889:8889"
```

---

## Additional QUIC Implementations

### LsQUIC (LiteSpeed)

**Overview:** LiteSpeed's high-performance QUIC implementation optimized for web servers.

**Configuration:**
```yaml
services:
  - name: "lsquic_server"
    type: "iut"
    implementation: "lsquic"
    role: "server"
    config:
      binary:
        path: "/opt/lsquic/bin/http_server"
        args: ["-D", "-s", "0.0.0.0:4433"]
      
      network:
        port: 4433
        interface: "0.0.0.0"
        bind_address: "0.0.0.0:4433"
      
      protocol:
        versions: ["Q046", "Q050", "h3-29", "h3-32"]
        congestion_control: "cubic"
        enable_ech: false
        delayed_acks: true
        pace_packets: true
      
      certificates:
        cert_file: "/certs/server.crt" 
        key_file: "/certs/server.key"
        cert_chain_file: "/certs/chain.pem"
      
      performance:
        engine_settings:
          max_connections: 1000
          max_streams_in: 100
          cfcw: 16777216  # Connection flow control window
          sfcw: 1048576   # Stream flow control window
          max_header_list_size: 65536
      
      logging:
        log_level: "debug"
        log_file: "/app/logs/lsquic.log"
        qlog_dir: "/app/logs/qlogs/"
```

### QUANT

**Overview:** Academic QUIC implementation focusing on protocol research and conformance.

**Configuration:**
```yaml
services:
  - name: "quant_server"
    type: "iut"
    implementation: "quant"
    role: "server"
    config:
      binary:
        path: "/app/server"
        args: ["-p", "4433", "-t", "3600"]
      
      network:
        port: 4433
        interface: "0.0.0.0"
        socket_buffer_size: 262144
      
      protocol:
        version: "1"
        initial_max_data: 1048576
        initial_max_stream_data_bidi_local: 262144
        initial_max_stream_data_bidi_remote: 262144
        initial_max_streams_bidi: 100
        max_packet_size: 1350
      
      certificates:
        cert_file: "/certs/cert.pem"
        key_file: "/certs/key.pem"
        verify_peer: false
      
      features:
        enable_qlog: true
        enable_keylog: true
        migration: false
        multipath: false
      
      logging:
        debug_level: 1
        qlog_dir: "/app/logs/"
        keylog_file: "/app/logs/keylog.txt"
```

### QUIC-GO

**Overview:** Go implementation of QUIC with excellent performance and HTTP/3 support.

**Configuration:**
```yaml
services:
  - name: "quic_go_server"
    type: "iut"
    implementation: "quic_go"
    role: "server"
    config:
      binary:
        path: "/app/server"
        args: ["-addr", "0.0.0.0:4433"]
      
      network:
        port: 4433
        address: "0.0.0.0"
        max_receive_buffer_size: 2097152
        max_send_buffer_size: 2097152
      
      protocol:
        versions: ["1", "draft-29"]
        handshake_timeout: "10s"
        idle_timeout: "30s"
        max_incoming_streams: 1000
        max_incoming_uni_streams: 1000
        connection_id_length: 4
      
      certificates:
        cert_file: "/certs/cert.pem"
        key_file: "/certs/key.pem"
        client_auth: "NoClientCert"
      
      features:
        enable_datagram: true
        disable_path_mtu_discovery: false
        allow_connection_migration: true
      
      logging:
        log_level: "info"
        enable_qlog: true
        qlog_dir: "/app/logs/qlogs/"
```

### Quinn (Rust)

**Overview:** Pure Rust QUIC implementation focusing on async performance and safety.

**Configuration:**
```yaml
services:
  - name: "quinn_server"
    type: "iut"
    implementation: "quinn"
    role: "server"
    config:
      binary:
        path: "/app/server"
        args: ["--listen", "0.0.0.0:4433"]
      
      network:
        port: 4433
        address: "0.0.0.0"
        receive_buffer_size: 1048576
        send_buffer_size: 1048576
      
      protocol:
        concurrent_connections: 1000
        bi_streams: 100
        uni_streams: 100
        datagram_receive_buffer_size: 1048576
        datagram_send_buffer_size: 1048576
        max_idle_timeout: "30s"
        keep_alive_interval: "15s"
      
      certificates:
        cert_chain_file: "/certs/cert.pem"
        key_file: "/certs/key.pem"
        protocols: ["h3"]
      
      congestion_control:
        algorithm: "cubic"
        initial_window: 32768
        minimum_window: 4096
        loss_detection_timer: "25ms"
      
      logging:
        log_level: "info"
        enable_qlog: true
        qlog_dir: "/app/logs/"
        stats_interval: "1s"
```

### Picoquic Shadow NS

**Overview:** Picoquic implementation adapted for Shadow Network Simulator testing environments.

**Configuration:**
```yaml
services:
  - name: "picoquic_shadow_server"
    type: "iut"
    implementation: "picoquic_shadow"
    role: "server"
    config:
      binary:
        path: "/app/picoquicdemo"
        args: ["-l", "/app/logs/server.log", "-D"]
      
      network:
        port: 4433
        interface: "0.0.0.0"
        shadow_environment: true
      
      protocol:
        alpn: ["hq-interop", "hq-29", "h3"]
        initial_version: "ff00001d"
        enable_multipath: false
        enable_simple_multipath: false
        congestion_algorithm: "cubic"
      
      certificates:
        cert_file: "/certs/cert.pem"
        key_file: "/certs/key.pem"
        root_trust_file: "/certs/ca.pem"
      
      shadow_specific:
        simulated_time: true
        deterministic_random: true
        log_packet_traces: true
        bandwidth_trace: "/traces/bandwidth.trace"
        latency_trace: "/traces/latency.trace"
      
      logging:
        log_level: "info"
        performance_log: "/app/logs/performance.csv"
        connection_log: "/app/logs/connections.log"
```

---

## Tester Services

### Panther Ivy Formal Verification

**Overview:** Formal verification tester using the Ivy verification system for protocol analysis.

**Configuration:**
```yaml
services:
  panther_ivy_tester:
    name: "panther_ivy_tester"
    implementation:
      name: "panther_ivy"
      type: "tester"
    protocol:
      name: "verification"
      version: "1.0"
      role: "tester"
    ports:
      - "9090:9090"
```

**Example Verification Workflow:**
```yaml
# Formal verification experiment
experiment:
  name: "quic_formal_verification"
  services:
    quic_server_under_test:
      name: "quic_server_under_test"
      implementation:
        name: "picoquic"
        type: "iut"
      protocol:
        name: "quic"
        version: "rfc9000"
        role: "server"
      ports:
        - "4433:4433"
      generate_new_certificates: true
      
    formal_verifier:
      name: "formal_verifier"
      implementation:
        name: "panther_ivy"
        type: "tester"
      protocol:
        name: "verification"
        version: "1.0"
        role: "tester"
      ports:
        - "9090:9090"
```

---

## Service Comparison Matrix

### QUIC Implementation Comparison

| Implementation | Language | Performance | Features | Maturity | Use Case |
|---------------|----------|-------------|----------|----------|----------|
| **Quiche** | Rust | High | HTTP/3, 0-RTT, Migration | Production | Web servers, CDN |
| **Picoquic** | C | Medium | Research features, Conformance | Research | Protocol research, Education |
| **Aioquic** | Python | Medium | HTTP/3, WebTransport | Production | Python applications, Prototyping |
| **MVFST** | C++ | Very High | Partial reliability, Datagrams | Production | Meta services, High-performance |
| **LsQUIC** | C | Very High | Web optimization, H3 | Production | LiteSpeed web servers |
| **QUANT** | C | Medium | Research focus, Clean code | Research | Academic research, Protocol testing |
| **QUIC-GO** | Go | High | HTTP/3, Clean API | Production | Go applications, Microservices |
| **Quinn** | Rust | High | Async, Memory safety | Production | Rust applications, Safety-critical |
| **Picoquic Shadow** | C | Medium | Shadow NS integration | Research | Network simulation, Large-scale testing |

### Protocol Support Matrix

| Implementation | QUIC v1 | QUIC Drafts | HTTP/3 | 0-RTT | Migration | Multipath | Datagrams |
|---------------|---------|-------------|---------|-------|-----------|-----------|-----------|
| **Quiche** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Picoquic** | ✅ | ✅ | ✅ | ✅ | ✅ | 🚧 | ✅ |
| **Aioquic** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **MVFST** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **LsQUIC** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **QUANT** | ✅ | ✅ | ❌ | ✅ | 🚧 | ❌ | ✅ |
| **QUIC-GO** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Quinn** | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ |
| **Picoquic Shadow** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |

Legend: ✅ Supported | ❌ Not supported | 🚧 In development
        timeout: 30
      
      behavior:
        echo_messages: true
        add_timestamp: true
        log_messages: true
      
      logging:
        log_file: "/app/logs/minip.log"
        log_level: "INFO"
```

---

## Advanced Service Configuration

### Multi-Role Services

**Combined Server-Client:**
```yaml
services:
  - name: "quic_dual_role"
    type: "iut"
    implementation: "quiche"
    roles: ["server", "client"]
    config:
      server:
        port: 4433
        cert_file: "/certs/server.crt"
        key_file: "/certs/server.key"
      
      client:
        targets: ["external_server:4433"]
        connection_count: 10
        request_rate: "100/s"
      
      shared:
        protocol:
          alpn: ["h3"]
          version: "rfc9000"
        logging:
          qlog: true
          log_level: "debug"
```

### Load Testing Configuration

**High-Performance Settings:**
```yaml
services:
  - name: "quic_load_server"
    type: "iut"
    implementation: "mvfst"
    role: "server"
    config:
      performance:
        worker_threads: 8
        max_connections: 10000
        connection_pool_size: 1000
        buffer_sizes:
          send_buffer: 262144
          receive_buffer: 262144
      
      protocol:
        congestion_control: "bbr"
        pacing: true
        early_data: true
      
      monitoring:
        enable_metrics: true
        metrics_port: 9090
        collection_interval: 1
```

### Security Testing

**Security-Focused Configuration:**
```yaml
services:
  - name: "quic_security_test"
    type: "iut"
    implementation: "picoquic"
    role: "server"
    config:
      security:
        strict_crypto: true
        disable_0rtt: true
        require_client_auth: true
        cipher_suites: ["TLS_AES_256_GCM_SHA384"]
        key_exchange: ["X25519"]
      
      certificates:
        cert_chain: "/certs/full_chain.pem"
        key_file: "/certs/private.key"
        ca_bundle: "/certs/ca_bundle.pem"
        crl_file: "/certs/revocation.crl"
      
      validation:
        verify_peer: true
        check_hostname: true
        verify_chain: true
```

### Development and Debugging

**Debug Configuration:**
```yaml
services:
  - name: "quic_debug"
    type: "iut"
    implementation: "quiche"
    role: "server"
    config:
      debug:
        enable_debug_symbols: true
        core_dumps: true
        memory_debugging: true
        trace_packets: true
      
      logging:
        log_level: "trace"
        log_modules: ["connection", "stream", "crypto"]
        packet_log: "/app/logs/packets.log"
        key_log: "/app/logs/keys.log"
      
      profiling:
        enable_profiling: true
        profile_cpu: true
        profile_memory: true
        sample_rate: 1000
```

---

## Service Lifecycle Management

### Service Dependencies

**Dependency Chain:**
```yaml
services:
  - name: "certificate_authority"
    type: "utility"
    implementation: "openssl_ca"
    startup_order: 1
    
  - name: "quic_server"
    type: "iut"
    implementation: "quiche"
    depends_on: ["certificate_authority"]
    startup_order: 2
    wait_for:
      - service: "certificate_authority"
        condition: "healthy"
        timeout: 30
    
  - name: "quic_client"
    type: "iut"
    implementation: "picoquic"
    depends_on: ["quic_server"]
    startup_order: 3
    wait_for:
      - service: "quic_server"
        condition: "port_open"
        port: 4433
        timeout: 60
```

### Health Checks and Monitoring

**Comprehensive Health Monitoring:**
```yaml
services:
  - name: "quic_server"
    type: "iut"
    implementation: "quiche"
    config:
      health_check:
        enabled: true
        type: "tcp"
        port: 4433
        interval: 10
        timeout: 5
        retries: 3
        start_period: 30
      
      monitoring:
        metrics:
          - type: "connection_count"
            threshold: 1000
            action: "alert"
          - type: "cpu_usage"
            threshold: 80
            action: "scale"
          - type: "memory_usage"
            threshold: 90
            action: "restart"
        
        alerts:
          - name: "high_error_rate"
            condition: "error_rate > 0.05"
            duration: "5m"
            action: "notify"
```

### Graceful Shutdown

**Shutdown Configuration:**
```yaml
services:
  - name: "quic_server"
    config:
      shutdown:
        grace_period: 30
        drain_connections: true
        save_state: true
        cleanup_resources: true
        
        signals:
          term: "SIGTERM"
          kill: "SIGKILL"
          reload: "SIGHUP"
        
        hooks:
          pre_stop: "/app/scripts/pre_stop.sh"
          post_stop: "/app/scripts/post_stop.sh"
```

---

## Service Templates and Customization

### Custom Service Implementation

**Creating a Custom Service:**
```python
# plugins/services/iut/custom_protocol/custom_implementation.py
from panther.plugins.services.iut.implementation_interface import IImplementationManager

class CustomProtocolImplementation(IImplementationManager):
    def __init__(self):
        super().__init__()
        self.name = "custom_protocol"
        self.version = "1.0"
    
    def prepare_environment(self, config):
        # Setup custom environment
        pass
    
    def start_service(self, config):
        # Start the service
        return self.execute_command(config.binary.path, config.binary.args)
    
    def stop_service(self):
        # Graceful shutdown
        pass
    
    def get_metrics(self):
        # Return service metrics
        return {
            "connections": self.get_connection_count(),
            "requests": self.get_request_count(),
            "errors": self.get_error_count()
        }
```

**Configuration Schema:**
```python
# plugins/services/iut/custom_protocol/config_schema.py
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class CustomProtocolConfig:
    binary: BinaryConfig
    network: NetworkConfig
    protocol: ProtocolConfig
    
@dataclass
class ProtocolConfig:
    version: str
    features: List[str]
    timeout: int = 30
    max_connections: int = 1000
```

### Service Templates

**Dockerfile Template:**
```dockerfile
# plugins/services/iut/custom_protocol/Dockerfile
FROM panther/base:latest

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    pkg-config

# Copy source code
COPY src/ /app/src/
WORKDIR /app

# Build application
RUN make clean && make release

# Setup runtime
EXPOSE {{ service.network.port }}
CMD ["/app/bin/{{ service.binary.name }}"]
```

**Service Configuration Template:**
```yaml
# plugins/services/iut/custom_protocol/config.yaml.j2
name: "{{ service.name }}"
implementation: "{{ service.implementation }}"
role: "{{ service.role }}"

config:
  binary:
    path: "/app/bin/{{ service.binary.name }}"
    args: {{ service.binary.args | to_json }}
    
  network:
    port: {{ service.network.port }}
    interface: "{{ service.network.interface | default('0.0.0.0') }}"
    
  protocol:
    version: "{{ service.protocol.version }}"
    features: {{ service.protocol.features | to_json }}
```

---

## Testing and Validation

### Conformance Testing

**Protocol Conformance:**
```yaml
tests:
  - name: "quic_conformance"
    services:
      - name: "quic_server"
        type: "iut"
        implementation: "quiche"
        role: "server"
        
      - name: "conformance_tester"
        type: "tester"
        implementation: "quic_conformance"
        config:
          test_suite: "rfc9000"
          test_cases: ["connection_establishment", "flow_control", "error_handling"]
```

### Interoperability Testing

**Multi-Implementation Testing:**
```yaml
tests:
  - name: "quic_interop"
    matrix:
      servers: ["quiche", "picoquic", "aioquic", "mvfst"]
      clients: ["quiche", "picoquic", "aioquic", "mvfst"]
    
    exclude:
      - server: "mvfst"
        client: "mvfst"  # Skip same implementation
    
    config:
      protocol:
        versions: ["rfc9000", "draft-29"]
        features: ["0rtt", "multipath", "datagrams"]
```

### Performance Testing

**Load Testing Configuration:**
```yaml
tests:
  - name: "quic_performance"
    services:
      - name: "quic_server"
        type: "iut"
        implementation: "mvfst"
        config:
          performance:
            max_connections: 10000
            worker_threads: 8
            
      - name: "load_generator"
        type: "tester"
        implementation: "quic_load_tester"
        config:
          load_pattern:
            ramp_up_time: "60s"
            steady_state: "300s"
            ramp_down_time: "60s"
            max_rps: 10000
            connection_count: 1000
```

---

## Troubleshooting and Debugging

### Common Issues

**Service Startup Failures:**
```yaml
services:
  - name: "debug_service"
    config:
      debug:
        startup_timeout: 60
        verbose_logging: true
        capture_stderr: true
        
      troubleshooting:
        check_dependencies: true
        validate_certificates: true
        test_network_connectivity: true
```

**Certificate Issues:**
```bash
# Generate test certificates
panther generate-certs --output /tmp/certs

# Validate certificate chain
openssl verify -CAfile /certs/ca.pem /certs/server.crt

# Test certificate compatibility
panther test-certs --server-cert /certs/server.crt --implementation quiche
```

**Network Connectivity:**
```bash
# Test service connectivity
panther test-connectivity --service quic_server --port 4433

# Debug network configuration
panther debug network --show-routing --show-firewall
```

### Debug Mode

**Enhanced Debugging:**
```bash
export PANTHER_DEBUG_SERVICES=1
export PANTHER_TRACE_PROTOCOLS=1
panther --experiment-config config.yaml --debug
```

---

## Best Practices

### 1. Service Configuration

**Consistent Configuration:**
```yaml
# Use environment variables for flexibility
services:
  - name: "quic_server"
    config:
      network:
        port: ${SERVER_PORT:-4433}
      logging:
        level: ${LOG_LEVEL:-INFO}
      certificates:
        cert_file: ${CERT_PATH}/server.crt
```

### 2. Resource Management

**Appropriate Resource Limits:**
```yaml
services:
  - name: "quic_server"
    config:
      resources:
        memory_limit: "1g"
        cpu_limit: 2.0
        file_descriptors: 65536
```

### 3. Logging and Monitoring

**Comprehensive Logging:**
```yaml
services:
  - name: "quic_server"
    config:
      logging:
        structured: true
        format: "json"
        fields: ["timestamp", "level", "component", "message", "connection_id"]
        rotation:
          size: "100MB"
          count: 10
```

### 4. Security

**Security Best Practices:**
```yaml
services:
  - name: "quic_server"
    config:
      security:
        run_as_user: "panther"
        drop_capabilities: ["ALL"]
        add_capabilities: ["NET_BIND_SERVICE"]
        read_only_filesystem: true
```

---

For network environment configuration, see [Network Environment Modules](network_environment_modules.md).
For testing tools and testers, see [Tester Modules](tester_modules.md).
For protocol details, see [Protocol Modules](protocol_modules.md).
