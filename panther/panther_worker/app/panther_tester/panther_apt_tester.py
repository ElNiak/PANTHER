# This script runs a sequence of tests on the picoquicdemo server.

import random
import pexpect
import os
import sys
import subprocess
import signal
from datetime import datetime
import platform
from time import sleep
import re
import resource

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from panther_tester.panther_tester import IvyTest
from panther_tester.panther_quic_tester import QUICIvyTest
from panther_tester.panther_minip_tester import MiniPIvyTest
from panther_utils.panther_constant import *

# On Windows, pexpect doesn't implement 'spawn'.
"""
Choose the process spawner for subprocess according to plateform
"""
if platform.system() == "Windows":
    from pexpect.popen_spawn import PopenSpawn

    spawn = PopenSpawn
else:
    spawn = pexpect.spawn


# TODO add tested implemenatation name
class APTIvyTest(IvyTest):
    def __init__(
        self,
        args,
        implem_dir_server,
        implem_dir_client,
        extra_args,
        implementation_name,
        mode,
        config,
        protocol_conf,
        implem_conf,
        current_protocol,
        apt_conf,
    ):

        super().__init__(
            args,
            implem_dir_server,
            implem_dir_client,
            extra_args,
            implementation_name,
            mode,
            config,
            protocol_conf,
            implem_conf,
            current_protocol,
        )
        self.log.setLevel(int(os.environ["LOG_LEVEL"]))
        self.apt_conf = apt_conf

        self.quic_tester = QUICIvyTest(
            args,
            implem_dir_server,
            implem_dir_client,
            extra_args,
            implementation_name,
            mode,
            config,
            protocol_conf,
            implem_conf,
            current_protocol,
        )

        self.minip_tester = MiniPIvyTest(
            args,
            implem_dir_server,
            implem_dir_client,
            extra_args,
            implementation_name,
            mode,
            config,
            protocol_conf,
            implem_conf,
            current_protocol,
        )

    def update_implementation_command(self, i):
        if self.current_protocol == "apt":
            current_protocol = self.apt_conf["protocol_origins"][
                self.implementation_name
            ]
        else:
            current_protocol = self.current_protocol
        if current_protocol == "quic":
            self.log.info("Updating command for quic implementation:")
            self.quic_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            return self.quic_tester.update_implementation_command(i)
        else:
            self.log.info("Updating command for apt implementation:")
            return i

    def set_process_limits(self):
        # Create a new session
        os.setsid()
        # resource.setrlimit(resource.RLIMIT_AS, (200 * 1024 * 1024, 200 * 1024 * 1024))

    def generate_shadow_config(self):
        if self.current_protocol == "apt":
            current_protocol = self.apt_conf["protocol_origins"][
                self.implementation_name
            ]
        else:
            current_protocol = self.current_protocol
        if current_protocol == "quic":
            self.log.info("Generating shadow command for quic implementation:")
            self.quic_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            self.quic_tester.implem_conf = self.implem_conf
            files = self.quic_tester.generate_shadow_config()
            self.quic_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            return files
        if current_protocol == "minip":
            self.log.info("Generating shadow command for minip implementation:")
            self.minip_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            self.minip_tester.implem_conf = self.implem_conf
            files = self.minip_tester.generate_shadow_config()
            self.minip_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            return files

    def generate_implementation_command(self):
        if self.current_protocol == "apt":
            current_protocol = self.apt_conf["protocol_origins"][
                self.implementation_name
            ]
        else:
            current_protocol = self.current_protocol
        if current_protocol == "quic":
            self.log.info("Generating command for quic implementation:")
            self.quic_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            self.quic_tester.implem_conf = self.implem_conf
            implems = self.quic_tester.generate_implementation_command()
            self.implem_cmd = implems[0]
            self.quic_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            return implems
        if current_protocol == "minip":
            self.log.info("Generating command for minip implementation:")
            self.minip_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            self.minip_tester.implem_conf = self.implem_conf
            implems = self.minip_tester.generate_implementation_command()
            self.implem_cmd = implems[0]
            self.minip_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            return implems

    def start_tester(self, iteration, iev, i):
        self.log.info("Starting tester from ATP:")
        print("Starting tester from ATP:")
        if self.current_protocol == "apt":
            current_protocol = self.apt_conf["protocol_origins"][
                self.implementation_name
            ]
        else:
            current_protocol = self.current_protocol
        if current_protocol == "quic":
            self.log.info("Starting tester for quic implementation:")
            self.quic_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            return self.quic_tester.start_tester(iteration, iev, i)
        if current_protocol == "minip":
            self.log.info("Starting tester for minip implementation:")
            self.minip_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            return self.minip_tester.start_tester(iteration, iev, i)

    def start_implementation(self, i, out, err):
        self.log.info("Start implementation:")
        if self.current_protocol == "apt":
            current_protocol = self.apt_conf["protocol_origins"][
                self.implementation_name
            ]
        else:
            current_protocol = self.current_protocol
        if current_protocol == "quic":
            self.log.info("Start quic implementation:")
            self.log.info(f"APT implemententation command {self.implem_cmd}")
            self.quic_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            self.log.info(
                f"QUIC implemententation command {self.quic_tester.implem_cmd}"
            )
            return self.quic_tester.start_implementation(i, out, err)
        if current_protocol == "minip":
            self.log.info("Start minip implementation:")
            self.log.info(f"APT implemententation command {self.implem_cmd}")
            self.minip_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            self.log.info(
                f"MINIP implemententation command {self.minip_tester.implem_cmd}"
            )
            return self.minip_tester.start_implementation(i, out, err)

    def stop_processes(self):
        self.log.info("Stop processes:")
        if self.implem_process != None:
            try:
                # os.kill(implem_process.pid, 9)
                os.killpg(os.getpgid(self.implem_process.pid), signal.SIGTERM)
            except OSError:
                self.log.info("pid is unassigned")
                self.implem_process.kill()
            else:
                self.log.info("pid is in use")
                self.implem_process.kill()
                self.log.info("implem_process.kill()")

    def generate_tester_command(self, iteration, iclient):
        if self.current_protocol == "apt":
            current_protocol = self.apt_conf["protocol_origins"][
                self.implementation_name
            ]
        else:
            current_protocol = self.current_protocol
        if current_protocol == "quic":
            command = self.quic_tester.generate_tester_command(iteration, iclient)
            self.quic_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            return command
        if current_protocol == "minip":
            command = self.minip_tester.generate_tester_command(iteration, iclient)
            self.minip_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            return command
