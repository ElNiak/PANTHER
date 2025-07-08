# PANTHER — Protocol Analysis and Testing Harness for Extensible Research

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.10819552.svg)](https://doi.org/10.5281/zenodo.10819552)
[![mkdocs](https://github.com/ElNiak/PANTHER/actions/workflows/pr-generate-docs.yaml/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/pr-generate-docs.yaml)
[![pages-build-deployment](https://github.com/ElNiak/PANTHER/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/pages/pages-build-deployment)
[![dependabot](https://github.com/ElNiak/PANTHER/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/dependabot/dependabot-updates)
[![Python application](https://github.com/ElNiak/PANTHER/actions/workflows/python-app.yml/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/python-app.yml)
[![Python package](https://github.com/ElNiak/PANTHER/actions/workflows/python-package.yml/badge.svg?branch=production)](https://github.com/ElNiak/PANTHER/actions/workflows/python-package.yml)
[![pypi](https://github.com/ElNiak/PANTHER/actions/workflows/python-publish.yml/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/python-publish.yml)
[![pytest](https://github.com/ElNiak/PANTHER/actions/workflows/unittests_codecov.yml/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/unittests_codecov.yml)
[![Greetings](https://github.com/ElNiak/PANTHER/actions/workflows/greetings.yml/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/greetings.yml)
[![pre-commit](https://github.com/ElNiak/PANTHER/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/pre-commit.yml)
[![CodeQL](https://github.com/ElNiak/PANTHER/actions/workflows/codeql.yml/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/codeql.yml)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/c8043e5320934d49a688e173db5a331d)](https://app.codacy.com/gh/ElNiak/PANTHER/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Qodana](https://github.com/ElNiak/PANTHER/actions/workflows/qodana_code_quality.yml/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/qodana_code_quality.yml)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white) ![C++](https://img.shields.io/badge/c++-%2300599C.svg?style=for-the-badge&logo=c%2B%2B&logoColor=white) ![Debian](https://img.shields.io/badge/Debian-D70A53?style=for-the-badge&logo=debian&logoColor=white)

PANTHER is a **plugin‑based, research‑grade test harness** that lets you design, reproduce, and analyse complex **network‑protocol experiments** without hand‑rolling scripts or bespoke infrastructure.

!!! info "What PANTHER Solves"
    - **Protocol Validation**: Test QUIC or custom protocol implementations under failure, jitter, or adverse timing
    - **Performance Profiling**: Analyze CPU, heap, and syscall characteristics across different builds or OS kernels
    - **Formal Verification**: Run conformance checks (Ivy) in deterministic network simulation (Shadow)

**Core characteristics:**

▸ **Reproducible:** every experiment is defined in a single YAML file and executed in an isolated container environment.

▸ **Extensible:** a plugin system adds new protocols, services, profilers, or network back‑ends with minimal boilerplate.

▸ **Multi‑audience:** useful to academic researchers, industrial developers, security analysts, SRE teams, and educators.esting Harness for Extensible Research

---

## 🐳 Docker Builder Modernization

This project includes a comprehensive modernization of PANTHER's Docker build system to support **multi-platform builds** with BuildKit, auto-detection of Docker builders, and optimized cross-platform compilation.

### Cross-Platform Build Architecture

#### Problem Statement
PANTHER needed to support building Docker images for different target architectures (AMD64, ARM64) while maintaining build performance and correctness. The original implementation had several critical issues:

1. **Platform Variable Confusion**: Dockerfile used `$TARGETPLATFORM` for builder stages, forcing emulation
2. **Missing BuildKit Arguments**: Platform variables like `$TARGETARCH` were empty due to improper argument passing
3. **Performance Penalties**: Cross-platform builds were 10-50x slower due to emulation
4. **Cache Inefficiency**: Platform-specific caches were incorrectly configured

#### Solution Overview
Our modernization implements Docker's recommended cross-platform build patterns:

```dockerfile
# ✅ CORRECT: Builder runs on native platform (fast)
FROM --platform=$BUILDPLATFORM ubuntu:20.04 AS builder

# ✅ CORRECT: Runtime targets destination platform
FROM --platform=$TARGETPLATFORM ubuntu:20.04 AS minimal
```

#### Key Architecture Concepts

**Platform Variables in Docker BuildKit**:
- **`BUILDPLATFORM`**: Platform where the build is running (e.g., `linux/arm64`)
- **`TARGETPLATFORM`**: Platform the image is being built for (e.g., `linux/amd64`)
- **`TARGETOS`**: Target operating system (e.g., `linux`)
- **`TARGETARCH`**: Target architecture (e.g., `amd64`, `arm64`)

**Cross-Platform Build Flow** (ARM64 → AMD64):
1. **Builder Stage** (`--platform=$BUILDPLATFORM`): Runs natively on ARM64 host → full performance
2. **Cross-Compilation**: Installs toolchains based on `$TARGETARCH`, compiles for AMD64
3. **Runtime Stages** (`--platform=$TARGETPLATFORM`): Final image runs on AMD64

#### Performance Characteristics

| Build Scenario | Performance | Notes |
|----------------|-------------|--------|
| **Native ARM64 → ARM64** | 100% | No cross-compilation needed |
| **ARM64 → AMD64 (Fixed)** | 80-95% | Native builder + cross-compilation |
| **ARM64 → AMD64 (Broken)** | 5-20% | Emulation penalty (what we fixed) |

#### Key Fixes Applied

1. **Platform Variable Fix**: Changed builder stage from `$TARGETPLATFORM` to `$BUILDPLATFORM`
2. **Builder Auto-Detection**: Intelligent detection of active Docker buildx builder
3. **Simplified Build Arguments**: Removed complex filtering that prevented essential arguments
4. **Cache Optimization**: Platform-aware cache mounting for maximum efficiency

For detailed technical documentation, see the [Docker Build Architecture Guide](#docker-build-architecture-guide) below.

---

## 🔄 Quick Workflow Overview

PANTHER experiments follow a **4-phase execution model**:

### Phase 1: Initialization

* Load configurations and validate experiment setup
* Initialize plugin system and service managers
* Create test case instances

### Phase 2: Plugin Loading & Service Setup

* Discover and load protocol/implementation plugins
* Create service managers for each IUT (Implementation Under Test)
* Generate deployment and execution commands

### Phase 3: Environment Deployment

* Setup network environment (Docker Compose, localhost, or Shadow NS)
* Build container images for protocol implementations
* Deploy services with proper networking and monitoring

### Phase 4: Test Execution

* Start services and execute test scenarios
* Monitor execution with automatic packet capture
* Collect results, logs, and performance metrics
* Teardown environment and generate reports

**Key Features:**

* **Reproducible**: Every experiment defined in single YAML configuration
* **Containerized**: Isolated execution environments with Docker
* **Event-driven**: Real-time monitoring and coordination
* **Extensible**: Plugin architecture for new protocols and environments

For detailed workflow documentation, see [WORKFLOW.md](WORKFLOW.md).

---

## System Requirements

| Component | Minimum | Notes |
|-----------|---------|-------|
| Python    | 3.10    | Use `venv` for isolation for main functionality. |
| Docker    | 27.x    | Required for all orchestration modes. |

`pyproject.toml` is the source of truth for Python dependencies.
`requirements.txt` is a frozen snapshot—**do not edit**.

**Note**: We propose to install [`slim`](https://github.com/slimtoolkit/slim) in our builder, fasten container size.

---

## 📑 Table of Contents

### Getting Started

1. [Installation Guide](INSTALL.md)
2. [Quick Start](QUICK_START.md)
3. [Configuration](panther/config/README.md)
4. [Workflows](WORKFLOW.md)
5. [Core](panther/core/README.md)
6. [Web Application Workflows](panther/webapp/README.md)

### System Features

7. [Fast-Fail System](FAST_FAIL_SYSTEM.md) - Intelligent experiment termination and error handling
8. [Experiment Reporting](EXPERIMENT_REPORTING.md) - Automatic generation of experiment reports and status summaries
9. [Configuration Management](panther/config/README.md) - Advanced configuration validation, auto-fixing, and protocol-aware port management

### Plugins

10. [Overview](panther/plugins/README.md)
11. [Inventory](panther/plugins/plugins_inventory.md)
12. **Environment Plugins**
   * [Overview](panther/plugins/environments/README.md)
   * [Network Environment](panther/plugins/environments/network_environment/README.md)
   * [Execution Environment](panther/plugins/environments/execution_environment/README.md)
13. **Protocol Plugins**
    * [Overview](panther/plugins/protocols/README.md)
    * [Client-Server Protocols](panther/plugins/protocols/client_server/README.md)
    * [Peer-to-Peer Protocols](panther/plugins/protocols/peer_to_peer/README.md)
14. **Service Plugins**
    * [Overview](panther/plugins/services/README.md)
    * [Implementation Under Tests (IUTs)](panther/plugins/services/iut/README.md)
    * [Testing Services](panther/plugins/services/testers/README.md)

### Developer Guide

15. [Contributing](CONTRIBUTING.md)
16. **Plugin Development**
    * [Overview](panther/plugins/development.md)
    * **Environment Plugins**
      * [Overview](panther/plugins/environments/development.md)
      * [Network Environment](panther/plugins/environments/network_environment/development.md)
      * [Execution Environment](panther/plugins/environments/execution_environment/development.md)
    * [Protocol Plugins](panther/plugins/protocols/development.md)
    * **Service Plugins**
      * [Overview](panther/plugins/services/development.md)
      * [Implementation Under Tests (IUTs)](panther/plugins/services/iut/development.md)
      * [Testing Services](panther/plugins/services/testers/development.md)

### Project Information

17. [Changelog](CHANGELOG.md)
18. [License](LICENSE.md)
19. [Code Reference](https://elniak.github.io/PANTHER/panther/)


## Documentation

For detailed information on using PANTHER, see the:

* [elniak.github.io/PANTHER](elniak.github.io/PANTHER)

## Contributing

Contributions are welcome! To get started:

* Fork the repository.
* Create a new branch for your feature or bug fix.
* Submit a pull request with a clear description of your changes.

For more details, see the [Contribution Guide](CONTRIBUTING.md).

## Contact

For support or inquiries, please contact:

* ElNiak
* Open an issue on the GitHub repository.

---

## 🐳 Docker Build Architecture Guide

### Detailed Technical Implementation

This section provides comprehensive technical details about the Docker builder modernization implemented in this project.

#### Multi-Stage Dockerfile Structure

The modernized `Dockerfile.buildkit` follows a four-stage architecture optimized for cross-platform builds:

```dockerfile
# STAGE 1: BUILDER (runs on build platform)
FROM --platform=$BUILDPLATFORM ubuntu:20.04 AS builder
# Installs cross-compilation tools based on $TARGETARCH
# Compiles software natively on ARM64 for AMD64 target

# STAGE 2: DEBUG (extends builder)
FROM builder AS debug
# Adds debugging tools

# STAGE 3: MINIMAL (runs on target platform)
FROM --platform=$TARGETPLATFORM ubuntu:20.04 AS minimal
# Runtime environment for target architecture

# STAGE 4: FINAL (runtime mode selection)
FROM ${RUNTIME_MODE} AS final
# Selects debug/minimal based on RUNTIME_MODE argument
```

#### Cache Strategy Implementation

Different cache types use different platform variables for optimal performance:

```dockerfile
# Build environment caches (use BUILDPLATFORM - where build happens)
--mount=type=cache,target=/var/cache/apt,id=apt-$BUILDPLATFORM,sharing=locked
--mount=type=cache,target=/tmp/git-cache,id=git-$BUILDPLATFORM,sharing=locked

# Compiled artifacts cache (use TARGETPLATFORM - what we're building for)
--mount=type=cache,target=/tmp/build-cache,id=build-$TARGETPLATFORM,sharing=private
```

#### Fixed Issues in Detail

##### 1. Platform Variable Emulation (Critical Fix)

**Before** (❌ Broken):
```dockerfile
FROM --platform=$TARGETPLATFORM ubuntu:20.04 AS builder
```
- Builder forced to run on AMD64 target platform
- ARM64 host emulates AMD64 → 10-50x performance penalty
- BuildKit platform arguments become inconsistent/empty

**After** (✅ Fixed):
```dockerfile
FROM --platform=$BUILDPLATFORM ubuntu:20.04 AS builder
```
- Builder runs natively on ARM64 build platform → full performance
- Cross-compilation handles AMD64 target → proper platform arguments

##### 2. Builder Auto-Detection Implementation

**Enhancement in `docker_builder.py`**:
```python
def _get_active_buildx_builder(self) -> str:
    """Auto-detect active buildx builder from 'docker buildx ls' output."""
    try:
        result = subprocess.run(["docker", "buildx", "ls"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line.strip() and not line.startswith(" \\"):
                    if "*" in line:  # Active builder marked with asterisk
                        name_part = line.split()[0]
                        builder_name = name_part.rstrip("*")
                        self.logger.debug("Auto-detected active buildx builder: %s", builder_name)
                        return builder_name
    except Exception as e:
        self.logger.warning("Unexpected error detecting buildx builder: %s, falling back to 'default'", e)
    return "default"
```

**Configuration Support**:
```python
buildx_builder: str = Field("auto",
    description="Use 'auto' for auto-detection, 'default' for Docker's default, or specify custom builder name")
```

##### 3. Simplified Build Argument Passing

**Problem**: Complex filtering logic prevented essential arguments from reaching Docker.

**Solution**: Simplified to pass all non-empty build arguments:
```python
# Add all build arguments
self.logger.debug("BUILDX: Adding build arguments: %s", build_args)
for key, value in build_args.items():
    if value is None or value == "":
        self.logger.warning("BUILDX: Skipping empty build arg: %s", key)
    else:
        buildx_cmd.extend(["--build-arg", f"{key}={value}"])
        self.logger.debug("BUILDX: Added arg: %s=%s", key, value)
```

#### Usage Examples

##### Building for Current Platform
```bash
docker buildx build --platform linux/amd64 --tag myapp:amd64 .
```

##### Cross-Platform Build (ARM64 → AMD64)
```bash
# Builder auto-detection (recommended)
docker buildx build --platform linux/amd64 --tag myapp:amd64 .

# Explicit builder selection
docker buildx build --builder mybuilder --platform linux/amd64 --tag myapp:amd64 .
```

##### Multi-Platform Build
```bash
docker buildx build --platform linux/amd64,linux/arm64 --tag myapp:latest .
```

#### Troubleshooting Guide

##### Empty Platform Variables
**Symptom**: `$TARGETARCH` appears empty in build output
```
#9 0.036 Unsupported target architecture:
```

**Cause**: Dockerfile using `$TARGETPLATFORM` for builder stage, causing emulation issues

**Fix**: Ensure builder stage uses `$BUILDPLATFORM`:
```dockerfile
FROM --platform=$BUILDPLATFORM ubuntu:20.04 AS builder  # ✅ Correct
```

##### Build Performance Issues
**Symptom**: Cross-platform builds extremely slow (10+ minutes for simple builds)

**Cause**: Builder stage running under emulation instead of native platform

**Verification**: Check Docker build output for platform information:
```bash
docker buildx build --progress=plain --platform linux/amd64 .
```

##### Builder Detection Issues
**Symptom**: "default builder not found" errors

**Solution**:
1. List available builders: `docker buildx ls`
2. Create builder if needed: `docker buildx create --name mybuilder --use`
3. Use auto-detection: Set `buildx_builder: "auto"` in configuration

#### Architecture Decision Records

##### ADR-001: Platform Variable Usage
**Decision**: Use `$BUILDPLATFORM` for builder stages, `$TARGETPLATFORM` for runtime stages

**Rationale**: Follows Docker's recommended pattern for cross-platform builds, avoids emulation penalties

**Consequences**: Significant performance improvement for cross-platform builds, proper BuildKit argument provision

##### ADR-002: Builder Auto-Detection
**Decision**: Implement auto-detection of active Docker buildx builder

**Rationale**: Reduces configuration burden, adapts to different Docker environments automatically

**Consequences**: More robust builds across different development environments

##### ADR-003: Simplified Build Argument Passing
**Decision**: Remove complex filtering logic, pass all non-empty arguments

**Rationale**: Complex filtering was preventing essential arguments from reaching Docker

**Consequences**: More predictable build behavior, easier debugging

#### Contributing to Docker Build System

When modifying the Docker build system:

1. **Test cross-platform builds**: Verify builds work correctly when `BUILDPLATFORM ≠ TARGETPLATFORM`
2. **Validate platform variables**: Ensure `$TARGETARCH` and other variables are properly populated
3. **Check cache efficiency**: Verify caches are properly isolated by platform where appropriate
4. **Performance test**: Measure build times for both native and cross-platform scenarios

#### References

- [Docker BuildKit Multi-Platform Builds](https://docs.docker.com/build/building/multi-platform/)
- [Docker Buildx Documentation](https://docs.docker.com/buildx/)
- [BuildKit Automatic Platform ARGs](https://docs.docker.com/engine/reference/builder/#automatic-platform-args-in-the-global-scope)

---

## :book: References

For further reading and context on the topics and methodologies used in this tool, refer to the following articles:

* Crochet, C., Aoga, J., & Legay, A. (2024). Formally Discovering and Reproducing Network Protocols Vulnerabilities (NordSec24).

```
@techreport{crochet2024formally,
  title={Formally Discovering and Reproducing Network Protocols Vulnerabilities},
  author={Crochet, Christophe and Aoga, John and Legay, Axel},
  year={2024}
  url={https://dial.uclouvain.be/pr/boreal/object/boreal:292503}
}
```

* Rousseaux, T., Crochet, C., Aoga, J., Legay, A. (2024). Network Simulator-Centric Compositional Testing. In: Castiglioni, V., Francalanza, A. (eds) Formal Techniques for Distributed Objects, Components, and Systems. FORTE 2024. Lecture Notes in Computer Science, vol 14678. Springer, Cham. <https://doi.org/10.1007/978-3-031-62645-6_10>

```
@inproceedings{rousseaux2024network,
  title={Network Simulator-Centric Compositional Testing},
  author={Rousseaux, Tom and Crochet, Christophe and Aoga, John and Legay, Axel},
  booktitle={International Conference on Formal Techniques for Distributed Objects, Components, and Systems},
  pages={177--196},
  year={2024},
  organization={Springer},
  doi={https://doi.org/10.1007/978-3-031-62645-6_10}
}
```

* Crochet, C., Rousseaux, T., Piraux, M., Sambon, J.-F., & Legay, A. (2021). Verifying quic implementations using ivy. In *Proceedings of the 2021 Workshop on Evolution, Performance and Interoperability of QUIC*. [DOI](10.1145/3488660.3493803)

```
@inproceedings{crochet2021verifying,
  title={Verifying QUIC implementations using Ivy},
  author={Crochet, Christophe and Rousseaux, Tom and Piraux, Maxime and Sambon, Jean-Fran{\c{c}}ois and Legay, Axel},
  booktitle={Proceedings of the 2021 Workshop on Evolution, Performance and Interoperability of QUIC},
  pages={35--41},
  year={2021},
  url={https://dl.acm.org/doi/abs/10.1145/3488660.3493803}
}
```

* Crochet, C., & Sambon, J.-F. (2021). Towards verification of QUIC and its extensions. (Master's thesis, UCL - Ecole polytechnique de Louvain). Available at [UCLouvain](http://hdl.handle.net/2078.1/thesis:30559). Keywords: QUIC, Formal Verification, RFC, IETF, Specification, Ivy, Network.

```
@article{crochettowards,
  title={Towards verification of QUIC and its extensions},
  author={Crochet, Christophe and Sambon, Jean-Fran{\c{c}}ois}
  year={2021},
  url={https://dial.uclouvain.be/downloader/downloader.php?pid=thesis%3A30559&datastream=PDF_01&cover=cover-mem}
}
```

For other useful resources, see the following:

* McMillan, K. L., & Padon, O. (2018). Deductive Verification in Decidable Fragments with Ivy. In A. Podelski (Ed.), *Static Analysis - 25th International Symposium, SAS 2018, Freiburg, Germany, August 29-31, 2018, Proceedings* (pp. 43–55). Springer. [DOI](10.1007/978-3-319-99725-4_4) - [PDF](SAS18.pdf)

* Taube, M., Losa, G., McMillan, K. L., Padon, O., Sagiv, M., Shoham, S., Wilcox, J. R., & Woos, D. (2018). Modularity for decidability of deductive verification with applications to distributed systems. In *Proceedings of the 39th ACM SIGPLAN Conference on Programming Language Design and Implementation, PLDI 2018, Philadelphia, PA, USA, June 18-22, 2018* (pp. 662–677). ACM. [DOI](10.1145/3192366.3192414)

* Padon, O., Hoenicke, J., McMillan, K. L., Podelski, A., Sagiv, M., & Shoham, S. (2018). Temporal Prophecy for Proving Temporal Properties of Infinite-State Systems. In *2018 Formal Methods in Computer Aided Design, FMCAD 2018, Austin, TX, USA, October 30 - November 2, 2018* (pp. 1–11). IEEE. [DOI](10.23919/FMCAD.2018.8603008) - [PDF](FMCAD18.pdf)

* Padon, O., McMillan, K. L., Panda, A., Sagiv, M., & Shoham, S. (2016). Ivy: safety verification by interactive generalization. In *Proceedings of the 37th ACM SIGPLAN Conference on Programming Language Design and Implementation, PLDI 2016, Santa Barbara, CA, USA, June 13-17, 2016* (pp. 614–630). ACM. [DOI](10.1145/2908080.2908118)

* McMillan, K. L. (2016). Modular specification and verification of a cache-coherent interface. In *2016 Formal Methods in Computer-Aided Design, FMCAD 2016, Mountain View, CA, USA, October 3-6, 2016* (pp. 109–116). [DOI](10.1109/FMCAD.2016.7886668)

* McMillan, K. L., & Zuck, L. D. (2019). Formal specification and testing of QUIC. In *Proceedings of ACM Special Interest Group on Data Communication (SIGCOMM’19)*. ACM. Note: to appear. [PDF](SIGCOMM19.pdf)

* [Ivy Documentation](https://microsoft.github.io/ivy/)

* [Ivy GitHub Repository](https://github.com/microsoft/ivy)

<picture>
  <source
    media="(prefers-color-scheme: dark)"
    srcset="
      https://api.star-history.com/svg?repos=ElNiak/PANTHER&type=Date&theme=dark
    "
  />
  <source
    media="(prefers-color-scheme: light)"
    srcset="
      https://api.star-history.com/svg?repos=ElNiak/PANTHER&type=Date
    "
  />
  <img
    alt="Star History Chart"
    src="https://api.star-history.com/svg?repos=ElNiak/PANTHER&type=Date"
  />
</picture>
