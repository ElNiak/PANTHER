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
        target_protocol=None,
        implem_dir_server_target=None,
        implem_dir_client_target=None,
        target_implem_conf=None,
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
        self.target_protocol = target_protocol
        self.target_implem_conf = target_implem_conf
        self.implem_dir_server_target = implem_dir_server_target
        self.implem_dir_client_target = implem_dir_client_target
        
        self.log.info(f"APT configuration: {self.apt_conf}")
        self.log.info(f"APT implementation configuration: {self.implem_conf}")
        self.log.info(f"APT target implementation configuration: {self.target_implem_conf}")
        self.log.info(f"APT implementation: {self.implementation_name}")
        self.log.info(f"APT protocol: {self.current_protocol}")
        self.log.info(f"APT target protocol: {self.target_protocol}")
        self.log.info(f"APT server directory: {self.implem_dir_server}")
        self.log.info(f"APT client directory: {self.implem_dir_client}")
        self.log.info(f"APT server target directory: {implem_dir_server_target}")
        self.log.info(f"APT client target directory: {implem_dir_client_target}")
        
        if not target_protocol:
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
        else:
            implementation_name = implementation_name.split("-")
            if target_protocol == "quic":
                self.quic_tester = QUICIvyTest(
                    args,
                    implem_dir_server_target,
                    implem_dir_client_target,
                    extra_args,
                    implementation_name[1],
                    mode,
                    config,
                    protocol_conf,
                    target_implem_conf,
                    current_protocol,
                )
                self.minip_tester = MiniPIvyTest(
                    args,
                    implem_dir_server,
                    implem_dir_client,
                    extra_args,
                    implementation_name[0],
                    mode,
                    config,
                    protocol_conf,
                    implem_conf,
                    current_protocol,
                )
            if target_protocol == "minip":
                self.quic_tester = QUICIvyTest(
                    args,
                    implem_dir_server,
                    implem_dir_client,
                    extra_args,
                    implementation_name[0],
                    mode,
                    config,
                    protocol_conf,
                    implem_conf,
                    current_protocol,
                )
                self.minip_tester = MiniPIvyTest(
                    args,
                    implem_dir_server_target,
                    implem_dir_client_target,
                    extra_args,
                    implementation_name[1],
                    mode,
                    config,
                    protocol_conf,
                    target_implem_conf,
                    current_protocol,
                )

    def update_implementation_command(self, i):
        if self.current_protocol == "apt":
            current_protocol = self.apt_conf["protocol_origins"][
                self.implementation_name
            ]
        else:
            current_protocol = self.current_protocol
        if "-" in current_protocol:   
            protocols = current_protocol.split("-") 
            updated_implementations_server = []
            updated_implementations_client = []
            if "quic" in protocols:
                self.log.info("Updating command for quic implementation:")
                self.quic_tester.__dict__.update(self.__dict__)
                super().__dict__.update(self.__dict__)
                # self.quic_tester.implem_cmd = self.implem_cmd if protocols[0] == "quic" else self.target_implem_cmd
                return self.quic_tester.update_implementation_command(i)
            if "minip" in protocols:
                self.log.info("Updating command for minip implementation:")
                self.minip_tester.__dict__.update(self.__dict__)
                super().__dict__.update(self.__dict__)
                # self.minip_tester.implem_cmd = self.implem_cmd if protocols[0] == "minip" else self.target_implem_cmd
                return self.minip_tester.update_implementation_command(i)
            
        elif current_protocol == "quic":
            self.log.info("Updating command for quic implementation:")
            self.quic_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            return self.quic_tester.update_implementation_command(i)
        elif current_protocol == "minip":
            self.log.info("Updating command for minip implementation:")
            self.minip_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            return self.minip_tester.update_implementation_command(i)
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
        if "-" in current_protocol:   
            protocols = current_protocol.split("-") 
            files = []
    
            implementations = self.implementation_name.split("-")
            for p in range(len(protocols)):
                if protocols[p] == "quic":
                    self.log.info("Generating shadow command for quic implementation:")
                    self.quic_tester.__dict__.update(self.__dict__)
                    super().__dict__.update(self.__dict__)
                    self.quic_tester.implem_conf = self.implem_conf if p == 0 else self.target_implem_conf
                    files += self.quic_tester.generate_shadow_config()
                    self.quic_tester.__dict__.update(self.__dict__)
                    super().__dict__.update(self.__dict__)
                if protocols[p] == "minip":
                    self.log.info("Generating shadow command for minip implementation:")
                    self.minip_tester.__dict__.update(self.__dict__)
                    super().__dict__.update(self.__dict__)
                    self.minip_tester.implem_conf = self.implem_conf if p == 0 else self.target_implem_conf
                    files += self.minip_tester.generate_shadow_config()
                    self.minip_tester.__dict__.update(self.__dict__)
                    super().__dict__.update(self.__dict__)
            return files
        else:
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
        self.log.info(f"Generating command for APT implementation: {self.implementation_name}")
        if self.current_protocol == "apt":
            current_protocol = self.apt_conf["protocol_origins"][
                self.implementation_name
            ]
        else:
            current_protocol = self.current_protocol
        self.log.info(f"Current protocol: {current_protocol}")
        
        if "-" in current_protocol:   
            protocols = current_protocol.split("-") 
            implems = []
    
            implementations = self.implementation_name.split("-")
            for p in range(len(protocols)):
                self.log.info(f"Protocol: {protocols[p]}")
                if protocols[p] == "quic":
                    self.log.info("Generating command for quic implementation:")
                    self.quic_tester.__dict__.update(self.__dict__)
                    super().__dict__.update(self.__dict__)
                    self.quic_tester.implem_conf = self.implem_conf if p == 0 else self.target_implem_conf
                    self.quic_tester.implementation_name = implementations[p]
                    implems = self.quic_tester.generate_implementation_command()
                    self.log.info(f"Implem command: {implems}")
                    if p == 0:
                        self.implem_cmd          = implems[0]
                        self.implem_cmd_opposite = implems[1]
                        # self.quic_tester.implem_cmd = self.implem_cmd
                        # self.quic_tester.implem_cmd_opposite = self.implem_cmd_opposite
                    else:
                        self.target_implem_cmd          = implems[0]
                        self.target_implem_cmd_opposite = implems[1]
                        # self.quic_tester.implem_cmd = self.target_implem_cmd
                        # self.quic_tester.implem_cmd_opposite = implems[1]
                    self.quic_tester.__dict__.update(self.__dict__)
                    # self.log.info(f"Implem command: {implems}")
                    # self.log.info(f"Implem implem_cmd: {self.implem_cmd}")
                    # self.log.info(f"Implem target_implem_cmd: {self.target_implem_cmd}")
                    super().__dict__.update(self.__dict__)
                elif protocols[p] == "minip":
                    self.log.info("Generating command for minip implementation:")
                    self.minip_tester.__dict__.update(self.__dict__)
                    super().__dict__.update(self.__dict__)
                    self.minip_tester.implem_conf = self.implem_conf if p == 0 else self.target_implem_conf
                    self.minip_tester.implementation_name = implementations[p]
                    implems = self.minip_tester.generate_implementation_command()
                    if p == 0:
                        self.implem_cmd          = implems[0]
                        self.implem_cmd_opposite = implems[1]
                        # self.quic_tester.implem_cmd = self.implem_cmd
                        # self.quic_tester.implem_cmd_opposite = self.implem_cmd_opposite
                    else:
                        self.target_implem_cmd          = implems[0]
                        self.target_implem_cmd_opposite = implems[1]
                    # self.log.info(f"Implem command: {implems}")
                    # self.log.info(f"Implem implem_cmd: {self.implem_cmd}")
                    # self.log.info(f"Implem target_implem_cmd: {self.target_implem_cmd}")
                    self.minip_tester.__dict__.update(self.__dict__)
                    super().__dict__.update(self.__dict__)
            self.log.info(f"Implem command: {self.implem_cmd}")
            self.log.info(f"Implem command opposite: {self.implem_cmd_opposite}")
            return [self.implem_cmd, self.implem_cmd_opposite]
        else:
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
        if "-" in current_protocol:   
            protocols = current_protocol.split("-") 
            implems = []
            
            res = []
    
            implementations = self.implementation_name.split("-")
            # if protocols[0] == "quic":
            self.log.info("Starting tester for system implementation:")
            self.quic_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            self.quic_tester.implementation_name = implementations[1]
            self.quic_tester.start_tester(iteration, iev, i)
            # if  protocols[0]  == "minip":
            #     self.log.info("Starting tester for minip implementation:")
            #     self.minip_tester.__dict__.update(self.__dict__)
            #     super().__dict__.update(self.__dict__)
            #     self.minip_tester.implementation_name = implementations[0]
            #     return self.minip_tester.start_tester(iteration, iev, i)
        else:
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
        if "-" in current_protocol:   
            protocols = current_protocol.split("-") 
            implems = []
    
            implementations = self.implementation_name.split("-")
            res = []
            self.log.info(f"Protocols: {protocols}")
            if protocols[0] == "quic":
                self.log.info("Start quic implementation:")
                self.log.info(f"APT implemententation command {self.implem_cmd}")
                self.quic_tester.__dict__.update(self.__dict__)
                super().__dict__.update(self.__dict__)
                self.log.info(
                    f"QUIC implemententation command {self.quic_tester.implem_cmd}"
                )
                self.quic_tester.start_implementation(i, out, err)
            elif  protocols[0]  == "minip":
                self.log.info("Start minip implementation:")
                self.log.info(f"APT implemententation command {self.implem_cmd}")
                self.minip_tester.__dict__.update(self.__dict__)
                super().__dict__.update(self.__dict__)
                self.log.info(
                    f"MINIP implemententation command {self.minip_tester.implem_cmd}"
                )
                self.minip_tester.start_implementation(i, out, err)
            if protocols[1] == "quic":
                self.log.info("Start quic target implementation:")
                self.log.info(f"APT implemententation target command {self.target_implem_cmd}")
                self.quic_tester.__dict__.update(self.__dict__)
                super().__dict__.update(self.__dict__)
                self.quic_tester.implem_cmd = self.target_implem_cmd
                self.quic_tester.implem_cmd_opposite = self.target_implem_cmd_opposite
                self.log.info(
                    f"QUIC implemententation command {self.quic_tester.implem_cmd}"
                )
                self.quic_tester.start_target_implementation(i, out, err)
            elif  protocols[1]  == "minip":
                self.log.info("Start minip target implementation:")
                self.log.info(f"APT implemententation target command {self.target_implem_cmd}")
                self.minip_tester.__dict__.update(self.__dict__)
                super().__dict__.update(self.__dict__)
                self.minip_tester.implem_cmd = self.target_implem_cmd
                self.minip_tester.implem_cmd_opposite = self.target_implem_cmd_opposite
                
                self.minip_tester.implem_dir_server = self.implem_dir_server_target
                self.minip_tester.implem_dir_client = self.implem_dir_client_target
                self.log.info(
                    f"MINIP implemententation command {self.minip_tester.implem_cmd}"
                )
                self.minip_tester.start_target_implementation(i, out, err)
            return res
        else:
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
        if self.current_protocol == "apt":
            current_protocol = self.apt_conf["protocol_origins"][
                self.implementation_name
            ]
        else:
            current_protocol = self.current_protocol
            
        if  "quic" in current_protocol:
            self.log.info("stop quic implementation:")        
            self.quic_tester.stop_processes()
        if "minip" in current_protocol:
            self.log.info("stop minip implementation:")
            self.minip_tester.stop_processes()

    def generate_tester_command(self, iteration, iclient):
        if self.current_protocol == "apt":
            current_protocol = self.apt_conf["protocol_origins"][
                self.implementation_name
            ]
        else:
            current_protocol = self.current_protocol
        if current_protocol == "quic" or "-" in current_protocol: # TODO
            command = self.quic_tester.generate_tester_command(iteration, iclient)
            self.quic_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            return command
        if current_protocol == "minip":
            command = self.minip_tester.generate_tester_command(iteration, iclient)
            self.minip_tester.__dict__.update(self.__dict__)
            super().__dict__.update(self.__dict__)
            return command
