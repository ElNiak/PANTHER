#!/usr/bin/env python3
"""Debug services loading."""

import yaml
from panther.config.config_manager_enhanced import ConfigManager

# Load configuration
config_manager = ConfigManager(
    experiment_file="experiment-config/experiment_config_example_minimal.yaml",
)

# Load experiment config
experiment_config = config_manager.load_and_validate_experiment_config()

# Check services
if experiment_config and hasattr(experiment_config, 'tests'):
    for test in experiment_config.tests:
        print(f"\nTest: {test.name}")
        if hasattr(test, 'services'):
            print(f"Services: {test.services}")
            for service_name, service_config in test.services.items():
                print(f"\n  Service: {service_name}")
                print(f"    Implementation: {service_config.implementation}")
                print(f"    Implementation type: {service_config.implementation.type}")
                print(f"    Implementation type value: {service_config.implementation.type.value if hasattr(service_config.implementation.type, 'value') else service_config.implementation.type}")
                print(f"    Protocol: {service_config.protocol}")
else:
    print("No experiment config loaded")