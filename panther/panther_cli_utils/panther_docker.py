import logging
import docker
from docker.errors import NotFound
import subprocess
import time
from panther_cli import execute_command


def log_docker_output(generator, task_name: str = "docker command execution") -> None:
    """_summary_

    Args:
        generator (_type_): _description_
        task_name (str, optional): _description_. Defaults to "docker command execution".

    Raises:
        ValueError: _description_
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
    """_summary_
    Check if the Docker container exists.

    Args:
        client (_type_): _description_
        container_name (_type_): _description_

    Returns:
        _type_: _description_
    """
    try:
        client.containers.get(container_name)
        return True
    except docker.errors.NotFound:
        return False
    except Exception as e:
        logging.error(f"Error checking container existence: {e}")
        return False


def get_container_ip(client, container_name):
    """_summary_
    Get the IP address of the Docker container.

    Args:
        client (_type_): _description_
        container_name (_type_): _description_

    Returns:
        _type_: _description_
    """
    try:
        container = client.containers.get(container_name)
        ip_address = container.attrs["NetworkSettings"]["Networks"].values()
        return list(ip_address)[0]["IPAddress"]
    except Exception as e:
        logging.error(f"Error getting IP address for container '{container_name}': {e}")
        return None


def get_panther_container():
    """_summary_

    Returns:
        _type_: _description_
    """
    client = docker.from_env()
    panther_containers = []
    for container in client.containers.list():
        if "panther" in container.name:
            panther_containers.append(container.name)
    return panther_containers


def push_image_to_registry(image_name, registry_url="elniak", tag="latest"):
    """_summary_
    Push a Docker image to a registry.

    Args:
        image_name (_type_): _description_
        registry_url (str, optional): _description_. Defaults to "elniak".
        tag (str, optional): _description_. Defaults to "latest".
    """
    try:
        command = f"docker tag {image_name} {registry_url}/{image_name}:{tag}"
        execute_command(command)
        command = f"docker push {registry_url}/{image_name}:{tag}"
        execute_command(command)
        logging.info(f"Pushed image '{image_name}' to registry '{registry_url}'.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error pushing image to registry: {e}")


def restore_hosts_file():
    """_summary_
    Restore the original /etc/hosts file from the backup.
    """
    try:
        execute_command("sudo cp /etc/hosts.bak /etc/hosts")
        logging.info("Restored the original /etc/hosts file.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error restoring /etc/hosts: {e}")


def append_to_hosts_file(entry):
    """_summary_
    Append a new entry to the /etc/hosts file.

    Args:
        entry (_type_): _description_
    """
    try:
        command = f"echo '{entry.strip()}' | sudo tee -a /etc/hosts"
        execute_command(command)
        logging.info(f"Added entry to /etc/hosts: {entry.strip()}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error adding entry to /etc/hosts: {e}")


def network_exists(client, network_name):
    """_summary_
    Check if the Docker network exists.

    Args:
        client (_type_): _description_
        network_name (_type_): _description_

    Returns:
        _type_: _description_
    """
    try:
        client.networks.get(network_name)
        return True
    except NotFound:
        return False
    except Exception as e:
        print(f"Error checking network existence: {e}")
        return False


def create_network(client, network_name, gateway, subnet):
    """_summary_
    Create a Docker network with the specified gateway and subnet.

    Args:
        client (_type_): _description_
        network_name (_type_): _description_
        gateway (_type_): _description_
        subnet (_type_): _description_
    """
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
    """_summary_
    Create the docker network
    """
    network_name = "net"
    gateway = "172.27.1.1"
    subnet = "172.27.1.0/24"

    client = docker.from_env()

    if network_exists(client, network_name):
        print(f"Network '{network_name}' already exists.")
    else:
        create_network(client, network_name, gateway, subnet)
