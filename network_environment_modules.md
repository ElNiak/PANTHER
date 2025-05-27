# Network Environment Modules 🌐

> **Purpose:** Comprehensive guide to PANTHER's network environments and simulation capabilities  
> **Target:** Network researchers; protocol developers; QA engineers testing under realistic network conditions  
> **Note:** For documentation corrections and updates, see `DOCUMENTATION_CORRECTIONS.md`

Network environments in PANTHER define **how your implementations communicate** during testing. They provide isolated networking, realistic network conditions, multi-container orchestration, and network simulation capabilities.

---

## Architecture Overview

PANTHER's network environments use a **layered approach** where each environment type provides:

1. **Network Isolation**: Controlled networking with custom topologies
2. **Service Discovery**: Automatic service registration and communication
3. **Realistic Conditions**: Latency, bandwidth, packet loss simulation
4. **Scalable Orchestration**: Multi-container and multi-host deployments

### Environment Types

| Environment | Purpose | Use Cases |
|-------------|---------|-----------|
| **Docker Compose** | Multi-container orchestration | Complex service interactions, realistic deployments |
| **Localhost Single Container** | Single-container testing on localhost | Basic functionality testing, development, CI/CD |
| **Shadow NS** | Discrete-event network simulation | Deterministic testing, large-scale simulation, academic research |

---

## Available Network Environments

### 1. Docker Compose Environment

**Purpose:** Orchestrates multiple containers with custom networking, service discovery, and realistic multi-service deployments.

**Basic Configuration:**
```yaml
network_environment:
  type: "docker_compose"
  config:
    version: "3.8"
    network_name: "panther_network"
    service_prefix: "panther"
    volumes:
      - "shared_data:/app/data"
      - "./certs:/certs:ro"
    environment:
      SERVER_PORT: "4433"
      CLIENT_COUNT: "10"
      LOG_LEVEL: "debug"
```

> **Note:** Complex network topologies, service definitions, and Docker Compose file generation are handled automatically by the framework based on the loaded service managers. The above configuration provides basic environment parameters that influence the generated Docker Compose file.

**Advanced Features:**
```yaml
network_environment:
  type: "docker_compose"
  config:
    # Custom compose template
    compose_template: "templates/custom-compose.yml.j2"
    
    # Environment variables
    environment:
      SERVER_PORT: "4433"
      CLIENT_COUNT: "10"
      
    # Network policies
    network_policies:
      - name: "frontend_isolation"
        rules:
          - allow: ["frontend", "backend"]
          - deny: ["external"]
    
    # Service dependencies
    dependencies:
      quic_client: ["quic_server", "certificate_authority"]
      load_balancer: ["quic_server"]
    
    # Health checks
    health_checks:
      quic_server:
        test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
        interval: "30s"
        timeout: "10s"
        retries: 3
```

**Generated Docker Compose:**
```yaml
version: '3.8'
services:
  quic_server:
    build:
      context: ./plugins/services/iut/quic/quiche
      dockerfile: Dockerfile
    networks:
      - frontend
    ports:
      - "4433:4433"
    environment:
      - SERVER_MODE=1
      - LOG_LEVEL=debug
    volumes:
      - shared_data:/app/data
      - ./certs:/certs:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  quic_client:
    build:
      context: ./plugins/services/iut/quic/picoquic
    networks:
      - frontend
    depends_on:
      - quic_server
    environment:
      - TARGET_SERVER=quic_server
      - TARGET_PORT=4433

networks:
  frontend:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  shared_data:
    driver: local
```

**Use Cases:**

- Multi-implementation interoperability testing
- Complex service architectures
- Realistic deployment scenarios
- Performance testing with multiple components

### 2. Localhost Single Container Environment

**Purpose:** Single-container testing environment on localhost for basic testing and development.

**Basic Configuration:**
```yaml
network_environment:
  type: "localhost_single_container"
  config:
    version: "3.8"
    network_name: "panther_localhost"
    service_prefix: "local"
    environment:
      SERVER_PORT: "4433"
      CLIENT_PORT: "4434"
      LOG_LEVEL: "info"
      TEST_MODE: "development"
```

> **Note:** Container-specific options like port mapping, resource limits, networking mode, and security options are configured automatically by the framework based on the service requirements. The above configuration provides environment variables and basic network settings.

**Use Cases:**
- Development and debugging
- Simple functionality testing
- Quick prototyping
- CI/CD pipeline testing

### 3. Shadow NS Environment

**Purpose:** Discrete-event network simulation for deterministic, large-scale, and reproducible testing.

⚠️ **Compatibility Note:** Shadow NS is incompatible with `strace` and `gperf` tools.

**Basic Configuration:**
```yaml
network_environment:
  type: "shadow_ns"
  config:
    general:
      stop_time: "60s"
      model_unblocked_syscall_latency: false
    
    experimental:
      strace_logging_mode: "standard"
    
    network:
      latency: 10  # milliseconds
      jitter: 10   # milliseconds  
      packet_loss: 0.0
    
    host_option_defaults:
      pcap_enabled: true
    
    hosts:
      server:
        network_node_id: 0
        ip_addr: "11.0.0.1"
        start_time: "1s"
      client:
        network_node_id: 0
        ip_addr: "11.0.0.2"
        start_time: "5s"
```

**Advanced Shadow NS Configuration:**
```yaml
network_environment:
  type: "shadow_ns"
  config:
    general:
      stop_time: "300s"
      model_unblocked_syscall_latency: true
    
    experimental:
      strace_logging_mode: "detailed"
    
    network:
      latency: 20
      jitter: 5
      packet_loss: 0.01
    
    host_option_defaults:
      pcap_enabled: true
    
    hosts:
      server:
        network_node_id: 0
        ip_addr: "11.0.0.1"
        start_time: "1s"
      client:
        network_node_id: 1
        ip_addr: "11.0.0.2"
        start_time: "5s"
      load_balancer:
        network_node_id: 0
        ip_addr: "11.0.0.10"
        start_time: "2s"
```

> **Note:** Advanced configurations for network topology, multiple nodes, and complex traffic patterns are handled through the underlying Shadow simulator. The PANTHER configuration focuses on simulation timing, host definitions, and basic network parameters. For complex scenarios, consult the Shadow documentation for detailed topology configuration options.
      - name: "web_traffic"
        pattern: "poisson"
        rate: "100/s"
        duration: "60s"
      - name: "bulk_transfer"
        pattern: "constant"
        rate: "10mbps"
        duration: "120s"
    
    # Failure scenarios
    failures:
      - type: "node_failure"
        target: "datacenter_a_node_50"
        start_time: "100s"
        duration: "30s"
      - type: "link_failure"
        target: "dc_a_to_dc_b"
        start_time: "200s"
        duration: "60s"
```

**Use Cases:**
- Large-scale protocol testing
- Academic research
- Performance evaluation
- Reproducible experiments

---

## Implementation Details and Container Building

### Container Building Process

PANTHER automatically handles Docker image building and container orchestration for each network environment:

#### **Generated File Locations:**

**Docker Compose Environment:**
```
./plugins/environments/network_environment/docker_compose/
├── docker_compose.generated.yml      # Template file
└── entrypoint.generated.sh          # Generated script

./outputs/[timestamp]/
├── docker_compose.yml               # Rendered Docker Compose file
└── entrypoint.sh                   # Rendered entrypoint script
```

**Localhost Single Container Environment:**
```
./plugins/environments/network_environment/localhost_single_container/
├── run.generated.sh                # Template script
└── Dockerfile.generated           # Template Dockerfile

./outputs/[timestamp]/
├── run.sh                         # Rendered run script
└── Dockerfile                     # Rendered Dockerfile
```

**Shadow NS Environment:**
```
./plugins/environments/network_environment/shadow_ns/
├── shadow.generated.yaml          # Template configuration
└── shadow.generated.sh           # Template script

./outputs/[timestamp]/
├── shadow.yaml                    # Rendered Shadow configuration
└── shadow.sh                     # Rendered execution script
```

#### **Service Manager Integration:**

Each service manager provides:
1. **Docker Build Context**: Path to service-specific Dockerfile and build materials
2. **Command Generation**: Runtime commands based on service configuration
3. **Port Requirements**: Network port specifications for container exposure
4. **Environment Variables**: Service-specific environment configuration
5. **Volume Mounts**: Data and configuration volume requirements

#### **Plugin Loading Mechanism:**

Network environments are loaded through the plugin system:
1. **Plugin Discovery**: Scans `./plugins/environments/network_environment/` directory
2. **Interface Validation**: Ensures implementation of `INetworkEnvironment` interface
3. **Configuration Schema**: Validates configuration against environment-specific schema
4. **Dynamic Registration**: Registers environment type with experiment manager

#### **Event System Integration:**

Network environments integrate with PANTHER's event system:
- **Environment Setup Events**: Fired during environment initialization
- **Service Deployment Events**: Triggered when containers are deployed
- **Health Check Events**: Periodic service health monitoring
- **Teardown Events**: Cleanup and resource deallocation notifications

### Compatibility Matrix

| Environment | strace | gperf | Multi-Service | Cross-Platform |
|-------------|--------|-------|---------------|----------------|
| **Docker Compose** | ✅ | ✅ | ✅ | ✅ (Linux/macOS/Windows) |
| **Localhost Single Container** | ✅ | ✅ | ❌ | ✅ (Linux/macOS/Windows) |
| **Shadow NS** | ❌ | ❌ | ✅ | ⚠️ (Linux only) |

### System Requirements

**Docker Compose Environment:**
- Docker Engine 20.10+
- Docker Compose 2.0+
- Available ports for service communication
- Sufficient system memory for multiple containers

**Localhost Single Container Environment:**
- Docker Engine 20.10+
- Host networking support
- Port availability on localhost

**Shadow NS Environment:**
- Linux operating system (Ubuntu 20.04+ recommended)
- Shadow Network Simulator installed
- Available system memory for simulation
- Root privileges for network namespace creation

---

## Network Configuration Patterns

### Service Discovery and Communication

**Automatic Service Discovery:**
```yaml
network_environment:
  type: "docker_compose"
  config:
    service_discovery:
      enabled: true
      registry: "consul"
      config:
        datacenter: "panther-test"
        encryption: true
    
    services:
      - name: "quic_server"
        discovery:
          tags: ["quic", "server", "v1.0"]
          health_check: "http://localhost:8080/health"
      - name: "quic_client"
        discovery:
          depends_on: ["quic", "server"]
```

**Custom DNS Configuration:**
```yaml
network_environment:
  config:
    dns_config:
      nameservers: ["172.20.0.10"]
      search_domains: ["panther.local"]
      custom_records:
        - name: "quic-server.panther.local"
          ip: "172.20.0.100"
        - name: "quic-client.panther.local"
          ip: "172.20.0.101"
```

### Network Policies and Security

**Traffic Isolation:**
```yaml
network_environment:
  config:
    network_policies:
      - name: "server_isolation"
        selector:
          service: "quic_server"
        ingress:
          - from:
              selector:
                service: "quic_client"
            ports: [4433]
        egress:
          - to: []  # Allow all outbound
      
      - name: "client_restrictions"
        selector:
          service: "quic_client"
        egress:
          - to:
              selector:
                service: "quic_server"
            ports: [4433]
```

**SSL/TLS Configuration:**
```yaml
network_environment:
  config:
    tls:
      enabled: true
      mutual_auth: true
      certificates:
        ca_cert: "/certs/ca.pem"
        server_cert: "/certs/server.pem"
        server_key: "/certs/server-key.pem"
        client_cert: "/certs/client.pem"
        client_key: "/certs/client-key.pem"
```

### Network Conditions Simulation

**Bandwidth Limitation:**
```yaml
network_environment:
  config:
    network_conditions:
      - interface: "eth0"
        bandwidth:
          download: "100mbps"
          upload: "10mbps"
        latency: "20ms"
        jitter: "5ms"
        packet_loss: "0.1%"
```

**Dynamic Network Conditions:**
```yaml
network_environment:
  config:
    dynamic_conditions:
      - time: "0s"
        bandwidth: "1000mbps"
        latency: "1ms"
      - time: "60s"
        bandwidth: "100mbps"
        latency: "10ms"
      - time: "120s"
        bandwidth: "10mbps"
        latency: "100ms"
```

---

## Advanced Features

### Multi-Region Deployments

```yaml
network_environment:
  type: "docker_compose"
  config:
    regions:
      - name: "us-east"
        compose_file: "docker-compose.us-east.yml"
        services: ["quic_server_1", "load_balancer"]
        network:
          subnet: "172.20.0.0/16"
          
      - name: "eu-west"
        compose_file: "docker-compose.eu-west.yml"
        services: ["quic_server_2", "quic_client"]
        network:
          subnet: "172.21.0.0/16"
    
    inter_region:
      vpn_gateway: true
      latency_simulation: "100ms"
      bandwidth_limit: "1gbps"
```

### Load Balancing and Scaling

```yaml
network_environment:
  config:
    load_balancing:
      enabled: true
      algorithm: "round_robin"
      health_checks: true
      
    scaling:
      auto_scale: true
      min_instances: 2
      max_instances: 10
      metrics:
        - type: "cpu"
          threshold: 70
        - type: "memory"
          threshold: 80
        - type: "connections"
          threshold: 1000
```

### Monitoring and Observability

```yaml
network_environment:
  config:
    monitoring:
      enabled: true
      collectors:
        - type: "prometheus"
          port: 9090
          scrape_interval: "15s"
        - type: "jaeger"
          port: 14268
          sampling_rate: 0.1
      
    logging:
      centralized: true
      aggregator: "fluentd"
      destinations:
        - "elasticsearch://logs.panther.local:9200"
        - "file:///app/logs/network.log"
```

---

## Output Analysis and Debugging

### Network Traffic Analysis

**Packet Capture:**
```yaml
network_environment:
  config:
    packet_capture:
      enabled: true
      interfaces: ["eth0", "eth1"]
      filters: ["port 4433", "proto \\udp"]
      output_format: "pcap"
      rotation_size: "100MB"
```

**Network Metrics Collection:**
```python
# Analyze network metrics
import pandas as pd
import matplotlib.pyplot as plt

# Load network metrics
df = pd.read_csv('/app/logs/network_metrics.csv')

# Plot bandwidth usage over time
plt.figure(figsize=(12, 6))
plt.plot(df['timestamp'], df['bandwidth_mbps'])
plt.title('Network Bandwidth Usage')
plt.xlabel('Time')
plt.ylabel('Bandwidth (Mbps)')
plt.show()

# Analyze latency distribution
latency_stats = df['latency_ms'].describe()
print(f"Latency Statistics:\n{latency_stats}")
```

### Service Communication Tracing

**Distributed Tracing:**
```yaml
network_environment:
  config:
    tracing:
      enabled: true
      sampler: "probabilistic"
      sampling_rate: 0.1
      exporters:
        - type: "jaeger"
          endpoint: "http://jaeger:14268/api/traces"
        - type: "zipkin"
          endpoint: "http://zipkin:9411/api/v2/spans"
```

### Performance Analysis

**Network Performance Metrics:**
```bash
# View network performance summary
panther analyze network --experiment-id exp_123

# Generate network topology visualization
panther visualize topology --output topology.png

# Export metrics for external analysis
panther export metrics --format csv --output network_metrics.csv
```

---

## Best Practices

### 1. Environment Selection

Choose environments based on testing requirements:

- **Development**: Use localhost single container
- **Integration**: Use Docker Compose
- **Research/Simulation**: Use Shadow Network Simulator
- **Performance**: Use Docker Compose with network conditions

### 2. Network Design

Design realistic network topologies:

```yaml
# Good: Realistic network hierarchy
topology:
  edge_nodes: 100
  core_nodes: 10
  bandwidth_ratios:
    edge_to_core: "100mbps"
    core_to_core: "10gbps"

# Avoid: Unrealistic flat networks
topology:
  nodes: 1000
  full_mesh: true  # Not realistic for large networks
```

### 3. Resource Management

Optimize resource usage:

```yaml
network_environment:
  config:
    resource_limits:
      cpu_per_service: "0.5"
      memory_per_service: "512MB"
      max_containers: 50
    
    cleanup:
      auto_cleanup: true
      cleanup_timeout: "30s"
      remove_orphaned: true
```

### 4. Reproducibility

Ensure consistent network conditions:

```yaml
network_environment:
  config:
    deterministic: true
    seed: 42
    fixed_delays: true
    precise_timing: true
```

---

## Troubleshooting

### Common Issues

**Port Conflicts:**
```bash
# Check for port usage
lsof -i :4433

# Use dynamic port allocation
panther run --config config.yaml --dynamic-ports
```

**Network Connectivity:**
```yaml
# Add debugging
network_environment:
  config:
    debug:
      ping_tests: true
      dns_resolution: true
      connectivity_matrix: true
```

**Container Communication:**
```bash
# Test container connectivity
docker exec quic_client ping quic_server

# Check network configuration
docker network inspect panther_network
```

**Performance Issues:**
```yaml
# Optimize for performance
network_environment:
  config:
    performance:
      disable_iptables: true
      use_host_network: false
      optimize_buffers: true
```

### Debug Mode

Enable comprehensive debugging:

```bash
export PANTHER_DEBUG_NETWORK=1
export PANTHER_NETWORK_VERBOSE=1
panther --experiment-config config.yaml
```

---

## Integration Examples

### Cloud Provider Integration

```yaml
network_environment:
  type: "cloud_compose"
  config:
    provider: "aws"
    regions: ["us-east-1", "eu-west-1"]
    vpc_config:
      cidr: "10.0.0.0/16"
      subnets:
        - "10.0.1.0/24"
        - "10.0.2.0/24"
```

---

## Related Documentation

### Comprehensive Workflow Documentation
For detailed workflow information, see:
- **[PANTHER Workflows](PANTHER_WORKFLOWS.md)** - Complete architecture and workflow documentation
  - Container building and deployment processes
  - Plugin system architecture and loading mechanisms
  - Event-driven architecture details
  - Service manager integration workflows
  - Performance optimization and troubleshooting

### Module-Specific Documentation
For specialized configuration details, see:
- **[Execution Environment Modules](execution_environment_modules.md)** - Execution environment configuration
- **[Service Modules](service_modules.md)** - Service configuration and management
- **[Protocol Modules](protocol_modules.md)** - Protocol-specific implementations
- **[Tester Modules](tester_modules.md)** - Test framework integration

### Configuration and Setup
For setup and configuration guidance, see:
- **[Configuration Guide](configuration_guide.md)** - Complete configuration reference
- **[Quick Start Guide](QUICK_START.md)** - Getting started with PANTHER
- **[Experiment Guide](EXPERIMENT_GUIDE.md)** - Designing and running experiments

### Development and Contributing
For development information, see:
- **[Development Guide](DEV_GUIDE.md)** - Development environment setup
- **[Contributing Guide](CONTRIBUTING.md)** - Contribution guidelines
- **[Core Components](CORE_COMPONENT.md)** - Architecture deep-dive

---

*This documentation has been updated to reflect the actual implementation schemas and capabilities. For a complete list of corrections made, see [Documentation Corrections](DOCUMENTATION_CORRECTIONS.md).*
