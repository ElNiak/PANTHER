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
        experiment_config = config_loader.experiment_config
        
        # Start the experiment
        experiment_manager = ExperimentManager(
            experiment_config=experiment_config,
            experiment_name=args.experiment_name
        )
        experiment_manager.run_tests()
        

if __name__ == "__main__":
    main()
