# PANTHER-SCP/panther/utils/docker_builder.py

import json
import logging
import subprocess
import docker
from docker.errors import DockerException, NotFound, BuildError, APIError
from pathlib import Path
from typing import Any, Dict, Optional, List

import yaml


class DockerBuilder:
    def __init__(self, build_log_file: Optional[Path] = None):
        self.logger = logging.getLogger("DockerBuilder")
        self.build_log_file = build_log_file
        try:
            self.client = docker.from_env()
            self.client.ping()
            self.logger.info("Connected to Docker daemon successfully.")
        except DockerException as e:
            self.logger.error(f"Failed to connect to Docker daemon: {e}")
            raise e

    def log_docker_output(self, generator, task_name: str = "docker command execution", log_f = None) -> None:
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
                    if log_f:
                        log_f.write(f"{output_str}\n")
                    self.logger.info(f"{task_name}: {output_str}")
                elif "error" in output:
                    if log_f:
                        log_f.write(f"{output['error']}\n")
                    raise ValueError(f'Error from {task_name}: {output["error"]}')
                
            except StopIteration:
                self.logger.info(f"{task_name} complete.")
                break
            except ValueError:
                self.logger.error(f"Error parsing output from {task_name}: {output}")


    def build_image(self, impl_name: str, version: str, dockerfile_path: Path, 
                    context_path: Path, config: Dict[str, Any], 
                    tag_version: str = "latest", build_image_force: bool = True) -> Optional[str]:
        """
        Builds a Docker image for a given implementation and version, considering dependencies.

        :param impl_name: Name of the implementation (e.g., 'picoquic').
        :param version: Version identifier (e.g., 'draft_29').
        :param dockerfile_path: Path to the Dockerfile.
        :param context_path: Build context path.
        :param config: Configuration dictionary for the specific version.
        :param tag_version: Tag version for the Docker image.
        :return: Image tag if build is successful, else None.
        """
        image_tag = f"{impl_name}_{version}_panther:{tag_version}"
        self.logger.info(f"Building Docker image '{image_tag}' from '{dockerfile_path}' with context '{context_path}'")

        if self.image_exists(image_tag) and not build_image_force:
            # TODO pass the force flag to the build_image function in the global config
            self.logger.info(f"Docker image '{image_tag}' already exists. Skipping build.")
            return image_tag

        # Extract dependencies
        dependencies = config.get('dependencies', {})
        dependencies_json = json.dumps(dependencies) if dependencies else "[]"

        try:
            build_args = {
                'VERSION': config.get('commit', 'master'),
                'DEPENDENCIES': dependencies_json
            }
            # Open the build log file if specified
            if self.build_log_file:
                with open(self.build_log_file, 'w') as log_f:
                    image, build_logs = self.client.images.build(
                        path=str(context_path),
                        dockerfile=str(dockerfile_path),
                        tag=image_tag,
                        buildargs=build_args,
                        rm=True,
                        network_mode="host",
                        decode=True
                    )
                    self.log_docker_output(build_logs, f"Building Docker image '{image_tag}'", log_f)
            else:
                image, build_logs = self.client.images.build(
                    path=str(context_path),
                    dockerfile=str(dockerfile_path),
                    tag=image_tag,
                    buildargs=build_args,
                    rm=True,
                    network_mode="host",
                )
            self.log_docker_output(build_logs, f"Building Docker image '{image_tag}'")
            self.logger.info(f"Successfully built Docker image '{image_tag}'")
            return image_tag
        except (BuildError, APIError) as e:
            self.logger.error(f"Failed to build Docker image '{image_tag}': {e}")
            if self.build_log_file:
                with open(self.build_log_file, 'a') as log_f:
                    log_f.write(f"ERROR: {e}\n")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during build of '{image_tag}': {e}")
            if self.build_log_file:
                with open(self.build_log_file, 'a') as log_f:
                    log_f.write(f"ERROR: {e}\n")
            return None

    def image_exists(self, image_tag: str) -> bool:
        """
        Checks if a Docker image with the given tag exists locally.

        :param image_tag: Tag of the Docker image.
        :return: True if exists, else False.
        """
        try:
            self.client.images.get(image_tag)
            self.logger.debug(f"Image '{image_tag}' found locally.")
            return True
        except NotFound:
            self.logger.debug(f"Image '{image_tag}' not found locally.")
            return False
        except DockerException as e:
            self.logger.error(f"Error checking if image exists '{image_tag}': {e}")
            return False

    def find_dockerfiles(self, plugins_dir: str) -> Dict[str, Path]:
        """
        Recursively searches for Dockerfiles within the implementations directories.

        :param plugins_dir: Base directory where plugins are located.
        :return: Dictionary mapping implementation names to Dockerfile paths.
        """
        dockerfiles = {}
        self.plugins_dir = plugins_dir  # Store for later use in dependency builds
        implementations_dir = Path(plugins_dir) / "implementations"
        self.logger.info(f"Scanning for Dockerfiles in '{implementations_dir.resolve()}'")

        if not implementations_dir.exists():
            self.logger.warning(f"Implementations directory '{implementations_dir}' does not exist.")
            return dockerfiles

        for impl_dir in implementations_dir.rglob("*"):
            if impl_dir.is_dir():
                dockerfile = impl_dir / "Dockerfile"
                if dockerfile.exists():
                    impl_name = impl_dir.name  # e.g., 'picoquic', 'picotls'
                    dockerfiles[impl_name] = dockerfile.resolve()
                    self.logger.debug(f"Found Dockerfile for implementation '{impl_name}': {dockerfile.resolve()}")

        self.logger.info(f"Total Dockerfiles found: {len(dockerfiles)}")
        return dockerfiles

    def load_config(self, impl_name: str, version: str) -> Optional[Dict[str, Any]]:
        """
        Loads the configuration for a specific implementation and version.

        :param impl_name: Name of the implementation.
        :param version: Version identifier.
        :return: Configuration dictionary if found, else None.
        """
        config_path = Path(self.plugins_dir) / "implementations" / impl_name / "config.yaml"
        if not config_path.exists():
            self.logger.error(f"Configuration file '{config_path}' does not exist for implementation '{impl_name}'.")
            return None

        with open(config_path, 'r') as f:
            full_config = yaml.safe_load(f)

        impl_config = full_config.get(impl_name, {})
        version_config = impl_config.get('versions', {}).get(version, {})
        if not version_config:
            self.logger.error(f"Version '{version}' not found in configuration for implementation '{impl_name}'.")
            return None

        return version_config
    
    def push_image_to_registry(self, image_tag: str, registry_url: str = "elniak", tag: str = "latest") -> bool:
        """
        Pushes a Docker image to a specified registry.

        :param image_tag: Tag of the Docker image to push.
        :param registry_url: URL of the Docker registry.
        :param tag: Tag version for the registry.
        :return: True if push is successful, else False.
        """
        registry_image_tag = f"{registry_url}/{image_tag.split(':')[0]}:{tag}"
        self.logger.info(f"Pushing image '{image_tag}' to registry '{registry_image_tag}'")

        try:
            # Tag the image for the registry
            image = self.client.images.get(image_tag)
            image.tag(registry_image_tag)
            self.logger.debug(f"Tagged image '{image_tag}' as '{registry_image_tag}'")

            # Push the image
            push_logs = self.client.images.push(registry_url, tag=tag, stream=True, decode=True)
            for chunk in push_logs:
                if 'status' in chunk:
                    self.logger.debug(f"Pushing: {chunk['status']}")
                elif 'error' in chunk:
                    self.logger.error(f"Pushing Error: {chunk['error']}")
                    return False
            self.logger.info(f"Successfully pushed image '{registry_image_tag}' to registry.")
            return True
        except (NotFound, DockerException) as e:
            self.logger.error(f"Failed to push image '{image_tag}' to registry: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during push of '{image_tag}': {e}")
            return False

    def list_panther_containers(self) -> List[str]:
        """
        Retrieves a list of all running containers related to Panther.

        :return: List of container names.
        """
        try:
            containers = self.client.containers.list(filters={"name": "panther"})
            container_names = [container.name for container in containers]
            self.logger.debug(f"Panther containers found: {container_names}")
            return container_names
        except DockerException as e:
            self.logger.error(f"Error listing Panther containers: {e}")
            return []

    def container_exists(self, container_name: str) -> bool:
        """
        Checks if a Docker container with the given name exists.

        :param container_name: Name of the Docker container.
        :return: True if exists, else False.
        """
        try:
            self.client.containers.get(container_name)
            self.logger.debug(f"Container '{container_name}' exists.")
            return True
        except NotFound:
            self.logger.debug(f"Container '{container_name}' does not exist.")
            return False
        except DockerException as e:
            self.logger.error(f"Error checking container existence '{container_name}': {e}")
            return False

    def get_container_ip(self, container_name: str) -> Optional[str]:
        """
        Retrieves the IP address of a Docker container.

        :param container_name: Name of the Docker container.
        :return: IP address as a string if found, else None.
        """
        try:
            container = self.client.containers.get(container_name)
            ip_address = container.attrs["NetworkSettings"]["Networks"].values()
            ip = list(ip_address)[0]["IPAddress"]
            self.logger.debug(f"Container '{container_name}' IP address: {ip}")
            return ip
        except (NotFound, KeyError, IndexError) as e:
            self.logger.error(f"Error retrieving IP for container '{container_name}': {e}")
            return None
        except DockerException as e:
            self.logger.error(f"Docker error retrieving IP for container '{container_name}': {e}")
            return None

    def restore_hosts_file(self) -> bool:
        """
        Restores the original /etc/hosts file from a backup.

        :return: True if successful, else False.
        """
        try:
            subprocess.run(
                ["sudo", "cp", "/etc/hosts.bak", "/etc/hosts"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.logger.info("Restored the original /etc/hosts file.")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error restoring /etc/hosts: {e.stderr.decode()}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error restoring /etc/hosts: {e}")
            return False

    def append_to_hosts_file(self, entry: str) -> bool:
        """
        Appends a new entry to the /etc/hosts file.

        :param entry: The entry to append.
        :return: True if successful, else False.
        """
        try:
            subprocess.run(
                ["sudo", "bash", "-c", f"echo '{entry.strip()}' >> /etc/hosts"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.logger.info(f"Added entry to /etc/hosts: {entry.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error adding entry to /etc/hosts: {e.stderr.decode()}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error adding entry to /etc/hosts: {e}")
            return False

    def create_network(self, network_name: str, driver: str = "bridge", subnet: str = "172.27.1.0/24", gateway: str = "172.27.1.1") -> bool:
        """
        Creates a Docker network with specified configurations.

        :param network_name: Name of the Docker network.
        :param driver: Network driver (default: bridge).
        :param subnet: Subnet for the network.
        :param gateway: Gateway for the network.
        :return: True if network is created successfully or already exists, else False.
        """
        try:
            if self.network_exists(network_name):
                self.logger.info(f"Network '{network_name}' already exists.")
                return True

            self.client.networks.create(
                name=network_name,
                driver=driver,
                ipam=docker.types.IPAMConfig(
                    pool_configs=[docker.types.IPAMPool(subnet=subnet, gateway=gateway)]
                )
            )
            self.logger.info(f"Network '{network_name}' created successfully.")
            return True
        except DockerException as e:
            self.logger.error(f"Failed to create network '{network_name}': {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error creating network '{network_name}': {e}")
            return False

    def network_exists(self, network_name: str) -> bool:
        """
        Checks if a Docker network with the given name exists.

        :param network_name: Name of the Docker network.
        :return: True if exists, else False.
        """
        try:
            self.client.networks.get(network_name)
            self.logger.debug(f"Network '{network_name}' exists.")
            return True
        except NotFound:
            self.logger.debug(f"Network '{network_name}' does not exist.")
            return False
        except DockerException as e:
            self.logger.error(f"Error checking network existence '{network_name}': {e}")
            return False

    def get_panther_containers(self) -> List[str]:
        """
        Retrieves a list of all running containers related to Panther.

        :return: List of container names.
        """
        try:
            containers = self.client.containers.list(filters={"name": "panther"})
            container_names = [container.name for container in containers]
            self.logger.debug(f"Panther containers found: {container_names}")
            return container_names
        except DockerException as e:
            self.logger.error(f"Error listing Panther containers: {e}")
            return []

    def stop_and_remove_container(self, container_name: str) -> bool:
        """
        Stops and removes a Docker container.

        :param container_name: Name of the Docker container.
        :return: True if successful, else False.
        """
        try:
            container = self.client.containers.get(container_name)
            container.stop()
            container.remove()
            self.logger.info(f"Stopped and removed container '{container_name}'.")
            return True
        except NotFound:
            self.logger.warning(f"Container '{container_name}' not found.")
            return False
        except DockerException as e:
            self.logger.error(f"Error stopping/removing container '{container_name}': {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error stopping/removing container '{container_name}': {e}")
            return False

    def cleanup_unused_images(self, keep_tags: List[str]):
        """
        Removes Docker images that are not in the keep_tags list.

        :param keep_tags: List of image tags to retain.
        """
        try:
            all_images = self.client.images.list()
            for image in all_images:
                image_tags = image.tags
                # If image has no tags, consider it for removal
                if not image_tags:
                    self.logger.info(f"Removing untagged image '{image.id}'")
                    self.client.images.remove(image.id, force=True)
                    continue

                for tag in image_tags:
                    if tag not in keep_tags:
                        self.logger.info(f"Removing unused Docker image '{tag}'")
                        self.client.images.remove(tag, force=True)
        except DockerException as e:
            self.logger.error(f"Error during Docker image cleanup: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during Docker image cleanup: {e}")
