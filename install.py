# /PFV/install.py
import configparser
import argparse
import os
import shutil
import subprocess
import docker
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
                if not "shadow" in implem:
                    build_implem(implem, config)
                elif config["modules"]['build_shadow'].lower() == 'true':
                    build_implem(implem, config)

    # if config['modules'].getboolean('build_docker_impem_standalone'):
    #     build_docker_impem_standalone()

    # if config['modules'].getboolean('build_visualizer'):
    #     build_docker_visualizer()

    # Docker-related tasks
    # if config['docker'].getboolean('use_docker'):
    #     client = docker.from_env()
    #     image = config['docker']['docker_image']
    #     print(f"Pulling Docker image: {image}")
    #     client.images.pull(image)
    #     print(f"Running Docker container from image: {image}")
    #     client.containers.run(image, detach=True)

    # Post-installation commands
    execute_command(config['commands']['post_install'])

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
        "bgp_bird": ("bird", "pfv/pfv_worker/implementations/bgp-implementations/bird", "Dockerfile.bird"),
        "bgp_gobgp": ("gobgp", "pfv/pfv_worker/implementations/bgp-implementations/gobgp", "Dockerfile.gobgp"),
        "coap_libcoap": ("libcoap", "pfv/pfv_worker/implementations/coap-implementations/libcoap", "Dockerfile.libcoap"),
        "minip_ping_pong": ("minip_ping_pong", "pfv/pfv_worker/implementations/minip-implementations", "Dockerfile.ping-pong"),
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
    image_obj, log_generator = client.images.build(path="pfv/pfv_worker/", dockerfile="Dockerfile.ubuntu", tag="ubuntu-ivy", rm=True, network_mode="host")
    log_docker_output(log_generator, "Building Docker image ubuntu-ivy")
    
    # Build the first ivy image
    image_obj, log_generator = client.images.build(path="pfv/pfv_worker/", dockerfile="Dockerfile.ivy_1", tag="ivy", rm=True, network_mode="host")
    log_docker_output(log_generator, "Building Docker image ivy")
    
    # Check if shadow build is needed
    shadow_tag = ""
    final_tag = f"{tag}-ivy"
    if config["modules"]['build_shadow'].lower() == 'true' and "shadow" in implem:
        image_obj, log_generator = client.images.build(path="pfv/pfv_worker/", dockerfile="Dockerfile.shadow", tag="shadow-ivy", rm=True, network_mode="host")
        log_docker_output(log_generator, "Building Docker image shadow-ivy")
        shadow_tag = "shadow-ivy"
        final_tag = f"{tag}-shadow-ivy"
    
    # Build the picotls image
    build_args = {"image": shadow_tag} if shadow_tag else None
    image_obj, log_generator = client.images.build(path="pfv/pfv_worker/", dockerfile="Dockerfile.picotls", tag="shadow-ivy-picotls", rm=True, network_mode="host", buildargs=build_args)
    log_docker_output(log_generator, "Building Docker image shadow-ivy-picotls")
    
    # Build the specified implementation image
    build_args = {"image": "shadow-ivy-picotls"} if shadow_tag else {"image": "ivy"}
    image_obj, log_generator = client.images.build(path=path, dockerfile=dockerfile, tag=tag, rm=True, network_mode="host", buildargs=build_args)
    log_docker_output(log_generator, f"Building Docker image {tag}")
    
    # Build the final implementation-ivy image
    build_args = {"image": tag}
    image_obj, log_generator = client.images.build(path="pfv/pfv_worker/", dockerfile="Dockerfile.ivy_2", tag=final_tag, rm=True, network_mode="host", buildargs=build_args)
    log_docker_output(log_generator, f"Building Docker image {final_tag}")


def build_docker_impem_standalone():
    execute_command("docker-compose up -d standalone")

def build_docker_visualizer():
    client = docker.from_env()
    print("Building Docker image visualizer")
    client.images.build(path="pfv/src/pfv-ivy", dockerfile="Dockerfile.visualizer", tag="visualizer")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Manage PFV Tool')
    parser.add_argument('--config', type=str, required=True, help='Path to the configuration file')
    parser.add_argument('command', choices=['install', 'clean',"build_webapp", "build_worker"], help='Command to execute')
    args = parser.parse_args()

    config = load_config(args.config)
    
    if args.command == 'install':
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
