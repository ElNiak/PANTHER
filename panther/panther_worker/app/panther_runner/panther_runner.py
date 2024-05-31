import os
import re
import sys
import configparser
import logging
import progressbar
import subprocess
import time
import socket

from panther_utils.panther_constant import *
from logger.CustomFormatter import ch

# TODO super class
class Runner:
    def __init__(
        self, config, protocol_config, current_protocol, implems, executed_test=[]
    ):
        # Setup logger
        self.log = logging.getLogger("panther-runner")
        self.log.setLevel(logging.INFO)
        # if (self.log.hasHandlers()):
        #     self.log.handlers.clear()
        self.log.addHandler(ch)
        self.log.propagate = False

        # Setup configuration
        self.log.info("START SETUP CONFIGURATION")
        self.current_protocol = current_protocol
        self.config = config
        self.log.info("SELECTED PROTOCOL: " + self.current_protocol)
        self.protocol_conf = protocol_config
        self.log.info("END SETUP PROTOCOL PARAMETERS")

        # TODO refactor
        self.iters = self.config["global_parameters"].getint(
            "iter"
        )  # Number of iteration per test           # TODO enforce in this file
        self.test_pattern = "*"  # Test to launch regex, * match all test # TODO

        self.extra_args = []  # TODO
        self.executed_tests = executed_test
        self.nb_test_to_execute = 0
        for mode in self.executed_tests.keys():
            self.nb_test_to_execute += len(self.executed_tests[mode])
        self.current_executed_test_count = 0

        self.implems = implems

        self.webapp_ip = socket.gethostbyname("panther-webapp")
        print(self.webapp_ip)
        print(self.nb_test_to_execute)
        print(self.nb_test_to_execute * self.config["global_parameters"].getint("iter"))
        # TODO make less general
        if (
            "quic_server_test_0rtt" in executed_test
            or "quic_client_test_0rtt" in executed_test
        ):
            self.bar_total_test = progressbar.ProgressBar(
                max_value=(self.nb_test_to_execute + 2)
                * self.config["global_parameters"].getint("iter")
            )
        else:
            self.bar_total_test = progressbar.ProgressBar(
                max_value=self.nb_test_to_execute
                * self.config["global_parameters"].getint("iter")
            )

    def save_shadow_binaries(self, implem, test, run_id):
        # TODO save shadow yml for better reproductibiltiy
        if self.config["net_parameters"].getboolean("shadow"):
            self.log.info("Save shadow binaries:")
            if test.mode == "client":
                index = 0
            else:
                index = 1
            binary_path = (
                self.implems[implem][index][implem]["binary-dir"]
                .replace(
                    "$IMPLEM_DIR", IMPLEM_DIR.replace("$PROT", self.current_protocol)
                )
                .replace("$MODEL_DIR", MODEL_DIR)
                + "/"
                + self.implems[implem][index][implem]["binary-name"]
                .replace(
                    "$IMPLEM_DIR", IMPLEM_DIR.replace("$PROT", self.current_protocol)
                )
                .replace("$MODEL_DIR", MODEL_DIR)
                .split(" ")[-1]
            )
            binary_name = (
                self.implems[implem][index][implem]["binary-name"]
                .replace(
                    "$IMPLEM_DIR", IMPLEM_DIR.replace("$PROT", self.current_protocol)
                )
                .replace("$MODEL_DIR", MODEL_DIR)
                .split(" ")[-1]
                .split("/")[-1]
            )
            os.system(
                "cp "
                + binary_path
                + " "
                + self.config["global_parameters"]["dir"]
                + str(run_id)
                + "/"
                + binary_name
            )
            os.system(
                "cp "
                + self.config["global_parameters"]["build_dir"]
                + test.name
                + " "
                + self.config["global_parameters"]["dir"]
                + str(run_id)
                + "/"
                + test.name
            )

    # Return dictionnary of paths according to possible location
    # TODO make more robust
    def get_implementation_dir(self, implem):
        return self.implems[implem][0][implem]["binary-dir"].replace(
            "$IMPLEM_DIR", IMPLEM_DIR.replace("$PROT", self.current_protocol)
        ), self.implems[implem][1][implem]["binary-dir"].replace(
            "$IMPLEM_DIR", IMPLEM_DIR.replace("$PROT", self.current_protocol)
        )

    def record_pcap(self, pcap_name):
        self.log.info("Start thsark")
        # time.sleep(10) # for server test
        # TODO kill entual old quic implem
        if self.config["net_parameters"].getboolean("vnet"):
            interface = "lo"
            p = subprocess.Popen(
                [
                    "ip",
                    "netns",
                    "exec",
                    "ivy",
                    "tshark",
                    "-w",
                    pcap_name,
                    "-i",
                    interface,
                    "-f",
                    self.protocol_conf[self.current_protocol + "_parameters"][
                        "protocol"
                    ],
                ],
                stdout=sys.stdout,
            )
            p = subprocess.Popen(
                [
                    "ip",
                    "netns",
                    "exec",
                    "implem",
                    "tshark",
                    "-w",
                    pcap_name.replace("ivy_lo_", "implem_lo_"),
                    "-i",
                    interface,
                    "-f",
                    self.protocol_conf[self.current_protocol + "_parameters"][
                        "protocol"
                    ],
                ],
                stdout=sys.stdout,
            )
            interface = "ivy"
            p = subprocess.Popen(
                [
                    "ip",
                    "netns",
                    "exec",
                    "ivy",
                    "tshark",
                    "-w",
                    pcap_name.replace("ivy_lo_", "ivy_ivy_"),
                    "-i",
                    interface,
                    "-f",
                    self.protocol_conf[self.current_protocol + "_parameters"][
                        "protocol"
                    ],
                ],
                stdout=sys.stdout,
            )
            interface = "implem"
            p = subprocess.Popen(
                [
                    "ip",
                    "netns",
                    "exec",
                    "implem",
                    "tshark",
                    "-w",
                    pcap_name.replace("ivy_lo_", "implem_"),
                    "-i",
                    interface,
                    "-f",
                    self.protocol_conf[self.current_protocol + "_parameters"][
                        "protocol"
                    ],
                ],
                stdout=sys.stdout,
            )
        elif self.config["net_parameters"].getboolean("shadow"):
            p = None
        else:
            interface = "lo"
            p = subprocess.Popen(
                [
                    "sudo",
                    "tshark",
                    "-w",
                    pcap_name,
                    "-i",
                    interface,
                    "-f",
                    self.protocol_conf[self.current_protocol + "_parameters"][
                        "protocol"
                    ],
                ],
                stdout=sys.stdout,
            )
        time.sleep(3)  # TODO
        return p

    def config_pcap(self, ivy_dir, implem, test):
        if self.config["net_parameters"].getboolean("vnet"):
            pcap_name = (
                ivy_dir + "/ivy_lo_" + implem + "_" + test.replace(".ivy", "") + ".pcap"
            )
            subprocess.Popen(
                "touch " + pcap_name, shell=True, executable="/bin/bash"
            ).wait()
            subprocess.Popen(
                "sudo /bin/chmod o=xw " + pcap_name, shell=True, executable="/bin/bash"
            ).wait()
            subprocess.Popen(
                "touch " + pcap_name.replace("ivy_lo_", "ivy_ivy_"),
                shell=True,
                executable="/bin/bash",
            ).wait()
            subprocess.Popen(
                "touch " + pcap_name.replace("ivy_lo_", "implem_lo_"),
                shell=True,
                executable="/bin/bash",
            ).wait()
            subprocess.Popen(
                "sudo /bin/chmod o=xw " + pcap_name.replace("ivy_lo_", "ivy_ivy_"),
                shell=True,
                executable="/bin/bash",
            ).wait()
            subprocess.Popen(
                "sudo /bin/chmod o=xw " + pcap_name.replace("ivy_lo_", "implem_lo_"),
                shell=True,
                executable="/bin/bash",
            ).wait()
            subprocess.Popen(
                "touch " + pcap_name.replace("ivy_lo_", "implem_"),
                shell=True,
                executable="/bin/bash",
            ).wait()
            subprocess.Popen(
                "sudo /bin/chmod o=xw " + pcap_name.replace("ivy_lo_", "implem_"),
                shell=True,
                executable="/bin/bash",
            ).wait()
        else:
            pcap_name = ivy_dir + "/" + implem + "_" + test + ".pcap"
            subprocess.Popen(
                "touch " + pcap_name, shell=True, executable="/bin/bash"
            ).wait()
            subprocess.Popen(
                "sudo /bin/chmod o=xw " + pcap_name, shell=True, executable="/bin/bash"
            ).wait()
        return pcap_name

    def create_exp_folder(self):
        folders = [
            os.path.join(self.config["global_parameters"]["dir"], f)
            for f in os.listdir(self.config["global_parameters"]["dir"])
            if os.path.isdir(os.path.join(self.config["global_parameters"]["dir"], f))
        ]
        pcap_i = len(folders) + 1
        self.log.info(pcap_i)
        ivy_dir = self.config["global_parameters"]["dir"] + str(pcap_i)
        subprocess.Popen(
            "/bin/mkdir " + ivy_dir, shell=True, executable="/bin/bash"
        ).wait()
        return ivy_dir, pcap_i

    def setup_exp(self, implem):
        if self.config["global_parameters"]["dir"] is None:
            self.log.info("ERROR")
            exit(0)

        # test, run_id, pcap_name,iteration,j
        # Put an array of eventual extra argument for the test (TODO)
        # self.extra_args = [opt_name+'='+opt_val for opt_name,opt_val in self.ivy_options.items() if opt_val is not None]
        self.log.info("Get implementation directory:")
        implem_dir_server, implem_dir_client = self.get_implementation_dir(implem)

        self.log.info("Server implementation directory: {}".format(implem_dir_server))
        self.log.info("Client implementation directory: {}".format(implem_dir_client))
        return implem_dir_server, implem_dir_client

    def get_exp_stats(self, implem, test, run_id, pcap_name, i):
        raise NotImplementedError

    def save_shadow_res(self, test, i, pcap_name, run_id):
        if self.config["net_parameters"].getboolean("shadow"):
            self.log.info("Save shadow res:")
            self.log.info(
                "mv /app/shadow.data/ "
                + self.config["global_parameters"]["dir"]
                + str(run_id)
            )
            os.system(
                "mv /app/shadow.data/ "
                + self.config["global_parameters"]["dir"]
                + str(run_id)
            )
            os.system(
                "mv /app/shadow.log "
                + self.config["global_parameters"]["dir"]
                + str(run_id)
                + "/shadow.log"
            )
            os.system("rm " + pcap_name)
            os.system(
                "cp "
                + self.config["global_parameters"]["dir"]
                + str(run_id)
                + "/shadow.data/hosts/client/eth0.pcap "
                + pcap_name
            )
            if "client" in test.mode:  # TODO
                os.system(
                    "cat "
                    + self.config["global_parameters"]["dir"]
                    + str(run_id)
                    + "/shadow.data/hosts/server/*.stderr >>"
                    + os.path.join(
                        self.config["global_parameters"]["dir"] + str(run_id),
                        "ivy_stderr.txt",
                    )
                )
                os.system(
                    "cat "
                    + self.config["global_parameters"]["dir"]
                    + str(run_id)
                    + "/shadow.data/hosts/server/*.stdout >>"
                    + os.path.join(
                        self.config["global_parameters"]["dir"] + str(run_id),
                        test.name + str(i) + ".iev",
                    )
                )
                os.system(
                    "cat "
                    + self.config["global_parameters"]["dir"]
                    + str(run_id)
                    + "/shadow.data/hosts/client/*.stdout >>"
                    + os.path.join(
                        self.config["global_parameters"]["dir"] + str(run_id),
                        test.name + str(i) + ".out",
                    )
                )
                os.system(
                    "cat "
                    + self.config["global_parameters"]["dir"]
                    + str(run_id)
                    + "/shadow.data/hosts/client/*.stderr >>"
                    + os.path.join(
                        self.config["global_parameters"]["dir"] + str(run_id),
                        test.name + str(i) + ".err",
                    )
                )
            elif "server" in test.mode:
                os.system(
                    "cat "
                    + self.config["global_parameters"]["dir"]
                    + str(run_id)
                    + "/shadow.data/hosts/client/*.stderr >>"
                    + os.path.join(
                        self.config["global_parameters"]["dir"] + str(run_id),
                        "ivy_stderr.txt",
                    )
                )
                os.system(
                    "cat "
                    + self.config["global_parameters"]["dir"]
                    + str(run_id)
                    + "/shadow.data/hosts/client/*.stdout >> "
                    + os.path.join(
                        self.config["global_parameters"]["dir"] + str(run_id),
                        test.name + str(i) + ".iev",
                    )
                )
                os.system(
                    "cat "
                    + self.config["global_parameters"]["dir"]
                    + str(run_id)
                    + "/shadow.data/hosts/server/*.stdout >>"
                    + os.path.join(
                        self.config["global_parameters"]["dir"] + str(run_id),
                        test.name + str(i) + ".out",
                    )
                )
                os.system(
                    "cat "
                    + self.config["global_parameters"]["dir"]
                    + str(run_id)
                    + "/shadow.data/hosts/server/*.stderr >>"
                    + os.path.join(
                        self.config["global_parameters"]["dir"] + str(run_id),
                        test.name + str(i) + ".err",
                    )
                )

    def run_exp(self, implem):
        raise NotImplementedError
