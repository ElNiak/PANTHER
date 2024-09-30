# PANTHER-SCP/panther/core/commands/shadow_commands.py

import subprocess
import logging
from .command import Command

class ShadowCommands(Command):
    def __init__(self):
        self.logger = logging.getLogger("ShadowCommands")

    def execute(self, command: str):
        """
        Executes a Shadow Network Simulator command.
        """
        self.logger.info(f"Executing Shadow command: {command}")
        try:
            result = subprocess.run(
                command.split(),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.logger.info(f"Shadow command output: {result.stdout.decode()}")
            return result.stdout.decode()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Shadow command failed: {e.stderr.decode()}")
            return None
