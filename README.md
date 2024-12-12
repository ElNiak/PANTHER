# PANTHER: Protocol Analysis and Testing Harness for Extensible Research

## :tiger: **P**rotocol formal **A**nalysis and formal **N**etwork **T**hreat **E**valuation **R**esources


[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.10819552.svg)](https://doi.org/10.5281/zenodo.10819552)
[![CodeQL](https://github.com/ElNiak/PANTHER/actions/workflows/codeql.yml/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/codeql.yml)
[![Documentation Generation](https://github.com/ElNiak/PANTHER/actions/workflows/pr-generate-docs.yaml/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/pr-generate-docs.yaml)
[![Dependabot Updates](https://github.com/ElNiak/PANTHER/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/dependabot/dependabot-updates)
[![Python application](https://github.com/ElNiak/PANTHER/actions/workflows/python-app.yml/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/python-app.yml)
[![pages-build-deployment](https://github.com/ElNiak/PANTHER/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/pages/pages-build-deployment)
[![Greetings](https://github.com/ElNiak/PANTHER/actions/workflows/greetings.yml/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/greetings.yml)
[![pre-commit](https://github.com/ElNiak/PANTHER/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/ElNiak/PANTHER/actions/workflows/pre-commit.yml)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/c8043e5320934d49a688e173db5a331d)](https://app.codacy.com/gh/ElNiak/PANTHER/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white) ![C++](https://img.shields.io/badge/c++-%2300599C.svg?style=for-the-badge&logo=c%2B%2B&logoColor=white) ![Debian](https://img.shields.io/badge/Debian-D70A53?style=for-the-badge&logo=debian&logoColor=white)


## :rocket: Overview

PANTHER is a modular framework designed for testing and validating network protocols in dynamic and extensible environments. It supports protocol implementations, custom plugins, and comprehensive experiment configurations, making it an essential tool for researchers and developers in networking and security.

---

## Features
- **Extensible Plugin Architecture**: Easily add new implementations, protocols, and environments.
- **Dynamic Configuration**: Configure experiments using YAML files with structured validation.
- **Docker Integration**: Seamless environment setup with dynamically built Docker images.
- **Comprehensive Logging**: Debug and trace experiments with detailed logs.
- **Multi-Protocol Testing**: Supports complex scenarios across multiple protocols and implementations.

---

## Installation

### Prerequisites
- Python 3.8 or higher
- Docker and Docker Compose
- Recommended: A virtual environment for Python dependencies

### Steps
1. Clone the repository:

  ```bash
  git clone https://github.com/ElNiak/panther.git;
  cd panther/;
  git submodule update --init --recursive;
  ```

2. Install the required Python packages:

  ```bash
  python -m venv .venv;
  source .venv/bin/activate;
  make package
  ```

3. Verify Docker is installed:

  ```bash
  docker --version;
  docker-compose --version;
  ```

## Quick Start

1. Set Up Configuration:

    - Create a sample configuration file:

```
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
  - name: "Strace - QUIC IyvClient-Server Communication Test"
    description: "Verify that the Picoquic server can communicate with the Ivy-Tester client over Docker Compose network."
    network_environment:
      type: "docker_compose"
    execution_environment:
      - type: "strace"
    iterations: 1
    services:
      picoquic_server:
        name: "picoquic_server"
        timeout: 100
        implementation:
          name: "picoquic" # parameters are presents in folder plugins/services/implementations/quic/picoquic/config.yaml
          type: "iut" # plugin is present plugins/services/iut/quic/picoquic
        protocol:     # plugin is present plugins/protocols/
          name: "quic"
          version: "rfc9000"
          role: "server"
        ports:
          - "4443:4443"
          - "8080:8080"
        generate_new_certificates: True
      ivy_client:
        name: "ivy_client"  # Added 'name' key
        timeout: 100
        implementation:
          name: "panther_ivy"
          type: "testers" # plugin is present plugins/services/testers/panther_ivy
          test: quic_server_test_stream
        protocol:  # plugin is present plugins/services/iut/quic
          name: "quic"
          version: "rfc9000"
          role: "client"
          target: "picoquic_server"  # Docker Compose service name
        ports:
          - "5000:5000"
          - "4987:4987"
          - "8081:8081"
        generate_new_certificates: True
    steps:
      wait: 100  # seconds to wait during the test
```

    - Modify the file as needed to suit your experiment.

2. Run an Experiment:

    - Execute an experiment:


    ```bash
    panther --config config/experiment_config.yaml;
    ```

    - View Results:
      Experiment results are saved in the `outputs/` directory.

## Project Structure

```
tests/                  # Unit tests
outputs/                # Experiment results and logs
panther/
├── config/              # Configuration files and schemas
├── core/                # Core experiment logic
├── plugins/             # Plugin implementations for protocols, environments, etc.
├──── services/          # Protocol implementations
├────── iut/             # Protocol-specific implementations
├────────── quic/        # QUIC protocol implementations
├──────────── picoquic/  # Picoquic implementation
├──────────── ...
├────────── minip/       # MiniP protocol implementations
├────────── ...
├────── testers/         # Testers for protocol implementations
├────────── panther_ivy/ # Ivy tester implementation
├──── environments/      # Environment configurations
├────── network_environment/    # Network environment configurations
├────────── docker_compose/     # Docker Compose configurations
├────────── shadow_ns/          # Shadow NS configurations
├────────── localhost_single_container/     # Localhost single container configurations
├────── execution_environment/  # Execution environment configurations
├────────── strace/             # Strace configurations
├────────── gperf_heap/         # Gperf Heap profiling configurations
├────────── gperf_cpu/          # Gperf CPU profiling configurations
├──── protocols/         # Protocol definitions
└── __main__.py          # Command-line interface for PANTHER
```

## Documentation

For detailed information on using PANTHER, see the:


## Contributing

Contributions are welcome! To get started:

  - Fork the repository.
  - Create a new branch for your feature or bug fix.
  - Submit a pull request with a clear description of your changes.

For more details, see the Contribution Guide.

## License

PANTHER is licensed under the MIT License. See the LICENSE file for details.

## Contact

For support or inquiries, please contact:

  - ElNiak
  - Open an issue on the GitHub repository.


---

## :book: References

For further reading and context on the topics and methodologies used in this tool, refer to the following articles:

- Rousseaux, T., Crochet, C., Aoga, J., Legay, A. (2024). Network Simulator-Centric Compositional Testing. In: Castiglioni, V., Francalanza, A. (eds) Formal Techniques for Distributed Objects, Components, and Systems. FORTE 2024. Lecture Notes in Computer Science, vol 14678. Springer, Cham. https://doi.org/10.1007/978-3-031-62645-6_10

- Crochet, C., Rousseaux, T., Piraux, M., Sambon, J.-F., & Legay, A. (2021). Verifying quic implementations using ivy. In *Proceedings of the 2021 Workshop on Evolution, Performance and Interoperability of QUIC*. [DOI](10.1145/3488660.3493803)

- Crochet, C., & Sambon, J.-F. (2021). Towards verification of QUIC and its extensions. (Master's thesis, UCL - Ecole polytechnique de Louvain). Available at [UCLouvain](http://hdl.handle.net/2078.1/thesis:30559). Keywords: QUIC, Formal Verification, RFC, IETF, Specification, Ivy, Network.


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