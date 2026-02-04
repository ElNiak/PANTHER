"""Plugin management mixin for ConfigurationManager."""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from panther.core.utils.logging_mixin import LoggerMixin


class PluginManagementMixin(LoggerMixin):
    """Handles plugin file management operations."""

    def add_plugin_tester_service(self):
        """
        Add the plugin testers service directory defined by "testers_dir" inside the application
        at panther/plugins/services/testers/{testers_dir}

        Raises:
            OSError: If the source directory does not exist or if there is an error during
             the copying process.
        """
        if getattr(self, "testers_dir", None) and self.testers_dir != "":
            self.logger.info(f"Copying testers from {self.testers_dir}")
            self.testers_dir = Path(self.testers_dir)
            testers_target_dir = os.path.join(
                getattr(self, "_panther_dir", getattr(self, "panther_dir", Path.cwd())),
                "plugins",
                "services",
                "testers",
                self.testers_dir.name,
            )
            self.copy_plugin_files(self.testers_dir, testers_target_dir)

    def remove_plugin_tester_service(self):
        """
        Remove the plugin testers service directory defined by "testers_dir" inside the application
        at panther/plugins/services/testers/{testers_dir}

        Side Effects:
            Deletes the directory specified platforby `testers_dir` and all its contents.
        """
        if getattr(self, "testers_dir", None) and self.testers_dir != "":
            testers_target_dir = os.path.join(
                getattr(self, "_panther_dir", getattr(self, "panther_dir", Path.cwd())),
                "plugins",
                "services",
                "testers",
                Path(self.testers_dir).name,
            )
            if os.path.exists(testers_target_dir):
                self.logger.info(f"Removing testers from {testers_target_dir}")
                shutil.rmtree(testers_target_dir)

    def add_plugin_iut_service(self):
        """
        Add the plugin IUTs service directory defined by "iut_dir" inside the application
        at panther/plugins/services/iut/{iut_dir}

        Raises:
            OSError: If the source directory does not exist or if there is an error during
             the copying process.
        """
        if getattr(self, "iut_dir", None) and self.iut_dir != "":
            self.logger.info(f"Copying IUT from {self.iut_dir}")
            self.iut_dir = Path(self.iut_dir)
            iut_target_dir = os.path.join(
                getattr(self, "_panther_dir", getattr(self, "panther_dir", Path.cwd())),
                "plugins",
                "services",
                "iut",
                self.iut_dir.name,
            )
            self.copy_plugin_files(self.iut_dir, iut_target_dir)

    def remove_plugin_iut_service(self):
        """
        Remove the plugin IUTs service directory defined by "iut_dir" inside the application
        at panther/plugins/services/iut/{iut_dir}

        Side Effects:
            Deletes the directory specified by `iut_dir` and all its contents.
        """
        if getattr(self, "iut_dir", None) and self.iut_dir != "":
            iut_target_dir = os.path.join(
                getattr(self, "_panther_dir", getattr(self, "panther_dir", Path.cwd())),
                "plugins",
                "services",
                "iut",
                Path(self.iut_dir).name,
            )
            if os.path.exists(iut_target_dir):
                self.logger.info(f"Removing IUT from {iut_target_dir}")
                shutil.rmtree(iut_target_dir)

    def add_plugin_network_environment(self):
        """
        Add the plugin network environment directory defined by "net_env_dir" inside the application
        at panther/plugins/environments/network_environment/{net_env_dir}

        Raises:
            OSError: If the source directory does not exist or if there is an error during
             the copying process.
        """
        if getattr(self, "net_env_dir", None) and self.net_env_dir != "":
            self.logger.info(f"Copying network environment from {self.net_env_dir}")
            self.net_env_dir = Path(self.net_env_dir)
            net_env_target_dir = os.path.join(
                getattr(self, "_panther_dir", getattr(self, "panther_dir", Path.cwd())),
                "plugins",
                "environments",
                "network_environment",
                self.net_env_dir.name,
            )
            self.copy_plugin_files(self.net_env_dir, net_env_target_dir)

    def remove_plugin_network_environment(self):
        """
        Remove the plugin network environment directory defined by "net_env_dir" inside the application
        at panther/plugins/environments/network_environment/{net_env_dir}

        Side Effects:
            Deletes the directory specified by `net_env_dir` and all its contents.
        """
        if getattr(self, "net_env_dir", None) and self.net_env_dir != "":
            net_env_target_dir = os.path.join(
                getattr(self, "_panther_dir", getattr(self, "panther_dir", Path.cwd())),
                "plugins",
                "environments",
                "network_environment",
                Path(self.net_env_dir).name,
            )
            if os.path.exists(net_env_target_dir):
                self.logger.info(
                    f"Removing network environment from {net_env_target_dir}"
                )
                shutil.rmtree(net_env_target_dir)

    def add_plugin_execution_environment(self):
        """
        Add the plugin execution environment directory defined by "exec_env_dir" inside the application
        at panther/plugins/environments/execution_environment/{exec_env_dir}

        Raises:
            OSError: If the source directory does not exist or if there is an error during
             the copying process.
        """
        if getattr(self, "exec_env_dir", None) and self.exec_env_dir != "":
            self.logger.info(f"Copying execution environment from {self.exec_env_dir}")
            self.exec_env_dir = Path(self.exec_env_dir)
            exec_env_target_dir = os.path.join(
                getattr(self, "_panther_dir", getattr(self, "panther_dir", Path.cwd())),
                "plugins",
                "environments",
                "execution_environment",
                self.exec_env_dir.name,
            )
            self.copy_plugin_files(self.exec_env_dir, exec_env_target_dir)

    def remove_plugin_execution_environment(self):
        """
        Remove the plugin execution environment directory defined by "exec_env_dir" inside the application
        at panther/plugins/environments/execution_environment/{exec_env_dir}

        Side Effects:
            Deletes the directory specified by `exec_env_dir` and all its contents.
        """
        if getattr(self, "exec_env_dir", None) and self.exec_env_dir != "":
            exec_env_target_dir = os.path.join(
                getattr(self, "_panther_dir", getattr(self, "panther_dir", Path.cwd())),
                "plugins",
                "environments",
                "execution_environment",
                Path(self.exec_env_dir).name,
            )
            if os.path.exists(exec_env_target_dir):
                self.logger.info(
                    f"Removing execution environment from {exec_env_target_dir}"
                )
                shutil.rmtree(exec_env_target_dir)

    def copy_plugin_files(
        self, source_dir: Union[str, Path], target_dir: Union[str, Path]
    ):
        """
        Copies plugin files from the source directory to the target directory.

        This method checks if the target directory exists, and if not, it creates it.
        It then iterates through all items in the source directory,
        and copies each item to the target directory. If an item is a directory, it
        recursively copies the entire directory. If an item is a file, it copies the file.

        Args:
            source_dir: The path to the source directory containing plugin files
            target_dir: The path to the target directory where plugin files should be copied.

        Raises:
            OSError: If the source directory does not exist or if there is an error during
             the copying process.
        """
        source_dir = Path(source_dir)
        target_dir = Path(target_dir)

        # Check if source directory exists before attempting to copy
        if not source_dir.exists():
            self.logger.warning(
                "Source directory %s does not exist, skipping copy", source_dir
            )
            return

        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)

        for item in source_dir.iterdir():
            self.logger.info(f"Copying {item.name} from {source_dir} to {target_dir}")
            target_item = target_dir / item.name

            if item.is_dir():
                if target_item.exists():
                    shutil.rmtree(target_item)
                shutil.copytree(item, target_item)
            else:
                shutil.copy2(item, target_item)

    def cleanup(self):
        """
        Legacy cleanup operations.

        This method is maintained for backward compatibility but delegates
        to the new unified cleanup system.
        """
        self.logger.info("Performing legacy cleanup operations")
        # Delegate to state management mixin if available
        if hasattr(self, "clear_cache"):
            self.clear_cache()
        if hasattr(self, "clear_configuration_overrides"):
            self.clear_configuration_overrides()
