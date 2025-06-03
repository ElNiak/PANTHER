#!/usr/bin/env python3
"""
Test script to verify how _combine_shell_constructs processes a specific input.
"""
import os
import logging
from panther.plugins.environments.network_environment.docker_compose.docker_compose import DockerComposeEnvironment
from panther.core.observer.event_manager import EventManager
from panther.plugins.environments.network_environment.docker_compose.config_schema import DockerComposeConfig

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_combine_specific")

def run_test():
    # Create a minimal environment instance 
    config = DockerComposeConfig()
    event_manager = EventManager()
    output_dir = "/tmp/panther_test"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create environment
    env = DockerComposeEnvironment(
        env_config_to_test=config,
        output_dir=output_dir,
        env_type="network_environment",
        env_sub_type="docker_compose",
        event_manager=event_manager
    )
    
    # Mock service attributes for the test
    service_targets = "target-service"
    service_name = "test-service"
    protocol_name = "test-protocol"
    
    # The specific input to test
    test_input = [
        "TARGET_IP=$(getent hosts " + service_targets + r' | tail -n 1 | awk "{ print \$1 }");',
        'echo "Resolved ' + service_targets + ' IP - $TARGET_IP" >> /app/logs/ivy_setup.log;',
        r'IVY_IP=$(hostname -I | awk "{ print \$1 }" | head -n 1);',
        'echo "Resolved  ' + service_name + ' IP - $IVY_IP" >> /app/logs/ivy_setup.log;',
        " ",
        "ip_to_hex() {",
        r'  echo $1 | awk -F"." "{ printf("%02X%02X%02X%02X", \$1, \$2, \$3, \$4) }";',
        "}",
        " ",
        "ip_to_decimal() {",
        r'  echo $1 | awk -F"." "{ printf("%.0f", (\$1 * 256 * 256 * 256) + (\$2 * 256 * 256) + (\$3 * 256) + \$4) }";',
        "}",
        " ",
        "TARGET_IP_HEX=$(ip_to_decimal $TARGET_IP);",
        "IVY_IP_HEX=$(ip_to_decimal $IVY_IP);",
        'echo "Resolved ' + service_targets + ' IP in hex - $TARGET_IP_HEX" >> /app/logs/ivy_setup.log;',
        'echo "Resolved ' + service_name + ' IP in hex - $IVY_IP_HEX" >> /app/logs/ivy_setup.log;',
        " ",
        "rm -rf /opt/panther_ivy/protocol-testing/apt/build/*;" if True else f"rm -rf /opt/panther_ivy/protocol-testing/{protocol_name}/build/*;",
    ]
    
    # Print the input
    logger.info("Input commands:")
    for i, cmd in enumerate(test_input):
        logger.info(f"[{i}] {repr(cmd)}")
    
    logger.info("-" * 70)
    
    # Process with _combine_shell_constructs
    result = env._combine_shell_constructs(test_input)
    
    # Print the result
    logger.info("Combined constructs:")
    for i, cmd in enumerate(result):
        logger.info(f"[{i}] {repr(cmd)}")
    
    # Examine what was combined and what wasn't
    logger.info("-" * 70)
    logger.info("Analysis of combination process:")

    if not result:
        logger.warning("Result is empty! This indicates a problem in processing.")
        return

    # Check for function definitions
    combined_text = " ".join(result)
    if "ip_to_hex() {" in combined_text and "}" in combined_text:
        logger.info("✅ Function 'ip_to_hex' was successfully combined")
    else:
        logger.warning("❌ Function 'ip_to_hex' was NOT properly combined")
    
    if "ip_to_decimal() {" in combined_text and "}" in combined_text:
        logger.info("✅ Function 'ip_to_decimal' was successfully combined")
    else:
        logger.warning("❌ Function 'ip_to_decimal' was NOT properly combined")
    
    # Count of items before and after
    logger.info(f"Input count: {len(test_input)}, Output count: {len(result)}")
    logger.info("Compression ratio: {:.2f}".format(len(test_input) / len(result) if result else float('inf')))

if __name__ == "__main__":
    run_test()
