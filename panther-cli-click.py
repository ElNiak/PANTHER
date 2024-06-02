# /PANTHER/install.py
import configparser
import argparse
import os
import shutil
import subprocess
import threading
import docker
from docker.errors import NotFound
import logging
import json
import time
import yaml
from datetime import datetime

from termcolor import colored, cprint
import terminal_banner
import sys
import os

os.system("clear")
banner = """
@@@@@@@@@@@@@@@@&&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@: .~JG#&@@@@@@@@@@@@@@@@@@@@@@@@@@&BJ~. .&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@G   .::: :?5G57~:.........:^!YG5J^.:^:.   5@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@G :.  :~                           ^:  .: Y@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@& .:  ^    .                   .    ^  :. #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@7   .:  .     .^.        ~:     .  ..   ~@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@7      ~~^.  ^7^::~ ~::^7^  .^~~.     !&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@7     :!~??~. :?!: .!?^ .~??~~^     :@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@J       .Y5~7J7..^   ^..7J?^YY.       ^&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@^   .   . !P7!^. .~. .^.  ~7!5~ .   :  ..B@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@:.  :~   !^  .:^^  .^.^.  ^^:.  ^J.  ^^  :.#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@P.^  ?^    ..:: :^.       .^^ .:.:.   .J  :~!@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@Y^^  5!    :??.  7!!?7!7J7!?.  ??^    ^5. :!!@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@#.!  Y5.   :J:^:  ..~P75!..  :^:?^   .YY  ~:G@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@?:. .YY7^. ~^^^^    ...    :^^^!  .!5Y: .: P@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@...  J557 .7:.     .:..    .:7. !5Y~  .^  .@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@5  ^7.~55.... ^B5:!?YY57!^J#! ....5. .77 .. Y@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@P :~ .7Y55.  . !@&:!!^.^!!:#@? .  ~Y7JJ^  :Y. #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@J .YJ   .^7:    .^G?5YJ^?J5?G~.    ~~^.     ^5!.?@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@! :Y!             .~~!YYJYY7~~.         .     J5Y.^@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@7 ^5~  :~         .JG!^~:.:~~~GY.         7!:^?5555 .@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@5  Y5  .P~        .5!!: ^~:~^ .!~Y.         ~J555555^ ~@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@   Y5!:?57         ?^  .::.::.  :J.            .:!55^  B@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@G   .?5555~          :!^.      .~:        J:       :5^  7@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@Y    .555^      ..     .^~~~~^:.          :~~:.     ~7  !@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@#      !P7     .!J^                            :?^    :. .@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@.       ~?    .Y^                         ....  :^        !@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@P     .   ..   ::                      ^~::....::^^.        .&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@~     ~J        !                  .:::^.           ^^.       .&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@&.      ~57.     !7        .....::::::.           .:             ?@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@.         .^~^   :.     .!?#^ .:...                              .@@@@@@@@@@@@@@@@@@@@@@@@@@#J7P@
@@!             :J:        :~G^ .?#~   .:..         :...             @@@@@@@@@@@@@@@@@@@@&G5J~.    P
@&               :5.        .. .7#!  .^^~   .:.    ^^                @@@@@@@@@@@@@@@@#7.           G
@Y              .757            !    .?&#..:.    .~     ..           &@@@@@@@@@@@@@#:            .P@
@J              ....!J?^             ^G:  ~GG  .::      .:^:.        &@@@@@@@@@@@@5         .^75#@@@
@@:..                :~?!::.         .    PJ^..            ...      Y@@@@@@@@@@@@&        :#@@@@@@@@
@@@^ .                :   ~~...          ..                      JG#@@@@@@@@@@@@@#        &@@@@@@@@@
@@@@?.                ..:.5&G.:                                  G@@@@@@@@@@@@@@@@:       &@@@@@@@@@
@@@@@&5~.         ::  .  :.:J?.                                 ^ .~P&@@@@@@@@@@@@&       7@@@@@@@@@
@@@@@@@@@&^       .  .~.                                        ^   .~J#@@@@@@@@@@@B    .  ?@@@@@@@@
@@@@@@@@@@B        : ^G#B! .                    5&.             ^     :^7&@@@@@@@@@@J   :.  P@@@@@@@
@@@@@@@@@@@Y   .^   :.  .7PP&B!                 @@J^.          ^        ::B@@@@@@@@@&   .   :@@@@@@@
@@@@@@@@@@@@&. :^  .    :&@@@@@P.               ^&P.~         ~~GY^.     ..P@@@@@@@@J    !. .@@@@@@@
@@@@@@@@@@@@@7     G&B! J@@@@@@@@?                : .^:.     ~~B@@@5.     . :JGBBBY:    ^P: J@@@@@@@
@@@@@@@@@@@@@P.  ~7: :5G5G@@@@@@@@@Y            .:    ~..    .:5@@@@&~    ..           .Y? ~@@@@@@@@
@@@@@@@@@@@@@@&? .YB?^G@@@@@@@@@@@@@&?           :    7        .@@@@@@G:   .^:.      .~J!.5@@@@@@@@@
@@@@@@@@@@@@@@@@&P7^?G5@@@@@@@@@@@@@@@&Y~:::~: .::    !         P@@@@@@@B~    :^^^^~!!~~5@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&5!:   .!         .&@@@@@@@@@#57~^^^~~7Y-#@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@#!  ~    .  .   !@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&7..        :! #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@!!:.  .: :^~ &@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&?.^?7~7YJ. !@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&. .^. ::  .7&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@# :.        :#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@P 7.    ..!~ ?@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@J.~         5@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@#!   ..:^~G@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&BPYYG&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                                            Made with ❤️ 
                                For the Community, By the Community   

                                ###################################
                    
                                        Made by ElNiak
                linkedin  - https://www.linkedin.com/in/christophe-crochet-5318a8182/ 
                                Github - https://github.com/elniak
                                                                                      
"""
banner_terminal = terminal_banner.Banner(banner)
cprint(banner_terminal, "green", file=sys.stderr)

import click

IMPLEM_BUILD_COMMAND = {
    # BGP Implementations
    "bgp_bird": (
        "bird",
        "panther/panther_worker/app/implementations/bgp-implementations/bird",
        "Dockerfile.bird",
    ),
    "bgp_gobgp": (
        "gobgp",
        "panther/panther_worker/app/implementations/bgp-implementations/gobgp",
        "Dockerfile.gobgp",
    ),
    # CoAP Implementations
    "coap_libcoap": (
        "libcoap",
        "panther/panther_worker/app/implementations/coap-implementations/libcoap",
        "Dockerfile.libcoap",
    ),
    # MiniP Implementations
    "minip_ping_pong": (
        "ping-pong",
        "panther/panther_worker/app/implementations/minip-implementations/ping-pong",
        "Dockerfile.ping-pong",
    ),
    # QUIC Implementations
    "quic_aioquic": (
        "aioquic",
        "panther/panther_worker/app/implementations/quic-implementations/aioquic",
        "Dockerfile.aioquic",
    ),
    "quic_lsquic": (
        "lsquic",
        "panther/panther_worker/app/implementations/quic-implementations/lsquic",
        "Dockerfile.lsquic",
    ),
    "quic_mvfst": (
        "mvfst",
        "panther/panther_worker/app/implementations/quic-implementations/mvfst",
        "Dockerfile.mvfst",
    ),
    "quic_picoquic": (
        "picoquic",
        "panther/panther_worker/app/implementations/quic-implementations/picoquic",
        "Dockerfile.picoquic",
    ),
    "quic_picoquic_shadow": (
        "picoquic-shadow",
        "panther/panther_worker/app/implementations/quic-implementations/picoquic",
        "Dockerfile.picoquic-shadow",
    ),
    "quic_picoquic_vuln": (
        "picoquic-shadow",
        "panther/panther_worker/app/implementations/quic-implementations/picoquic",
        "Dockerfile.picoquic-vuln",
    ),
    "quic_quant": (
        "quant",
        "panther/panther_worker/app/implementations/quic-implementations/quant",
        "Dockerfile.quant",
    ),
    "quic_quic_go": (
        "quic-go",
        "panther/panther_worker/app/implementations/quic-implementations/quic-go",
        "Dockerfile.quic-go",
    ),
    "quic_quiche": (
        "quiche",
        "panther/panther_worker/app/implementations/quic-implementations/quiche",
        "Dockerfile.quiche",
    ),
    "quic_quinn": (
        "quinn",
        "panther/panther_worker/app/implementations/quic-implementations/quinn",
        "Dockerfile.quinn",
    ),
}


log_file = f"logs/panther_docker_{datetime.now()}.log"
logging.basicConfig(handlers=[
                        logging.FileHandler(log_file),
                        logging.StreamHandler()
                    ],
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

def log_docker_output(generator, task_name: str = "docker command execution") -> None:
    """
    Log output to console from a generator returned from docker client
    :param Any generator: The generator to log the output of
    :param str task_name: A name to give the task, i.e. 'Build database image', used for logging
    """
    while True:
        try:
            output = generator.__next__()
            if "stream" in output:
                output_str = output["stream"].strip("\r\n").strip("\n")
                logging.info(f"{task_name}: {output_str}")
            elif "error" in output:
                raise ValueError(f'Error from {task_name}: {output["error"]}')
        except StopIteration:
            logging.info(f"{task_name} complete.")
            break
        except ValueError:
            logging.error(f"Error parsing output from {task_name}: {output}")


def container_exists(client, container_name):
    """Check if the Docker container exists."""
    try:
        client.containers.get(container_name)
        return True
    except docker.errors.NotFound:
        return False
    except Exception as e:
        logging.error(f"Error checking container existence: {e}")
        return False


def get_container_ip(client, container_name):
    """Get the IP address of the Docker container."""
    try:
        container = client.containers.get(container_name)
        ip_address = container.attrs["NetworkSettings"]["Networks"].values()
        return list(ip_address)[0]["IPAddress"]
    except Exception as e:
        logging.error(f"Error getting IP address for container '{container_name}': {e}")
        return None


def restore_hosts_file():
    """Restore the original /etc/hosts file from the backup."""
    try:
        execute_command("sudo cp /etc/hosts.bak /etc/hosts")
        logging.info("Restored the original /etc/hosts file.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error restoring /etc/hosts: {e}")


def append_to_hosts_file(entry):
    """Append a new entry to the /etc/hosts file."""
    try:
        command = f"echo '{entry.strip()}' | sudo tee -a /etc/hosts"
        execute_command(command)
        logging.info(f"Added entry to /etc/hosts: {entry.strip()}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error adding entry to /etc/hosts: {e}")


def load_config(config_path):
    config = configparser.ConfigParser()
    config.read(config_path)
    return config


def execute_command(command):
    logging.debug(f"Executing command: {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command)


def get_current_branch():
    result = subprocess.run(
        f"git rev-parse --abbrev-ref HEAD",
        shell=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    logging.info(f"Current branch: {result.stdout.strip()}")
    return result.stdout.strip()


def network_exists(client, network_name):
    """Check if the Docker network exists."""
    try:
        client.networks.get(network_name)
        return True
    except NotFound:
        return False
    except Exception as e:
        print(f"Error checking network existence: {e}")
        return False


def create_network(client, network_name, gateway, subnet):
    """Create a Docker network with the specified gateway and subnet."""
    try:
        client.networks.create(
            name=network_name,
            driver="bridge",
            ipam={"Config": [{"Subnet": subnet, "Gateway": gateway}]},
        )
        print(f"Network '{network_name}' created successfully.")
    except Exception as e:
        print(f"Error creating network: {e}")


def create_docker_network():
    network_name = "net"
    gateway = "172.27.1.1"
    subnet = "172.27.1.0/24"

    client = docker.from_env()

    if network_exists(client, network_name):
        print(f"Network '{network_name}' already exists.")
    else:
        create_network(client, network_name, gateway, subnet)


def create_docker_compose_config():
    pass

@click.command()
@click.pass_context
@click.option('--config_file', default="install_config.ini", help='Configuration file to use for installation')
def start_tool(config_file):
    config = load_config(config_file)
    client = docker.from_env()
    create_docker_network()
    execute_command("sudo chown -R $USER:$GROUPS $PWD/panther/")
    execute_command("xhost +")
    yaml_path, defined_services = update_docker_compose(config)
    execute_command(f"cat {yaml_path}")
    execute_command(f"docker compose -f {yaml_path} up -d")

    for container_name in defined_services:
        if container_exists(client, container_name):
            thread = threading.Thread(target=monitor_docker_usage, args=([container_name, 10, -1])) 
            thread.start()
            ip_address = get_container_ip(client, container_name)
            if ip_address:
                entry = f"{ip_address} {container_name}\n"
                append_to_hosts_file(entry)
        else:
            print(f"Container '{container_name}' does not exist.")


def monitor_docker_usage(container_name, interval=1.0, duration=10.0):
    """
    Monitor the CPU and memory usage of a Docker container.

    :param container_name: Name or ID of the Docker container to monitor
    :param interval: Time interval (in seconds) between checks
    :param duration: Total duration (in seconds) to monitor
    """
    client = docker.from_env()

    try:
        container = client.containers.get(container_name)
    except docker.errors.NotFound:
        logging.info(f"No container found with name or ID {container_name}")
        return

    start_time = time.time()
    duration_condition = lambda: (
        (time.time() - start_time) < duration if duration > 0 else True
    )
    while duration_condition():
        try:
            stats = container.stats(stream=False)

            # Check for missing keys and default to 0 if missing
            cpu_delta = stats["cpu_stats"]["cpu_usage"].get("total_usage", 0) - stats[
                "precpu_stats"
            ]["cpu_usage"].get("total_usage", 0)
            system_cpu_delta = stats["cpu_stats"].get("system_cpu_usage", 0) - stats[
                "precpu_stats"
            ].get("system_cpu_usage", 0)
            number_cpus = len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage", []))
            cpu_usage = (
                (cpu_delta / system_cpu_delta) * number_cpus * 100.0
                if system_cpu_delta > 0
                else 0.0
            )

            memory_usage = stats["memory_stats"].get("usage", 0) / (
                1024 * 1024
            )  # Convert to MB
            memory_limit = stats["memory_stats"].get("limit", 1) / (
                1024 * 1024
            )  # Convert to MB
            memory_percentage = (
                (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0.0
            )

            logging.info(
                f"Name {container_name} - Time: {time.time() - start_time:.2f}s - CPU Usage: {cpu_usage:.2f}% - Memory Usage: {memory_usage:.2f}MB ({memory_percentage:.2f}%)"
            )
        except docker.errors.APIError as e:
            logging.error(f"An error occurred: {e}")
            break
        except KeyError as e:
            logging.warning(f"Missing key in stats: {e}")
        time.sleep(interval)

@click.command()
@click.pass_context
@click.option('--config_file', default="install_config.ini",        help='Configuration file to use for installation')
@click.option('--yaml_path',   default="panther/docker-compose.yml", help='Path to the Docker Compose YAML file')
def update_docker_compose(config_file, yaml_path="panther/docker-compose.yml"):
    config = load_config(config_file)
    with open(yaml_path, "r") as file:
        # save backup version
        shutil.copyfile(yaml_path, f"{yaml_path}.bak")
        docker_compose = yaml.safe_load(file)

    base_ip = [172, 27, 1, 11]
    base_port = 49160
    defined_services = set()
    defined_services.add("panther-webapp")
    for implem, should_build in config["implems"].items():
        if should_build.lower() == "true":
            updated_name = implem.split("_", 1)[-1].replace("_", "-")
            service_name = f"{updated_name}-ivy"
            defined_services.add(service_name)
            if service_name not in docker_compose["services"]:
                base_ip[-1] += 1
                base_port += 1
                ipv4_address = ".".join(map(str, base_ip))
                port = base_port

                docker_compose["services"][service_name] = {
                    "hostname": service_name,
                    "container_name": service_name,
                    "image": f"{service_name}:latest",
                    "command": "bash -c \"stty cols 100 rows 100 && python3 panther_client.py\"",
                    "ports": [f"{port}:80"],
                    "volumes": [
                        "/tmp/.X11-unix:/tmp/.X11-unix",
                        "${PWD}/panther/panther_worker/app/:/app/",
                        "${PWD}/panther/panther_worker/app/panther-ivy/protocol-testing/:/app/panther-ivy/protocol-testing/",
                        "${PWD}/panther/panther_worker/app/panther-ivy/ivy/include/:/app/panther-ivy/ivy/include/",
                        "${PWD}/panther/outputs/tls-keys:/app/tls-keys",
                        "${PWD}/panther/outputs/tickets:/app/tickets",
                        "${PWD}/panther/outputs/qlogs:/app/qlogs",
                    ],
                    "networks": {"net": {"ipv4_address": ipv4_address}},
                    "privileged": True,
                    "tty": True,
                    "stdin_open": True,
                    # Spectre/Meltdown mitigation ~30% performance hit
                    "security_opt" : ["seccomp:unconfined"],
                    "environment": [
                        "DISPLAY=${DISPLAY}",
                        "XAUTHORITY=~/.Xauthority",
                        "ROOT_PATH=${PWD}",
                        'MPLBACKEND="Agg"',
                        "COLUMNS=100",
                        "LINES=100",
                    ],
                    "restart": "always",
                    "depends_on": ["panther-webapp"],
                }

    # Remove services not defined in config
    services_to_remove = set(docker_compose["services"].keys()) - defined_services
    for service in services_to_remove:
        del docker_compose["services"][service]

    with open(yaml_path, "w") as file:
        yaml.safe_dump(docker_compose, file)

    logging.info("Docker Compose configuration updated successfully.")
    return yaml_path, defined_services


@click.command()
@click.pass_context
@click.option('--config_file', default="install_config.ini", help='Configuration file to use for installation')
def install_tool(config_file, branch=None):
    config = load_config(config_file)
    # Pre-installation commands
    logging.info("Running pre-installation commands")

    # Create necessary directories
    for folder in config["directories"]:
        logging.info(f"Creating directory: {config['directories'][folder]}")
        # Create build/ and test/temp/ directories inside folder
        os.makedirs(os.path.join(folder, "build"), exist_ok=True)
        os.makedirs(os.path.join(folder, "test", "temp"), exist_ok=True)

    # Install modules
    if config["modules"].getboolean("checkout_git"):
        logging.info("Checking out git repositories")
        if branch is not None:
            execute_command(f"git checkout {branch}")
        current_branch = get_current_branch()
        execute_command("git submodule update --init --recursive")
        # TODO cd not working -> chdir
        execute_command(
            f"cd panther/panther_worker/panther-ivy/; git fetch; git checkout {current_branch}; git pull"
        )
        execute_command(
            "cd panther/panther_worker/panther-ivy;   git submodule update --init --recursive"
        )
        # execute_command(
        #     "cd panther/panther_worker/app/implementations/quic-implementations/picotls-implem;" + \  
        #     "git checkout 047c5fe20bb9ea91c1caded8977134f19681ec76;" + \
        #     "git submodule update --init --recursive" + \
        # )

    if config["modules"].getboolean("build_webapp"):
        build_ivy_webapp()

    if config["modules"].getboolean("build_worker"):
        for implem, should_build in config["implems"].items():
            if should_build.lower() == "true":
                if not "shadow" in implem:
                    build_worker(implem, config)
                elif config["modules"]["build_shadow"].lower() == "true":
                    build_worker(implem, config)

    if config["modules"].getboolean("build_visualizer"):
        build_docker_visualizer()

    update_docker_compose(config)

@click.command()
@click.pass_context
@click.option('--config_file', default="install_config.ini", help='Configuration file to use for installation')
def clean_tool(config_file):
    config = load_config(config_file)
    client = docker.from_env()
    docker_containers = client.containers.list(all=True)
    for dc in docker_containers:
        dc.remove(force=True)
    logging.info(client.containers.prune())
    logging.info(client.images.prune(filters={"dangling": False}))
    logging.info(client.networks.prune())
    logging.info(client.volumes.prune())

@click.command()
@click.pass_context
def build_ivy_webapp():
    client = docker.from_env()
    logging.info("Building Docker image panther-webapp")
    execute_command("sudo chown -R $USER:$GROUPS $PWD/panther/panther_webapp/")
    image_obj, log_generator = client.images.build(
        path="panther/panther_webapp",
        dockerfile="Dockerfile.ivy_webapp",
        tag="panther-webapp",
        network_mode="host",
        rm=True,
        quiet=False,
    )  # squash=True,
    log_docker_output(log_generator, "Building Docker image ivy-webap")





@click.command()
@click.pass_context
@click.option('--config_file', default="install_config.ini", help='Configuration file to use for installation')
@click.option('--implem',      default="all",                help=f'Implementations to build (all vs individual): \n{IMPLEM_BUILD_COMMAND.keys()}')
def build_worker(implem, config_file):
    config = load_config(config_file)
    stop_tool()
    execute_command("git clean -f -d panther/panther_worker/panther-ivy;")
    client = docker.from_env()
    
    if implem == "all":
        for implem, should_build in config["implems"].items():
            build_worker(implem, config_file)
        return
    
    tag, path, dockerfile = IMPLEM_BUILD_COMMAND[implem]
    logging.info(f"Building Docker image {tag} from {dockerfile}")
    # Build the base ubuntu-ivy image
    logging.debug("Building Docker image ubuntu-ivy")
    image_obj, log_generator = client.images.build(
        path="panther/panther_worker/",
        dockerfile="Dockerfile.ubuntu",
        tag="ubuntu-ivy",
        rm=True,
        network_mode="host",
    )
    log_docker_output(log_generator, "Building Docker image ubuntu-ivy")

    # Build the first ivy image
    logging.debug("Building Docker image ivy")
    image_obj, log_generator = client.images.build(
        path="panther/panther_worker/",
        dockerfile="Dockerfile.ivy_1",
        tag="ivy",
        rm=True,
        buildargs={"CACHEBUST": str(time.time())},
        network_mode="host",
    )
    log_docker_output(log_generator, "Building Docker image ivy")
    # Check if shadow build is needed
    shadow_tag = None
    final_tag = f"{tag}-ivy"
    # final_tag = final_tag.split("_",1)[-1].replace("_","-")
    if config["modules"]["build_shadow"].lower() == "true" and "shadow" in implem:
        logging.debug("Building Docker image shadow-ivy")
        image_obj, log_generator = client.images.build(
            path="panther/panther_worker/",
            dockerfile="Dockerfile.shadow",
            tag="shadow-ivy",
            rm=True,
            network_mode="host",
        )
        log_docker_output(log_generator, "Building Docker image shadow-ivy")
        shadow_tag = "shadow-ivy"

    # Build the picotls image
    build_args = {"image": shadow_tag} if shadow_tag else {"image": "ivy"}
    itag = "shadow-ivy-picotls" if shadow_tag else "ivy-picotls"
    logging.debug(f"Building Docker image {itag} from tag {build_args}")
    image_obj, log_generator = client.images.build(
        path="panther/panther_worker/app/implementations/quic-implementations/picotls/",
        dockerfile="Dockerfile.picotls",
        tag=itag,
        rm=True,
        network_mode="host",
        buildargs=build_args,
    )
    log_docker_output(log_generator, "Building Docker image shadow-ivy-picotls")

    # Build the specified implementation image
    build_args = (
        {"image": "shadow-ivy-picotls"} if shadow_tag else {"image": "ivy-picotls"}
    )
    logging.debug(f"Building Docker image {tag} from tag {build_args}")
    image_obj, log_generator = client.images.build(
        path=path,
        dockerfile=dockerfile,
        tag=tag,
        rm=True,
        network_mode="host",
        buildargs=build_args,
    )

    log_docker_output(log_generator, f"Building Docker image {tag}")
    # Build the final implementation-ivy image
    build_args = {"image": tag}
    logging.debug(f"Building Docker image {final_tag} from tag {build_args}")
    image_obj, log_generator = client.images.build(
        path="panther/panther_worker/",
        dockerfile="Dockerfile.ivy_2",
        tag=final_tag,
        rm=True,
        network_mode="host",
        buildargs=build_args,
    )
    log_docker_output(log_generator, f"Building Docker image {final_tag}")


def build_docker_visualizer():
    client = docker.from_env()
    logging.info("Building Docker image visualizer")
    client.images.build(
        path="panther/panther_webapp/tools/",
        rm=True,
        dockerfile="Dockerfile.visualizer",
        tag="ivy-visualizer",
        network_mode="host",
    )

@click.command()
@click.pass_context
def stop_tool():
    client = docker.from_env()
    docker_containers = client.containers.list(all=True)
    for dc in docker_containers:
        dc.stop()

def get_nproc():
    """Get the number of processors available."""
    try:
        result = subprocess.run(["nproc"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting the number of processors: {e}")
        return "1"

@click.command()
@click.pass_context
def start_bash_container(implem):
    """Start a Docker container with the specified parameters."""
    client = docker.from_env()
    pwd = os.getcwd()
    nproc = get_nproc()
    cpus = f"{nproc}.0"

    container_name = f"{implem}-ivy"

    volumes = {
        f"{pwd}/tls-keys": {"bind": "/PANTHER/tls-keys", "mode": "rw"},
        f"{pwd}/tickets": {"bind": "/PANTHER/tickets", "mode": "rw"},
        f"{pwd}/qlogs": {"bind": "/PANTHER/qlogs", "mode": "rw"},
        f"{pwd}/src/Protocols-Ivy/doc/examples/quic": {
            "bind": "/PANTHER/Protocols-Ivy/doc/examples/quic",
            "mode": "rw",
        },
        f"{pwd}/src/Protocols-Ivy/ivy/include/1.7": {
            "bind": "/PANTHER/Protocols-Ivy/ivy/include/1.7",
            "mode": "rw",
        },
    }

    try:
        container = client.containers.run(
            image=container_name,
            command="bash",
            privileged=True,
            cpus=cpus,
            mem_limit="10g",
            mem_reservation="9.5g",
            volumes=volumes,
            tty=True,
            stdin_open=True,
            detach=True,
        )
        print(f"Started container {container.id} ({container_name})")
    except Exception as e:
        print(f"Error starting the container: {e}")

@click.group()
def cli():
    pass

cli.add_command(start_tool)
cli.add_command(install_tool)
cli.add_command(clean_tool)
cli.add_command(stop_tool)
cli.add_command(start_bash_container)
cli.add_command(build_worker)
cli.add_command(build_ivy_webapp)

if __name__ == '__main__':
    cli()
