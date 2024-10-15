from datetime import datetime
import logging
from typing import Any, Dict, List

from core.experiment_manager import ExperimentManager
from core.interfaces.environments.environment_interface import IEnvironmentPlugin
from core.interfaces.service_manager_interface import IServiceManager


class Test:
    def __init__(self, test_config: Dict[str, Any], experiment_manager: 'ExperimentManager'):
        self.logger = logging.getLogger(f"Test:{test_config.get('name', 'Unnamed Test')}")
        self.test_config = test_config
        self.name = test_config.get('name', 'Unnamed Test')
        self.description = test_config.get('description', '')
        self.protocol = test_config.get('protocol')
        self.environment = test_config.get('network_environment')
        self.services = test_config.get('services', {})
        self.steps = test_config.get('steps', {})
        self.assertions = test_config.get('assertions', [])
        self.experiment_manager = experiment_manager
        self.service_managers: List[IServiceManager] = []
        self.environment_managers: List[IEnvironmentPlugin] = []
        self.current_test_services = self.services

    def run(self):
        self.logger.info(f"Starting Test: {self.name}")
        self.logger.info(f"Description: {self.description}")

        # Step 1: Extract required implementations from services
        required_implementations = set()
        for service_name, service_details in self.services.items():
            implementation = service_details.get("implementation")
            if implementation:
                required_implementations.add(implementation)
            else:
                self.logger.warning(f"Service '{service_name}' does not specify an implementation.")

        if not required_implementations:
            self.logger.error("No implementations specified for services. Aborting test.")
            return

        self.logger.debug(f"Required implementations for this test: {required_implementations}")

        # Step 2: Initialize service managers
        self.initialize_protocol_managers([self.protocol], required_implementations)

        # Step 3: Initialize environment managers
        self.initialize_environment_managers([self.environment])

        # Step 4: Build Docker images if necessary
        self.build_docker_images()

        # Step 5: Generate deployment commands
        deployment_commands = self.generate_deployment_commands(self.environment)

        # Generate timestamp and paths
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        paths = self.experiment_manager.experiment_config.get('paths', {})

        # Step 6: Setup environments with services
        self.setup_environments(self.services, deployment_commands, paths, timestamp)

        # Step 7: Deploy services
        self.deploy_services()

        # Step 8: Execute test steps
        self.execute_steps(self.steps)

        # Step 9: Perform assertions
        self.perform_assertions(self.assertions)

        # Step 10: Teardown for the test
        self.teardown_test()

        self.logger.info(f"Completed Test: {self.name}")
        self.experiment_manager.event_manager.notify(Event("test_completed", {"test": self.name}))

    # Methods to be implemented...

