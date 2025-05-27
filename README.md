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

* **What it solves:**  
  - Validating that a new QUIC or custom protocol implementation behaves correctly under failure, jitter, or adverse timing.  
  - Profiling performance characteristics (CPU, heap, syscall mix) across different builds or OS kernels.  
  - Running formal conformance checks (Ivy) inside a deterministic network simulator (Shadow) to catch logic bugs early.  

* **Core characteristics:**  
  ▸ **Reproducible:** every experiment is defined in a single YAML file and executed in an isolated container environment.  
  ▸ **Extensible:** a plugin system adds new protocols, services, profilers, or network back‑ends with minimal boilerplate.  
  ▸ **Multi‑audience:** useful to academic researchers, industrial developers, security analysts, SRE teams, and educators.

---

## 📑 Table of Contents
1. [Quick Start](quick_start.md)  
2. [Core Component](core_component.md)  
3. [Configuration Guide](configuration_guide.md)  
4. [Execution-Environment Modules](execution_environment_modules.md)  
5. [Network-Environment Modules](network_environment_modules.md)  
6. [Protocol Modules](protocol_modules.md)  
7. [Service (IUT) Modules](service_modules.md)  
8. [Tester Modules](tester_modules.md)  
9. [Web-app Interface](webapp_interface.md)  
10. [Output Analysis](output_analysis.md)  
11. [Developer Guide](developer_guide.md)  
12. [Plugin Developer Guide](plugin_guide.md)  
13. [Comprehensive Workflows](PANTHER_WORKFLOWS.md)

---

## 🔄 Quick Workflow Overview

PANTHER experiments follow a **4-phase execution model**:

### Phase 1: Initialization
- Load configurations and validate experiment setup
- Initialize plugin system and service managers
- Create test case instances

### Phase 2: Plugin Loading & Service Setup
- Discover and load protocol/implementation plugins
- Create service managers for each IUT (Implementation Under Test)
- Generate deployment and execution commands

### Phase 3: Environment Deployment
- Setup network environment (Docker Compose, localhost, or Shadow NS)
- Build container images for protocol implementations
- Deploy services with proper networking and monitoring

### Phase 4: Test Execution
- Start services and execute test scenarios
- Monitor execution with automatic packet capture
- Collect results, logs, and performance metrics
- Teardown environment and generate reports

**Key Features:**
- **Reproducible**: Every experiment defined in single YAML configuration
- **Containerized**: Isolated execution environments with Docker
- **Event-driven**: Real-time monitoring and coordination
- **Extensible**: Plugin architecture for new protocols and environments

For detailed workflow documentation, see [PANTHER_WORKFLOWS.md](PANTHER_WORKFLOWS.md).

---

## System Requirements

| Component | Minimum | Notes |
|-----------|---------|-------|
| Python    | 3.10    | Use `venv` for isolation. |
| Docker    | 27.x    | Required for all orchestration modes. |

`pyproject.toml` is the source of truth for Python dependencies.
`requirements.txt` is a frozen snapshot—**do not edit**.

---



## Documentation

For detailed information on using PANTHER, see the:

- [elniak.github.io/PANTHER](elniak.github.io/PANTHER)


## Contributing

Contributions are welcome! To get started:

- Fork the repository.

- Create a new branch for your feature or bug fix.

- Submit a pull request with a clear description of your changes.

For more details, see the Contribution Guide.


## Contact

For support or inquiries, please contact:

- ElNiak
- Open an issue on the GitHub repository.

---

## :book: References

For further reading and context on the topics and methodologies used in this tool, refer to the following articles:

- Crochet, C., Aoga, J., & Legay, A. (2024). Formally Discovering and Reproducing Network Protocols Vulnerabilities (NordSec24).

```
@techreport{crochet2024formally,
  title={Formally Discovering and Reproducing Network Protocols Vulnerabilities},
  author={Crochet, Christophe and Aoga, John and Legay, Axel},
  year={2024}
  url={https://dial.uclouvain.be/pr/boreal/object/boreal:292503}
}
```

- Rousseaux, T., Crochet, C., Aoga, J., Legay, A. (2024). Network Simulator-Centric Compositional Testing. In: Castiglioni, V., Francalanza, A. (eds) Formal Techniques for Distributed Objects, Components, and Systems. FORTE 2024. Lecture Notes in Computer Science, vol 14678. Springer, Cham. https://doi.org/10.1007/978-3-031-62645-6_10

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

- Crochet, C., Rousseaux, T., Piraux, M., Sambon, J.-F., & Legay, A. (2021). Verifying quic implementations using ivy. In *Proceedings of the 2021 Workshop on Evolution, Performance and Interoperability of QUIC*. [DOI](10.1145/3488660.3493803)

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

- Crochet, C., & Sambon, J.-F. (2021). Towards verification of QUIC and its extensions. (Master's thesis, UCL - Ecole polytechnique de Louvain). Available at [UCLouvain](http://hdl.handle.net/2078.1/thesis:30559). Keywords: QUIC, Formal Verification, RFC, IETF, Specification, Ivy, Network.

```
@article{crochettowards,
  title={Towards verification of QUIC and its extensions},
  author={Crochet, Christophe and Sambon, Jean-Fran{\c{c}}ois}
  year={2021},
  url={https://dial.uclouvain.be/downloader/downloader.php?pid=thesis%3A30559&datastream=PDF_01&cover=cover-mem}
}
```

For other useful resources, see the following:

- McMillan, K. L., & Padon, O. (2018). Deductive Verification in Decidable Fragments with Ivy. In A. Podelski (Ed.), *Static Analysis - 25th International Symposium, SAS 2018, Freiburg, Germany, August 29-31, 2018, Proceedings* (pp. 43–55). Springer. [DOI](10.1007/978-3-319-99725-4_4) - [PDF](SAS18.pdf)

- Taube, M., Losa, G., McMillan, K. L., Padon, O., Sagiv, M., Shoham, S., Wilcox, J. R., & Woos, D. (2018). Modularity for decidability of deductive verification with applications to distributed systems. In *Proceedings of the 39th ACM SIGPLAN Conference on Programming Language Design and Implementation, PLDI 2018, Philadelphia, PA, USA, June 18-22, 2018* (pp. 662–677). ACM. [DOI](10.1145/3192366.3192414)

- Padon, O., Hoenicke, J., McMillan, K. L., Podelski, A., Sagiv, M., & Shoham, S. (2018). Temporal Prophecy for Proving Temporal Properties of Infinite-State Systems. In *2018 Formal Methods in Computer Aided Design, FMCAD 2018, Austin, TX, USA, October 30 - November 2, 2018* (pp. 1–11). IEEE. [DOI](10.23919/FMCAD.2018.8603008) - [PDF](FMCAD18.pdf)

- Padon, O., McMillan, K. L., Panda, A., Sagiv, M., & Shoham, S. (2016). Ivy: safety verification by interactive generalization. In *Proceedings of the 37th ACM SIGPLAN Conference on Programming Language Design and Implementation, PLDI 2016, Santa Barbara, CA, USA, June 13-17, 2016* (pp. 614–630). ACM. [DOI](10.1145/2908080.2908118)

- McMillan, K. L. (2016). Modular specification and verification of a cache-coherent interface. In *2016 Formal Methods in Computer-Aided Design, FMCAD 2016, Mountain View, CA, USA, October 3-6, 2016* (pp. 109–116). [DOI](10.1109/FMCAD.2016.7886668)

- McMillan, K. L., & Zuck, L. D. (2019). Formal specification and testing of QUIC. In *Proceedings of ACM Special Interest Group on Data Communication (SIGCOMM’19)*. ACM. Note: to appear. [PDF](SIGCOMM19.pdf)

- [Ivy Documentation](https://microsoft.github.io/ivy/)

- [Ivy GitHub Repository](https://github.com/microsoft/ivy)

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