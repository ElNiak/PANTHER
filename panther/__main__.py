import argparse
import logging
import sys
from panther.core.experiment_manager import ExperimentManager
from panther.config.config_manager import ConfigLoader
from panther.webapp.web_app import run

def main():
    parser = argparse.ArgumentParser(description="Panther CLI")
    # TODO manage dir of the experiments configs
    parser.add_argument(
        "--experiment-config",
        type=str,
        default="experiment-config/experiment_config.yaml",
        help="Path to the configuration directory.",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Flag to validate the configuration.",
    )
    parser.add_argument(
        "--exec-env-dir",
        type=str,
        help="Path to the execution plugin additional directory.",
    )
    parser.add_argument(
        "--net-env-dir",
        type=str,
        help="Path to the network plugin additional directory.",
    )
    parser.add_argument(
        "--iut-dir",
        type=str,
        help="Path to a new IUT plugin additional directory.",
    )
    parser.add_argument(
        "--tester-dir",
        type=str,
        help="Path to a new tester plugin additional directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Path to the output directory.",
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
    parser.add_argument(
        "--webapp",
        action="store_true",
        help="Start the web app to configurate the experiments.",
    )
    args = parser.parse_args()

    if args.teardown:
        if not args.experiment_dir:
            print(
                "Please provide the experiment directory to teardown using '--experiment-dir'."
            )
            return
        raise NotImplementedError("Teardown functionality is not implemented yet.")
    elif args.validate_config:
        print("Validating the configuration.")
        config_loader = ConfigLoader(
            args.experiment_config,
            args.output_dir,
            args.exec_env_dir,
            args.net_env_dir,
            args.iut_dir,
            args.tester_dir,
        )
        # We get the global configurations
        global_config = config_loader.load_and_validate_global_config()
        # We create the experiment manager
        experiment_manager = ExperimentManager(
            global_config=global_config, experiment_name=args.experiment_name
        )
        config_loader.load_and_validate_experiment_config()
    else:
        # We start by loading the configuration
        config_loader = ConfigLoader(
            args.experiment_config,
            args.output_dir,
            args.exec_env_dir,
            args.net_env_dir,
            args.iut_dir,
            args.tester_dir,
        )
        # We get the global configurations
        global_config = config_loader.load_and_validate_global_config()
        if args.webapp:
            try:
                raise NotImplementedError(
                    "Webapp functionality is not fully refactored/implemented yet."
                )
                run(config_loader, global_config, args)
            except Exception as e:
                logging.error(e)
            finally:
                sys.stdout.close()
                sys.stderr.close()
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
        else:
            try:
                # We create the experiment manager
                experiment_manager = ExperimentManager(
                    global_config=global_config, experiment_name=args.experiment_name
                )
                experiment_config = config_loader.load_and_validate_experiment_config()
                # Once we have the experiments configurations, we can initialize the experiment
                experiment_manager.initialize_experiments(experiment_config)
                # Start the experiment
                experiment_manager.run_tests()
            except Exception as e:
                logging.error(e)
                raise e
            finally:
                config_loader.cleanup()


if __name__ == "__main__":
    main()
