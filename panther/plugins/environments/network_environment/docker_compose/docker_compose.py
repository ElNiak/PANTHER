import os
from pathlib import Path
import subprocess
from panther.utils.command import ShellCommand
from panther.core.observer.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
import traceback


class DockerComposeEnvironment(INetworkEnvironment):
    """
    DockerComposeEnvironment is a class that manages the setup, deployment, monitoring, and teardown of a
    Docker Compose environment.

    Attributes:
        services_network_config_file_path (Path): Path to the generated Docker Compose configuration file.
        rendered_services_network_config_file_path (Path): Path to the rendered Docker Compose configuration file.
    Methods:
        __init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
            Initializes the DockerComposeEnvironment with the given configuration and paths.
        __str__():
            Returns a string representation of the DockerComposeEnvironment instance.
        __repr__():
            Returns a string representation of the DockerComposeEnvironment instance.
        setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader, execution_environment):
        prepare_environment():
            Prepares the environment (currently not implemented).
        deploy_services():
            Deploys the services defined in the Docker Compose environment.
        generate_environment_services(paths, timestamp):
        launch_environment_services():
        monitor_environment():
        teardown_environment():
    """

    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager)
        self.services_network_config_file_path = Path(
            os.path.join(
                self._plugin_dir,
                env_type,
                env_sub_type,
                f"{env_sub_type}.generated.yml",
            )
        )
        self.rendered_services_network_config_file_path = Path(
            os.path.join(self.output_dir, f"{env_sub_type}.yml")
        )

        self.services_network_script_file_path = Path(
            os.path.join(
                self._plugin_dir,
                env_type,
                env_sub_type,
                "entrypoint.generated.sh",
            )
        )
        self.rendered_services_network_script_file_path = Path(
            os.path.join(self.output_dir, "entrypoint.sh")
        )

    def __str__(self):
        return f"DockerComposeEnvironment({self.__dict__})"

    def __repr__(self):
        return f"DockerComposeEnvironment({self.__dict__})"

    def setup_environment(
        self,
        services_managers: list[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_loader: PluginLoader,
        execution_environment: list[IExecutionEnvironment],
    ):
        """
        Sets up the Docker Compose environment by generating the docker-compose.yml file with deployment commands.
        """
        self.update_environment(
            execution_environment,
            global_config,
            plugin_loader,
            services_managers,
            test_config,
        )
        self.notify_environment_setup_started(details={"environment_instance": self})
        self.generate_environment_services(paths=self.global_config.paths, timestamp=timestamp)
        self.logger.info("Docker Compose environment setup complete")

    def prepare_environment(self):
        pass

    def deploy_services(self):
        self.logger.info("Deploying services")
        self.launch_environment_services()

    def generate_environment_services(self, paths: dict[str, str], timestamp: str):
        """
        Generates the docker-compose.yml file using the provided services and deployment commands.

        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        try:
            # Ensure the log directory for each service exists
            self.setup_execution_plugins(timestamp)

            for service in self.services_managers:
                # TODO: move this to the service manager
                self.create_log_dir(service)
                self.logger.debug("Generating Docker Compose file for %s", service.service_name)

                if "ivy" in service.service_name:
                    self.logger.debug(
                        "Adding wait for Ivy testers to be ready for %s", service.service_name
                    )
                    for other_service in self.services_managers:
                        if other_service.service_name != service.service_name:
                            self.wait_tester_command(other_service)

            for service in self.services_managers:
                self.tshark_command(service)

            for service in self.services_managers:
                service.environments = self.resolve_environment_variables(service.environments)
                self.logger.debug(
                    "Service %s environment: %s", service.service_name, service.environments
                )

            for service in self.services_managers:
                # Add debugging to declared functions in run_cmds (if any)
                for cmd_key, cmds in service.run_cmd.items():
                    self.logger.debug(
                        "Service %s command key: %s - %s", service.service_name, cmd_key, cmds
                    )

                    self.logger.debug(
                        "Service %s command key: %s - %s",
                        service.service_name,
                        cmd_key,
                        service.run_cmd[cmd_key],
                    )

            for service in self.services_managers:
                self.logger.debug(
                    "Generating entrypoint script for service %s", service.service_name
                )
                # Use the specialized method for entrypoint generation that handles structured commands
                self.generate_entrypoint_with_structured_args(
                    service,
                    paths,
                    timestamp,
                    Path(
                        str(self.rendered_services_network_script_file_path).replace(
                            ".sh", f"_{service.service_name}.sh"
                        )
                    ),
                    Path(
                        str(self.services_network_script_file_path).replace(
                            ".sh", f"_{service.service_name}.sh"
                        )
                    ),
                )

            self.generate_from_template(
                "docker-compose-template.jinja",
                paths,
                timestamp,
                self.rendered_services_network_config_file_path,
                self.services_network_config_file_path,
            )

            # Delete the file self.services_network_script_file_path
            if self.services_network_script_file_path.exists():
                self.services_network_script_file_path.unlink()
                self.logger.debug("Deleted the file %s", self.services_network_script_file_path)

            self.logger.info(
                "Docker Compose file generated at '%s'",
                self.rendered_services_network_config_file_path,
            )
        except Exception as e:
            self.logger.error(
                "Failed to generate Docker Compose file: %s\n%s", e, traceback.format_exc()
            )
            exit(1)

    def tshark_command(self, service):
        service.run_cmd["post_compile_cmds"] = service.run_cmd["post_compile_cmds"] + [
            "(touch /app/logs/"
            + service.service_name
            + ".pcap; tshark -a duration:"
            + str(service.service_config_to_test.timeout)
            + " -i any -w /app/logs/"
            + service.service_name
            + ".pcap;) & "
        ]

    def wait_tester_command(self, other_service):
        other_service.volumes.append("shared_logs:/app/sync_logs")
        other_service.run_cmd["post_compile_cmds"] = other_service.run_cmd["post_compile_cmds"] + [
            "while [ ! -f /app/sync_logs/ivy_ready.log ]; do",
            '\techo "Waiting for Ivy testers to be ready..." >> /app/logs/tester_ready.log;',
            "\tsleep 2;",
            "done;",
            'echo "Ivy testers is ready, starting '
            + other_service.service_name
            + '..." >> /app/logs/tester_ready.log;',
        ]

    def _combine_shell_constructs(self, command_list):
        """
        Combine consecutive elements in a command list that form a single shell construct.

        This function detects shell constructs like loops, functions, and conditional blocks
        that are split across multiple list elements and combines them into a single
        multiline command string. This is necessary because shell constructs that span
        multiple lines need to be treated as a single command unit rather than individual
        commands.

        Supported shell constructs:
        - while/done loops
        - for/done loops
        - if/fi conditionals
        - case/esac statements
        - function definitions

        Example:
            Input: ['for i in 1 2 3; do', 'echo $i', 'done']
            Output: ['for i in 1 2 3; do\necho $i\ndone']

        Args:
            command_list: List of command strings or ShellCommand objects to process

        Returns:
            A new list with combined shell constructs as multiline strings or ShellCommand objects.
            Returns an empty list if the input is empty or invalid.
        """
        # Input validation
        if not command_list:
            self.logger.debug("Empty command list provided to _combine_shell_constructs")
            return []

        if not isinstance(command_list, list):
            self.logger.warning(
                "Invalid command_list type provided to _combine_shell_constructs: %s",
                type(command_list),
            )
            return []

        # Filter out empty entries and process both string and ShellCommand objects
        filtered_commands = []
        original_objects = []  # Keep track of original objects

        for cmd in command_list:
            if not cmd:
                continue

            if isinstance(cmd, str):
                if cmd.strip():
                    filtered_commands.append(cmd)
                    original_objects.append(None)  # No original object for strings
            elif isinstance(cmd, ShellCommand):
                # Handle ShellCommand objects by extracting their command string
                if cmd.command and cmd.command.strip():
                    filtered_commands.append(cmd.command)
                    original_objects.append(cmd)  # Store the original ShellCommand

        if not filtered_commands:
            self.logger.debug("No valid commands found in command_list after filtering")
            return []

        # Use filtered commands for processing
        self.logger.debug(
            "Processing %d commands in shell construct combination", len(filtered_commands)
        )

        # Track shell constructs we're looking for
        construct_patterns = {
            "while": {
                "start": ["while"],
                "end": ["done"],
                "patterns": [
                    # while condition; do
                    lambda s: s.strip()
                    .lower()
                    .startswith("while "),
                ],
            },
            "for": {
                "start": ["for"],
                "end": ["done"],
                "patterns": [
                    # for var in list; do
                    lambda s: s.strip()
                    .lower()
                    .startswith("for "),
                ],
            },
            "if": {
                "start": ["if"],
                "end": ["fi"],
                "patterns": [
                    # if condition; then
                    lambda s: s.strip()
                    .lower()
                    .startswith("if "),
                ],
            },
            "case": {
                "start": ["case"],
                "end": ["esac"],
                "patterns": [
                    # case var in
                    lambda s: s.strip()
                    .lower()
                    .startswith("case "),
                ],
            },
            "function": {
                "start": ["function", "() {", "(){"],
                "end": ["}"],
                # Additional patterns to identify function definitions
                "patterns": [
                    # function name() { ... }
                    lambda s: s.strip().lower().startswith("function ")
                    and ("() {" in s or "(){" in s),
                    # name() { ... }
                    lambda s: ("() {" in s or "(){" in s)
                    and not s.strip().lower().startswith("function "),
                    # function name { ... }
                    lambda s: s.strip().lower().startswith("function ") and "{" in s,
                ],
            },
        }

        result = []
        construct_buffer = []
        construct_buffer_originals = []  # Track original objects for buffered commands
        active_constructs = []

        for i, cmd in enumerate(filtered_commands):
            # Skip empty commands (should not happen after filtering)
            if not cmd or not cmd.strip():
                continue

            cmd_lower = cmd.lower().strip()
            first_word = cmd_lower.split()[0] if cmd_lower.split() else ""

            # Check if this line starts a new construct
            starts_construct = False
            for construct, patterns in construct_patterns.items():
                # First check for explicit patterns if defined
                if "patterns" in patterns:
                    for pattern_func in patterns["patterns"]:
                        if pattern_func(cmd):
                            starts_construct = True
                            active_constructs.append(construct)
                            self.logger.debug(
                                "Starting %s construct (pattern match): %s",
                                construct,
                                cmd.strip()[:40],
                            )
                            break
                    if starts_construct:
                        break

                # Then check for start keywords
                if not starts_construct and any(p in cmd_lower for p in patterns["start"]):
                    # For function definitions
                    if construct == "function":
                        # Check for the two common function definition styles:
                        # 1. function name() { ... }
                        # 2. name() { ... }
                        if (
                            "function " in cmd_lower
                            or (
                                any(
                                    cmd_lower.find(f"{c}") > -1
                                    for c in ["() {", "(){", "()\n{", "() \n{"]
                                )
                            )
                            or (
                                cmd_lower.rstrip().endswith("{")
                                and "(" in cmd_lower
                                and ")" in cmd_lower
                            )
                        ):
                            starts_construct = True
                            active_constructs.append(construct)
                            self.logger.debug(
                                "Starting %s construct (keyword match): %s",
                                construct,
                                cmd.strip()[:40],
                            )
                            break
                    # For other constructs, check if it's the first word
                    elif first_word in patterns["start"]:
                        starts_construct = True
                        active_constructs.append(construct)
                        self.logger.debug(
                            "Starting %s construct (first word match): %s",
                            construct,
                            cmd.strip()[:40],
                        )
                        break

            # Check if this line ends an active construct
            ends_construct = False
            if active_constructs:
                current_construct = active_constructs[-1]
                end_patterns = construct_patterns[current_construct]["end"]

                # Check for end patterns in the command
                if any(p in cmd_lower for p in end_patterns):
                    # For closing braces of functions, ensure it's not part of another construct
                    if current_construct == "function" and "}" in cmd_lower:
                        # Make sure it's a standalone "}" or at the end of a line
                        if cmd_lower == "}" or cmd_lower.endswith("}") or cmd_lower.endswith("};"):
                            ends_construct = True
                            active_constructs.pop()
                            self.logger.debug(
                                "Ending %s construct: %s", current_construct, cmd.strip()[:40]
                            )
                    # For other end patterns
                    else:
                        # Make sure the end pattern appears as a complete word
                        for pattern in end_patterns:
                            if pattern in cmd_lower.split() or cmd_lower.endswith(pattern + ";"):
                                ends_construct = True
                                active_constructs.pop()
                                self.logger.debug(
                                    "Ending %s construct: %s", current_construct, cmd.strip()[:40]
                                )
                                break

            # Buffer the current command and its original object
            construct_buffer.append(cmd)
            construct_buffer_originals.append(original_objects[i])

            # If we've ended all active constructs or encountered a standalone command
            if (ends_construct and not active_constructs) or (
                not starts_construct and not active_constructs
            ):
                # If we have only one command in buffer and it's not part of a construct, add it as is
                if len(construct_buffer) == 1 and not starts_construct and not ends_construct:
                    # If the original command was a ShellCommand, return the original object
                    original_obj = construct_buffer_originals[0]
                    if original_obj is not None:
                        result.append(original_obj)
                    else:
                        result.append(construct_buffer[0])
                else:
                    # Join the buffered commands into a single multiline command
                    multiline_cmd = "\n".join(construct_buffer)

                    # Check if any of the original commands were ShellCommand objects
                    has_shell_command = any(obj is not None for obj in construct_buffer_originals)

                    if has_shell_command:
                        # Find the first ShellCommand object to use as a template
                        shell_cmd_template = None
                        for obj in construct_buffer_originals:
                            if obj is not None:
                                shell_cmd_template = obj
                                break

                        if shell_cmd_template:
                            # Create a new ShellCommand object based on the template
                            # Check if this is a function definition and adjust the description accordingly
                            description = shell_cmd_template.description
                            if "\n" in multiline_cmd and (
                                "() {" in multiline_cmd.split("\n")[0]
                                or "(){" in multiline_cmd.split("\n")[0]
                                or "function " in multiline_cmd.lower().split("\n")[0]
                            ):
                                # Extract function name for better description
                                first_line = multiline_cmd.split("\n")[0].strip().lower()
                                if "function " in first_line:
                                    fn_name = (
                                        first_line.replace("function ", "").split("{")[0].strip()
                                    )
                                    if "(" in fn_name:
                                        fn_name = fn_name.split("(")[0].strip()
                                else:  # name() { syntax
                                    fn_name = first_line.split("(")[0].strip()

                                # Use plain function name without special characters in description
                                description = f"Function: {fn_name}"
                                self.logger.debug(
                                    f"Setting safer function description for combined construct: {fn_name}"
                                )

                            new_shell_cmd = ShellCommand(
                                command=multiline_cmd,
                                description=description,
                                is_critical=shell_cmd_template.is_critical,
                                is_multiline=True,
                                is_function_definition=shell_cmd_template.is_function_definition,
                                is_function_call=shell_cmd_template.is_function_call,
                            )
                            result.append(new_shell_cmd)
                        else:
                            result.append(multiline_cmd)
                    else:
                        result.append(multiline_cmd)

                    # Identify the type of construct for better logging
                    construct_type = "unknown"
                    if construct_buffer and construct_buffer[0]:
                        first_line = construct_buffer[0].strip().lower()
                        if "function " in first_line or "() {" in first_line or "(){" in first_line:
                            construct_type = "function definition"
                        elif first_line.startswith("if "):
                            construct_type = "if block"
                        elif first_line.startswith("for "):
                            construct_type = "for loop"
                        elif first_line.startswith("while "):
                            construct_type = "while loop"
                        elif first_line.startswith("case "):
                            construct_type = "case statement"

                    self.logger.debug(
                        "Combined %s into multiline command: %s",
                        construct_type,
                        multiline_cmd.split("\n")[0].strip()[:40] + "...",
                    )
                construct_buffer = []
                construct_buffer_originals = []

        # Handle any remaining commands in the buffer
        if construct_buffer:
            # If we have incomplete constructs (active_constructs not empty), log a warning
            if active_constructs:
                self.logger.warning(
                    "Incomplete shell construct detected: %s. Commands: %s",
                    active_constructs,
                    [
                        cmd.strip()[:40] + "..." if len(cmd) > 40 else cmd
                        for cmd in construct_buffer
                    ],
                )

            # Still combine the remaining commands to avoid losing them
            multiline_cmd = "\n".join(construct_buffer)

            # Check if any of the original commands were ShellCommand objects
            has_shell_command = any(obj is not None for obj in construct_buffer_originals)

            if has_shell_command:
                # Find the first ShellCommand object to use as a template
                shell_cmd_template = None
                for obj in construct_buffer_originals:
                    if obj is not None:
                        shell_cmd_template = obj
                        break

                if shell_cmd_template:
                    # Create a new ShellCommand object from the template
                    new_shell_cmd = ShellCommand(
                        command=multiline_cmd,
                        description=shell_cmd_template.description,
                        is_critical=shell_cmd_template.is_critical,
                        is_multiline=True,
                        is_function_definition=shell_cmd_template.is_function_definition,
                        is_function_call=shell_cmd_template.is_function_call,
                    )
                    result.append(new_shell_cmd)
                else:
                    result.append(multiline_cmd)
            else:
                result.append(multiline_cmd)

            self.logger.debug(
                "Combined remaining commands into multiline command: %s",
                multiline_cmd.split("\n")[0].strip()[:40] + "...",
            )

        # Final validation - make sure we don't return empty result
        if not result:
            self.logger.warning(
                "Shell construct combination resulted in empty list. Original commands: %s",
                [
                    str(cmd)[:40] + "..." if len(str(cmd)) > 40 else str(cmd)
                    for cmd in command_list[:5]
                ],
            )

            # If we have original ShellCommand objects, return those
            if any(obj is not None for obj in original_objects):
                return [
                    obj if obj is not None else cmd
                    for cmd, obj in zip(filtered_commands, original_objects)
                ]

            # Otherwise return filtered string commands
            return filtered_commands

        return result

    def generate_entrypoint_with_structured_args(
        self, service, paths, timestamp, output_path, template_path
    ):
        """
        Generates an entrypoint script with properly structured and quoted command arguments.

        This method uses the structured approach to handle command arguments and environment variables,
        ensuring proper escaping of special characters in shell commands.

        Args:
            service: The service manager instance
            paths: Dictionary of path configurations
            timestamp: Timestamp string
            output_path: Path where the generated entrypoint script will be written
            template_path: Path to the template file (not used directly)
        """
        self.logger.debug(
            "Generating entrypoint script for %s with structured arguments", service.service_name
        )

        # Process commands to ensure proper quoting and escaping
        processed_commands = {}

        # Process each command type in the run_cmd dictionary
        for cmd_type, cmds in service.run_cmd.items():
            self.logger.debug(
                "Processing command type '%s' for service '%s': %s",
                cmd_type,
                service.service_name,
                cmds,
            )
            if cmd_type == "run_cmd":
                # Handle the special structure of run_cmd
                run_cmd = service.run_cmd["run_cmd"]

                if not run_cmd:
                    # If run_cmd is empty or None, provide a default structure
                    processed_commands["run_cmd"] = {
                        "working_dir": "",
                        "command_args": [],
                        "env_vars": {},
                        "timeout": 60,
                    }
                    self.logger.debug(
                        "Empty run_cmd provided, using default structure: %s",
                        processed_commands["run_cmd"],
                    )
                    continue

                # Maintain separate fields for command_binary and command_args
                if run_cmd.get("command_binary"):
                    self.logger.debug("Using command binary: %s", run_cmd["command_binary"])

                # Process command_args
                command_args = []
                if isinstance(run_cmd.get("command_args"), list):
                    # Already structured as a list
                    self.logger.debug("Using command args list: %s", run_cmd["command_args"])
                    command_args = run_cmd["command_args"]
                elif run_cmd.get("command_args"):
                    # Convert string to list using shlex for proper splitting
                    try:
                        cmd_parts = service.build_command_args(run_cmd["command_args"])
                        self.logger.debug("Using command args from string: %s", cmd_parts)
                        # Ensure all parts are strings
                        command_args.extend(cmd_parts)
                    except (AttributeError, TypeError) as e:
                        self.logger.warning(
                            "Error converting command args: %s. Using empty list.", e
                        )
                        # Continue with empty args rather than failing

                # Process environment variables
                env_vars = {}
                if run_cmd.get("environment"):
                    try:
                        env_vars = {k: str(v) for k, v in run_cmd["environment"].items()}
                        self.logger.debug("Using environment variables: %s", env_vars)
                    except (AttributeError, TypeError) as e:
                        self.logger.warning("Error processing env vars: %s. Using empty dict.", e)

                processed_commands["run_cmd"] = {
                    "working_dir": run_cmd.get("working_dir", ""),
                    "command_binary": run_cmd.get("command_binary", "")
                    .strip()
                    .replace("\n", ""),  # Keep command_binary separate
                    "command_args": run_cmd.get("command_args", "")
                    .strip()
                    .replace("\n", ""),  # Keep original command_args
                    "environment": env_vars,  # Change to environment to match template
                    "timeout": run_cmd.get("timeout", 60),
                }
            else:
                # Process regular command lists
                if isinstance(cmds, list):
                    # Skip processing entirely empty lists
                    if not cmds:
                        self.logger.debug("Skipping empty command list for %s", cmd_type)
                        processed_commands[cmd_type] = []
                        continue

                    for i, cmd in enumerate(cmds):
                        self.logger.debug("Processing command %d for %s: %s", i, cmd_type, cmd)
                    # First combine any shell constructs that might be split across multiple elements
                    # Filter out None and empty strings before combining
                    valid_cmds = []
                    for c in cmds:
                        if not c:
                            continue
                        if isinstance(c, ShellCommand):
                            # Keep ShellCommand objects unchanged
                            valid_cmds.append(c)
                        elif isinstance(c, str) and c.strip():
                            # Only filter empty strings
                            valid_cmds.append(ShellCommand.from_string(c))
                        elif isinstance(c, dict) and "command" in c and c["command"].strip():
                            # Handle dict representation of commands
                            valid_cmds.append(ShellCommand.from_dict(c))

                    if not valid_cmds:
                        self.logger.debug("No valid commands found in list for %s", cmd_type)
                        processed_commands[cmd_type] = []
                        continue

                    combined_cmds = self._combine_shell_constructs(valid_cmds)
                    self.logger.debug(
                        "Combined %d commands into %d constructs for %s",
                        len(valid_cmds),
                        len(combined_cmds),
                        cmd_type,
                    )

                    # Extra validation: log first few commands before and after combination for debugging
                    if len(valid_cmds) > 0 and len(combined_cmds) > 0:
                        # Handle both string and ShellCommand objects for valid_cmds[0]
                        if isinstance(valid_cmds[0], str):
                            before_sample = valid_cmds[0].strip()[:40] + (
                                "..." if len(valid_cmds[0]) > 40 else ""
                            )
                        else:
                            # For ShellCommand objects, use the command property
                            cmd_text = valid_cmds[0].command
                            before_sample = cmd_text.strip()[:40] + (
                                "..." if len(cmd_text) > 40 else ""
                            )

                        # Handle both string and ShellCommand objects for combined_cmds[0]
                        if isinstance(combined_cmds[0], str):
                            after_text = combined_cmds[0]
                            after_sample = after_text.split("\n")[0].strip()[:40] + (
                                "..." if len(after_text) > 40 else ""
                            )
                        else:
                            # For ShellCommand objects, use the command property
                            cmd_text = combined_cmds[0].command
                            after_sample = cmd_text.split("\n")[0].strip()[:40] + (
                                "..." if len(cmd_text) > 40 else ""
                            )

                        self.logger.debug(
                            "Sample before combination: '%s', after: '%s'",
                            before_sample,
                            after_sample,
                        )

                    # Check for null results after combination
                    if not combined_cmds:
                        self.logger.warning(
                            "Combined commands resulted in empty list for %s, using original commands",
                            cmd_type,
                        )
                        # Use the original validated commands as fallback to avoid losing commands
                        combined_cmds = valid_cmds
                        if not combined_cmds:  # Double check we have something
                            self.logger.error(
                                "No valid commands available for %s after combination attempt",
                                cmd_type,
                            )
                            processed_commands[cmd_type] = []
                            continue

                    # Process each command in the combined list
                    processed_list = []
                    for cmd in combined_cmds:
                        if isinstance(cmd, ShellCommand):
                            # Pass the entire ShellCommand object with all its properties
                            if not cmd.command or cmd.command.strip() == "":
                                self.logger.warning("ShellCommand object has no command: %s", cmd)
                                continue
                            self.logger.debug("Processing ShellCommand: %s", cmd.to_dict())
                            processed_list.append(cmd.to_dict())
                        elif isinstance(cmd, str):
                            # For backward compatibility, convert string commands to ShellCommand objects                                # Enhanced detection for combined shell constructs
                            # First create the ShellCommand object and log detailed info about the command
                            shell_cmd = ShellCommand.from_string(cmd, is_critical=True)
                            if "\n" in cmd and len(cmd.split("\n")) > 1:
                                self.logger.debug(
                                    "Processing multiline command with %d lines, starting with: '%s'",
                                    len(cmd.split("\n")),
                                    cmd.split("\n")[0].strip()[:40]
                                    + ("..." if len(cmd.split("\n")[0]) > 40 else ""),
                                )

                            # Enhanced detection for multiline constructs and function definitions
                            if "\n" in cmd:
                                shell_cmd.is_multiline = True
                                first_line = cmd.split("\n")[0].strip().lower()

                                # Check for function definition patterns with comprehensive detection
                                if (
                                    "() {" in cmd or "(){" in cmd or "function " in cmd.lower()
                                ) and "}" in cmd:
                                    shell_cmd.is_function_definition = True
                                    # Extract function name for better description
                                    fn_name = (
                                        first_line.split("(")[0].replace("function ", "").strip()
                                    )
                                    # Use plain function name without special characters in description
                                    shell_cmd.description = f"Function: {fn_name}"
                                    self.logger.debug(
                                        "Detected function definition in combined construct: %s",
                                        first_line + "...",
                                    )

                                # Check for explicit function definition syntax variations
                                elif first_line.startswith("function ") and (
                                    first_line.endswith("{") or "{" in first_line
                                ):
                                    shell_cmd.is_function_definition = True
                                    # Extract function name for better description
                                    fn_name = (
                                        first_line.replace("function ", "").split("{")[0].strip()
                                    )
                                    # If the name has parentheses, clean them
                                    if "(" in fn_name:
                                        fn_name = fn_name.split("(")[0].strip()
                                    # Use plain function name without special characters
                                    shell_cmd.description = f"Function: {fn_name}"
                                    self.logger.debug(
                                        "Detected function definition (function keyword): %s",
                                        first_line + "...",
                                    )

                                # Function definition with name() { syntax across multiple lines
                                elif (
                                    "(" in first_line
                                    and ")" in first_line
                                    and (
                                        first_line.endswith("{")
                                        or (
                                            len(cmd.split("\n")) > 1
                                            and cmd.split("\n")[1].strip() == "{"
                                        )
                                        or "{" in cmd.split("\n")[0]
                                    )
                                ):
                                    shell_cmd.is_function_definition = True
                                    # Extract function name for better description
                                    fn_name = first_line.split("(")[0].strip()
                                    # Use plain function name without special characters in description
                                    shell_cmd.description = f"Function: {fn_name}"
                                    self.logger.debug(
                                        "Detected function definition (name() syntax): %s",
                                        first_line + "...",
                                    )

                                # Check for control structures
                                elif (
                                    first_line.startswith("if ")
                                    or first_line.startswith("for ")
                                    or first_line.startswith("while ")
                                    or first_line.startswith("case ")
                                ):
                                    shell_cmd.is_control_structure = True
                                    self.logger.debug(
                                        "Detected control structure in combined construct: %s",
                                        first_line + "...",
                                    )

                            if not shell_cmd.command or shell_cmd.command.strip() == "":
                                self.logger.warning(
                                    "ShellCommand object has no command: %s", shell_cmd
                                )
                                continue

                            self.logger.debug("Processing string command: %s", shell_cmd.to_dict())
                            processed_list.append(shell_cmd.to_dict())
                        elif isinstance(cmd, dict) and "command" in cmd:
                            # Handle dict that resembles a ShellCommand
                            shell_cmd = ShellCommand(**cmd)
                            if not shell_cmd.command or shell_cmd.command.strip() == "":
                                self.logger.warning(
                                    "ShellCommand object has no command: %s", shell_cmd
                                )
                                continue
                            self.logger.debug("Processing dict command: %s", shell_cmd.to_dict())
                            processed_list.append(shell_cmd.to_dict())
                        else:
                            # Try to convert other types to string as a fallback
                            try:
                                shell_cmd = ShellCommand.from_string(str(cmd), is_critical=True)
                                # Ensure multiline detection for combined constructs
                                if "\n" in str(cmd) and not shell_cmd.is_multiline:
                                    shell_cmd.is_multiline = True

                                if not shell_cmd.command or shell_cmd.command.strip() == "":
                                    self.logger.warning(
                                        "ShellCommand object has no command: %s", shell_cmd
                                    )
                                    continue
                                self.logger.debug(
                                    "Processing command from other type: %s", shell_cmd.to_dict()
                                )
                                processed_list.append(shell_cmd.to_dict())
                            except Exception as e:
                                self.logger.warning(
                                    "Could not convert command to ShellCommand: %s, error: %s",
                                    cmd,
                                    e,
                                )
                                # Skip this command
                    processed_commands[cmd_type] = processed_list
                elif isinstance(cmds, dict) and "command" in cmds:
                    # Handle single ShellCommand-like dictionary
                    shell_cmd = ShellCommand(**cmds)
                    if not shell_cmd.command or shell_cmd.command.strip() == "":
                        self.logger.warning("ShellCommand object has no command: %s", shell_cmd)
                        continue
                    self.logger.debug(
                        "Processing single ShellCommand dict: %s", shell_cmd.to_dict()
                    )
                    processed_commands[cmd_type] = [shell_cmd.to_dict()]
                elif cmds and isinstance(cmds, str):
                    # Single string command
                    shell_cmd = ShellCommand.from_string(cmds)
                    if not shell_cmd.command or shell_cmd.command.strip() == "":
                        self.logger.warning("ShellCommand object has no command: %s", shell_cmd)
                        continue
                    self.logger.debug("Processing single string command: %s", shell_cmd.to_dict())
                    processed_commands[cmd_type] = [shell_cmd.to_dict()]
                else:
                    # Empty or unsupported type
                    self.logger.debug("Processing empty or unsupported command type: %s", cmd_type)
                    processed_commands[cmd_type] = []

        # Render entrypoint template with structured arguments
        self.logger.debug(
            "Rendering entrypoint template for service '%s' with structured commands: %s",
            service,
            processed_commands,
        )
        self.generate_from_template(
            "entrypoint.sh.jinja",
            paths,
            timestamp,
            output_path,
            template_path,
            additional_param=service,
            structured_commands=processed_commands,
        )

    def launch_environment_services(self):
        """
        Launches the Docker Compose environment using the generated docker-compose.yml file.
        """
        try:
            with open(
                os.path.join(self.output_dir, "logs", "docker-compose-up.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "docker-compose-up.err.log"),
                    "w",
                ) as log_file_err:
                    # TODO check if previous containers are running and stop them
                    result = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            str(self.rendered_services_network_config_file_path),
                            "up",
                            "-d",  # Detached mode: Run containers in the background
                            "-V",  # Recreate anonymous volumes instead of retrieving data from the previous containers
                            "--remove-orphans",  # Remove containers for services not defined in the Compose file
                        ],
                        check=True,
                        capture_output=True,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                self.logger.info("Docker Compose environment launched successfully.")
                self.notify_environment_setup_started()
            with open(os.path.join(self.output_dir, "logs", "docker-compose.log"), "w") as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "docker-compose.err.log"), "w"
                ) as log_file_err:
                    result_exp = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            str(self.rendered_services_network_config_file_path),
                            "logs",
                            "--no-color",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result_exp.stdout)
                    log_file_err.write(result_exp.stderr)
                self.logger.info("Docker Compose environment logs successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to launch Docker Compose environment: %s", e.stderr)
            raise e

    def monitor_environment(self):
        """
        Monitors the Docker Compose environment by checking the status of services.
        """
        try:
            with open(
                os.path.join(self.output_dir, "logs", "docker-compose-ps.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "docker-compose-ps.err.log"),
                    "w",
                ) as log_file_err:
                    result = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            str(self.rendered_services_network_config_file_path),
                            "ps",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    # NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS
                    #
                    std_split = result.stdout.split("\n")
                    self.logger.debug(
                        "docker-compose ps: %s - %s - %s  - %s",
                        result.stdout,
                        result.stderr,
                        len(self.services_managers),
                        len(std_split),
                    )
                    if len(std_split) < len(self.services_managers) * 2:
                        self.logger.debug(
                            "Docker Compose environment monitored successfully - Experiment finished earlier"
                        )
                        self.notify_experiment_early_finish(
                            reason="Services finished early",
                            details={
                                "expected_services": len(self.services_managers),
                                "found_services": len(std_split),
                                "message": "Docker Compose experiment finished earlier than expected",
                            },
                        )
                    else:
                        self.logger.info(
                            "Docker Compose environment monitored successfully - All services are running"
                        )

                self.logger.debug("Docker Compose environment monitored successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to monitor Docker Compose environment: %s", e.stderr)
            raise e

    def teardown_environment(self):
        """
        Tears down the Docker Compose environment by bringing down services.
        """
        # TODO: add a way to retrieve the logs, results, binary
        with open(
            os.path.join(self.output_dir, "logs", "docker-compose-teardown.log"), "w"
        ) as log_file:
            with open(
                os.path.join(self.output_dir, "logs", "docker-compose-teardown.err.log"),
                "w",
            ) as log_file_err:
                try:
                    # For other network drivers, use docker-compose
                    result = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            self.services_network_config_file_path,
                            "down",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    os.system("docker volume prune -a -f")
                    self.logger.info("Docker Compose environment torn down successfully")
                    self.notify_environment_teardown(success=True)  # TODO
                except subprocess.CalledProcessError as e:
                    self.logger.error(
                        "Failed to tear down Docker Compose environment: %s", e.stderr
                    )
                    raise e
