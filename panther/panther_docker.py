import logging
import docker
from docker.errors import NotFound
import subprocess
import time
from panther_cli import execute_command


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

def get_panther_container():
    client = docker.from_env()
    panther_containers = []
    for container in client.containers.list():
        if "panther" in container.name:
            panther_containers.append(container.name)
    return panther_containers

def push_image_to_registry(image_name, registry_url="elniak", tag="latest"):
    """Push a Docker image to a registry."""
    try:
        command = f"docker tag {image_name} {registry_url}/{image_name}:{tag}"
        execute_command(command)
        command = f"docker push {registry_url}/{image_name}:{tag}"
        execute_command(command)
        logging.info(f"Pushed image '{image_name}' to registry '{registry_url}'.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error pushing image to registry: {e}")

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


def monitor_docker_usage(docker_to_monitor, interval=1.0, duration=10.0):
    """
    Monitor the CPU and memory usage of a Docker container.

    :param container_name: Name or ID of the Docker container to monitor
    :param interval: Time interval (in seconds) between checks
    :param duration: Total duration (in seconds) to monitor
    """
    client = docker.from_env()

    for container_name in docker_to_monitor:
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
        execute_command("clear")
        for container_name in docker_to_monitor:
            try:
                container = client.containers.get(container_name)

                stats = container.stats(stream=False)

                # Check for missing keys and default to 0 if missing
                cpu_delta = stats["cpu_stats"]["cpu_usage"].get(
                    "total_usage", 0
                ) - stats["precpu_stats"]["cpu_usage"].get("total_usage", 0)
                system_cpu_delta = stats["cpu_stats"].get(
                    "system_cpu_usage", 0
                ) - stats["precpu_stats"].get("system_cpu_usage", 0)
                number_cpus = len(
                    stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [])
                )
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
                    f"Name {container_name}\n\t - Time: {time.time() - start_time:.2f}s\n\t - CPU Usage: {cpu_usage:.2f}%\n\t - Memory Usage: {memory_usage:.2f}MB ({memory_percentage:.2f}%)"
                )
            except docker.errors.APIError as e:
                logging.error(f"An error occurred: {e}")
                break
            except KeyError as e:
                logging.warning(f"Missing key in stats: {e}")
        time.sleep(interval)

