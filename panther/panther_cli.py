# PANTHER-SCP/panther/panther_cli.py

import argparse
from datetime import datetime
import os
import logging
from pathlib import Path
from core.experiment_manager import ExperimentManager
from config.config import ConfigLoader



def main():
    parser = argparse.ArgumentParser(description="Panther CLI")
    parser.add_argument(
        "--config-dir",
        type=str,
        default="config",
        help="Path to the configuration directory.",
    )
    parser.add_argument(
        "--plugin-dir",
        type=str,
        default="plugins",
        help="Path to the configuration directory.",
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default=None,
        help="Name of the experiment.",
    )
    parser.add_argument(
        "--teardown",
        action="store_true",
        help="Flag to teardown an existing experiment.",
    )
    args = parser.parse_args()
    
    if args.teardown:
        if not args.experiment_dir:
            print("Please provide the experiment directory to teardown using '--experiment-dir'.")
            return
        raise NotImplementedError("Teardown functionality is not implemented yet.")
    else:
        # # Load Configurations
        config_loader = ConfigLoader(args.config_dir)
        global_config = config_loader.global_config
        experiment_config = config_loader.experiment_config
        # Start the experiment
        experiment_manager = ExperimentManager(
            global_config=global_config,
            experiment_config=experiment_config,
            experiment_name=args.experiment_name
        )
        experiment_manager.run_tests()
        

        # # Create Experiment Directory
        # experiment_dir = create_experiment_directory(global_config)
        # logs_dir = experiment_dir / "logs"
        # docker_compose_logs_dir = experiment_dir / "docker_compose_logs"
        # container_logs_dir = experiment_dir / "container_logs"
        # other_artifacts_dir = experiment_dir / "other_artifacts"

        # # Create necessary subdirectories
        # logs_dir.mkdir(parents=True, exist_ok=True)
        # docker_compose_logs_dir.mkdir(parents=True, exist_ok=True)
        # container_logs_dir.mkdir(parents=True, exist_ok=True)
        # other_artifacts_dir.mkdir(parents=True, exist_ok=True)

        # # Setup Logging
        # logger = setup_logger(global_config, logs_dir)

        # # Initialize PluginLoader
        # plugins_dir = args.plugin_dir  # Adjust as per your directory structure
        # plugin_loader = PluginLoader(plugins_dir)

        # # Load plugins and build Docker images
        # loaded_plugins = plugin_loader.load_plugins(
        #     build_docker_image=global_config.docker.build_docker_image
        # )

        # # Access built images if needed
        # built_images = loaded_plugins.get("built_images", {})
        # logger.info(f"Built Images: {built_images}")

        # # Initialize Experiment Manager
        # experiment_manager = ExperimentManager(
        #     experiment_config=experiment_config,
        #     protocol_plugins=loaded_plugins["protocol_plugins"],
        #     environment_plugins=loaded_plugins["environment_plugins"],
        #     global_config=global_config,
        # )

        # # Run Experiments
        # experiment_manager.run_experiment()

        # logger.info("Panther-SCP CLI Finished")



def create_experiment_directory(global_config) -> Path:
    """
    Creates a unique experiment directory based on the current timestamp.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    experiment_dir = Path(
        os.path.join(global_config.paths.output_dir, f"experiment_{timestamp}")
    )
    experiment_dir.mkdir(parents=True, exist_ok=True)
    return experiment_dir


if __name__ == "__main__":
    main()
