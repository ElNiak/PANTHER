from panther_utils.panther_constant import *
import os
import configparser
import logging
import subprocess

logging.basicConfig(level=logging.INFO)

# Ivy related
IVY_INCLUDE_PATH = os.path.join(SOURCE_DIR, "/app/panther-ivy/ivy/include/1.7/")
MODEL_DIR = os.path.join(SOURCE_DIR, "/app/panther-ivy/protocol-testing/")

# QUIC related
TLS_KEY_PATH = os.path.join(SOURCE_DIR, "/tls-keys")
QUIC_TICKET_PATH = os.path.join(SOURCE_DIR, "/tickets")
QLOGS_PATH = os.path.join(SOURCE_DIR, "/qlogs")

# TODO create Config class


def execute_command(command):
    logging.debug(f"Executing command: {command}")
    result = subprocess.run(command, shell=True, executable="/bin/bash")  # .wait()
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command)


def restore_config():
    with open("configs/config.ini", "w") as configfile:
        with open("configs/default_config.ini", "r") as default_config:
            default_settings = default_config.read()
            configfile.write(default_settings)


def update_config(experiment_parameters, current_protocol):
    if experiment_parameters:
        config = configparser.ConfigParser(allow_no_value=True)
        config.read("configs/config.ini")
        for arg in experiment_parameters:
            if arg in config["global_parameters"]:
                logging.info(
                    f"Updating global parameter: {arg} : {experiment_parameters[arg]}"
                )
                config.set("global_parameters", arg, experiment_parameters[arg])
            if arg in config["debug_parameters"]:
                logging.info(
                    f"Updating debug parameter: {arg} : {experiment_parameters[arg]}"
                )
                config.set("debug_parameters", arg, experiment_parameters[arg])
            if arg == "net_parameters":
                net_args = experiment_parameters[arg]
                logging.info(
                    f"Updating network parameter: {net_args} : {experiment_parameters[arg]}"
                )
            if arg in config["shadow_parameters"]:
                config.set("shadow_parameters", arg, experiment_parameters[arg])

        for arg in config["net_parameters"]:
            logging.info(net_args)
            if arg in net_args:
                logging.info(f"Network parameter set to True: {arg}")
                config.set("net_parameters", arg, "true")
            else:
                logging.info(f"Network parameter set to False: {arg}")
                config.set("net_parameters", arg, "false")

        for arg in config["verified_protocol"]:
            if current_protocol == arg:
                logging.info(f"Protocol parameter set to True: {arg}")
                config.set("verified_protocol", arg, "true")
            else:
                logging.info(f"Protocol parameter set to False: {arg}")
                config.set("verified_protocol", arg, "false")

        with open("configs/config.ini", "w") as configfile:
            config.write(configfile)


def update_protocol_config(protocol_argument, current_protocol, current_tests):
    protocol_conf = configparser.ConfigParser(allow_no_value=True)
    protocol_conf.read(
        "configs/" + current_protocol + "/" + current_protocol + "_config.ini"
    )
    for arg in protocol_argument:
        if arg in protocol_conf[current_protocol + "_parameters"]:
            logging.info(f"Protocol parameter set to: {arg} : {protocol_argument[arg]}")
            protocol_conf.set(
                current_protocol + "_parameters", arg, protocol_argument[arg]
            )
    for test_type in protocol_conf.sections():
        for test in current_tests:
            if test_type in test:
                logging.info(f"Test parameter set to True: {test_type}-{test}")
                protocol_conf.set(test_type, test, "true")
    with open(
        "configs/" + current_protocol + "/" + current_protocol + "_config.ini", "w"
    ) as configfile:
        protocol_conf.write(configfile)


def get_experiment_config(
    new_current_protocol=None, get_all_test=False, get_default_conf=False
):
    config = configparser.ConfigParser(allow_no_value=True)
    config.read("configs/config.ini")

    current_protocol = ""
    supported_protocols = config["verified_protocol"].keys()

    is_apt = config["global_parameters"].getboolean("apt")

    if new_current_protocol:
        current_protocol = new_current_protocol
    else:
        for p in supported_protocols:
            if config["verified_protocol"].getboolean(p):
                current_protocol = p
                break

    (
        tests_enabled,
        conf_implementation_enable,
        implementation_enable,
        protocol_model_path,
        protocol_results_path,
        protocol_test_path,
        protocol_conf,
    ) = get_protocol_config(
        config, current_protocol, get_all_test, get_default_conf, is_apt
    )

    return (
        supported_protocols,
        current_protocol,
        tests_enabled,
        conf_implementation_enable,
        implementation_enable,
        protocol_model_path,
        protocol_results_path,
        protocol_test_path,
        config,
        protocol_conf,
    )


def get_protocol_config(
    config, protocol, get_all_test=False, get_default_conf=False, is_apt=False
):
    protocol_conf = configparser.ConfigParser(allow_no_value=True)
    for envar in P_ENV_VAR[protocol]:
        os.environ[envar] = P_ENV_VAR[protocol][envar]

    if get_default_conf:
        protocol_conf.read(
            "configs/" + protocol + "/default_" + protocol + "_config.ini"
        )
    else:
        protocol_conf.read("configs/" + protocol + "/" + protocol + "_config.ini")

    if is_apt:
        protocol_model_path = os.path.join(MODEL_DIR, "apt")
        config.set(
            "global_parameters",
            "tests_dir",
            os.path.join(MODEL_DIR, "apt", "apt_tests"),
        )
        config.set(
            "global_parameters", "dir", os.path.join(MODEL_DIR, "apt", "test", "temps")
        )
        config.set(
            "global_parameters", "build_dir", os.path.join(MODEL_DIR, "apt", "build")
        )

    else:
        protocol_model_path = os.path.join(MODEL_DIR, protocol)
        config.set(
            "global_parameters",
            "tests_dir",
            os.path.join(MODEL_DIR, protocol, protocol + "_tests"),
        )
        config.set(
            "global_parameters",
            "dir",
            os.path.join(MODEL_DIR, protocol, "test", "temps"),
        )
        config.set(
            "global_parameters", "build_dir", os.path.join(MODEL_DIR, protocol, "build")
        )

    protocol_test_path = os.path.join(protocol_model_path, "tests/")
    protocol_results_path = os.path.join(protocol_model_path, "test/", "temp/")

    if not os.path.exists(protocol_results_path):
        logging.info(f"Creating directory: {protocol_results_path}")
        os.mkdir(os.path.join(protocol_model_path, "test/"))
        os.mkdir(protocol_results_path)
    if not os.path.exists(protocol_test_path):
        logging.info(f"Creating directory: {protocol_test_path}")
        os.mkdir(protocol_test_path)

    tests_enabled = {}
    for category in protocol_conf.keys():
        if "_test" in category:
            tests_enabled[category] = []
            for test in protocol_conf[category]:
                if get_all_test or protocol_conf[category].getboolean(test):
                    tests_enabled[category].append(test)

    implem_config_path_server = "configs/" + protocol + "/implem-server"
    implem_config_path_client = "configs/" + protocol + "/implem-client"

    conf_implementation_enable = {}
    for file_path in os.listdir(implem_config_path_server):
        # check if current file_path is a file
        # TODO check if enable in global config
        if os.path.isfile(os.path.join(implem_config_path_server, file_path)):
            implem_name = file_path.replace(".ini", "")

            implem_conf_server = configparser.ConfigParser(allow_no_value=True)
            implem_conf_server.read(os.path.join(implem_config_path_server, file_path))

            implem_conf_client = configparser.ConfigParser(allow_no_value=True)
            implem_conf_client.read(os.path.join(implem_config_path_client, file_path))

            conf_implementation_enable[implem_name] = [
                implem_conf_server,
                implem_conf_client,
            ]

    implementation_enable = {}
    global_conf_file = "configs/global-conf.ini"
    global_config = configparser.ConfigParser(allow_no_value=True)
    global_config.read(global_conf_file)
    for key in global_config:
        if "implementations" in key and protocol in key:
            implem = key.replace("-implementations", "")
            for implem in global_config[key]:
                implementation_enable[implem] = global_config[key].getboolean(implem)

    return (
        tests_enabled,
        conf_implementation_enable,
        implementation_enable,
        protocol_model_path,
        protocol_results_path,
        protocol_test_path,
        protocol_conf,
    )
