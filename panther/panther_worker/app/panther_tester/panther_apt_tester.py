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

from panther_tester.panther_tester import IvyTest
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

    def update_implementation_command(self, i):
        return i
    
    def set_process_limits(self):
        # Create a new session
        os.setsid()
        resource.setrlimit(resource.RLIMIT_AS, (200 * 1024 * 1024, 200 * 1024 * 1024))

    def generate_shadow_config(self):
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

        client_implem_args = re.sub("\s{2,}", " ", client_implem_args)
        server_implem_args = re.sub("\s{2,}", " ", server_implem_args)

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
        if "client_test" in self.name:
            file = "/app/shadow_client_test.yml"
            file_temp = "/app/shadow_client_test_template.yml"
        else:
            file = "/app/shadow_server_test.yml"
            file_temp = "/app/shadow_server_test_template.yml"
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
        server_command = (
            self.implem_conf[0][self.implementation_name]["binary-name"]
            .replace(
                "$IMPLEM_DIR",
                IMPLEM_DIR.replace("$PROT", self.current_protocol)
                + self.current_protocol,
            )
            .replace("$MODEL_DIR", MODEL_DIR + self.current_protocol)
            + " "
            + self.implem_conf[0][self.implementation_name]["source-format"]
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
        client_command = (
            self.implem_conf[1][self.implementation_name]["binary-name"]
            .replace(
                "$IMPLEM_DIR",
                IMPLEM_DIR.replace("$PROT", self.current_protocol)
                + self.current_protocol,
            )
            .replace("$MODEL_DIR", MODEL_DIR + self.current_protocol)
            + " "
            + self.implem_conf[1][self.implementation_name]["destination-format"]
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
        client_command = re.sub("\s{2,}", " ", client_command)
        server_command = re.sub("\s{2,}", " ", server_command)
        if self.is_client:
            return [client_command, server_command]
        else:
            return [server_command, client_command]

    def start_implementation(self, i, out, err):
        if self.run:
            self.update_implementation_command(i)
            self.log.info(self.implem_cmd)
            qcmd = (
                "sleep 5; "
                if self.is_client
                and not self.config["net_parameters"].getboolean("shadow")
                else ""
            ) + self.implem_cmd  # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +
            qcmd = 'RUST_LOG="debug" RUST_BACKTRACE=1 ' + qcmd
            self.log.info("implementation command: {}".format(qcmd))
            if not self.config["net_parameters"].getboolean("shadow"):
                self.log.info("not shadow test:")
                self.implem_process = subprocess.Popen(
                    qcmd,
                    cwd=(
                        self.implem_dir_client
                        if self.is_client
                        else self.implem_dir_server
                    ),
                    stdout=out,
                    stderr=err,
                    shell=True,  # self.is_client,
                    preexec_fn=self.set_process_limits,
                )
                self.log.info("implem_process pid: {}".format(self.implem_process.pid))
            else:
                # TODO use config file
                self.log.info("Generating shadow config:")
                file = self.generate_shadow_config()
                self.log.info(
                    "command: RUST_BACKTRACE=1 shadow " + file + " > shadow.log"
                )
                try:
                    os.system("RUST_BACKTRACE=1 shadow " + file + " > shadow.log")
                except:
                    pass

    def start_tester(self, iteration, iev, i):
        self.log.info("Starting tester:")
        ok = True
        if not self.config["net_parameters"].getboolean("shadow"):
            try:
                for iclient in range(
                    0, self.nclient
                ):  # TODO for multiple implem client only
                    self.log.info("iclient = " + str(iclient))
                    ok = ok and self.run_tester(iteration, iev, i, iclient)
            except KeyboardInterrupt:
                if self.run and not self.config["global_parameters"].getboolean(
                    "keep_alive"
                ):
                    self.log.info("cool kill")
                    if self.config["net_parameters"].getboolean("vnet"):
                        subprocess.Popen(
                            "/bin/bash " + SOURCE_DIR + "/vnet_reset.sh",
                            shell=True,
                            executable="/bin/bash",
                        ).wait()
                    self.implem_process.terminate()
                raise KeyboardInterrupt

            if self.run and not self.config["global_parameters"].getboolean(
                "keep_alive"
            ):
                self.log.info("implem_process.terminate()")
                # The above code is terminating the process.
                self.implem_process.terminate()
                retcode = self.implem_process.wait()
                self.log.info(retcode)
                if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                    iev.write("server_return_code({})\n".format(retcode))
                    self.log.info("server return code: {}".format(retcode))
                    self.implem_process.kill()
                    return False
        return ok

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
        strace_cmd, gperf_cmd, timeout_cmd = super().generate_tester_command(
            iteration, iclient
        )

        os.environ["TIMEOUT_IVY"] = str(
            self.config["global_parameters"].getint("timeout")
        )

        randomSeed = random.randint(0, 1000)
        random.seed(datetime.now())

        prefix = ""
        server_port = 4443
        client_port = 2 * iteration + 4987 + iclient

        print(self.name)
        # time.sleep(5)
        if self.config["debug_parameters"].getboolean("gdb"):
            # TODO refactor
            prefix = " gdb --args "
        if self.config["net_parameters"].getboolean("vnet"):
            envs = "env - "
            for env_var in ENV_VAR:
                if env_var != "PATH":  # TODO remove it is useless
                    envs = envs + env_var + '="' + ENV_VAR[env_var] + '" '
                else:
                    envs = envs + env_var + '="' + os.environ.get(env_var) + '" '
            prefix = (
                "sudo ip netns exec ivy "
                + envs
                + " "
                + strace_cmd
                + " "
                + gperf_cmd
                + " "
            )
            ip_server = 0x0A000003 if not self.is_client else 0x0A000001
            ip_client = 0x0A000001 if not self.is_client else 0x0A000003
        elif self.config["net_parameters"].getboolean("shadow"):
            ip_server = 0x0B000002 if not self.is_client else 0x0B000001
            ip_client = 0x0B000001 if not self.is_client else 0x0B000002
        else:
            # prefix = strace_cmd + " "
            ip_server = 0x7F000001
            ip_client = ip_server

        return " ".join(
            [
                "{}{}{}/{} seed={} server_port={} server_addr={}  {}".format(
                    timeout_cmd,
                    prefix,
                    self.config["global_parameters"]["build_dir"],
                    self.name,
                    randomSeed,
                    server_port,
                    ip_server,
                    (
                        ""
                        if self.is_client
                        else "client_port={}  client_addr={}".format(
                            client_port, ip_client
                        )
                    ),
                )
            ]
            + self.extra_args
            + ([""] if self.config["net_parameters"].getboolean("vnet") else [""])
        )
