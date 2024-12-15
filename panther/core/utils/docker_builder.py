import json
import logging
import subprocess
import docker
from docker.errors import DockerException, NotFound, BuildError
from pathlib import Path
from typing import Any
import os
from panther.core.exceptions import EnvironmentPluginNotFound, ServicePluginNotFound
from importlib_resources import files

class DockerBuilder:
    """
    DockerBuilder is a utility class for managing Docker images and containers. It provides methods to build, push, and manage Docker images and containers, as well as manipulate the /etc/hosts file and Docker networks.

    Methods:
        __init__(self, build_log_file: Path | None = None):
            Initializes the DockerBuilder instance, sets up logging, and connects to the Docker daemon.

        log_docker_output(self, generator, task_name: str = "docker command execution", log_f=None) -> None:
            Logs the output of Docker commands.

        build_image(self, impl_name: str, version: str, dockerfile_path: Path, context_path: Path, config: dict[str, Any], tag_version: str = "latest", build_image_force: bool = False) -> str | None:
            Builds a Docker image for the specified implementation.

        image_exists(self, image_tag: str) -> bool:

        find_dockerfiles(self, plugins_dir: str) -> dict[str, Path]:

        push_image_to_registry(self, image_tag: str, registry_url: str = "elniak", tag: str = "latest") -> bool:

        list_panther_containers(self) -> list[str]:

        container_exists(self, container_name: str) -> bool:

        get_container_ip(self, container_name: str) -> str | None:

        restore_hosts_file(self) -> bool:

        append_to_hosts_file(self, entry: str) -> bool:

        create_network(self, network_name: str, driver: str = "bridge", subnet: str = "172.27.1.0/24", gateway: str = "172.27.1.1") -> bool:

        network_exists(self, network_name: str) -> bool:

        get_panther_containers(self) -> list[str]:

        stop_and_remove_container(self, container_name: str) -> bool:

        cleanup_unused_images(self, keep_tags: list[str]):
    """
    def __init__(self, build_log_file: Path | None = None):
        self.plugins_dir = None
        self.logger = logging.getLogger("DockerBuilder")
        self.build_log_file = build_log_file
        try:
            self.client = docker.from_env()
            self.client.ping()
            self.logger.info("Connected to Docker daemon successfully.")
        except DockerException as e:
            self.logger.error(f"Failed to connect to Docker daemon: {e}")
            raise e

    def log_docker_output(
        self, generator, task_name: str = "docker command execution", log_f=None
    ) -> None:
        """
        Logs the output of a Docker command execution.
        This method processes the output from a generator that yields Docker command
        execution results. It logs the output to a specified log file and the logger.
        Args:
            generator (Generator): A generator that yields Docker command execution results.
            task_name (str, optional): The name of the task being executed. Defaults to "docker command execution".
            log_f (file object, optional): A file object to write log output to. Defaults to None.
        Raises:
            ValueError: If an error is encountered in the Docker command execution output.
        """
        output = None
        while True:
            try:
                output = generator.__next__()
                if "stream" in output:
                    output_str = output["stream"].strip("\r\n").strip("\n")
                    if log_f:
                        log_f.write(f"{task_name}:{output_str}\n")
                    self.logger.debug(f"{task_name}: {output_str}")
                elif "error" in output:
                    if log_f:
                        log_f.write(f"{task_name}:{output['error']}\n")
                    self.logger.error(f"Error from {task_name}: {output['error']}")
                    raise ValueError(f'Error from {task_name}: {output["error"]}')

            except StopIteration:
                self.logger.info(f"{task_name} complete.")
                break
            except ValueError:
                self.logger.error(f"Error parsing output from {task_name}: {output}")

    def build_image(
        self,
        impl_name: str,
        version: str,
        dockerfile_path: Path,
        context_path: Path,
        config: dict[str, Any],
        tag_version: str = "latest",
        build_image_force: bool = True, 
    ) -> str | None:
        """
        Build a Docker image for the specified implementation.
        Args:
            impl_name (str): The name of the implementation.
            version (str): The version of the implementation.
            dockerfile_path (Path): The path to the Dockerfile.
            context_path (Path): The path to the build context.
            config (dict[str, Any]): Configuration dictionary containing build parameters.
            tag_version (str, optional): The tag version for the Docker image. Defaults to "latest".
            build_image_force (bool, optional): Force rebuild of the Docker image even if it already exists. Defaults to False.
        Returns:
            str | None: The tag of the built Docker image, or None if the build was skipped.
        """
        image_tag = f"{impl_name}_{version}_panther:{tag_version}"
        self.logger.debug(
            f"Building Docker image '{image_tag}' from '{dockerfile_path}' with context '{context_path}'"
        )

        if self.image_exists(image_tag) and not build_image_force:
            # TODO pass the force flag to the build_image function in the global config
            self.logger.info(
                f"Docker image '{image_tag}' already exists. Skipping build."
            )
            return image_tag

        # Extract dependencies
        dependencies = config.get("dependencies", {})
        dependencies_json = json.dumps(dependencies) if dependencies else "[]"
        log_f = None
        try:
            build_args = {
                "VERSION": config.get("commit", "master"),
                "DEPENDENCIES": dependencies_json,
                "USER_UID": str(os.getuid()),
                "USER_GID": str(os.getgid()),
                "USER_N": os.getlogin(),
            }
            # Open the build log file if specified
            if self.build_log_file:
                with open(self.build_log_file, "w") as log_f:
                    image, build_logs = self.client.images.build(
                        path=str(context_path),
                        dockerfile=str(dockerfile_path),
                        tag=image_tag,
                        buildargs=build_args,
                        rm=True,
                        network_mode="host",
                        decode=True,
                    )
                    self.log_docker_output(
                        build_logs, f"Building Docker image '{image_tag}'", log_f
                    )
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
            self.logger.info(
                f"Successfully built Docker image '{image_tag}' with context '{context_path}' and build args '{build_args}'"
            )
            return image_tag
        except BuildError as e:
            self.logger.error(f"Failed to build Docker image '{image_tag}' : {e}")
            self.log_docker_output(
                e.build_log, f"Building Docker image '{image_tag}'", log_f
            )
            if self.build_log_file:
                with open(self.build_log_file, "a") as log_f:
                    log_f.write(f"ERROR: {e}\n")
            exit(1)
        except Exception as e:
            self.logger.error(f"Unexpected error during build of '{image_tag}': {e}")
            if self.build_log_file:
                with open(self.build_log_file, "a") as log_f:
                    log_f.write(f"ERROR: {e}\n")
            exit(1)

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

    def find_dockerfiles(self, plugins_dir: str) -> dict[str, Path]:
        """
        Scans the specified plugins directory and its subdirectories for Dockerfiles.
        This method searches for Dockerfiles in three main locations within the plugins directory:
        - services/iut
        - services/testers
        - environments
        For each Dockerfile found, it adds an entry to the returned dictionary with the implementation
        name as the key and the resolved path to the Dockerfile as the value.
        Args:
            plugins_dir (str): The path to the plugins directory to scan for Dockerfiles.
        Returns:
            dict[str, Path]: A dictionary where keys are implementation names and values are paths to the Dockerfiles.
        Raises:
            ServicePluginNotFound: If the 'services/iut' directory does not exist.
            EnvironmentPluginNotFound: If the 'environments' directory does not exist.
        """
        
        dockerfiles = {}
        self.plugins_dir = str(plugins_dir)  # Store for later use in dependency builds

        # implementations_dir =  Path(os.path.dirname(__file__)) / Path(plugins_dir) / "services" / "iut"
        implementations_dir = Path(self.plugins_dir) / "services" / "iut"

        self.logger.info(
            f"Scanning for Dockerfiles in '{implementations_dir.resolve()}'"
        )
        print(f"Scanning for Dockerfiles in '{implementations_dir.resolve()}'")
        if not implementations_dir.exists():
            self.logger.warning(
                f"Implementations directory '{implementations_dir}' does not exist."
            )
            raise ServicePluginNotFound()

        for impl_dir in implementations_dir.rglob("*"):
            if impl_dir.is_dir():
                dockerfile = impl_dir / "Dockerfile"
                if dockerfile.exists():
                    impl_name = impl_dir.name  # e.g., 'picoquic', 'picotls'
                    dockerfiles[impl_name] = dockerfile.resolve()
                    self.logger.debug(
                        f"Found Dockerfile for implementation '{impl_name}': {dockerfile.resolve()}"
                    )

        tester_dir = Path(self.plugins_dir) / "services" / "testers"
        self.logger.info(f"Scanning for Dockerfiles in '{tester_dir.resolve()}'")
        print(f"Scanning for Dockerfiles in '{tester_dir.resolve()}'")
        if not tester_dir.exists():
            self.logger.warning(f"Testers directory '{tester_dir}' does not exist.")
            return dockerfiles

        for impl_dir in tester_dir.rglob("*"):
            if impl_dir.is_dir():
                dockerfile = impl_dir / "Dockerfile"
                if dockerfile.exists():
                    impl_name = impl_dir.name  # e.g., 'picoquic', 'picotls'
                    dockerfiles[impl_name] = dockerfile.resolve()
                    self.logger.debug(
                        f"Found Dockerfile for testers '{impl_name}': {dockerfile.resolve()}"
                    )

        env_dir = Path(plugins_dir) / "environments"
        self.logger.info(f"Scanning for Dockerfiles in '{env_dir.resolve()}'")
        print(f"Scanning for Dockerfiles in '{env_dir.resolve()}'")
        if not env_dir.exists():
            self.logger.warning(f"Environment directory '{env_dir}' does not exist.")
            raise EnvironmentPluginNotFound()

        for impl_dir in env_dir.rglob("*"):
            if impl_dir.is_dir():
                dockerfile = impl_dir / "Dockerfile"
                if dockerfile.exists():
                    impl_name = impl_dir.name  # e.g., 'picoquic', 'picotls'
                    dockerfiles[impl_name] = dockerfile.resolve()
                    self.logger.debug(
                        f"Found Dockerfile for environment '{impl_name}': {dockerfile.resolve()}"
                    )

        self.logger.info(f"Total Dockerfiles found: {len(dockerfiles)}")
        print(f"Total Dockerfiles found: {len(dockerfiles)}")
        self.logger.debug(f"Dockerfiles found: {dockerfiles}")
        print(f"Dockerfiles found: {dockerfiles}")
        return dockerfiles

    def push_image_to_registry(
        self, image_tag: str, registry_url: str = "elniak", tag: str = "latest"
    ) -> bool:
        """
        Pushes a Docker image to a specified registry.
        Args:
            image_tag (str): The tag of the image to be pushed.
            registry_url (str, optional): The URL of the registry to push the image to. Defaults to "elniak".
            tag (str, optional): The tag to apply to the image in the registry. Defaults to "latest".
        Returns:
            bool: True if the image was successfully pushed, False otherwise.
        Logs:
            - Info: When starting to push the image and upon successful push.
            - Debug: When tagging the image and during the push process.
            - Error: If there is an error during the push process.
        """
        registry_image_tag = f"{registry_url}/{image_tag.split(':')[0]}:{tag}"
        self.logger.info(
            f"Pushing image '{image_tag}' to registry '{registry_image_tag}'"
        )

        try:
            # Tag the image for the registry
            image = self.client.images.get(image_tag)
            image.tag(registry_image_tag)
            self.logger.debug(f"Tagged image '{image_tag}' as '{registry_image_tag}'")

            # Push the image
            push_logs = self.client.images.push(
                registry_url, tag=tag, stream=True, decode=True
            )
            for chunk in push_logs:
                if "status" in chunk:
                    self.logger.debug(f"Pushing: {chunk['status']}")
                elif "error" in chunk:
                    self.logger.error(f"Pushing Error: {chunk['error']}")
                    return False
            self.logger.info(
                f"Successfully pushed image '{registry_image_tag}' to registry."
            )
            return True
        except (NotFound, DockerException) as e:
            self.logger.error(f"Failed to push image '{image_tag}' to registry: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during push of '{image_tag}': {e}")
            return False

    def list_panther_containers(self) -> list[str]:
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
        Check if a Docker container with the given name exists.
        Args:
            container_name (str): The name of the Docker container to check.
        Returns:
            bool: True if the container exists, False otherwise.
        Raises:
            DockerException: If there is an error while checking the container existence.
        """
        
        try:
            self.client.containers.get(container_name)
            self.logger.debug(f"Container '{container_name}' exists.")
            return True
        except NotFound:
            self.logger.debug(f"Container '{container_name}' does not exist.")
            return False
        except DockerException as e:
            self.logger.error(
                f"Error checking container existence '{container_name}': {e}"
            )
            return False

    def get_container_ip(self, container_name: str) -> str | None:
        """
        Retrieve the IP address of a Docker container by its name.
        Args:
            container_name (str): The name of the Docker container.
        Returns:
            str | None: The IP address of the container if found, otherwise None.
        Logs:
            Debug: Logs the IP address of the container if successfully retrieved.
            Error: Logs an error message if the container is not found, or if there is an issue retrieving the IP address.
        """
        try:
            container = self.client.containers.get(container_name)
            ip_address = container.attrs["NetworkSettings"]["Networks"].values()
            ip = list(ip_address)[0]["IPAddress"]
            self.logger.debug(f"Container '{container_name}' IP address: {ip}")
            return ip
        except (NotFound, KeyError, IndexError) as e:
            self.logger.error(
                f"Error retrieving IP for container '{container_name}': {e}"
            )
            return None
        except DockerException as e:
            self.logger.error(
                f"Docker error retrieving IP for container '{container_name}': {e}"
            )
            return None

    def restore_hosts_file(self) -> bool:
        """
        Restores the original /etc/hosts file from a backup.
        This method attempts to copy the backup file /etc/hosts.bak to /etc/hosts
        using the `sudo cp` command. If the operation is successful, it logs an
        informational message and returns True. If there is an error during the
        process, it logs an error message and returns False.
        Returns:
            bool: True if the /etc/hosts file was successfully restored, False otherwise.
        Raises:
            subprocess.CalledProcessError: If the subprocess command fails.
            Exception: For any other unexpected errors.
        """
        
        try:
            subprocess.run(
                ["sudo", "cp", "/etc/hosts.bak", "/etc/hosts"],
                check=True,
                capture_output=True,
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
        Appends a given entry to the /etc/hosts file.
        This method uses a subprocess to run a command that appends the provided entry
        to the /etc/hosts file. It requires sudo privileges to execute the command.
        Args:
            entry (str): The entry to be added to the /etc/hosts file.
        Returns:
            bool: True if the entry was successfully added, False otherwise.
        Raises:
            subprocess.CalledProcessError: If the subprocess command fails.
            Exception: For any other unexpected errors.
        """
        
        try:
            subprocess.run(
                ["sudo", "bash", "-c", f"echo '{entry.strip()}' >> /etc/hosts"],
                check=True,
                capture_output=True,
            )
            self.logger.info(f"Added entry to /etc/hosts: {entry.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error adding entry to /etc/hosts: {e.stderr.decode()}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error adding entry to /etc/hosts: {e}")
            return False

    def create_network(
        self,
        network_name: str,
        driver: str = "bridge",
        subnet: str = "172.27.1.0/24",
        gateway: str = "172.27.1.1",
    ) -> bool:
        """
        Creates a Docker network with the specified parameters.
        Args:
            network_name (str): The name of the network to create.
            driver (str, optional): The network driver to use. Defaults to "bridge".
            subnet (str, optional): The subnet for the network. Defaults to "172.27.1.0/24".
            gateway (str, optional): The gateway for the network. Defaults to "172.27.1.1".
        Returns:
            bool: True if the network was created successfully or already exists, False otherwise.
        Raises:
            DockerException: If there is an error creating the network.
            Exception: If there is an unexpected error.
        """
        try:
            if self.network_exists(network_name):
                self.logger.info(f"Network '{network_name}' already exists.")
                return True

            self.client.networks.create(
                name=network_name,
                driver=driver,
                ipam=docker.service_types.IPAMConfig(
                    pool_configs=[
                        docker.service_types.IPAMPool(subnet=subnet, gateway=gateway)
                    ]
                ),
            )
            self.logger.info(f"Network '{network_name}' created successfully.")
            return True
        except DockerException as e:
            self.logger.error(f"Failed to create network '{network_name}': {e}")
            return False
        except Exception as e:
            self.logger.error(
                f"Unexpected error creating network '{network_name}': {e}"
            )
            return False

    def network_exists(self, network_name: str) -> bool:
        """
        Check if a Docker network exists.
        Args:
            network_name (str): The name of the Docker network to check.
        Returns:
            bool: True if the network exists, False otherwise.
        Logs:
            Debug: Logs whether the network exists or not.
            Error: Logs any DockerException encountered during the check.
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

    def get_panther_containers(self) -> list[str]:
        """
        Retrieves a list of all running containers related to Panther.

        Returns:
            List of container names.
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
            self.logger.error(
                f"Error stopping/removing container '{container_name}': {e}"
            )
            return False
        except Exception as e:
            self.logger.error(
                f"Unexpected error stopping/removing container '{container_name}': {e}"
            )
            return False

    def cleanup_unused_images(self, keep_tags: list[str]):
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
