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

[comment]: <> (TODO -> > "[!WARNING]", ... must be replaced temporary by "!!! warning" for the online documentation)

> [!NOTE]
>  "What PANTHER Solves"
>    - **Protocol Validation**: Test QUIC or custom protocol implementations under failure, jitter, or adverse timing
>    - **Performance Profiling**: Analyze CPU, heap, and syscall characteristics across different builds or OS kernels
>    - **Formal Verification**: Run conformance checks (Ivy) in deterministic network simulation (Shadow)

**Core characteristics:**

▸ **Reproducible:** every experiment is defined in a single YAML file and executed in an isolated container environment.

▸ **Extensible:** a plugin system adds new protocols, services, profilers, or network back‑ends with minimal boilerplate.

▸ **Multi‑audience:** useful to academic researchers, industrial developers, security analysts, SRE teams, and educators.

---

> [!WARNING]
> CLI and core being refactored, some deadcode and legacy or unimplemented code remains.

> [!WARNING]
> ARM still need some works, Z3 generate maths errors and docker modules is being refactored in consequences (thus introducing potencial bugs)
> This branch is more stable (but not supporting ARM at all) - [development-scp-refactor](https://github.com/ElNiak/PANTHER/tree/development-scp-refactor)

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

For detailed workflow documentation, see [workflow.md](workflow.md).

---

## System Requirements

| Component | Minimum | Notes |
|-----------|---------|-------|
| Python    | 3.10    | Use `venv` for isolation for main functionality. |
| Docker    | 27.x    | Required for all orchestration modes. |
| Docker Compose | v2.x     | Bundled with Docker Desktop; may need separate install on Linux |

`pyproject.toml` is the source of truth for Python dependencies.
`requirements.txt` is a frozen snapshot—**do not edit**.

> [!NOTE]
>  (TODO) We propose to install [`slim`](https://github.com/slimtoolkit/slim) in our builder, fasten container size.

> [!WARNING]
> I tried but it seems that it is not as straight forward as it seems, need more research before using that.

---

## 📑 Table of Contents

### Getting Started

1. [Installation Guide](INSTALL.md)
2. [Quick Start](QUICK_START.md)
3. [Configuration](panther/config/README.md)
4. [Workflows](workflow.md)
5. [Core](panther/core/README.md)
6. [Web Application Workflows](panther/webapp/README.md)

### System Features

7. [Configuration Management](panther/config/README.md) - Advanced configuration validation, auto-fixing, and protocol-aware port management
8. [Core Architecture](panther/core/README.md) - Experiment orchestration, fast-fail system, and reporting

### Plugins

PANTHER's extensible plugin architecture enables seamless integration of new protocols, implementations, testing frameworks, and environments. The modern inheritance-based system provides 47.2% average code reduction while ensuring consistent behavior across all plugin types.

**Core Plugin Categories:**

10. [Overview](panther/plugins/README.md) - Architecture and design patterns
11. [Inventory](panther/plugins/plugins_inventory.md) - Complete plugin catalog
12. **Environment Plugins** - Network simulation and execution environments
   * [Overview](panther/plugins/environments/README.md) - Environment plugin architecture
   * [Network Environment](panther/plugins/environments/network_environment/README.md) - Docker Compose, localhost, Shadow NS
   * [Execution Environment](panther/plugins/environments/execution_environment/README.md) - Performance profiling and analysis
13. **Protocol Plugins** - Protocol definitions and behavioral specifications
    * [Overview](panther/plugins/protocols/README.md) - Protocol plugin patterns
    * [Client-Server Protocols](panther/plugins/protocols/client_server/README.md) - QUIC, HTTP, TCP/UDP variants
    * [Peer-to-Peer Protocols](panther/plugins/protocols/peer_to_peer/README.md) - BitTorrent, WebRTC protocols
14. **Service Plugins** - Implementation testing and verification services
    * [Overview](panther/plugins/services/README.md) - Service plugin architecture
    * [Implementation Under Tests (IUTs)](panther/plugins/services/iut/README.md) - picoquic, aioquic, quiche, quinn
    * [Testing Services](panther/plugins/services/testers/README.md) - Ivy formal verification, custom testers

**Plugin System Features:**
- **Automatic Discovery**: Decorator-based registration with metadata validation
- **Dependency Management**: Semantic versioning and automatic dependency resolution
- **Version Configurations**: Protocol version-specific configurations (RFC9000, draft-29, etc.)
- **Event Integration**: Built-in event emission and coordination across plugin lifecycle
- **Configuration Schema**: JSON Schema-based validation with auto-fixing capabilities
- **Performance Optimization**: Class caching and lazy loading for improved startup time

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

* [elniak.github.io/PANTHER](https://elniak.github.io/PANTHER)

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

## :book: References

For further reading and context on the topics and methodologies used in this tool, refer to the following articles:

* Crochet, C., Aoga, J., & Legay, A. (2024). Formally Discovering and Reproducing Network Protocols Vulnerabilities (NordSec24).

```bibtex
@techreport{crochet2024formally,
  title={Formally Discovering and Reproducing Network Protocols Vulnerabilities},
  author={Crochet, Christophe and Aoga, John and Legay, Axel},
  year={2024}
  url={https://dial.uclouvain.be/pr/boreal/object/boreal:292503}
}
```

* Rousseaux, T., Crochet, C., Aoga, J., Legay, A. (2024). Network Simulator-Centric Compositional Testing. In: Castiglioni, V., Francalanza, A. (eds) Formal Techniques for Distributed Objects, Components, and Systems. FORTE 2024. Lecture Notes in Computer Science, vol 14678. Springer, Cham. <https://doi.org/10.1007/978-3-031-62645-6_10>

```bibtex
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

* Crochet, C., Rousseaux, T., Piraux, M., Sambon, J.-F., & Legay, A. (2021). Verifying quic implementations using ivy. In *Proceedings of the 2021 Workshop on Evolution, Performance and Interoperability of QUIC*. [DOI](https://doi.org/10.1145/3488660.3493803)

```bibtex
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

```bibtex
@article{crochettowards,
  title={Towards verification of QUIC and its extensions},
  author={Crochet, Christophe and Sambon, Jean-Fran{\c{c}}ois}
  year={2021},
  url={https://dial.uclouvain.be/downloader/downloader.php?pid=thesis%3A30559&datastream=PDF_01&cover=cover-mem}
}
```

For other useful resources, see the following:

* McMillan, K. L., & Padon, O. (2018). Deductive Verification in Decidable Fragments with Ivy. In A. Podelski (Ed.), *Static Analysis - 25th International Symposium, SAS 2018, Freiburg, Germany, August 29-31, 2018, Proceedings* (pp. 43–55). Springer. [DOI](https://doi.org/10.1007/978-3-319-99725-4_4) - PDF

* Taube, M., Losa, G., McMillan, K. L., Padon, O., Sagiv, M., Shoham, S., Wilcox, J. R., & Woos, D. (2018). Modularity for decidability of deductive verification with applications to distributed systems. In *Proceedings of the 39th ACM SIGPLAN Conference on Programming Language Design and Implementation, PLDI 2018, Philadelphia, PA, USA, June 18-22, 2018* (pp. 662–677). ACM. [DOI](https://doi.org/10.1145/3192366.3192414)

* Padon, O., Hoenicke, J., McMillan, K. L., Podelski, A., Sagiv, M., & Shoham, S. (2018). Temporal Prophecy for Proving Temporal Properties of Infinite-State Systems. In *2018 Formal Methods in Computer Aided Design, FMCAD 2018, Austin, TX, USA, October 30 - November 2, 2018* (pp. 1–11). IEEE. [DOI](https://doi.org/10.23919/FMCAD.2018.8603008) - PDF

* Padon, O., McMillan, K. L., Panda, A., Sagiv, M., & Shoham, S. (2016). Ivy: safety verification by interactive generalization. In *Proceedings of the 37th ACM SIGPLAN Conference on Programming Language Design and Implementation, PLDI 2016, Santa Barbara, CA, USA, June 13-17, 2016* (pp. 614–630). ACM. [DOI](https://doi.org/10.1145/2908080.2908118)

* McMillan, K. L. (2016). Modular specification and verification of a cache-coherent interface. In *2016 Formal Methods in Computer-Aided Design, FMCAD 2016, Mountain View, CA, USA, October 3-6, 2016* (pp. 109–116). [DOI](https://doi.org/10.1109/FMCAD.2016.7886668)

* McMillan, K. L., & Zuck, L. D. (2019). Formal specification and testing of QUIC. In *Proceedings of ACM Special Interest Group on Data Communication (SIGCOMM’19)*. ACM. Note: to appear. PDF

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
