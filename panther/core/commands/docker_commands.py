# PANTHER-SCP/panther/core/commands/docker_commands.py

import subprocess
import logging
from .command import Command

class DockerCommands(Command):
    def __init__(self):
        self.logger = logging.getLogger("DockerCommands")

    def execute(self, command: str):
        """
        Executes a Docker command.
        """
        self.logger.info(f"Executing Docker command: {command}")
        try:
            result = subprocess.run(
                command.split(),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.logger.info(f"Docker command output: {result.stdout.decode()}")
            return result.stdout.decode()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Docker command failed: {e.stderr.decode()}")
            return None
