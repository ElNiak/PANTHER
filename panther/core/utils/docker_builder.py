import json
import logging
import subprocess
import docker
from docker.errors import DockerException, NotFound, BuildError
from pathlib import Path
from typing import Any
import os
from panther.core.exceptions import EnvironmentPluginNotFound, ServicePluginNotFound


class DockerBuilder:
    """
    DockerBuilder is a utility class for managing Docker images and containers. It provides methods to build, push, and manage Docker images and containers, as well as manipulate the /etc/hosts file and Docker networks.
    TODO: use more the docker client API instead of subprocess calls for better error handling and logging.
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

    def __init__(self, build_log_file: bool = False):
        self.plugins_dir = None
        self.logger = logging.getLogger("DockerBuilder")
        self.build_log_file = build_log_file
        self.client = None
        try:
            self.client = docker.from_env()
            self.client.ping()
            self.logger.info("Connected to Docker daemon successfully.")
        except DockerException as e:
            self.logger.error("Failed to connect to Docker daemon: %s", e)
            exit(1)

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
                # Handle both dictionary and string output
                if isinstance(output, dict):
                    if "stream" in output:
                        output_str = output["stream"].strip("\r\n").strip("\n")
                        if log_f:
                            log_f.write(f"{task_name}:{output_str}\n")
                        self.logger.debug("%s: %s", task_name, output_str)
                    elif "error" in output:
                        if log_f:
                            log_f.write(f"{task_name}:{output['error']}\n")
                        self.logger.warning("Error from %s: %s", task_name, output["error"])
                else:
                    # Handle raw output (bytes or string)
                    output_str = str(output).strip("\r\n").strip("\n")
                    if log_f:
                        log_f.write(f"{task_name}:{output_str}\n")
                    self.logger.debug("%s: %s", task_name, output_str)

            except StopIteration:
                self.logger.info("%s complete.", task_name)
                break
            except ValueError:
                self.logger.error("Error parsing output from %s: %s", task_name, output)

    def build_image(
        self,
        impl_name: str,
        version: str,
        dockerfile_path: Path,
        context_path: Path,
        config: dict[str, Any],
        tag_version: str = "latest",
        build_image_force: bool = True,
        remove_dangling: bool = False,
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
        if self.client is None:
            self.logger.error("Docker client is not available. Cannot build Docker image.")
            raise RuntimeError(
                "Docker client is not available. Please check Docker daemon is running."
            )

        image_tag = f"{impl_name}_{version}_panther:{tag_version}"
        self.logger.debug(
            "Building Docker image '%s' from '%s' with context '%s'",
            image_tag,
            dockerfile_path,
            context_path,
        )

        # Check if the image already exists
        existing_image = self.image_exists(image_tag)
        self.logger.debug("Checking if image '%s' exists: %s", image_tag, existing_image)
        if existing_image and not build_image_force:
            # TODO pass the force flag to the build_image function in the global config
            self.logger.info(
                "Docker image '%s' already exists and force rebuild is not enabled. Skipping build.",
                image_tag,
            )
            return image_tag

        # Extract dependencies
        dependencies = config.get("dependencies", {})
        dependencies_json = json.dumps(dependencies) if dependencies else "[]"
        log_f = None
        try:
            # Get username safely - os.getlogin() can fail in some environments
            try:
                username = os.getlogin()
            except (OSError, AttributeError):
                # Fallback to environment variable or default
                username = os.environ.get("USER", os.environ.get("USERNAME", "panther"))
                self.logger.warning("Could not get login username, using fallback: %s", username)

            build_args = {
                "VERSION": config.get("commit", "master"),
                "DEPENDENCIES": dependencies_json,
                "USER_UID": str(os.getuid()),
                "USER_GID": str(os.getgid()),
                "USER_N": username,
            }
            # Open the build log file if specified
            log_f = None
            if self.build_log_file:
                log_filename = image_tag.replace(":", "_").replace("/", "_") + ".log"
                log_f = open(log_filename, "w")

            # Calculate relative path from context to dockerfile for Docker API
            relative_dockerfile_path = Path(dockerfile_path).relative_to(context_path)

            image, build_logs = self.client.images.build(
                path=str(context_path),
                dockerfile=str(relative_dockerfile_path),
                tag=image_tag,
                buildargs=build_args,
                rm=False,  # Remove intermediate containers after build
                network_mode="host",
                platform="linux/amd64",
                # platform="linux/arm64",
                # squash=True,  # Squash layers to reduce image size
            )
            self.log_docker_output(build_logs, f"Building Docker image '{image_tag}'", log_f)
            if log_f:
                log_f.close()
            self.logger.info(
                "Successfully built Docker image '%s' with context '%s' and build args '%s'",
                image_tag,
                context_path,
                build_args,
            )

            # Clean up any dangling images that were created during this build
            if remove_dangling:
                self.logger.info("Removing dangling images after build.")
                self.remove_dangling_images()

            return image_tag
        except BuildError as e:
            self.logger.error("Failed to build Docker image '%s' : %s", image_tag, e)
            if log_f:
                self.log_docker_output(e.build_log, f"Building Docker image '{image_tag}'", log_f)
                log_f.write(f"ERROR: {e}\n")
                log_f.close()
            raise RuntimeError(f"Failed to build Docker image '{image_tag}': {e}")
        except Exception as e:
            self.logger.error("Unexpected error during build of '%s': %s", image_tag, e)
            if log_f:
                log_f.write(f"ERROR: {e}\n")
                log_f.close()
            raise RuntimeError(f"Unexpected error during build of Docker image '{image_tag}': {e}")

    def image_exists(self, image_tag: str) -> bool:
        """
        Checks if a Docker image with the given tag exists locally.

        :param image_tag: Tag of the Docker image.
        :return: True if exists, else False.
        """
        if self.client is None:
            self.logger.error("Docker client is not available. Cannot check if image exists.")
            return False

        try:
            self.logger.debug(
                "Checking if image '%s' exists locally. (Available images %s)",
                image_tag,
                self.client.images.list(),
            )
            self.client.images.get(image_tag)
            self.logger.debug("Image '%s' found locally.", image_tag)
            return True
        except NotFound:
            self.logger.debug("Image '%s' not found locally.", image_tag)
            return False
        except DockerException as e:
            self.logger.error("Error checking if image exists '%s': %s", image_tag, e)
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

        self.logger.info("Scanning for Dockerfiles in '%s'", implementations_dir.resolve())
        print(f"Scanning for Dockerfiles in '{implementations_dir.resolve()}'")
        if not implementations_dir.exists():
            self.logger.warning(
                "Implementations directory '%s' does not exist.", implementations_dir
            )
            raise ServicePluginNotFound(plugin_name="iut")

        for impl_dir in implementations_dir.rglob("*"):
            if impl_dir.is_dir():
                dockerfile = impl_dir / "Dockerfile"
                if dockerfile.exists():
                    impl_name = impl_dir.name  # e.g., 'picoquic', 'picotls'
                    dockerfiles[impl_name] = dockerfile.resolve()
                    self.logger.debug(
                        "Found Dockerfile for implementation '%s': %s",
                        impl_name,
                        dockerfile.resolve(),
                    )

        tester_dir = Path(self.plugins_dir) / "services" / "testers"
        self.logger.info("Scanning for Dockerfiles in '%s'", tester_dir.resolve())
        print(f"Scanning for Dockerfiles in '{tester_dir.resolve()}'")
        if not tester_dir.exists():
            self.logger.warning("Testers directory '%s' does not exist.", tester_dir)
            return dockerfiles

        for impl_dir in tester_dir.rglob("*"):
            if impl_dir.is_dir():
                dockerfile = impl_dir / "Dockerfile"
                if dockerfile.exists():
                    impl_name = impl_dir.name  # e.g., 'picoquic', 'picotls'
                    dockerfiles[impl_name] = dockerfile.resolve()
                    self.logger.debug(
                        "Found Dockerfile for testers '%s': %s", impl_name, dockerfile.resolve()
                    )

        env_dir = Path(plugins_dir) / "environments"
        self.logger.info("Scanning for Dockerfiles in '%s'", env_dir.resolve())
        print(f"Scanning for Dockerfiles in '{env_dir.resolve()}'")
        if not env_dir.exists():
            self.logger.warning("Environment directory '%s' does not exist.", env_dir)
            raise EnvironmentPluginNotFound(plugin_name="environments")

        for impl_dir in env_dir.rglob("*"):
            if impl_dir.is_dir():
                dockerfile = impl_dir / "Dockerfile"
                if dockerfile.exists():
                    impl_name = impl_dir.name  # e.g., 'picoquic', 'picotls'
                    dockerfiles[impl_name] = dockerfile.resolve()
                    self.logger.debug(
                        "Found Dockerfile for environment '%s': %s", impl_name, dockerfile.resolve()
                    )

        self.logger.info("Total Dockerfiles found: %s", len(dockerfiles))
        print(f"Total Dockerfiles found: {len(dockerfiles)}")
        self.logger.debug("Dockerfiles found: %s", dockerfiles)
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
        if self.client is None:
            self.logger.error("Docker client is not available. Cannot push image to registry.")
            return False

        registry_image_tag = f"{registry_url}/{image_tag.split(':')[0]}:{tag}"
        self.logger.info("Pushing image '%s' to registry '%s'", image_tag, registry_image_tag)

        try:
            # Tag the image for the registry
            image = self.client.images.get(image_tag)
            image.tag(registry_image_tag)
            self.logger.debug("Tagged image '%s' as '%s'", image_tag, registry_image_tag)

            # Push the image
            push_logs = self.client.images.push(registry_url, tag=tag, stream=True, decode=True)
            for chunk in push_logs:
                if "status" in chunk:
                    self.logger.debug("Pushing: %s", chunk["status"])
                elif "error" in chunk:
                    self.logger.error("Pushing Error: %s", chunk["error"])
                    return False
            self.logger.info("Successfully pushed image '%s' to registry.", registry_image_tag)
            return True
        except (NotFound, DockerException) as e:
            self.logger.error("Failed to push image '%s' to registry: %s", image_tag, e)
            return False
        except Exception as e:
            self.logger.error("Unexpected error during push of '%s': %s", image_tag, e)
            return False

    def list_panther_containers(self) -> list[str]:
        """
        Retrieves a list of all running containers related to Panther.

        :return: List of container names.
        """
        if self.client is None:
            self.logger.error("Docker client is not available. Cannot list Panther containers.")
            return []

        try:
            containers = self.client.containers.list(filters={"name": "panther"})
            container_names = [container.name for container in containers]
            self.logger.debug("Panther containers found: %s", container_names)
            return container_names
        except DockerException as e:
            self.logger.error("Error listing Panther containers: %s", e)
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
        if self.client is None:
            self.logger.error("Docker client is not available. Cannot check if container exists.")
            return False

        try:
            self.client.containers.get(container_name)
            self.logger.debug("Container '%s' exists.", container_name)
            return True
        except NotFound:
            self.logger.debug("Container '%s' does not exist.", container_name)
            return False
        except DockerException as e:
            self.logger.error("Error checking container existence '%s': %s", container_name, e)
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
        if self.client is None:
            self.logger.error("Docker client is not available. Cannot get container IP.")
            return None

        try:
            container = self.client.containers.get(container_name)
            ip_address = container.attrs["NetworkSettings"]["Networks"].values()
            ip = list(ip_address)[0]["IPAddress"]
            self.logger.debug("Container '%s' IP address: %s", container_name, ip)
            return ip
        except (NotFound, KeyError, IndexError) as e:
            self.logger.error("Error retrieving IP for container '%s': %s", container_name, e)
            return None
        except DockerException as e:
            self.logger.error(
                "Docker error retrieving IP for container '%s': %s", container_name, e
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
            self.logger.error("Error restoring /etc/hosts: %s", e.stderr.decode())
            return False
        except Exception as e:
            self.logger.error("Unexpected error restoring /etc/hosts: %s", e)
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
            self.logger.info("Added entry to /etc/hosts: %s", entry.strip())
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error("Error adding entry to /etc/hosts: %s", e.stderr.decode())
            return False
        except Exception as e:
            self.logger.error("Unexpected error adding entry to /etc/hosts: %s", e)
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
        if self.client is None:
            self.logger.error("Docker client is not available. Cannot create network.")
            return False

        try:
            if self.network_exists(network_name):
                self.logger.info("Network '%s' already exists.", network_name)
                return True

            self.client.networks.create(
                name=network_name,
                driver=driver,
                ipam=docker.service_types.IPAMConfig(
                    pool_configs=[docker.service_types.IPAMPool(subnet=subnet, gateway=gateway)]
                ),
            )
            self.logger.info("Network '%s' created successfully.", network_name)
            return True
        except DockerException as e:
            self.logger.error("Failed to create network '%s': %s", network_name, e)
            return False
        except Exception as e:
            self.logger.error("Unexpected error creating network '%s': %s", network_name, e)
            return False

    def network_exists(self, network_name: str) -> bool:
        """
        Check if a Docker network exists.
        Args:zdzd
            network_name (str): The name of the Docker network to check.
        Returns:
            bool: True if the network exists, False otherwise.
        Logs:
            Debug: Logs whether the network exists or not.
            Error: Logs any DockerException encountered during the check.
        """
        if self.client is None:
            self.logger.error("Docker client is not available. Cannot check if network exists.")
            return False

        try:
            self.client.networks.get(network_name)
            self.logger.debug("Network '%s' exists.", network_name)
            return True
        except NotFound:
            self.logger.debug("Network '%s' does not exist.", network_name)
            return False
        except DockerException as e:
            self.logger.error("Error checking network existence '%s': %s", network_name, e)
            return False

    def get_panther_containers(self) -> list[str]:
        """
        Retrieves a list of all running containers related to Panther.

        Returns:
            List of container names.
        """
        if self.client is None:
            self.logger.error("Docker client is not available. Cannot get Panther containers.")
            return []

        try:
            containers = self.client.containers.list(filters={"name": "panther"})
            container_names = [container.name for container in containers]
            self.logger.debug("Panther containers found: %s", container_names)
            return container_names
        except DockerException as e:
            self.logger.error("Error listing Panther containers: %s", e)
            return []

    def stop_and_remove_container(self, container_name: str) -> bool:
        """
        Stops and removes a Docker container.

        :param container_name: Name of the Docker container.
        :return: True if successful, else False.
        """
        if self.client is None:
            self.logger.error("Docker client is not available. Cannot stop and remove container.")
            return False

        try:
            container = self.client.containers.get(container_name)
            container.stop()
            container.remove()
            self.logger.info("Stopped and removed container '%s'.", container_name)
            return True
        except NotFound:
            self.logger.warning("Container '%s' not found.", container_name)
            return False
        except DockerException as e:
            self.logger.error("Error stopping/removing container '%s': %s", container_name, e)
            return False
        except Exception as e:
            self.logger.error(
                "Unexpected error stopping/removing container '%s': %s", container_name, e
            )
            return False

    def cleanup_unused_images(self, keep_tags: list[str]):
        """
        Removes Docker images that are not in the keep_tags list.

        :param keep_tags: List of image tags to retain.
        """
        if self.client is None:
            self.logger.error("Docker client is not available. Cannot cleanup unused images.")
            return

        try:
            all_images = self.client.images.list()
            for image in all_images:
                image_tags = image.tags
                # If image has no tags, consider it for removal
                if not image_tags:
                    self.logger.info("Removing untagged image '%s'", image.id)
                    self.client.images.remove(image.id, force=True)
                    continue

                for tag in image_tags:
                    if tag not in keep_tags:
                        self.logger.info("Removing unused Docker image '%s'", tag)
                        self.client.images.remove(tag, force=True)
        except DockerException as e:
            self.logger.error("Error during Docker image cleanup: %s", e)
        except Exception as e:
            self.logger.error("Unexpected error during Docker image cleanup: %s", e)

    def remove_dangling_images(self):
        """
        Removes dangling Docker images (images with <none>:<none> tag).

        These images are typically created when building a new image with the same tag
        as an existing one, causing the original image to lose its tag.

        Returns:
            bool: True if successful, False if an error occurred
        """
        if self.client is None:
            self.logger.error("Docker client is not available. Cannot remove dangling images.")
            return False

        try:
            # Get a list of all dangling images
            dangling_images = self.client.images.list(filters={"dangling": True})

            if not dangling_images:
                self.logger.debug("No dangling images found to remove.")
                return True

            # Remove each dangling image
            for image in dangling_images:
                self.logger.info("Removing dangling image %s", image.id[:12])
                self.client.images.remove(image.id, force=False)

            self.logger.info("Successfully removed %s dangling images", len(dangling_images))
            return True
        except DockerException as e:
            self.logger.error("Error removing dangling images: %s", e)
            return False
        except OSError as e:
            self.logger.error("Unexpected error removing dangling images: %s", e)
            return False
