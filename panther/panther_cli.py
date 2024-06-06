"""
# PANTHER CLI

This script is the main entry point for the PANTHER CLI.
It provides a command-line interface to manage the PANTHER tool.
"""

# panther_cli.py
import configparser
import argparse
import os
import shutil
import subprocess
import threading
import docker
from docker.errors import NotFound
from datetime import datetime
import logging
import click
import json
import time
import yaml

try:
    log_file = f"logs/panther_docker_{datetime.now()}.log"
    logging.basicConfig(
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        level=logging.INFO,
    )

    logger = logging.getLogger("panther-cli")
except Exception as e:
    print(f"Error setting up logging: {e}")


def load_config(config_path):
    """
    Load the configuration from the specified file path.

    Args:
        config_path (str): The path to the configuration file.

    Returns:
        configparser.ConfigParser: The loaded configuration object.
    """
    config = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation()
    )
    config.read(config_path)
    return config


def is_htop_installed():
    """
    Check if htop is installed by running 'htop --version' command.

    Returns:
        bool: True if htop is installed, False otherwise.
    """
    try:
        result = subprocess.run(
            ["htop", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def execute_command(command, cwd=None):
    """
    Executes a command in the shell.

    Args:
        command (str): The command to be executed.
        tmux (bool, optional): If True, the command will be executed in a tmux session. Defaults to None.
        cwd (str, optional): The current working directory for the command. Defaults to None.

    Raises:
        subprocess.CalledProcessError: If the command execution returns a non-zero exit code.
    """
    logger.debug(f"Executing command: {command}")

    if cwd:
        result = subprocess.run(command, shell=True, cwd=cwd)
    else:
        result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command)


def setup_tmux_layout(yaml_path, swarm):
    """
    Set up the tmux layout based on whether htop is installed.

    Args:
        yaml_path (str): Path to the docker compose yaml file.
        swarm (bool): Whether the docker setup is using swarm.
    """
    session_name = (
        subprocess.check_output(["tmux", "display-message", "-p", "#S"])
        .strip()
        .decode("utf-8")
    )
    htop_installed = is_htop_installed()
    os.system(f"tmux kill-pane -a -t {session_name}")

    # Setup the initial panes
    os.system(f"tmux split-window -v -l 50% -t {session_name}:0.0")
    os.system(f"tmux split-window -v -l 50% -t {session_name}:0.1")
    os.system(f"tmux split-window -h -l 50% -t {session_name}:0.0")

    # Run bash in the top left pane
    os.system(f"tmux send-keys -t {session_name}:0.2 'bash' C-m")

    # Run docker stats in the bottom pane
    os.system(f"tmux send-keys -t {session_name}:0.0 'docker stats' C-m")

    # Run htop or docker logs in the top right pane
    if htop_installed:
        os.system(f"tmux send-keys -t {session_name}:0.1 'htop' C-m")
    else:
        os.system(f"tmux send-keys -t {session_name}:0.1 'docker stats' C-m")

    # Run docker compose logs in the bottom right pane
    if swarm:
        compose_log = f"logs/swarm_{datetime.now()}.log"
        logger.info(f"Logging docker stack services to {compose_log}")
        os.system(
            f"tmux send-keys -t {session_name}:0.3 'docker stack services panther | tee \"{compose_log}\"' C-m"
        )
    else:
        compose_log = f"logs/compose_{datetime.now()}.log"
        logger.info(f"Logging docker stack services to {compose_log}")
        os.system(
            f"tmux send-keys -t {session_name}:0.3 'docker compose -f {yaml_path} logs -f | tee \"{compose_log}\"' C-m"
        )


from panther_cli_utils.panther_docker import *
from panther_cli_utils.panther_compose import *
from panther_cli_utils.panther_swarm import *


def get_current_branch():
    """_summary_

    Returns:
        _type_: _description_
    """
    result = subprocess.run(
        f"git rev-parse --abbrev-ref HEAD",
        shell=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    logger.info(f"Current branch: {result.stdout.strip()}")
    return result.stdout.strip()


def start_tool(config, swarm=False):
    """_summary_

    Args:
        config (_type_): _description_
        swarm (bool, optional): _description_. Defaults to False.
    """
    client = docker.from_env()

    create_docker_network()

    execute_command("sudo chown -R $USER:$GROUPS $PWD/")
    execute_command("xhost +")

    if swarm:
        execute_command("docker swarm init")
        yaml_path, defined_services = update_docker_swarm(config)
    else:
        yaml_path, defined_services = update_docker_compose(config)

    execute_command(f"cat {yaml_path}")

    if swarm:
        execute_command(f"docker stack rm panther")
        execute_command(f"docker stack -c {yaml_path} panther")
    else:
        execute_command(f"docker compose -f {yaml_path} up -d")

    execute_command("clear")

    setup_tmux_layout(yaml_path, swarm)


def install_tool(config, branch=None):
    """_summary_

    Args:
        config (_type_): _description_
        branch (_type_, optional): _description_. Defaults to None.
    """
    # Pre-installation commands
    logger.info("Running pre-installation commands")

    # Create necessary directories
    # TODO already done in other scripts
    for folder in config["directories"]:
        logger.info(f"Creating directory: {config['directories'][folder]}")
        # Create build/ and test/temp/ directories inside folder
        os.makedirs(os.path.join(folder, "build"), exist_ok=True)
        os.makedirs(os.path.join(folder, "test", "temp"), exist_ok=True)

    # Install modules
    if config["modules"].getboolean("checkout_git"):
        logger.info("Checking out git repositories")
        if branch is not None:
            execute_command(f"git checkout {branch}")
        current_branch = get_current_branch()
        execute_command("git submodule update --init --recursive")
        # TODO cd not working -> chdir
        execute_command(f"git fetch", cwd="panther_worker/panther-ivy/")
        execute_command(
            f"git checkout {current_branch}", cwd="panther_worker/panther-ivy/"
        )
        execute_command(f"git pull", cwd="panther_worker/panther-ivy/")
        execute_command(
            f"git submodule update --init --recursive",
            cwd="panther_worker/panther-ivy/",
        )
        execute_command(f"git pull", cwd="panther_worker/panther-ivy/")
        # execute_command(
        #     "cd panther_worker/app/implementations/quic-implementations/picotls-implem;" + \
        #     "git checkout 047c5fe20bb9ea91c1caded8977134f19681ec76;" + \
        #     "git submodule update --init --recursive" + \
        # )

    if config["modules"].getboolean("build_webapp"):
        build_webapp()

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


def clean_tool(config):
    """_summary_

    Args:
        config (_type_): _description_
    """
    client = docker.from_env()
    docker_containers = client.containers.list(all=True)
    for dc in docker_containers:
        dc.remove(force=True)
    logger.info(client.containers.prune())
    logger.info(client.images.prune(filters={"dangling": False}))
    logger.info(client.networks.prune())
    logger.info(client.volumes.prune())


def build_webapp(push=False):
    """_summary_

    Args:
        push (bool, optional): _description_. Defaults to False.
    """
    client = docker.from_env()
    logger.info("Building Docker image panther-webapp")
    execute_command("sudo chown -R $USER:$GROUPS $PWD/panther_webapp/")
    image_obj, log_generator = client.images.build(
        path="panther_webapp",
        dockerfile="Dockerfile.ivy_webapp",
        tag="panther-webapp",
        network_mode="host",
        rm=True,
        quiet=False,
    )  # squash=True,
    log_docker_output(log_generator, "Building Docker image panther-webap")
    if push:
        push_image_to_registry("panther-webapp")


def build_worker(implem, config, push=False):
    """_summary_

    Args:
        implem (_type_): _description_
        config (_type_): _description_
        push (bool, optional): _description_. Defaults to False.
    """
    stop_tool()
    execute_command("git clean -f -d panther_worker/panther-ivy;")
    client = docker.from_env()

    implem_build_commands = dict(config.items("implem_build_commands"))
    shadow_support = config["shadow_support"]
    tag, path, dockerfile = eval(implem_build_commands[implem])
    execute_command("sudo chown -R $USER:$GROUPS $PWD/")

    logger.info(f"Building Docker image {tag} from {dockerfile}")
    # Build the base ubuntu-panther image
    logger.debug("Building Docker image ubuntu-panther")
    image_obj, log_generator = client.images.build(
        path="panther_worker/",
        dockerfile="Dockerfile.ubuntu",
        tag="ubuntu-panther",
        rm=True,
        network_mode="host",
    )
    log_docker_output(log_generator, "Building Docker image ubuntu-panther")

    # Build the first ivy image
    logger.debug("Building Docker image ivy")
    image_obj, log_generator = client.images.build(
        path="panther_worker/",
        dockerfile="Dockerfile.ivy_1",
        tag="ivy",
        rm=True,
        # buildargs={"CACHEBUST": str(time.time())}, # Cache invalidation
        network_mode="host",
    )
    log_docker_output(log_generator, "Building Docker image ivy")

    # Check if shadow build is needed
    shadow_tag = None
    final_tag = f"{tag}-panther"

    if shadow_support.getboolean(implem):
        logger.debug("Building Docker image shadow-panther")
        image_obj, log_generator = client.images.build(
            path="panther_worker/",
            dockerfile="Dockerfile.shadow",
            tag="shadow-panther",
            rm=True,
            network_mode="host",
        )
        log_docker_output(log_generator, "Building Docker image shadow-panther")
        shadow_tag = "shadow-panther"

        # Build the picotls image
        build_args = {"image": shadow_tag}
        itag = "shadow-panther-picotls"
        logger.debug(f"Building Docker image {itag} from tag {build_args}")
        image_obj, log_generator = client.images.build(
            path="panther_worker/app/implementations/quic-implementations/picotls/",
            dockerfile="Dockerfile.picotls",
            tag=itag,
            rm=True,
            network_mode="host",
            buildargs=build_args,
        )
        log_docker_output(log_generator, "Building Docker image shadow-panther-picotls")
    else:
        # Build the picotls image
        build_args = {"image": "ivy"}
        itag = "panther-picotls"
        logger.debug(f"Building Docker image {itag} from tag {build_args}")
        image_obj, log_generator = client.images.build(
            path="panther_worker/app/implementations/quic-implementations/picotls/",
            dockerfile="Dockerfile.picotls",
            tag=itag,
            rm=True,
            network_mode="host",
            buildargs=build_args,
        )
        log_docker_output(log_generator, "Building Docker image panther-picotls")

    # Build the specified implementation image
    build_args = (
        {"image": "shadow-panther-picotls"}
        if shadow_tag
        else {"image": "panther-picotls"}
    )
    logger.debug(f"Building Docker image {tag} from tag {build_args}")
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
    logger.debug(f"Building Docker image {final_tag} from tag {build_args}")
    image_obj, log_generator = client.images.build(
        path="panther_worker/",
        dockerfile="Dockerfile.ivy_2",
        tag=final_tag,
        rm=True,
        network_mode="host",
        buildargs=build_args,
    )
    log_docker_output(log_generator, f"Building Docker image {final_tag}")

    if push:
        push_image_to_registry(final_tag)


def build_docker_visualizer(push=False):
    """_summary_

    Args:
        push (bool, optional): _description_. Defaults to False.
    """
    client = docker.from_env()
    logger.info("Building Docker image visualizer")
    client.images.build(
        path="panther_webapp/tools/",
        rm=True,
        dockerfile="Dockerfile.visualizer",
        tag="ivy-visualizer",
        network_mode="host",
    )
    if push:
        push_image_to_registry("ivy-visualizer")


def stop_tool():
    """_summary_"""
    client = docker.from_env()
    docker_containers = client.containers.list(all=True)
    for dc in docker_containers:
        dc.stop()


def start_bash_container(implem):
    """_summary_
    Start a Docker container with the specified parameters.

    Args:
        implem (_type_): _description_

    Returns:
        _type_: _description_
    """
    client = docker.from_env()
    pwd = os.getcwd()

    def get_nproc():
        """Get the number of processors available."""
        try:
            result = subprocess.run(
                ["nproc"], capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error getting the number of processors: {e}")
            return "1"

    nproc = get_nproc()
    cpus = f"{nproc}.0"

    container_name = f"{implem}-panther"

    volumes = {
        f"{pwd}/tls-keys": {"bind": "/app/tls-keys", "mode": "rw"},
        f"{pwd}/tickets": {"bind": "/app/tickets", "mode": "rw"},
        f"{pwd}/qlogs": {"bind": "/app/qlogs", "mode": "rw"},
        f"{pwd}/panther_worker/app/panther-ivy/protocol-testing/": {
            "bind": "/app/panther-ivy/protocol-testing/",
            "mode": "rw",
        },
        f"{pwd}/panther_worker/app/panther-ivy/ivy/include/1.7": {
            "bind": "/app/panther-ivy/ivy/include/1.7",
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


from termcolor import colored, cprint
import terminal_banner
import sys
import os

os.system("clear")


def is_tmux_session():
    """Check if running inside a tmux session."""
    return "TMUX" in subprocess.run(["env"], capture_output=True, text=True).stdout


if not is_tmux_session():
    print("Not running inside a tmux session.")
    print(
        "Please start a tmux session first using `tmux` command and then run this script again."
    )
    exit(0)

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
@@!             :J:        :~G^ .?#~   .:..         :...             @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@&               :5.        .. .7#!  .^^~   .:.    ^^                @@@@@@@@@@@@@@@@&G5J~.    P
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

if __name__ == "__main__":
    """_summary_"""
    parser = argparse.ArgumentParser(description="Manage PANTHER Tool")
    parser.add_argument(
        "--config", type=str, required=True, help="Path to the configuration file"
    )
    parser.add_argument(
        "--implem", type=str, required=False, help="Name of the implementation to build"
    )
    parser.add_argument(
        "--debug", required=False, help="Debug mode", action="store_true"
    )
    parser.add_argument(
        "--push_to_hub",
        required=False,
        help="Push image to docker hub",
        action="store_true",
    )
    parser.add_argument(
        "command",
        choices=[
            "install",
            "clean",
            "build_webapp",
            "build_worker",
            "push_tools",
            "run_tools",
            "run_workers",
            "run_webapp",
            "run_tools_prod",
            "run_workers_prod",
            "run_webapp",
            "update_docker_compose",
            "update_docker_swarm",
            "stop_tools",
        ],
        help="Command to execute",
    )
    args = parser.parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    config = load_config(args.config)

    if args.implem:
        build_worker(args.implem, config)
    elif args.command == "update_docker_compose":
        update_docker_compose(config)
    elif args.command == "run_tools":
        start_tool(config)
    elif args.command == "run_workers":
        pass
    elif args.command == "run_webapp":
        pass
    elif args.command == "stop_tools":
        stop_tool()

    elif args.command == "update_docker_swarm":
        update_docker_swarm(config, prod=True)
    elif args.command == "run_tools_prod":
        start_tool(config, swarm=True)
    elif args.command == "run_workers_prod":
        pass
    elif args.command == "run_webapp_prod":
        pass

    elif args.command == "install":
        install_tool(config)
    elif args.command == "build_webapp":
        build_webapp(push=args.push_to_hub)
    elif args.command == "build_worker":
        for implem, should_build in config["implems"].items():
            if should_build.lower() == "true":
                build_worker(implem, config, push=args.push_to_hub)

    elif args.command == "clean":
        clean_tool(config)
    elif args.command == "push_tools":
        container_names = get_panther_container()
        for container_name in container_names:
            push_image_to_registry(container_name)
