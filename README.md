# PANTHER: Protocol Analysis and Testing Harness for Extensible Research

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
  pip install -r requirements.txt;
  ```

3. Verify Docker is installed:
  
  ```bash
  docker --version;
  docker-compose --version;
  ```

## Quick Start

1. Set Up Configuration:
        
    - Copy the sample configuration file:

    ```bash
    cp config/experiment_config.yaml.example config/experiment_config.yaml;
    ```

    - Modify the file as needed to suit your experiment.

2. Run an Experiment:

    - Execute an experiment:


    ```bash
    python panther_cli.py --config config/experiment_config.yaml;
    ```

    - View Results: 
      Experiment results are saved in the `outputs/` directory.

## Project Structure

```
panther/
├── config/                 # Configuration files and schemas
├── core/                   # Core experiment logic
├── plugins/                # Plugin implementations for protocols, environments, etc.
├── outputs/                # Experiment results and logs
├── tests/                  # Unit tests
├── Dockerfile              # Base Docker configuration
└── panther_cli.py          # Command-line interface for PANTHER
```

## Documentation

For detailed information on using PANTHER, see the [User Guide](docs/user_guide.md).

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

