claude-flow config show<div class="frontmatter">

<div class="keyword">

Plugins architecture ,Formal Verification ,Network Protocols ,Network
Simulation ,Reproducibility ,QUIC ,Ivy ,Shadow ,Black Box testing

</div>

</div>

<div id="tab:metadata">

| **Nr.** | **Description**                                                   | **Code metadata**                                                         |
|:-------:|:------------------------------------------------------------------|:--------------------------------------------------------------------------|
|   C1    | Current code version                                              | v1.1.4                                                                    |
|   C2    | Permanent link to code/repository used for this code version      | <https://github.com/ElNiak/PANTHER>                                       |
|   C3    | Permanent link to Reproducible Capsule                            |                                                                           |
|   C4    | Legal Code License                                                | MIT                                                                       |
|   C5    | Code versioning system used                                       | git                                                                       |
|   C6    | Software code languages, tools, and services used                 | Python 3.10, docker, Ivy, Shadow                                          |
|   C7    | Compilation requirements, operating environments and dependencies | Linux OS (Ubuntu, Debian), MacOS; Docker version 27.2.1, build 9e34c9b |
|   C8    | If available, link to developer documentation/manual              | <https://elniak.github.io/PANTHER>                                        |
|   C9    | Support email for questions                                       | <christophe.crochet@uclouvain.be>                                           |

Code metadata (mandatory)

</div>

# Introduction

General-purpose formal-method tools (e.g., TLA+ with Apalache, ProB)
enable high-level verification of protocol models but do not execute
real code or simulate detailed network behavior . White-box fuzzers and
property-based testing frameworks can find implementation bugs but lack
formal specificationification integration and cannot model
timing-sensitive network conditions .

Simulators like NS-2/NS-3 model packet flows realistically but cannot
run actual protocol implementations . Model-based testing (MBT) tools
such as TorXakis generate test suites from formal models but lack
extensibility and reproducibility for diverse scenarios .
Protocol-specific testers (e.g., QUIC tools) do not generalize to other
protocols.

Network-Centric Compositional Testing (NCT) leverages Ivy to produce
formal, stateful testers and revealed 27 distinct errors (including
crashes, assertion failures, and protocol compliance violations) across
multiple QUIC server implementations during its evaluation and led to
real‐world fixes and standard clarification . While NCT supports
adversarial testing, it does not model network timing, so experiments
can be non-deterministic and irreproducible. Network Simulator-Centric
Compositional Testing (NSCT) integrates Ivy with the Shadow simulator,
enabling deterministic, time-aware testing of real implementations and
detected bugs—such as an idle‐timeout compliance error in picoquic .
However, NSCT is a proof-of-concept requiring manual per-protocol
integration. Network Attack-Centric Compositional Testing (NACT) uses
formal specification mutations and and composable attacker models to
discover multiple new vulnerabilities (e.g., version negotiation abuse,
buffer‐overflow scenarios) across five widely used QUIC stacks,
including regressions introduced by patches , but focuses on black-box
security scenarios rather than reproducible code-level experimentation.

`PANTHER` extends Ivy by automating our methodologies (NSCT and NACT)
workflows with a plugin-based architecture. Its modified Ivy core
automatically links test generation with Shadow simulation and supports
adversarial mutation injection.
Table <a href="#tab:comparison" data-reference-type="ref"
data-reference="tab:comparison">[tab:comparison]</a> compares PANTHER’s
capabilities with prior tools.

This paper is organized as follows. Section
<a href="#sec:desc" data-reference-type="ref"
data-reference="sec:desc">2</a> describes `PANTHER`’s architecture and
core components, including the plugin framework, configuration system,
and observer infrastructure. Section
<a href="#sec:eg" data-reference-type="ref"
data-reference="sec:eg">3</a> presents a concrete example—testing a QUIC
connection. Finally, Section
<a href="#sec:concl" data-reference-type="ref"
data-reference="sec:concl">4</a> concludes and outlines directions for
future work.

# Software Description

## Motivation

Network protocols are complex and prone to subtle bugs; comprehensive
testing frameworks are needed to validate both their dynamic behavior
and formal properties. `PANTHER` addresses this need by combining
simulation, execution, and formal analysis in a unified environment. In
particular, it integrates the Shadow network simulator with the Ivy
verification tool to enable time-dependent protocol analysis. By running
protocol implementations under containerized networks and formal test
suites, `PANTHER` helps researchers uncover errors or vulnerabilities
that other analysis techniques alone might miss.  
`PANTHER` offers several key features:

1. **Extensible plugin architecture:** New protocols, implementations,
    or environment types can be integrated via plugins, and the
    framework includes templates and guides for adding custom plugins.

2. **Shadow network simulation:** A built-in Shadow environment
    emulates networks with configurable latency and multi-node
    topologies, enabling reproducible tests of distributed protocols.

3. **Formal Ivy testing:** The Ivy-based tester plugin automatically
    runs tests derived from a formal protocol model, bridging
    specification and execution. Extended with formal specification
    mutation testing.

4. **Docker-based:** Experiments are containerized for consistency. A
    Docker Compose plugin sets up multi-container networks, and all
    components (services, Ivy tester, etc.) are launched in Docker so
    that tests are isolated and repeatable.

## Architecture and Design

`PANTHER` core is a CLI framework that reads an experiment configuration
(YAML file with schema validation) and assembles the testbed. The
framework uses a plugin-based architecture: each experiment is defined
by a combination of plugins for the network, execution environment, the
implementation under test (IUT), and the tester (and their related
protocols). For example:

- **Network environments:** Plugins implement different network
    setups. `PANTHER` provides a Docker Compose environment (for simple
    LANs) and a Shadow network simulator based environment for realistic
    multi-hop topologies.

- **Execution environments:** Plugins such as `strace` or `gprof`
    allow profiling or instrumentation of the IUT processes (CPU,
    memory, system calls).

- **Services/Implementations (IUT):** Each protocol implementation
    (e.g. PicoQUIC for QUIC, or the MiniP PingPong service) is
    encapsulated as an IUT plugin. These plugins point to executables
    and configuration files for different protocol versions.

- **Testers:** Tester plugins drive the experiment logic. `PANTHER`
    includes a “PantherIvy” tester that generates and executes protocol
    tests derived from formal Ivy specifications. Additional tester
    types (e.g. custom fuzzers or scripted tests) can be added
    similarly.

- **Protocol plugins:** Specify protocol‐specific metadata (e.g.,
    client/server vs. P2P roles, RFC versions, frame/packet formats).
    These plugins ensure both IUTs and testers use consistent protocol
    logic and parameters.

The user writes a YAML file describing the services (including roles,
ports, timeouts) and test steps; `PANTHER` validates it and then
launches all components via Docker. For example, after preparing an
experiment config one can simply run
`panther –experiment-config experiment-config.yaml` to execute the test
suite. Experiment details are fully specified in YAML files (with schema
validation), and results (logs, pass/fail status) are collected
automatically.

`PANTHER` is implemented in Python and relies on Docker for reproducible
environments. Its Python package (`panther_net`) is open-source Python,
supplemented by C/C++ code in the Ivy library and Rust in the the
Shadow. It is distributed via PyPI (installable as
`pip install panther_net`) or by cloning the GitHub repository and
running the provided setup. Experiments are orchestrated by Python code
that invokes `docker-compose` (to set up the network) and controls the
execution plugins. The framework has been tested on Ubuntu 20.04 with
Docker (v27+) and Python 3.10+, and continuous-integration pipelines
ensure code quality.

Figure <a href="#fig:panther_architecture" data-reference-type="ref"
data-reference="fig:panther_architecture">[fig:panther_architecture]</a>
shows the `PANTHER` core components. An `ExperimentManager` orchestrates
the entire testing workflow and sets up `TestCase` instances, while a
dynamic `PluginManager` discovers and loads protocol, service and
environment plugins. Each `ServiceManager` encapsulates a protocol
implementation under test (IUT) or a tester, handling build/deploy
commands and lifecycle hooks (pre‐run, main‐run and post‐run).
Environment plugins—`NetworkEnvironment` (e.g. Docker Compose or Shadow)
and `ExecutionEnvironment` (e.g. Docker, gprof/strace profilers, memory
checkers)—establish network topologies and isolated runtimes for each
service.

An event‐driven `Observer System` collects logs, metrics and outputs in
real time, and a `Configuration System` (global and per‐experiment
YAMLs) validates schemas and supplies typed parameters to all plugins.

All experiments are defined declaratively in single YAML files, ensuring
reproducibility. The configuration system validates input and supplies
parameters to plugins via typed schemas and OmegaConf python package.

## Experiments Workflow

`PANTHER` experiments follow a multi-phase workflow that cleanly
separates build, configuration, execution, and analysis tasks. In
general, each experiment proceeds through four main phases:

- **Phase 1 - Initialization:** Load and validate the global and
    experiment-specific configurations. The framework reads the YAML
    experiment file (containing service, protocol, and environment
    specifications) and instantiates an `ExperimentManager`. It
    initializes core objects and prepares each TestCase. This phase must
    complete successfully before any resources are provisioned.

- **Phase 2 - Plugin Loading and Service Setup:** The Plugin Manager
    scans the plugin directories and loads all specified components
    (protocol plugins, IUT and tester service plugins, environment
    plugins). For each service, a service manager is created and a
    sequence of commands is generated. This includes commands for
    building binaries/images, and deployment/run commands templated via
    Jinja2 using parameters from the configuration. The result is a set
    of ready-to-execute instructions for each containerized service.

- **Phase 3 - Environment Setup and Deployment:** The selected network
    environment plugin is invoked to configure the network. For example,
    a Docker Compose workflow will generate a `docker-compose.yml`
    defining the IUT and tester services, shared volumes, networks, and
    environment variables. The framework then builds any necessary
    container images (e.g. compiling the IUT or pulling base images) and
    deploys the services according to the environment specification.
    Monitoring tools (e.g. packet capture or metrics collectors) are
    also deployed at this stage.

- **Phase 4 - Test Execution:** The Experiment Manager starts the
    network environment, then issues the “start” commands for each IUT
    and tester service. It executes any pre-run setup commands, then
    runs the main test commands on the tester to exercise the protocol
    (e.g. initiating a handshake or sending data). During execution, the
    framework observes events (packets, logs, metrics) in real time.
    After the main commands complete, any post-run cleanup commands are
    executed. Finally, the framework collects results: stopping services
    and the network, gathering logs, packet captures, and performance
    metrics into a structured results directory.

# Example: QUIC Connection

As a concrete use-case, consider testing the TLS handshake over QUIC
between a client IuT and server tester. In `PANTHER`, one would
configure an experiment YAML specifying a QUIC server IUT plugin (e.g.
the `picoquic` service) and a corresponding tester plugin (which could
be an Ivy-based protocol tester). The experiment would use the QUIC
protocol plugin to drive the handshake logic.

A Docker Compose network environment plugin might be chosen to create
two containerized hosts. During the build phase, `PANTHER` would compile
or pull the necessary images for both the client and tester. The
configuration phase loads settings such as which QUIC version and
certificates to use. Upon execution, the framework deploys the
containers, starts the QUIC server (IUT) and tester.

The client initiates a QUIC connection, performing the handshake
sequence while the tester plugin checks each received packet. It also
used its formal specfication to generate valid (or not) packet.

All network packets (e.g. the ClientHello/ServerHello, encryption
handshake) and performance metrics (RTT, CPU usage) are recorded.
Because the entire scenario is defined by a YAML file, the experiment is
fully reproducible.

After the handshake completes, logs and packet captures are available
for off-line analysis or verification.

(<a href="#app:quic_example" data-reference-type="ref"
data-reference="app:quic_example">5</a> provides a sample snippet of the
YAML configuration and commands involved in a QUIC handshake workflow.)

# Conclusion and Future Works

`PANTHER` combines formal verification with deterministic, realistic
simulations of real code. By using Shadow for controlled latency and
jitter, it ensures reproducible, time‐dependent property checks .
Meanwhile, `Ivy`’s black‐box approach validates implementations against
formal specifications . Its plugin architecture allows new protocols,
environments, and testing modules—including multiple protocols in one
experiment.

Future work includes a GUI for experiment design and result
visualization, simplifying network scenario setup and analysis. A
stateful fuzzer plugin will extend `Ivy`’s formal checks by exploring
protocol state transitions for vulnerabilities.

Finally, integrating a Large Language Model module will enable further
development of the tool. ntegrating large language models (LLMs) is also
planned to assist in automated test‐case generation and analysis.

Future work will also explore integrating `PANTHER` with the AMC3
project to automate Common Criteria Certification workflows while
testing more advanced softwares.

#### **Acknoledgements**

The research underlying these results received funding from the Defense
Department under contract no. \[23DEFRA001\].

# Concrete Example: QUIC connection Experiment

This appendix illustrates a complete, minimal PANTHER experiment for
testing a QUIC connection between a client and server implementation
(e.g., `picoquic`). We show:

1. A sample experiment YAML file (`quic_connection.yaml`).

2. The resulting Docker Compose snippet generated by the
    `picoquic_service` plugin.

3. The Ivy tester invocation (via the `panther_ivy` plugin).

4. How test output files and optional performance metrics can be
    collected.

## Experiment YAML: `quic_connection.yaml`

``` yaml
# quic_connection.yaml
logging:
  level: DEBUG
  format: "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"

paths:
  output_dir: "outputs"
  log_dir: "outputs/logs"
  config_dir: "panther/configs"
  plugin_dir: "panther/plugins"

docker:
  build_docker_image: True

tests:
  - name: quic_connection_test
    description: >
      Verify picoquic server completes a QUIC v1 handshake with Ivy-based
      formal tester.

    network_environment:
      - docker_compose
      
    services:
      picoquic_client:
        timeout: 100
        name: "picoquic_client_name"
        implementation:
          name: "picoquic"
          type: "iut"
        protocol:
          name: "quic"
          version: "rfc9000"
          role: "client"
          target: "ivy_server"  # Docker Compose service name
        ports:
          - "5000:5000"
          - "8081:8081"
        generate_new_certificates: True

      ivy_server:
        name: "ivy_server"
        timeout: 150
        implementation:
          name: "panther_ivy"
          type: "testers"
          test: quic_client_test_max
        protocol:
          name: "quic"
          version: "rfc9000"
          role: "server"
          target: "picoquic_client"  # Docker Compose service name
        ports:
          - "5000:5000"
          - "4987:4987"
          - "8081:8081"
        generate_new_certificates: True

    steps:
      wait: 150  # seconds to wait during the test
```

When developing a new environment plugin for PANTHER, one typically
extends the base schema in `panther/config/config_experiment_schema.py`.
Below is an example of how to define `DockerComposeConfig`. This
dataclass is used to validate and automatically generate the
corresponding fields:

``` python
from dataclasses import dataclass, field
from panther.config.config_experiment_schema import NetworkEnvironmentConfig

@dataclass
class DockerComposeConfig(NetworkEnvironmentConfig):
    type: str = "docker_compose"
    version: str = "3.8"
    network_name: str = "default_network"
    service_prefix: str | None = None
    volumes: list[str] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
```

## Generated Docker Compose Snippet

During Phase 3 (Environment Setup), PANTHER’s `picoquic_service` plugin
substitutes variables like `{{server_port}}` and `{{server_ip}}`. The
following excerpt is the generated `docker-compose.yml` for the `server`
and `client` services:

``` yaml
name: quic_connection
services:
  picoquic_client:
    image: picoquic_rfc9000_panther:latest
    container_name: picoquic_client
    stop_grace_period: 30s
    ports:
      - "5000:5000"
      - "8081:8081"
    environment:
      ROLE: client
      SSLKEYLOGFILE: "/app/logs/sslkeylogfile.txt"
    tty: true
    stdin_open: true
    cap_add:
      - CAP_NET_ADMIN
      - CAP_NET_RAW
    working_dir: "/opt/picoquic"
    entrypoint:
      - /bin/sh
      - -c
      - |
        chmod +x /app/entrypoint.sh \
        && exec /app/entrypoint.sh

    volumes:
      - outputs/quic_connection_test/logs/picoquic_client:/app/logs/
      - outputs/quic_connection_test/entrypoint_picoquic_client.sh:/app/entrypoint.sh
      - "shared_logs:/app/sync_logs"
    networks:
      panther_network:
        aliases:
          - picoquic_client

  ivy_server:
    image: panther_ivy_rfc9000_panther:latest
    container_name: ivy_server
    stop_grace_period: 30s
    ports:
      - "4443:4443"
      - "4987:4987"
      - "8080:8080"
    environment:
      ROLE: server
      SSLKEYLOGFILE: "/app/logs/sslkeylogfile.txt"
      PROTOCOL_TESTED: "quic"
      RUST_LOG: "debug"
      RUST_BACKTRACE: "1"
      SOURCE_DIR: "/opt/"
      IVY_DIR: "/opt//panther_ivy"
      INITIAL_VERSION: "1"
      TEST_TYPE: "client"
    tty: true
    stdin_open: true
    cap_add:
      - CAP_NET_ADMIN
      - CAP_NET_RAW
    working_dir: "/opt/panther_ivy/protocol-testing/quic/"
    entrypoint:
      - /bin/sh
      - -c
      - |
        chmod +x /app/entrypoint.sh \
        && exec /app/entrypoint.sh

    volumes:
      - outputs/quic_connection_test/logs/ivy_server:/app/logs/
      - outputs/quic_connection_test/entrypoint_ivy_server.sh:/app/entrypoint.sh
      - "panther/plugins/services/testers/panther_ivy/ivy/include/1.7:
            /opt/panther_ivy/ivy/include/1.7"
      - "panther/plugins/services/testers/panther_ivy/protocol-testing/quic:
            /opt/panther_ivy/protocol-testing/quic"
      - "shared_logs:/app/sync_logs"
    networks:
      panther_network:
        aliases:
          - ivy_server

networks:
  panther_network:
    driver: bridge

volumes:
  shared_logs:
    driver: local
```

**Note:** The entrypoint script (`/app/entrypoint.sh`) is generated via
a Jinja template supplied by the service plugin, ensuring that
command‐line arguments (e.g., ALPN, certificate paths) are correctly
set.

## Test Invocation

When the `docker-compose.yml` is ready, PANTHER executes:

``` bash
docker-compose -f quic_connection/docker-compose.yml up -d --build
```

This builds and starts both the `picoquic_client` and `ivy_server`
containers. The Ivy tester (`panther_ivy`) inside `ivy_server` then
automatically runs `quic_client_test_max`, driving the handshake against
the running `picoquic_demo` in `picoquic_client`. The Ivy‐generated test
sequences, including packet injections and state checks, occur over the
Shadow‐controlled virtual network.

Below is a minimal Ivy model (‘.ivy‘) for a QUIC server tester. It
imports the necessary modules, fixes some transport parameters, and
exports the relevant frame‐ and packet‐handling actions as well as a
final validation check.

``` bash
#lang ivy1.7

include order
include quic_infer
include file
include ivy_quic_shim_server
include quic_locale
include ivy_quic_server_behavior
include ivy_quic_server_standard_tp
include quic_time

after init {
    call time_api.c_timer.start;
}

export frame.ack.handle
export frame.stream.handle
export frame.crypto.handle
export frame.path_response.handle  
export frame.handshake_done.handle
export packet_event
export client_send_event
export tls_recv_event

export action _finalize = {
    require is_no_error | is_no_error_h3;
    require conn_total_data(the_cid) > 0;
    require respect_idle_timeout;
}
```

In this snippet:

- We begin with `#lang ivy1.7` and include several Ivy modules that
    contain QUIC‐specific definitions (`ivy_quic_shim_server`,
    `ivy_quic_server_behavior`, etc.).

- We include `ivy_quic_server_standard_tp` to fix the initial
    transport parameters. In a more sophisticated test one might choose
    them randomly instead.

- The `after init { … }` block starts the Ivy‐provided timer
    (“`c_timer`”). This ties Ivy’s notion of elapsed time to our
    Shadow‐driven simulation clock (so that timeouts behave
    deterministically).

- We `export` a set of frame‐ and packet‐handling actions:
    `frame.ack.handle`, `frame.stream.handle`, `frame.crypto.handle`,
    `frame.path_response.handle`, `frame.handshake_done.handle`,
    `packet_event`, `client_send_event`, and `tls_recv_event`. Ivy will
    attempt to generate these events when driving the server under test.

- Finally, we define the special Ivy action `_finalize`. This is
    invoked when the test ends. Our `require` statements assert that:

    1. No protocol‐level error occurred (`is_no_error`)

    2. At least some data was exchanged on the connection
        (`conn_total_data(the_cid) > 0`).

    3. The server respected the idle timeout (`respect_idle_timeout`).

    If any of these checks fail, Ivy reports a counterexample.

## Result Collection and Metrics

After the handshake completes (or times out), PANTHER performs:

1. **Container Teardown:**

    ``` bash
        docker-compose -f quic_connection/docker-compose.yml down
    ```

2. **Log Aggregation:**

    - `outputs/quic_connection_test/logs/picoquic_client/` contains:

        - `picoquic_client_setup.log` (environment and compilation
            logs).

        - `picoquic_client_commands.log` (command‐line parameters and
            execution details).

    - `outputs/quic_connection_test/logs/ivy_server/` contains:

        - `ivy_server_setup.log` (Ivy model compilation).

        - `ivy_server_commands.log` (Ivy invocation and random seed).

        - `ivy_server_status.log` (pass/fail outcomes, state
            assertions).

        - `ivy_server_error.log` (detailed counterexamples on
            failure).

    - `outputs/quic_connection_test/logs/docker-compose.log` and  
        `docker-compose-up.err.log` record container lifecycle events.

3. **Optional Packet Capture:**

    ``` bash
        tcpdump -i lo -w outputs/quic_connection_test/trace.pcap udp port 4443
    ```

    PANTHER will start `tcpdump` on the host to capture all QUIC traffic
    for offline analysis.

4. **Performance Metrics (Optional):**

    - **RTT:** Ivy can record timestamps of packet events—e.g., client
        Initial send vs. server Initial ACK receipt—allowing calculation
        of round‐trip times.

    - **Packet Loss / Retransmissions:** Ivy’s model can log expected
        vs. actual packet numbers; discrepancies indicate
        retransmissions or losses.

    - **Throughput / Bandwidth Usage:** If the IUT supports counters
        (e.g., via `-B` options), PANTHER’s service plugin can collect
        and merge them into `outputs/quic_connection_test/metrics.json`.

    - **Resource Usage:** CPU and memory usage of `picoquic_client`
        and `ivy_server` are recorded for performance profiling.

**Directory Layout After Test Completion:**

``` bash
outputs/
└── quic_connection_test/
    ├── docker-compose.yml
    ├── entrypoint_picoquic_client.sh
    ├── entrypoint_ivy_server.sh
    ├── logs/
    │   ├── docker-compose.log
    │   ├── docker-compose-up.err.log
    │   ├── picoquic_client/
    │   │   ├── picoquic_client_setup.log
    │   │   ├── picoquic_client_commands.log
    │   │   └── … 
    │   └── ivy_server/
    │       ├── ivy_server_setup.log
    │       ├── ivy_server_commands.log
    │       ├── ivy_server_status.log
    │       └── ivy_server_error.log
    ├── metrics.json               % (if enabled)
    └── trace.pcap                 % (if capture enabled)
```
