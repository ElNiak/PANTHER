"""
Configuration builders for interactive experiment design.

Each builder handles a specific section of the configuration.
"""

import logging
from typing import Any, Dict, List, Optional


class BaseBuilder:
    """Base class for configuration builders."""

    def __init__(self, quick_mode: bool = False):
        self.quick_mode = quick_mode

    def prompt(
        self,
        message: str,
        default: Optional[str] = None,
        choices: Optional[List[str]] = None,
        required: bool = True,
    ) -> Optional[str]:
        """Generic prompt helper with validation."""
        if choices:
            logging.info(f"\n{message}")
            for i, choice in enumerate(choices, 1):
                logging.info(f"  {i}. {choice}")
            if default and default in choices:
                default_idx = choices.index(default) + 1
                prompt_text = (
                    f"Enter choice [1-{len(choices)}] (default: {default_idx}): "
                )
            else:
                prompt_text = f"Enter choice [1-{len(choices)}]: "
        else:
            if default:
                prompt_text = f"\n{message} (default: {default}): "
            else:
                prompt_text = f"\n{message}: "

        while True:
            try:
                response = input(prompt_text).strip()

                if not response:
                    if default:
                        return default
                    elif not required:
                        return None
                    else:
                        logging.info(
                            "❌ This field is required. Please provide a value."
                        )
                        continue

                if choices:
                    try:
                        idx = int(response) - 1
                        if 0 <= idx < len(choices):
                            return choices[idx]
                        else:
                            logging.info(
                                f"❌ Please enter a number between 1 and {len(choices)}"
                            )
                            continue
                    except ValueError:
                        # Check if they typed the choice directly
                        if response in choices:
                            return response
                        logging.info(
                            f"❌ Invalid choice. Please enter a number between 1 and {len(choices)}"
                        )
                        continue

                return response

            except KeyboardInterrupt:
                logging.info("\n⚠️  Cancelled by user")
                raise

    def prompt_bool(self, message: str, default: bool = True) -> bool:
        """Prompt for yes/no question."""
        default_str = "Y/n" if default else "y/N"
        response = self.prompt(
            f"{message} [{default_str}]",
            default="y" if default else "n",
            required=False,
        )
        return response.lower() in ["y", "yes", "true", "1"] if response else default

    def prompt_int(
        self,
        message: str,
        default: int = None,
        min_val: int = None,
        max_val: int = None,
    ) -> int:
        """Prompt for integer with validation."""
        while True:
            response = self.prompt(message, str(default) if default else None)
            try:
                value = int(response)
                if min_val is not None and value < min_val:
                    logging.info(f"❌ Value must be at least {min_val}")
                    continue
                if max_val is not None and value > max_val:
                    logging.info(f"❌ Value must be at most {max_val}")
                    continue
                return value
            except ValueError:
                logging.info("❌ Please enter a valid number")


class GlobalConfigBuilder(BaseBuilder):
    """Builds global configuration section."""

    def build(self) -> Dict[str, Any]:
        """Build global configuration interactively."""
        config = {}

        logging.info("\n🌐 Global Configuration")
        logging.info("=" * 40)

        # Logging configuration
        if not self.quick_mode or self.prompt_bool(
            "Configure logging settings?", False
        ):
            config["logging"] = self._build_logging()

        # Observers configuration
        if not self.quick_mode or self.prompt_bool("Configure observers?", False):
            config["observers"] = self._build_observers()

        # Paths configuration
        config["paths"] = self._build_paths()

        # Docker configuration
        config["docker"] = self._build_docker()

        return config

    def _build_logging(self) -> Dict[str, Any]:
        """Build logging configuration."""
        logging.info("\n📝 Logging Configuration")

        level = self.prompt(
            "Logging level",
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        )

        enable_colors = self.prompt_bool("Enable colored output?", True)

        logging_config = {"level": level, "enable_colors": enable_colors}

        if not self.quick_mode:
            custom_format = self.prompt_bool("Use custom log format?", False)
            if custom_format:
                logging_config["format"] = self.prompt(
                    "Log format",
                    default="%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
                )

        return logging_config

    def _build_observers(self) -> Dict[str, Any]:
        """Build observers configuration."""
        logging.info("\n👁️  Observers Configuration")

        observers = {}

        # Logger observer
        observers["logger"] = {
            "enabled": self.prompt_bool("Enable logger observer?", True)
        }

        # Metrics observer
        if self.prompt_bool("Enable metrics collection?", not self.quick_mode):
            observers["metrics"] = {
                "enabled": True,
                "collect_system_metrics": self.prompt_bool(
                    "Collect system metrics?", True
                ),
            }

        # Storage observer
        if self.prompt_bool("Enable storage observer?", not self.quick_mode):
            observers["storage"] = {
                "enabled": True,
                "storage_path": self.prompt("Storage path", default="outputs/storage"),
            }

        return observers

    def _build_paths(self) -> Dict[str, Any]:
        """Build paths configuration."""
        logging.info("\n📁 Paths Configuration")

        paths = {
            "output_dir": self.prompt("Output directory", default="outputs"),
            "log_dir": self.prompt("Log directory", default="outputs/logs"),
            "plugin_dir": self.prompt("Plugin directory", default="panther/plugins"),
        }

        return paths

    def _build_docker(self) -> Dict[str, Any]:
        """Build Docker configuration."""
        logging.info("\n🐳 Docker Configuration")

        docker = {
            "force_build_docker_image": self.prompt_bool(
                "Build Docker images? (required for first run)", True
            )
        }

        if not self.quick_mode:
            docker["remove_docker_container"] = self.prompt_bool(
                "Remove containers after experiment?", True
            )
            docker["remove_docker_volume"] = self.prompt_bool(
                "Remove volumes after experiment?", True
            )

        return docker


class TestConfigBuilder(BaseBuilder):
    """
    Builds individual test configurations.
    TODO: make this class not hardcoded, but rather discover available plugins dynamically.
    This allows users to select from available plugins for network environments, execution environments, IUTs
    """

    def __init__(self, test_number: int, quick_mode: bool = False):
        super().__init__(quick_mode)
        self.test_number = test_number
        self.available_plugins = self._discover_plugins()

    def _discover_plugins(self) -> Dict[str, List[str]]:
        """Discover available plugins."""
        # This is a simplified version - in production would scan actual directories
        return {
            "network_environment": [
                "docker_compose",
                "localhost_single_container",
                "shadow_ns",
            ],
            "execution_environment": [
                "strace",
                "gperf_cpu",
                "gperf_heap",
                "memcheck",
                "helgrind",
            ],
            "iut": {
                "quic": [
                    "picoquic",
                    "aioquic",
                    "lsquic",
                    "mvfst",
                    "quiche",
                    "quinn",
                    "quic_go",
                    "quant",
                ],
                "http": ["nginx", "apache"],
                "minip": ["ping_pong"],
            },
            "testers": ["panther_ivy"],
        }

    def build(self) -> Dict[str, Any]:
        """Build test configuration interactively."""
        logging.info(f"\n🧪 Test {self.test_number} Configuration")
        logging.info("=" * 40)

        test = {}

        # Basic information
        test["name"] = self.prompt("Test name", default=f"Test {self.test_number}")

        test["description"] = (
            self.prompt("Test description", default="Test description", required=False)
            or "No description provided"
        )

        # Network environment
        test["network_environment"] = self._build_network_environment()

        # Execution environments
        test["execution_environment"] = self._build_execution_environment()

        # Services
        test["services"] = self._build_services()

        # Steps
        test["steps"] = self._build_steps()

        # Iterations - always include this as it's required
        test["iterations"] = (
            self.prompt_int("Number of iterations", default=1, min_val=1, max_val=100)
            if not self.quick_mode
            else 1
        )

        return test

    def _build_network_environment(self) -> Dict[str, Any]:
        """Build network environment configuration."""
        logging.info("\n🌐 Network Environment")

        env_type = self.prompt(
            "Select network environment type",
            default="docker_compose",
            choices=self.available_plugins["network_environment"],
        )

        return {"type": env_type}

    def _build_execution_environment(self) -> List[Dict[str, Any]]:
        """Build execution environment configurations."""
        environments = []

        if self.quick_mode:
            return environments

        logging.info("\n⚙️  Execution Environments (Optional)")

        if self.prompt_bool("Add execution environments (profilers)?", False):
            available = self.available_plugins["execution_environment"]

            while True:
                env_type = self.prompt(
                    "Select execution environment", choices=available + ["done"]
                )

                if env_type == "done":
                    break

                environments.append({"type": env_type})

                if not self.prompt_bool("Add another execution environment?", False):
                    break

        return environments

    def _build_services(self) -> Dict[str, Any]:
        """Build services configuration."""
        logging.info("\n🔧 Services Configuration")
        services = {}

        # Determine protocol first
        protocols = list(self.available_plugins["iut"].keys())
        protocol = self.prompt("Select protocol", default="quic", choices=protocols)

        # Add at least one server
        logging.info("\n➕ Adding server service...")
        server_name = self.prompt("Server service name", default="server")
        services[server_name] = self._build_service(protocol, "server")

        # Add clients
        while True:
            if not self.prompt_bool("\nAdd a client service?", True):
                break

            client_name = self.prompt(
                "Client service name", default=f"client_{len(services)}"
            )
            services[client_name] = self._build_service(protocol, "client", server_name)

        # Option to add Ivy tester
        if protocol == "quic" and not self.quick_mode:
            if self.prompt_bool("\nAdd Ivy formal tester?", False):
                services["ivy_tester"] = self._build_ivy_service()

                # Update a client to target Ivy
                client_names = [
                    k
                    for k, v in services.items()
                    if v.get("protocol", {}).get("role") == "client"
                ]
                if client_names:
                    update_client = self.prompt(
                        "Which client should target the Ivy tester?",
                        choices=client_names + ["none"],
                    )
                    if update_client != "none":
                        services[update_client]["protocol"]["target"] = "ivy_tester"

        return services

    def _build_service(
        self, protocol: str, role: str, target: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build individual service configuration."""
        service = {}

        # Implementation
        implementations = self.available_plugins["iut"].get(protocol, [])
        impl_name = self.prompt(
            f"Select {protocol} implementation",
            default=implementations[0] if implementations else "unknown",
            choices=implementations,
        )

        service["implementation"] = {"name": impl_name, "type": "iut"}

        # Protocol
        service["protocol"] = {
            "name": protocol,
            "version": "rfc9000" if protocol == "quic" else "1.1",
            "role": role,
        }

        if role == "client" and target:
            service["protocol"]["target"] = target

        # Timeout
        service["timeout"] = self.prompt_int(
            "Service timeout (seconds)", default=100, min_val=10, max_val=600
        )

        # Ports for server
        if role == "server":
            default_port = "4443" if protocol == "quic" else "8080"
            port = self.prompt(f"Server port", default=default_port)
            service["ports"] = [f"{port}:{port}"]

        # Certificates
        if protocol == "quic":
            service["generate_new_certificates"] = self.prompt_bool(
                "Generate new certificates?", True
            )

        return service

    def _build_ivy_service(self) -> Dict[str, Any]:
        """Build Ivy tester service configuration."""
        service = {
            "implementation": {
                "name": "panther_ivy",
                "type": "testers",
                "test": self.prompt(
                    "Ivy test to run",
                    default="quic_client_test_max",
                    choices=[
                        "quic_client_test_max",
                        "quic_server_test",
                        "quic_client_test_0rtt",
                        "quic_client_test_version",
                    ],
                ),
            },
            "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
            "timeout": 200,
            "ports": ["4443:4443", "4987:4987"],
        }

        return service

    def _build_steps(self) -> Dict[str, Any]:
        """Build test steps configuration."""
        logging.info("\n⏱️  Test Steps")

        wait_time = self.prompt_int(
            "Test duration (seconds)", default=60, min_val=10, max_val=600
        )

        return {"wait": wait_time}
