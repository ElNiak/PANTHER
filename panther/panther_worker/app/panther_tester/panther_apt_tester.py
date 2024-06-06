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
        # TODO add path to shadow config and then call the protocol specific function
        server_implem_args = (
            self.implem_conf[0][self.implementation_name]["source-format"]
            .replace(
                "[source]", self.implem_conf[0][self.implementation_name]["source"]
            )
            .replace(
                "[source-value]",
                self.implem_conf[0][self.implementation_name]["source-value"],
            )
            .replace("[port]", self.implem_conf[0][self.implementation_name]["port"])
            .replace(
                "[port-value]",
                self.implem_conf[0][self.implementation_name]["port-value"],
            )
        )

        client_implem_args = (
            self.implem_conf[1][self.implementation_name]["destination-format"]
            .replace(
                "[destination]",
                self.implem_conf[1][self.implementation_name]["destination"],
            )
            .replace(
                "[destination-value]",
                self.implem_conf[1][self.implementation_name]["destination-value"],
            )
            .replace("[port]", self.implem_conf[1][self.implementation_name]["port"])
            .replace(
                "[port-value]",
                self.implem_conf[1][self.implementation_name]["port-value"],
            )
        )

        client_implem_args = re.sub("\\s{2,}", " ", client_implem_args)
        server_implem_args = re.sub("\\s{2,}", " ", server_implem_args)

        implem_env = ""  # TODO use a list of env

        ivy_args = (
            self.generate_tester_command(
                self.config["global_parameters"].getint("iter"), 1
            )
            .split("/")[-1]
            .replace(self.name, "")
        )
        ivy_env = ""  # TODO use a list of env

        # TODO use config file
        self.log.info("shadow test:")
        print("shadow test:")
        for env_var in ENV_VAR:
            print(env_var, ENV_VAR[env_var])
        if "attacker_test" in self.name:
            file = "/app/shadow_attacker_test.yml"
            file_temp = "/app/shadow_attacker_test_template.yml"
        else:
            file = "/app/shadow_man_in_the_middle_test.yml"
            file_temp = "/app/shadow_man_in_the_middle_test_template.yml"
        with open(file_temp, "r") as f:
            content = f.read()  # todo replace
        with open(file, "w") as f:
            content = content.replace("<TEST_NAME>", self.name)
            content = content.replace("<JITTER>", str(ENV_VAR["JITTER"]))
            content = content.replace("<LATENCY>", str(ENV_VAR["LATENCY"]))
            content = content.replace("<LOSS>", str(float(ENV_VAR["LOSS"])))
            content = content.replace(
                "<IMPLEM_PATH>",
                (
                    self.implem_dir_server
                    + "/"
                    + self.implem_conf[0][self.implementation_name]["binary-name"]
                    if not self.is_client
                    else self.implem_dir_client
                    + "/"
                    + self.implem_conf[1][self.implementation_name]["binary-name"]
                ),
            )
            content = content.replace(
                "<IMPLEM_ARGS>",
                server_implem_args if not self.is_client else client_implem_args,
            )
            content = content.replace(
                "<BUILD_PATH>", self.config["global_parameters"]["build_dir"]
            )
            content = content.replace("<TEST_ARGS>", ivy_args)
            self.log.info(content)
            print(content)
            f.write(content)
        os.chdir("/app")
        self.log.info("rm -r /app/shadow.data/ ")
        print("rm -r /app/shadow.data/ ")
        os.system("rm -r /app/shadow.data/ ")
        os.system("rm  /app/shadow.log ")
        self.log.info("command: shadow " + file + " > shadow.log")
        print("command: shadow " + file + " > shadow.log")

        return file

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

    def start_tester(self, iteration, iev, i):
        self.log.info("Starting tester:")
        print("Starting tester:")
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
