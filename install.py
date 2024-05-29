# /PFV/install.py
import configparser
import argparse
import os
import shutil
import subprocess
import docker
import logging

logging.basicConfig(level=logging.INFO)

def load_config(config_path):
    config = configparser.ConfigParser()
    config.read(config_path)
    return config

def execute_command(command):
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command)

def get_current_branch():
    result = subprocess.run(f"git rev-parse --abbrev-ref HEAD", 
                            shell=True, stdout=subprocess.PIPE, text=True)
    logging.info(f"Current branch: {result.stdout.strip()}")
    return result.stdout.strip()


def start_tool(config):
    execute_command("docker-compose up -d")
    # execute_command("cd pfv/pfv_worker/pfv/scripts/hosts/; bash update_etc_hosts.sh")


def build_ivy_webapp():
    client = docker.from_env()
    logging.info("Building Docker image ivy-webapp")
    execute_command("sudo chown -R $(USER):$(GROUPS) $(PWD)/pfv/pfv_webapp/")
    client.images.build(path="pfv/pfv_webapp", dockerfile="Dockerfile.ivy_webapp", tag="ivy-webapp", network_mode="host", rm=True)

def install_tool(config, branch=None):
    # Pre-installation commands
    logging.info("Running pre-installation commands")

    # Create necessary directories
    for folder in config['directories']:
        logging.info(f"Creating directory: {config['directories'][folder]}")
        # Create build/ and test/temp/ directories inside folder
        os.makedirs(os.path.join(folder, "build"), exist_ok=True)
        os.makedirs(os.path.join(folder, "test", "temp"), exist_ok=True)

    # Install modules
    if config['modules'].getboolean('checkout_git'):
        logging.info("Checking out git repositories")
        if branch is not None:
            execute_command(f"git checkout {branch}")
        current_branch = get_current_branch()
        execute_command("git submodule update --init --recursive")
        execute_command(f"cd pfv/pfv_worker/pfv-ivy/; git fetch; git checkout {current_branch}; git pull")
        execute_command("cd pfv/pfv_worker/pfv-ivy;  git submodule update --init --recursive")

    if config['modules'].getboolean('build_webapp'):
        build_ivy_webapp()


    if config['modules'].getboolean('build_worker'):
        for implem, should_build in config['implems'].items():
            if should_build.lower() == 'true':
                build_implem(implem)

    if config['modules'].getboolean('build_docker_impem_standalone'):
        build_docker_impem_standalone()

    if config['modules'].getboolean('build_visualizer'):
        build_docker_visualizer()

    # Docker-related tasks
    if config['docker'].getboolean('use_docker'):
        client = docker.from_env()
        image = config['docker']['docker_image']
        print(f"Pulling Docker image: {image}")
        client.images.pull(image)
        print(f"Running Docker container from image: {image}")
        client.containers.run(image, detach=True)

    # Post-installation commands
    execute_command(config['commands']['post_install'])

def clean_tool(config):
    build_dir = config['directories']['build']
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    print(f"Cleaned build directory: {build_dir}")

# Functions to replace Make commands
def build_docker_compose_full():
    execute_command("docker-compose -f docker-compose.full.yml up -d")

def build_shadow():
    execute_command("sh pfv/src/pfv-ivy/build_shadow.sh")

def build_gperf():
    execute_command("sh pfv/src/pfv-ivy/build_gperf.sh")

def build_implem(implem):
    client = docker.from_env()
    implem_build_commands = {
        "picoquic-shadow": ("picoquic-shadow", "pfv/src/pfv-ivy", "Dockerfile.picoquic-shadow"),
        "picoquic": ("picoquic", "pfv/src/pfv-ivy", "Dockerfile.picoquic"),
        "ping-pong": ("ping-pong", "pfv/src/pfv-ivy", "Dockerfile.ping-pong"),
        "bgp_bird": ("bird", "pfv/src/pfv-ivy", "Dockerfile.bird"),
        "bgp_frr": ("frr", "pfv/src/pfv-ivy", "Dockerfile.frr"),
        "bgp_gobgp": ("gobgp", "pfv/src/pfv-ivy", "Dockerfile.gobgp"),
        "coap_libcoap": ("libcoap", "pfv/src/pfv-ivy", "Dockerfile.libcoap"),
        "minip_ping_pong": ("minip_ping_pong", "pfv/src/pfv-ivy", "Dockerfile.ping-pong"),
        "quic_aioquic": ("aioquic", "pfv/src/pfv-ivy", "Dockerfile.aioquic"),
        "quic_lsquic": ("lsquic", "pfv/src/pfv-ivy", "Dockerfile.lsquic"),
        "quic_mvfst": ("mvfst", "pfv/src/pfv-ivy", "Dockerfile.mvfst"),
        "quic_picoquic": ("picoquic", "pfv/src/pfv-ivy", "Dockerfile.picoquic"),
        "quic_picotls": ("picotls", "pfv/src/pfv-ivy", "Dockerfile.picotls"),
        "quic_quant": ("quant", "pfv/src/pfv-ivy", "Dockerfile.quant"),
        "quic_quic_go": ("quic-go", "pfv/src/pfv-ivy", "Dockerfile.quic-go"),
        "quic_quiche": ("quiche", "pfv/src/pfv-ivy", "Dockerfile.quiche"),
        "quic_quinn": ("quinn", "pfv/src/pfv-ivy", "Dockerfile.quinn")
    }
    tag, path, dockerfile = implem_build_commands[implem]
    print(f"Building Docker image {tag} from {dockerfile}")
    client.images.build(path=path, dockerfile=dockerfile, tag=tag)

def build_docker_impem_standalone():
    execute_command("docker-compose up -d standalone")

def build_docker_visualizer():
    client = docker.from_env()
    print("Building Docker image visualizer")
    client.images.build(path="pfv/src/pfv-ivy", dockerfile="Dockerfile.visualizer", tag="visualizer")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Manage PFV Tool')
    parser.add_argument('--config', type=str, required=True, help='Path to the configuration file')
    parser.add_argument('command', choices=['install', 'clean'], help='Command to execute')
    args = parser.parse_args()

    config = load_config(args.config)
    
    if args.command == 'install':
        install_tool(config)
    elif args.command == 'clean':
        clean_tool(config)
