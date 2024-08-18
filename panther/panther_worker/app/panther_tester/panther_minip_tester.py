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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

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
class MiniPIvyTest(IvyTest):
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
        self.log.setLevel(int(os.environ["LOG_LEVEL"]))

        self.is_mim = True if "mim" in self.mode else False  # TODO
        
        self.is_attacker_client = True if ("attacker" in self.mode and "client" in self.mode) else False  # TODO
        self.is_attacker_server = True if ("attacker" in self.mode and "server" in self.mode) else False
        self.minip_process_1 = None
        self.minip_process_2 = None
        
    def update_implementation_command(self, i,is_target=False):
        self.log.debug(f"Update implementation before {self.implem_cmd}")
        if self.config["net_parameters"].getboolean("vnet"):
            implem_cmd_copy = self.implem_cmd
            # if self.implementation_name == "picoquic":
            #     implem_cmd = "cd " + IMPLEM_DIR.replace("$PROT",self.current_protocol) + '/picoquic;'  + implem_cmd + "cd " + IMPLEM_DIR.replace("$PROT",self.current_protocol) + '/picoquic;'
            envs = "env - "
            for env_var in ENV_VAR:
                if env_var != "PATH":  # TODO remove it is useless
                    envs = envs + env_var + '="' + ENV_VAR[env_var] + '" '
                else:
                    envs = envs + env_var + '="' + os.environ.get(env_var) + '" '

            if  self.is_mim or self.is_attacker_client or self.is_attacker_server:
                client_addr = "10.0.0.2"       
                server_addr = "10.0.0.3"   
                if is_target:
                    client_addr = "10.0.0.4"
                    server_addr = "10.0.0.5"    
                if self.config["vnet_parameters"].getboolean("bridged"):
                    if self.is_mim:
                        self.implem_cmd = self.implem_cmd.replace("11.0.0.1", server_addr)
                        self.implem_cmd = self.implem_cmd.replace("11.0.0.2", server_addr)
                        self.implem_cmd = self.implem_cmd.replace("11.0.0.3", server_addr)

                        self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.1", server_addr)
                        self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.2", server_addr)
                        self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.3", server_addr)
                    elif self.is_attacker_client:
                        self.implem_cmd = self.implem_cmd.replace("11.0.0.1", client_addr)
                        self.implem_cmd = self.implem_cmd.replace("11.0.0.3", client_addr)

                        self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.2", "10.0.0.1")
                        self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.3", "10.0.0.1")
                    elif self.is_attacker_server:
                        self.implem_cmd = self.implem_cmd.replace("11.0.0.2", server_addr)
                        self.implem_cmd = self.implem_cmd.replace("11.0.0.3", server_addr)

                        self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.1", client_addr)
                        self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.3", client_addr)
                else:
                    self.log.error("Not implemented in non-bridged mode")
                    exit(1)
                    
                maxreplace = 1
                netns_server = "tested_server"
                if is_target:
                    netns_server = "tested_tserver"
                maxreplace = 1
                self.implem_cmd = (
                    f"sudo ip netns exec {netns_server} " + envs + self.implem_cmd
                )
                old = "implem"
                new = (
                    "veth_server"
                    if self.config["vnet_parameters"].getboolean("bridged") and not is_target
                    else  ("veth_tserver" if self.config["vnet_parameters"].getboolean("bridged") and is_target
                    else "server_client")
                )
                self.implem_cmd = new.join(self.implem_cmd.rsplit(old, maxreplace))

                netns_client = "tested_client"
                if is_target:
                    netns_client = "tested_tclient"
                self.implem_cmd_opposite = (
                    f"sudo ip netns exec {netns_client} "
                    + envs
                    + self.implem_cmd_opposite
                )
                old = "implem"
                new = (
                    "veth_client"
                    if self.config["vnet_parameters"].getboolean("bridged") and not is_target
                    else  ("veth_tclient" if self.config["vnet_parameters"].getboolean("bridged") and is_target
                    else "server_server")
                )
                self.implem_cmd_opposite = new.join(
                    self.implem_cmd_opposite.rsplit(old, maxreplace)
                )
            else:
                self.implem_cmd = "sudo ip netns exec implem "
                self.implem_cmd = self.implem_cmd + envs + implem_cmd_copy
                self.implem_cmd = self.implem_cmd.replace("11.0.0.1", "10.0.0.1")
                self.implem_cmd = self.implem_cmd.replace("11.0.0.3", "10.0.0.1")
                    
                
        self.log.debug(f"Update implementation after {self.implem_cmd}")

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
        self.log.info(f"Generate implementation command: {self.implementation_name}")
        self.log.info(self.implem_conf)
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
        client_command = re.sub("\\s{2,}", " ", client_command)
        server_command = re.sub("\\s{2,}", " ", server_command)
        if self.is_client:
            return [client_command, server_command]
        else:
            return [server_command, client_command]

    def start_implementation(self, i, out, err):
        if self.run:
            self.update_implementation_command(i)
            self.log.info(self.implem_cmd)
            qcmd = (
                "sleep 5; exec "
                if self.is_client
                and not self.config["net_parameters"].getboolean("shadow")
                else "exec "
            ) + self.implem_cmd  # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +

            if self.is_mim:
                self.log.info("Updating implementation:")
                print("Updating implementation:")
                self.update_implementation_command(i)
                
                self.log.info("Implementation command server: {}".format(qcmd))
                print("Implementation command server: {}".format(qcmd))
                try:
                    self.minip_process_1 = subprocess.Popen(
                        qcmd,
                        cwd=(self.implem_dir_server),
                        stdout=out,
                        stderr=err,
                        shell=True,  # self.is_client,
                        preexec_fn=self.set_process_limits,
                    )
                except subprocess.CalledProcessError as e:
                    print(e)
                self.log.info(
                    "minip_process_1 pid: {}".format(self.minip_process_1.pid)
                )
                print("minip_process_1 pid: {}".format(self.minip_process_1.pid))

                qcmd = (
                    "sleep 10; exec "
                ) + self.implem_cmd_opposite  # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +
                self.log.info("Implementation command client: {}".format(qcmd))
                print("Implementation command client: {}".format(qcmd))
                with self.open_out(self.name + "_client.out") as out_c:
                    with self.open_out(self.name + "_client.err") as err_c:
                        try:
                            self.minip_process_2 = subprocess.Popen(
                                qcmd,
                                cwd=(self.implem_dir_client),
                                stdout=out_c,
                                stderr=err_c,
                                shell=True,  # self.is_client,
                                preexec_fn=self.set_process_limits,
                            )
                        except subprocess.CalledProcessError as e:
                            print(e)
                self.log.info(
                    "minip_process_2 pid: {}".format(self.minip_process_2.pid)
                )
                print("minip_process_2 pid: {}".format(self.minip_process_2.pid))            
            elif self.is_attacker_server:
                self.log.info("Updating implementation:")
                print("Updating implementation:")
                self.update_implementation_command(i)
                if self.config["net_parameters"].getboolean("shadow"):
                    self.log.info("Generate shadow config")
                    print("Generate shadow config")
                    file = self.generate_shadow_config()
                    try:
                        os.system(
                            "RUST_BACKTRACE=1 shadow " + file + " > shadow.log"
                        )
                    except Exception as e:
                        print(e)
                else:
                    if self.implementation_name == "quant":
                        os.system("ip netns exec tested_client echo 0 | sudo tee /proc/sys/kernel/randomize_va_space")
                        os.system("ip netns exec tested_server echo 0 | sudo tee /proc/sys/kernel/randomize_va_space")
                        qcmd = (
                            self.implem_cmd
                        )
                    else:
                        qcmd = (
                            "RUST_LOG='debug' RUST_BACKTRACE=1  exec " + self.implem_cmd
                        )
                    self.log.info("Implementation command server: {}".format(qcmd))
                    print("Implementation command server: {}".format(qcmd))
                    self.minip_process_1 = subprocess.Popen(
                        qcmd,
                        cwd=(self.implem_dir_server),
                        stdout=out,
                        stderr=err,
                        shell=True,
                        preexec_fn=self.set_process_limits,
                    )
                    self.log.info("minip_process_1 pid: {}".format(self.minip_process_1.pid))
                    print("minip_process_1 pid: {}".format(self.minip_process_1.pid))
            elif self.is_attacker_client:
                self.log.info("Updating implementation:")
                print("Updating implementation:")
                self.update_implementation_command(i)
                if self.config["net_parameters"].getboolean("shadow"):
                    self.log.info("Generate shadow config")
                    print("Generate shadow config")
                    file = self.generate_shadow_config()
                    try:
                        os.system(
                            "RUST_BACKTRACE=1 shadow " + file + " > shadow.log"
                        )
                    except Exception as e:
                        print(e)
                else:
                    if self.implementation_name == "quant":
                        os.system("ip netns exec tested_client echo 0 | sudo tee /proc/sys/kernel/randomize_va_space")
                        os.system("ip netns exec tested_server echo 0 | sudo tee /proc/sys/kernel/randomize_va_space")
                        qcmd = (
                            "sleep 10; "
                            + self.implem_cmd
                        )  # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +
                    else:
                        qcmd = (
                            "sleep 10; "
                            + "RUST_LOG='debug' RUST_BACKTRACE=1  exec "
                            + self.implem_cmd
                        )
                    self.log.info("Implementation command client: {}".format(qcmd))
                    print("Implementation command client: {}".format(qcmd))
                    self.minip_process_1 = subprocess.Popen(
                        qcmd,
                        cwd=(self.implem_dir_client),
                        stdout=out,
                        stderr=err,
                        shell=True,
                        preexec_fn=self.set_process_limits,
                    )
                    self.log.info("minip_process_1 pid: {}".format(self.minip_process_1.pid))
                    print("minip_process_1 pid: {}".format(self.minip_process_1.pid))     
            elif self.config["net_parameters"].getboolean("shadow"):
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
            else:
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
                    self.log.info(
                        "implem_process pid: {}".format(self.implem_process.pid)
                    )

    def start_target_implementation(self, i, out, err):
        if self.run:
            self.update_implementation_command(i,True)
            self.log.info(self.implem_cmd)
            qcmd = (
                "sleep 5; exec "
                if self.is_client
                and not self.config["net_parameters"].getboolean("shadow")
                else "exec "
            ) + self.implem_cmd  # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +

            if self.is_mim:
                self.log.info("Updating implementation:")
                print("Updating implementation:")
                self.update_implementation_command(i,True)
                
                self.log.info("Implementation command server: {}".format(qcmd))
                print("Implementation command server: {}".format(qcmd))
                with self.open_out(self.name + "_target_server.out") as out_c:
                    with self.open_out(self.name + "_target_server.err") as err_c:
                        self.minip_process_1 = subprocess.Popen(
                            qcmd,
                            cwd=(self.implem_dir_server),
                            stdout=out_c,
                            stderr=err_c,
                            shell=True,  # self.is_client,
                            preexec_fn=self.set_process_limits,
                        )
                self.log.info(
                    "minip_process_1 pid: {}".format(self.minip_process_1.pid)
                )
                print("minip_process_1 pid: {}".format(self.minip_process_1.pid))

                qcmd = (
                    "sleep 5; exec "
                ) + self.implem_cmd_opposite  # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +
                self.log.info("Implementation command client: {}".format(qcmd))
                print("Implementation command client: {}".format(qcmd))
                with self.open_out(self.name + "_target_client.out") as out_c:
                    with self.open_out(self.name + "_target_client.err") as err_c:
                        self.minip_process_2 = subprocess.Popen(
                            qcmd,
                            cwd=(self.implem_dir_client),
                            stdout=out_c,
                            stderr=err_c,
                            shell=True,  # self.is_client,
                            preexec_fn=self.set_process_limits,
                        )
                self.log.info(
                    "minip_process_2 pid: {}".format(self.minip_process_2.pid)
                )
                print("minip_process_2 pid: {}".format(self.minip_process_2.pid))            
            elif self.is_attacker_server:
                self.log.info("Updating implementation:")
                print("Updating implementation:")
                self.update_implementation_command(i,True)
                if self.config["net_parameters"].getboolean("shadow"):
                    self.log.info("Generate shadow config")
                    print("Generate shadow config")
                    file = self.generate_shadow_config()
                    try:
                        os.system(
                            "RUST_BACKTRACE=1 shadow " + file + " > shadow.log"
                        )
                    except Exception as e:
                        print(e)
                else:
                    if self.implementation_name == "quant":
                        os.system("ip netns exec tested_client echo 0 | sudo tee /proc/sys/kernel/randomize_va_space")
                        os.system("ip netns exec tested_server echo 0 | sudo tee /proc/sys/kernel/randomize_va_space")
                        qcmd = (
                            self.implem_cmd
                        )
                    else:
                        qcmd = (
                            "RUST_LOG='debug' RUST_BACKTRACE=1  exec " + self.implem_cmd
                        )
                    self.log.info("Implementation command server: {}".format(qcmd))
                    print("Implementation command server: {}".format(qcmd))
                    self.minip_process_1 = subprocess.Popen(
                        qcmd,
                        cwd=(self.implem_dir_server),
                        stdout=out,
                        stderr=err,
                        shell=True,
                        preexec_fn=self.set_process_limits,
                    )
                    self.log.info("minip_process_1 pid: {}".format(self.minip_process_1.pid))
                    print("minip_process_1 pid: {}".format(self.minip_process_1.pid))
            elif self.is_attacker_client:
                self.log.info("Updating implementation:")
                print("Updating implementation:")
                self.update_implementation_command(i,True)
                if self.config["net_parameters"].getboolean("shadow"):
                    self.log.info("Generate shadow config")
                    print("Generate shadow config")
                    file = self.generate_shadow_config()
                    try:
                        os.system(
                            "RUST_BACKTRACE=1 shadow " + file + " > shadow.log"
                        )
                    except Exception as e:
                        print(e)
                else:
                    if self.implementation_name == "quant":
                        os.system("ip netns exec tested_client echo 0 | sudo tee /proc/sys/kernel/randomize_va_space")
                        os.system("ip netns exec tested_server echo 0 | sudo tee /proc/sys/kernel/randomize_va_space")
                        qcmd = (
                            "sleep 10; "
                            + self.implem_cmd
                        )  # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +
                    else:
                        qcmd = (
                            "sleep 10; "
                            + "RUST_LOG='debug' RUST_BACKTRACE=1  exec "
                            + self.implem_cmd
                        )
                    self.log.info("Implementation command client: {}".format(qcmd))
                    print("Implementation command client: {}".format(qcmd))
                    self.minip_process_1 = subprocess.Popen(
                        qcmd,
                        cwd=(self.implem_dir_client),
                        stdout=out,
                        stderr=err,
                        shell=True,
                        preexec_fn=self.set_process_limits,
                    )
                    self.log.info("minip_process_1 pid: {}".format(self.minip_process_1.pid))
                    print("minip_process_1 pid: {}".format(self.minip_process_1.pid))     
            elif self.config["net_parameters"].getboolean("shadow"):
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
            else:
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
                    self.log.info(
                        "implem_process pid: {}".format(self.implem_process.pid)
                    )

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
                    self.stop_processes()
                raise KeyboardInterrupt

            if self.run and not self.config["global_parameters"].getboolean(
                "keep_alive"
            ):
                if not self.is_mim and not self.is_attacker_client and not self.is_attacker_server:
                    self.log.info("self.stop_processes()")
                    # The above code is terminating the process.
                    self.implem_process.terminate()
                    retcode = self.implem_process.wait()
                    self.log.info(retcode)
                    if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                        iev.write("server_return_code({})\n".format(retcode))
                        self.log.info("server return code: {}".format(retcode))
                        self.implem_process.terminate()
                        return False
                    else:
                        if self.is_attacker_client or self.is_attacker_server or self.is_mim:
                            self.minip_process_1.terminate()
                            retcode = self.minip_process_1.wait()
                            self.log.info(retcode)
                            print(retcode)
                            if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                                iev.write("server_return_code({})\n".format(retcode))
                                self.log.info("server return code: {}".format(retcode))
                                print("server return code: {}".format(retcode))
                                self.minip_process_1.kill()
                                return False
                        self.minip_process_2.terminate()
                        retcode = self.minip_process_2.wait()
                        self.log.info(retcode)
                        print(retcode)
                        if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                            iev.write("server_return_code({})\n".format(retcode))
                            self.log.info("server return code: {}".format(retcode))
                            print("server return code: {}".format(retcode))
                            self.minip_process_2.kill()
                            return False
                        
        return ok

    def stop_processes(self):
        self.log.info("Stop processes:")
        if not self.is_mim and not self.is_attacker_client and not self.is_attacker_server:
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
        else:
            if self.minip_process_1 is not None:
                try:
                    self.minip_process_1.terminate()
                    try:
                        retcode = self.minip_process_1.wait(timeout=10)  # Timeout after 10 seconds
                    except subprocess.TimeoutExpired:
                        self.log.info("Process did not terminate in time, killing it forcefully.")
                        self.minip_process_1.kill()
                        retcode = self.minip_process_1.wait()  # Wait again after killing
                    self.log.info(f"Process terminated with return code: {retcode}")
                    print(f"Process terminated with return code: {retcode}")
                    if retcode not in [-15, 0]:  # If not terminated by SIGTERM or normal exit
                        self.minip_process_1.kill()
                        self.log.info("Process killed due to non-zero exit code.")
                except Exception as e:
                    self.log.error(f"Failed to terminate process: {e}")
                    print(f"Failed to terminate process: {e}")
                    
            
            if self.minip_process_2 is not None:
                try:
                    self.minip_process_2.terminate()
                    try:
                        retcode = self.minip_process_2.wait(timeout=10)  # Timeout after 10 seconds
                    except subprocess.TimeoutExpired:
                        self.log.info("Process did not terminate in time, killing it forcefully.")
                        self.minip_process_2.kill()
                        retcode = self.minip_process_2.wait()  # Wait again after killing
                    self.log.info(f"Process terminated with return code: {retcode}")
                    print(f"Process terminated with return code: {retcode}")
                    if retcode not in [-15, 0]:  # If not terminated by SIGTERM or normal exit
                        self.minip_process_2.kill()
                        self.log.info("Process killed due to non-zero exit code.")
                except Exception as e:
                    self.log.error(f"Failed to terminate process: {e}")
                    print(f"Failed to terminate process: {e}")

    def generate_tester_command(self, iteration, iclient):
        strace_cmd, gperf_cmd, timeout_cmd = super().generate_tester_command(
            iteration, iclient
        )

        os.environ["TIMEOUT_IVY"] = str(
            self.config["global_parameters"].getint("timeout")
        )
        timeout_cmd = ("sleep 5; " if not self.is_client else "") + timeout_cmd

        ENV_VAR["PROTOCOL_TESTED"] = self.current_protocol

        randomSeed = random.randint(0, 1000)
        random.seed(datetime.now())

        prefix = ""
        server_port = 4443
        client_port = 2 * iteration + 4987 + iclient

        if self.config["debug_parameters"].getboolean("gdb"):
            self.log.debug("Prefix added: gdb")
            # TODO refactor
            prefix = " gdb --args "
        if self.config["debug_parameters"].getboolean("ptrace"):
            self.log.debug("Prefix added: ptrace")
            # TODO refactor
            prefix = " ptrace "
        if self.config["debug_parameters"].getboolean("strace"):
            self.log.debug("Prefix added: strace")
            # TODO refactor
            prefix = strace_cmd + " "

        print(self.name)

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
                + (
                    (" " + strace_cmd)
                    if self.config["debug_parameters"].getboolean("ptrace")
                    else ""
                )
                + (
                    (" " + gperf_cmd)
                    if self.config["debug_parameters"].getboolean("gperf")
                    else ""
                )
                + " "
            )
        if self.config["net_parameters"].getboolean("vnet"):
            if self.is_mim:
                if self.config["vnet_parameters"].getboolean("bridged"):
                    ip_client = 0x0A000002
                    ip_server = 0x0A000003
                else:
                    ip_server = 0x0A000004
                    ip_client = 0x0A000002
            elif self.is_attacker_client:
                ip_client = 0x0A000002
                ip_server = 0x0A000003
            elif self.is_attacker_server:
                ip_client = 0x0A000002
                ip_server = 0x0A000003
            else:
                ip_server = 0x0A000002 if not self.is_client else 0x0A000001
                ip_client = 0x0A000001 if not self.is_client else 0x0A000002
                
        elif self.config["net_parameters"].getboolean("shadow"):
            ip_server = 0x0B000002 if not self.is_client else 0x0B000001
            ip_client = 0x0B000001 if not self.is_client else 0x0B000002
        else:
            # prefix = strace_cmd + " "
            ip_server = 0x7F000001
            ip_client = ip_server

        self.log.debug(f"Prefix of tester command: {prefix}")

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
