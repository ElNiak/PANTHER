import os
import configparser
import logging
import subprocess
from dataclasses import dataclass
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from panther_utils.panther_constant import *

#
# Panther Configuration TODO
#


@dataclass
class GlobalConfig:
    shadow: bool
    docker: bool
    docker_swarm: bool
    init_submodule: bool


@dataclass
class QuicImplementations:
    picoquic: bool
    quant: bool
    picoquic_shadow: bool
    mvfst: bool
    aioquic: bool
    lsquic: bool
    quic_go: bool
    quiche: bool
    quinn: bool


@dataclass
class QuicTools:
    visualizer: bool


@dataclass
class MinipImplementations:
    ping_pong: bool
    ping_pong_flaky: bool
    ping_pong_fail: bool
    ping_pong_mt: bool
    ping_pong_flaky_mt: bool
    ping_pong_fail_mt: bool


@dataclass
class BgpImplementations:
    gobgp: bool
    bird: bool
    frr: bool


@dataclass
class AptImplementations:
    picoquic_shadow: bool
    picoquic: bool
    quant: bool
    quic_go: bool
    ping_pong: bool


@dataclass
class PantherConfig:
    global_parameters: GlobalConfig
    quic_implementations: QuicImplementations
    quic_tools: QuicTools
    minip_implementations: MinipImplementations
    bgp_implementations: BgpImplementations
    apt_implementations: AptImplementations



#
# Experiment Configuration
#


@dataclass
class GlobalParameters:
    dir: str = "temp/"
    build_dir: str = "build/"
    tests_dir: str = "tests/"
    iter: int = 1
    internal_iteration: int = 100
    getstats: bool = False
    compile: bool = True
    run: bool = True
    timeout: int = 100
    keep_alive: bool = False
    update_ivy: bool = True
    docker: bool = False
    apt: bool = False


@dataclass
class DebugParameters:
    gperf: bool = False
    gdb: bool = False
    memprof: bool = False
    ivy_process_tracer: bool = False


@dataclass
class NetParameters:
    localhost: bool = True
    vnet: bool = False
    shadow: bool = False


@dataclass
class ShadowParameters:
    loss: float = 0.0
    jitter: float = 0.0
    latency: float = 0.0


@dataclass
class VerifiedProtocol:
    quic: bool = True
    minip: bool = False
    bgp: bool = False
    apt: bool = False


@dataclass
class ExperimentConfig:
    global_parameters: GlobalParameters
    debug_parameters: DebugParameters
    net_parameters: NetParameters
    shadow_parameters: ShadowParameters
    verified_protocol: VerifiedProtocol


# Create an instance of ExperimentConfig
experiment_config = ExperimentConfig(
    global_parameters=GlobalParameters(
        dir="temp/",
        build_dir="build/",
        tests_dir="tests/",
        iter=1,
        internal_iteration=100,
        getstats=False,
        compile=True,
        run=True,
        timeout=100,
        keep_alive=False,
        update_ivy=True,
        docker=False,
        apt=False,
    ),
    debug_parameters=DebugParameters(
        gperf=False, gdb=False, memprof=False, ivy_process_tracer=False
    ),
    net_parameters=NetParameters(localhost=True, vnet=False, shadow=False),
    shadow_parameters=ShadowParameters(loss=0.0, jitter=0.0, latency=0.0),
    verified_protocol=VerifiedProtocol(quic=True, minip=False, bgp=False, apt=False),
)


def update_experiment_config(experiment_parameters, current_protocol):
    if experiment_parameters:
        config = configparser.ConfigParser(allow_no_value=True)
        config.read("configs/default_config.ini")
        for arg in experiment_parameters:
            if arg in config["global_parameters"]:
                setattr(
                    experiment_config.global_parameters,
                    arg,
                    config["global_parameters"].getboolean(arg),
                )
            elif arg in config["debug_parameters"]:
                setattr(
                    experiment_config.debug_parameters,
                    arg,
                    config["debug_parameters"].getboolean(arg),
                )
            elif arg in config["net_parameters"]:
                setattr(
                    experiment_config.net_parameters,
                    arg,
                    config["net_parameters"].getboolean(arg),
                )
            elif arg in config["shadow_parameters"]:
                setattr(
                    experiment_config.shadow_parameters,
                    arg,
                    config["shadow_parameters"].getfloat(arg),
                )
            elif arg in config["verified_protocol"]:
                setattr(
                    experiment_config.verified_protocol,
                    arg,
                    config["verified_protocol"].getboolean(arg),
                )
        with open("configs/config.ini", "w") as configfile:
            config.write(configfile)


# TODO use these dataclasses to update the configuration files


def execute_command(command, must_pass=True):
    logging.debug(f"Executing command: {command}")
    result = subprocess.run(command, shell=True, executable="/bin/bash")  # .wait()
    if result.returncode != 0 and must_pass:
        raise subprocess.CalledProcessError(result.returncode, command)


def restore_config():
    with open("configs/config.ini", "w") as configfile:
        with open("configs/default_config.ini", "r") as default_config:
            default_settings = default_config.read()
            configfile.write(default_settings)
    with open("configs/quic/quic_config.ini", "w") as configfile:
        with open("configs/quic/default_quic_config.ini", "r") as default_config:
            default_settings = default_config.read()
            configfile.write(default_settings)
    with open("configs/minip/minip_config.ini", "w") as configfile:
        with open("configs/minip/default_minip_config.ini", "r") as default_config:
            default_settings = default_config.read()
            configfile.write(default_settings)
    with open("configs/apt/apt_config.ini", "w") as configfile:
        with open("configs/apt/default_apt_config.ini", "r") as default_config:
            default_settings = default_config.read()
            configfile.write(default_settings)


def update_config(experiment_parameters, current_protocol):
    if experiment_parameters:
        config = configparser.ConfigParser(allow_no_value=True)
        config.read("configs/config.ini")
        for arg in experiment_parameters:
            if arg in config["global_parameters"]:
                logging.debug(
                    f"Updating global parameter: {arg} : {experiment_parameters[arg]}"
                )
                config.set("global_parameters", arg, experiment_parameters[arg])
            if arg in config["debug_parameters"]:
                logging.debug(
                    f"Updating debug parameter: {arg} : {experiment_parameters[arg]}"
                )
                config.set("debug_parameters", arg, experiment_parameters[arg])
            if arg == "net_parameters":
                net_args = experiment_parameters[arg]
                logging.debug(
                    f"Updating network parameter: {net_args} : {experiment_parameters[arg]}"
                )
            if arg in config["shadow_parameters"]:
                config.set("shadow_parameters", arg, experiment_parameters[arg])

        for arg in config["net_parameters"]:
            logging.debug(net_args)
            if arg in net_args:
                logging.debug(f"Network parameter set to True: {arg}")
                config.set("net_parameters", arg, "true")
            else:
                logging.debug(f"Network parameter set to False: {arg}")
                config.set("net_parameters", arg, "false")

        for arg in config["verified_protocol"]:
            if current_protocol == arg:
                logging.debug(f"Protocol parameter set to True: {arg}")
                config.set("verified_protocol", arg, "true")
            else:
                logging.debug(f"Protocol parameter set to False: {arg}")
                config.set("verified_protocol", arg, "false")

        with open("configs/config.ini", "w") as configfile:
            config.write(configfile)


def update_protocol_config(protocol_argument, current_protocol, current_tests):
    logging.info(f"Updating protocol configuration: {current_protocol}")
    protocol_conf = configparser.ConfigParser(allow_no_value=True)
    protocol_conf.read(
        "configs/" + current_protocol + "/" + current_protocol + "_config.ini"
    )
    for arg in protocol_argument:
        if arg in protocol_conf[current_protocol + "_parameters"]:
            logging.debug(
                f"Protocol parameter set to: {arg} : {protocol_argument[arg]}"
            )
            protocol_conf.set(
                current_protocol + "_parameters", arg, protocol_argument[arg]
            )
    for test_type in protocol_conf.sections():
        logging.debug(f"Test type: {test_type}")
        for test in current_tests:
            logging.debug(f"\t - Test: {test}")
            test_type_in = test_type.replace("_tests", "_test")  # TODO
            if test_type_in in test:
                logging.debug(f"\t   Test parameter set to True: {test_type}-{test}")
                protocol_conf.set(test_type, test, "true")
    with open(
        "configs/" + current_protocol + "/" + current_protocol + "_config.ini", "w"
    ) as configfile:
        protocol_conf.write(configfile)
        
    if current_protocol == "apt":
        config = configparser.ConfigParser(allow_no_value=True)
        config.read("configs/config.ini")
        supported_protocols = config["verified_protocol"].keys()
        # we modify all other protocol config files
        for protocol in supported_protocols:
            protocol_conf = configparser.ConfigParser(allow_no_value=True)
            protocol_conf.read(
                "configs/" + protocol + "/" + protocol + "_config.ini"
            )
            for arg in protocol_argument:
                if arg in protocol_conf[protocol + "_parameters"]:
                    logging.debug(
                        f"Protocol parameter set to: {arg} : {protocol_argument[arg]}"
                    )
                    protocol_conf.set(
                        protocol + "_parameters", arg, protocol_argument[arg]
                    )
            for test_type in protocol_conf.sections():
                logging.debug(f"Test type: {test_type}")
                for test in current_tests:
                    logging.debug(f"\t - Test: {test}")
                    test_type_in = test_type.replace("_tests", "_test")
            with open(
                "configs/" + protocol + "/" + protocol + "_config.ini", "w"
            ) as configfile:
                protocol_conf.write(configfile)


def get_experiment_config(
    new_current_protocol=None, get_all_test=False, get_default_conf=False
):
    config = configparser.ConfigParser(allow_no_value=True)
    config.read("configs/config.ini")

    current_protocol = ""
    supported_protocols = config["verified_protocol"].keys()

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
    ) = get_protocol_config(config, current_protocol, get_all_test, get_default_conf)

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


def get_protocol_config(config, protocol, get_all_test=False, get_default_conf=False):
    """
    Retrieves the configuration for a specific protocol.

    Args:
        config (ConfigParser): The main configuration object.
        protocol (str): The protocol for which to retrieve the configuration.
        get_all_test (bool, optional): Flag to indicate whether to retrieve all tests. Defaults to False.
        get_default_conf (bool, optional): Flag to indicate whether to retrieve the default configuration. Defaults to False.

    Returns:
        tuple: A tuple containing the following elements:
            - tests_enabled (dict): A dictionary containing the enabled tests for each category.
            - conf_implementation_enable (dict): A dictionary containing the enabled implementations for each implementation file.
            - implementation_enable (dict): A dictionary containing the enabled implementations for the protocol.
            - protocol_model_path (str): The path to the protocol model.
            - protocol_results_path (str): The path to the protocol results.
            - protocol_test_path (str): The path to the protocol tests.
            - protocol_conf (ConfigParser): The protocol configuration object.
    """
    protocol_conf = configparser.ConfigParser(allow_no_value=True)
    for envar in P_ENV_VAR[protocol]:
        os.environ[envar] = P_ENV_VAR[protocol][envar]
        ENV_VAR[envar] = P_ENV_VAR[protocol][envar]  # TODO only for quic

    if get_default_conf:
        protocol_conf.read(
            "configs/" + protocol + "/default_" + protocol + "_config.ini"
        )
    else:
        protocol_conf.read("configs/" + protocol + "/" + protocol + "_config.ini")

    protocol_model_path = os.path.join(MODEL_DIR, protocol)
    config.set(
        "global_parameters",
        "tests_dir",
        os.path.join(MODEL_DIR, protocol, protocol + "_tests"),
    )
    config.set(
        "global_parameters",
        "dir",
        os.path.join(MODEL_DIR, protocol, "test", "temp"),
    )
    config.set(
        "global_parameters", "build_dir", os.path.join(MODEL_DIR, protocol, "build")
    )

    protocol_test_path    = os.path.join(protocol_model_path, "test/")
    protocol_results_path = os.path.join(protocol_model_path, "test/", "temp/")

    if not os.path.isdir(os.path.join(protocol_model_path, "test/")):
        path = os.path.join(protocol_model_path, "test/")
        logging.debug(f"Creating directory: {path}")
        os.mkdir(os.path.join(protocol_model_path, "test/"))
    if not os.path.isdir(protocol_results_path):
        logging.debug(f"Creating directory: {protocol_results_path}")
        os.mkdir(protocol_results_path)
    if not os.path.isdir(protocol_test_path):
        logging.debug(f"Creating directory: {protocol_test_path}")
        os.mkdir(protocol_test_path)

    tests_enabled = {}
    for category in protocol_conf.keys():
        logging.debug(f"Category: {category}")
        if "_tests" in category:
            tests_enabled[category] = []
            for test in protocol_conf[category]:
                logging.debug(f"\t - Test: {test}")
                if get_all_test or protocol_conf[category].getboolean(test):
                    tests_enabled[category].append(test)

    implem_config_path_server = "configs/" + protocol + "/implem-server"
    implem_config_path_client = "configs/" + protocol + "/implem-client"
    implem_config_path_server_target = "configs/" + protocol + "/implem-server"
    implem_config_path_client_target = "configs/" + protocol + "/implem-client"

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
            
            if protocol == "apt":
                implem_conf_server_target = configparser.ConfigParser(allow_no_value=True)
                implem_conf_server_target.read(os.path.join(implem_config_path_server_target, file_path))
                implem_conf_client_target = configparser.ConfigParser(allow_no_value=True)
                implem_conf_client_target.read(os.path.join(implem_config_path_client_target, file_path))

                conf_implementation_enable[implem_name] = [
                    implem_conf_server,
                    implem_conf_client,
                    implem_conf_server_target,
                    implem_conf_client_target,
                ]   
            else:        
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

    if protocol == "apt":
        protocol_origins = configparser.ConfigParser(allow_no_value=True)
        protocol_origins.read("configs/apt/apt_protocols_config.ini")
        protocol_conf["protocol_origins"] = protocol_origins["implems"]

    return (
        tests_enabled,
        conf_implementation_enable,
        implementation_enable,
        protocol_model_path,
        protocol_results_path,
        protocol_test_path,
        protocol_conf,
    )
