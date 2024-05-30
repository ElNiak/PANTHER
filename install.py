# /PFV/install.py
import configparser
import argparse
import os
import shutil
import subprocess
import docker
from docker.errors import NotFound
import logging
import click
import json

logging.basicConfig(level=logging.DEBUG)

def log_docker_output(generator, task_name: str = 'docker command execution') -> None:
    """
    Log output to console from a generator returned from docker client
    :param Any generator: The generator to log the output of
    :param str task_name: A name to give the task, i.e. 'Build database image', used for logging
    """
    while True:
        try:
            output = generator.__next__()
            if 'stream' in output:
                output_str = output['stream'].strip('\r\n').strip('\n')
                click.echo(output_str)
            elif 'error' in output:
                raise ValueError(f'Error from {task_name}: {output["error"]}')
        except StopIteration:
            click.echo(f'{task_name} complete.')
            break
        except ValueError:
            click.echo(f'Error parsing output from {task_name}: {output}')


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
        ip_address = container.attrs['NetworkSettings']['Networks'].values()
        return list(ip_address)[0]['IPAddress']
    except Exception as e:
        logging.error(f"Error getting IP address for container '{container_name}': {e}")
        return None

def restore_hosts_file():
    """Restore the original /etc/hosts file from the backup."""
    try:
        execute_command('sudo cp /etc/hosts.bak /etc/hosts')
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
    result = subprocess.run(f"git rev-parse --abbrev-ref HEAD", 
                            shell=True, stdout=subprocess.PIPE, text=True)
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
            ipam={
                'Config': [{
                    'Subnet': subnet,
                    'Gateway': gateway
                }]
            }
        )
        print(f"Network '{network_name}' created successfully.")
    except Exception as e:
        print(f"Error creating network: {e}")
        
def create_docker_network():
    network_name = 'net'
    gateway = '172.27.1.1'
    subnet = '172.27.1.0/24'

    client = docker.from_env()

    if network_exists(client, network_name):
        print(f"Network '{network_name}' already exists.")
    else:
        create_network(client, network_name, gateway, subnet)

def create_docker_compose_config():
    pass

def start_tool(config):
    client = docker.from_env()
    create_docker_network()
    execute_command("sudo chown -R $USER:$GROUPS $PWD/pfv/pfv_worker/pfv-ivy/")
    execute_command("xhost +")
    execute_command("docker-compose up -d")
    
    containers = {
        'ivy-webapp': 'ivy-webapp',
        'ivy-visualizer': 'ivy-visualizer'
    }
    for container_name, host_entry in containers.items():
        if container_exists(client, container_name):
            ip_address = get_container_ip(client, container_name)
            if ip_address:
                entry = f"{ip_address} {host_entry}\n"
                append_to_hosts_file(entry)
        else:
            print(f"Container '{container_name}' does not exist.")

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
        execute_command("cd pfv/pfv_worker/pfv-ivy;   git submodule update --init --recursive")

    if config['modules'].getboolean('build_webapp'):
        build_ivy_webapp()

    if config['modules'].getboolean('build_worker'):
        for implem, should_build in config['implems'].items():
            if should_build.lower() == 'true':
                if not "shadow" in implem:
                    build_implem(implem, config)
                elif config["modules"]['build_shadow'].lower() == 'true':
                    build_implem(implem, config)

    if config['modules'].getboolean('build_visualizer'):
        build_docker_visualizer()


def clean_tool(config):
    client = docker.from_env()
    docker_containers = client.containers.list(all=True)
    for dc in docker_containers:
        dc.remove(force=True)
    logging.info(client.containers.prune())
    logging.info(client.images.prune(filters={'dangling': False}))
    logging.info(client.networks.prune())
    logging.info(client.volumes.prune())

def build_ivy_webapp():
    client = docker.from_env()
    logging.info("Building Docker image ivy-webapp")
    execute_command("sudo chown -R $USER:$GROUPS $PWD/pfv/pfv_webapp/")
    image_obj, log_generator = client.images.build(path="pfv/pfv_webapp", dockerfile="Dockerfile.ivy_webapp",
                        tag="ivy-webapp", network_mode="host", rm=True,  quiet=False) # squash=True,
    log_docker_output(log_generator, "Building Docker image ivy-webap")

def build_implem(implem,config):
    client = docker.from_env()
    implem_build_commands = {
        # BGP Implementations
        "bgp_bird": ("bird", "pfv/pfv_worker/implementations/bgp-implementations/bird", "Dockerfile.bird"),
        "bgp_gobgp": ("gobgp", "pfv/pfv_worker/implementations/bgp-implementations/gobgp", "Dockerfile.gobgp"),
        
        # CoAP Implementations
        "coap_libcoap": ("libcoap", "pfv/pfv_worker/implementations/coap-implementations/libcoap", "Dockerfile.libcoap"),
        
        # MiniP Implementations
        "minip_ping_pong": ("ping_pong", "pfv/pfv_worker/implementations/minip-implementations/ping-pong", "Dockerfile.ping-pong"),
        
        # QUIC Implementations
        "quic_aioquic": ("aioquic", "pfv/pfv_worker/implementations/quic-implementations/aioquic", "Dockerfile.aioquic"),
        "quic_lsquic": ("lsquic", "pfv/pfv_worker/implementations/quic-implementations/lsquic", "Dockerfile.lsquic"),
        "quic_mvfst": ("mvfst", "pfv/pfv_worker/implementations/quic-implementations/mvfst", "Dockerfile.mvfst"),
        "quic_picoquic": ("picoquic", "pfv/pfv_worker/implementations/quic-implementations/picoquic", "Dockerfile.picoquic"),
        "quic_picoquic_shadow" : ("picoquic-shadow", "pfv/pfv_worker/implementations/quic-implementations/picoquic", "Dockerfile.picoquic-shadow"),
        "quic_picoquic_vuln" : ("picoquic-shadow", "pfv/pfv_worker/implementations/quic-implementations/picoquic", "Dockerfile.picoquic-vuln"),
        "quic_quant": ("quant", "pfv/pfv_worker/implementations/quic-implementations/quant", "Dockerfile.quant"),
        "quic_quic_go": ("quic-go", "pfv/pfv_worker/implementations/quic-implementations/quic-go", "Dockerfile.quic-go"),
        "quic_quiche": ("quiche", "pfv/pfv_worker/implementations/quic-implementations/quiche", "Dockerfile.quiche"),
        "quic_quinn": ("quinn", "pfv/pfv_worker/implementations/quic-implementations/quinn", "Dockerfile.quinn")
    }
    tag, path, dockerfile = implem_build_commands[implem]
    logging.info(f"Building Docker image {tag} from {dockerfile}")
    # Build the base ubuntu-ivy image
    logging.debug("Building Docker image ubuntu-ivy")
    image_obj, log_generator = client.images.build(path="pfv/pfv_worker/", dockerfile="Dockerfile.ubuntu", 
                                                   tag="ubuntu-ivy", rm=True, network_mode="host")
    log_docker_output(log_generator, "Building Docker image ubuntu-ivy")
    
    # Build the first ivy image
    logging.debug("Building Docker image ivy")
    image_obj, log_generator = client.images.build(path="pfv/pfv_worker/", dockerfile="Dockerfile.ivy_1", 
                                                   tag="ivy", rm=True, network_mode="host")
    log_docker_output(log_generator, "Building Docker image ivy")
    
    # Check if shadow build is needed
    shadow_tag = None
    final_tag = f"{tag}-ivy"
    if config["modules"]['build_shadow'].lower() == 'true' and "shadow" in implem:
        logging.debug("Building Docker image shadow-ivy")
        image_obj, log_generator = client.images.build(path="pfv/pfv_worker/", dockerfile="Dockerfile.shadow", 
                                                       tag="shadow-ivy", rm=True, network_mode="host")
        log_docker_output(log_generator, "Building Docker image shadow-ivy")
        shadow_tag = "shadow-ivy"
        final_tag = f"{tag}-shadow-ivy"
    
    # Build the picotls image
    build_args = {"image": shadow_tag} if shadow_tag else  {"image":"ivy"}
    itag       = "shadow-ivy-picotls" if shadow_tag else "ivy-picotls"
    logging.debug(f"Building Docker image {itag} from tag {build_args}")
    image_obj, log_generator = client.images.build(path="pfv/pfv_worker/implementations/quic-implementations/picotls/", dockerfile="Dockerfile.picotls", 
                                                   tag=itag, rm=True, network_mode="host", buildargs=build_args)
    log_docker_output(log_generator, "Building Docker image shadow-ivy-picotls")
    
    # Build the specified implementation image
    build_args = {"image": "shadow-ivy-picotls"} if shadow_tag else {"image": "ivy-picotls"}
    logging.debug(f"Building Docker image {tag} from tag {build_args}")
    image_obj, log_generator = client.images.build(path=path, dockerfile=dockerfile, 
                                                   tag=tag, rm=True, network_mode="host", buildargs=build_args)
    log_docker_output(log_generator, f"Building Docker image {tag}")
    
    # Build the final implementation-ivy image
    build_args = {"image": tag}
    logging.debug(f"Building Docker image {final_tag} from tag {build_args}")
    image_obj, log_generator = client.images.build(path="pfv/pfv_worker/", dockerfile="Dockerfile.ivy_2", tag=final_tag, rm=True, network_mode="host", buildargs=build_args)
    log_docker_output(log_generator, f"Building Docker image {final_tag}")


def build_docker_visualizer():
    client = docker.from_env()
    logging.info("Building Docker image visualizer")
    client.images.build(path="pfv/pfv_webapp/tools/", rm=True, dockerfile="Dockerfile.visualizer", 
                        tag="ivy-visualizer", network_mode="host")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Manage PFV Tool')
    parser.add_argument('--config', type=str, required=True,  help='Path to the configuration file')
    parser.add_argument('--implem', type=str, required=False, help='Name of the implementation to build')
    parser.add_argument('command', choices=['install', 'clean',
                                            "build_webapp", "build_worker",
                                            "run_tools", "run_workers", "run_webapp"], 
                        help='Command to execute')
    args = parser.parse_args()

    config = load_config(args.config)
    
    if args.implem:
        build_implem(args.implem, config)
    elif args.command == 'run_tools':
        start_tool(config)
    elif args.command == 'run_workers':
        pass
    elif args.command == 'run_webapp':
        pass
    elif args.command == 'install':
        install_tool(config)
    elif args.command == 'build_webapp':
        build_ivy_webapp()
    elif args.command == "build_worker":
        for implem, should_build in config['implems'].items():
            if should_build.lower() == 'true':
                if not "shadow" in implem:
                    build_implem(implem, config)
                elif config["modules"]['build_shadow'].lower() == 'true':
                    build_implem(implem, config)
    elif args.command == 'clean':
        clean_tool(config)
