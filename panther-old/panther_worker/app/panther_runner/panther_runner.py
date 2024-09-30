import glob
import os
import sys
import logging
import progressbar
import subprocess
import time
import socket

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from panther_utils.panther_constant import *
from logger.CustomFormatter import ch
import shutil
from panther_utils.panther_vnet import *

# TODO super class
class Runner:
    def __init__(
        self, config, protocol_config, current_protocol, implems, executed_test=[]
    ):
        # Setup logger
        self.log = logging.getLogger("panther-runner")
        self.log.setLevel(int(os.environ["LOG_LEVEL"]))
        # # if (self.log.hasHandlers()):
        # #     self.log.handlers.clear()
        # self.log.addHandler(ch)
        # self.log.propagate = False

        self.protocol_conf = protocol_config
        self.apt_conf = None

        # Setup configuration
        self.current_protocol = current_protocol
        self.config = config
        self.log.debug("Protocol:        " + self.current_protocol)
        self.log.debug("Implementations: " + str(implems))

        # TODO refactor
        # TODO enforce in this file
        self.iters = self.config["global_parameters"].getint(
            "iter"
        )  # Number of iteration per test

        self.test_pattern = "*"  # Test to launch regex, * match all test # TODO

        self.extra_args = []  # TODO
        self.executed_tests = executed_test
        self.nb_test_to_execute = 0
        for mode in self.executed_tests.keys():
            self.nb_test_to_execute += len(self.executed_tests[mode])
        self.current_executed_test_count = 0

        self.implems = implems

        self.webapp_ip = socket.gethostbyname("panther-webapp")
        self.log.debug(f"IP panther-webapp: {self.webapp_ip}")
        self.log.debug(f"Number of test to execute: {self.nb_test_to_execute}")
        self.log.debug(
            f"Total number of test to execute: {self.nb_test_to_execute * self.config['global_parameters'].getint('iter')}"
        )

        # TODO make more general
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
        """
        Save shadow binaries for the given implementation and test.

        Parameters:
        implem (str): Implementation name.
        test (object): Test object containing test details.
        run_id (int): Unique run identifier.
        """
        if not self.config["net_parameters"].getboolean("shadow"):
            return

        self.log.info("Save shadow binaries:")

        try:
            binary_path, binary_name = self.get_binary_details(implem, test.mode)
            self.copy_file(
                binary_path,
                os.path.join(
                    self.config["global_parameters"]["dir"], str(run_id), binary_name
                ),
            )

            test_path = os.path.join(
                self.config["global_parameters"]["build_dir"], test.name
            )
            dest_test_path = os.path.join(
                self.config["global_parameters"]["dir"], str(run_id), test.name
            )
            self.copy_file(test_path, dest_test_path)

        except Exception as e:
            self.log.error(f"Failed to save shadow binaries: {e}")

    def get_binary_details(self, implem, mode):
        """
        Get binary path and name for the given implementation and mode.

        Parameters:
        implem (str): Implementation name.
        mode (str): Mode of the test (client/server).

        Returns:
            tuple: (binary_path, binary_name)
        """
        index = 0 if mode == "client" else 1
        binary_dir = self.implems[implem][index][implem]["binary-dir"]
        binary_name = self.implems[implem][index][implem]["binary-name"]

        if self.current_protocol == "apt":
            current_protocol = self.apt_conf["protocol_origins"][implem]
        else:
            current_protocol = self.current_protocol

        binary_path = (
            binary_dir.replace(
                "$IMPLEM_DIR", IMPLEM_DIR.replace("$PROT", current_protocol)
            ).replace("$MODEL_DIR", MODEL_DIR)
            + "/"
            + binary_name.replace(
                "$IMPLEM_DIR", IMPLEM_DIR.replace("$PROT", current_protocol)
            )
            .replace("$MODEL_DIR", MODEL_DIR)
            .split(" ")[-1]
        )

        binary_name = binary_name.split("/")[-1].split(" ")[-1]
        return binary_path, binary_name

    def copy_file(self, src, dst):
        """
        Copy a file from source to destination.

        Parameters:
        src (str): Source file path.
        dst (str): Destination file path.
        """
        self.log.info(f"Copy file: {src} to {dst}")
        shutil.copyfile(src, dst)

    # Return dictionnary of paths according to possible location
    # TODO make more robust
    def get_implementation_dir(self, implem):
        if self.current_protocol == "apt":
            current_protocol = self.apt_conf["protocol_origins"][implem]
        else:
            current_protocol = self.current_protocol
        if "-" in current_protocol:
            implem_dir_server = []
            implem_dir_client = []  
            protocols = current_protocol.split("-") 
            implementations = implem.split("-")
            for p in range(len(protocols)):
                implem_dir_server.append(
                    self.implems[implementations[p]][0][implementations[p]]["binary-dir"].replace(
                        "$IMPLEM_DIR",
                        IMPLEM_DIR.replace("$PROT", protocols[p]).replace(
                            "$MODEL_DIR", MODEL_DIR
                        ),
                    )
                )
                implem_dir_client.append(
                    self.implems[implementations[p]][1][implementations[p]]["binary-dir"].replace(
                        "$IMPLEM_DIR",
                        IMPLEM_DIR.replace("$PROT", protocols[p]).replace(
                            "$MODEL_DIR", MODEL_DIR
                        ),
                    )
                )
            return implem_dir_server, implem_dir_client
        else:
            return self.implems[implem][0][implem]["binary-dir"].replace(
                "$IMPLEM_DIR",
                IMPLEM_DIR.replace("$PROT", current_protocol).replace(
                    "$MODEL_DIR", MODEL_DIR
                ),
            ), self.implems[implem][1][implem]["binary-dir"].replace(
                "$IMPLEM_DIR",
                IMPLEM_DIR.replace("$PROT", current_protocol).replace(
                    "$MODEL_DIR", MODEL_DIR
                ),
            )

    def start_tshark(self, interfaces, pcap_protocol):
        for ns, interface, pcap_file in interfaces:
            if self.config["net_parameters"].getboolean("vnet"):
                cmd = ["tshark", "-w", pcap_file, "-i", interface]
            else:
                cmd = ["tshark", "-w", pcap_file, "-i", interface, "-f", pcap_protocol]
            if ns:
                cmd = ["ip", "netns", "exec", ns] + cmd
            p = subprocess.Popen(cmd, stdout=sys.stdout)
            self.log.info(
                f"Started tshark for {ns}:{interface} capturing to {pcap_file}"
            )
        return p

    def record_pcap(self, pcap_name):
        self.log.info("Start tshark pcap recording")
        # time.sleep(10) # for server test
        # TODO kill entual old quic implem
        if self.current_protocol == "apt":
            current_protocol = self.apt_conf["protocol_origins"][
                self.current_implementation
            ]
        else:
            current_protocol = self.current_protocol

        if "-" in current_protocol:
            pcap_protocol = "udp"
        else:
            pcap_protocol = self.protocol_conf[current_protocol + "_parameters"]["protocol"]

                
        if self.config["net_parameters"].getboolean("vnet"):
            if self.config["vnet_parameters"].getboolean("mitm"):
                if self.config["vnet_parameters"].getboolean("bridged"):
                    interfaces = [
                        ("ivy", "lo", pcap_name),
                        (
                            "tested_client",
                            "lo",
                            pcap_name.replace("ivy_lo_", "client_lo_"),
                        ),
                        (
                            "tested_server",
                            "lo",
                            pcap_name.replace("ivy_lo_", "server_lo_"),
                        ),
                        ("ivy", "veth_ivy", pcap_name.replace("ivy_lo_", "ivy_veth_")),
                        (
                            "tested_client",
                            "veth_client",
                            pcap_name.replace("ivy_lo_", "client_veth_"),
                        ),
                        (
                            "tested_server",
                            "veth_server",
                            pcap_name.replace("ivy_lo_", "server_veth_"),
                        ),
                        (
                            "tested_tclient",
                            "veth_tclient",
                            pcap_name.replace("ivy_lo_", "targ_client_veth_"),
                        ),
                        (
                            "tested_tserver",
                            "veth_tserver",
                            pcap_name.replace("ivy_lo_", "targ_server_veth_"),
                        ),
                        ("", "br_ivy", pcap_name.replace("ivy_lo_", "br_ivy_")),
                        ("", "br_client", pcap_name.replace("ivy_lo_", "br_client_")),
                        ("", "br_server", pcap_name.replace("ivy_lo_", "br_server_")),
                        ("", "br_tserver", pcap_name.replace("ivy_lo_", "br_targ_client_")),
                        ("", "br_tclient", pcap_name.replace("ivy_lo_", "br_targ_server_")),
                    ]
                else:
                    interfaces = [
                        ("ivy", "lo", pcap_name),
                        (
                            "tested_client",
                            "lo",
                            pcap_name.replace("ivy_lo_", "client_lo_"),
                        ),
                        (
                            "tested_server",
                            "lo",
                            pcap_name.replace("ivy_lo_", "server_lo_"),
                        ),
                        (
                            "ivy",
                            "ivy_client",
                            pcap_name.replace("ivy_lo_", "ivy_client_"),
                        ),
                        (
                            "ivy",
                            "ivy_server",
                            pcap_name.replace("ivy_lo_", "ivy_server_"),
                        ),
                        (
                            "tested_client",
                            "client_ivy",
                            pcap_name.replace("ivy_lo_", "client_"),
                        ),
                        (
                            "tested_server",
                            "server_ivy",
                            pcap_name.replace("ivy_lo_", "server_"),
                        ),
                        (
                            "tested_client",
                            "client_server",
                            pcap_name.replace("ivy_lo_", "client_server_"),
                        ),
                        (
                            "tested_server",
                            "server_client",
                            pcap_name.replace("ivy_lo_", "server_client_"),
                        ),
                    ]
            else:
                interfaces = [
                    ("ivy", "lo", pcap_name),
                    ("implem", "lo", pcap_name.replace("ivy_lo_", "implem_lo_")),
                    ("ivy", "ivy_client", pcap_name.replace("ivy_lo_", "ivy_client_")),
                    (
                        "implem",
                        "implem_client",
                        pcap_name.replace("ivy_lo_", "implem_client_"),
                    ),
                ]
        elif self.config["net_parameters"].getboolean("shadow"):
            return None
        else:
            interfaces = [("", "lo", pcap_name)]

        p = self.start_tshark(interfaces, pcap_protocol)
        time.sleep(3)  # TODO .wait() ?
        return p

    def config_pcap(self, ivy_dir, implem, test):
        def prepare_pcap_files(base_name, suffixes):
            for suffix in suffixes:
                file = base_name.replace("ivy_lo_", suffix)
                open(file, mode="w").close()
                subprocess.Popen(
                    f"/bin/chmod o=xw {file}",
                    shell=True,
                    executable="/bin/bash",
                ).wait()

        if self.config["net_parameters"].getboolean("vnet"):
            if self.config["vnet_parameters"].getboolean("mitm"):
                if self.config["vnet_parameters"].getboolean("bridged"):
                    pcap_name = (
                        ivy_dir
                        + "/ivy_lo_"
                        + implem
                        + "_"
                        + test.replace(".ivy", "")
                        + ".pcap"
                    )
                    suffixes = [
                        "ivy_lo_",
                        "target_client_lo_",
                        "target_server_lo_",
                        "client_lo_",
                        "server_lo_",
                        "ivy_veth_",
                        "target_client_veth_",
                        "target_server_veth_",
                        "client_veth_",
                        "server_veth_",
                        "br_ivy_",
                        "br_client_",
                        "br_server_",
                        "br_targ_client_",
                        "br_targ_server_",
                    ]
                    prepare_pcap_files(pcap_name, suffixes)
                else:
                    pcap_name = (
                        ivy_dir
                        + "/ivy_lo_"
                        + implem
                        + "_"
                        + test.replace(".ivy", "")
                        + ".pcap"
                    )
                    suffixes = [
                        "ivy_lo_",
                        "client_lo_",
                        "server_lo_",
                        "ivy_client_",
                        "ivy_server_",
                        "client_",
                        "server_",
                        "client_server_",
                        "server_client_",
                    ]
                    prepare_pcap_files(pcap_name, suffixes)
            else:
                pcap_name = (
                    ivy_dir
                    + "/ivy_lo_"
                    + implem
                    + "_"
                    + test.replace(".ivy", "")
                    + ".pcap"
                )
                suffixes = ["ivy_lo_", "ivy_ivy_", "implem_lo_", "implem_"]
                prepare_pcap_files(pcap_name, suffixes)
        else:
            pcap_name = ivy_dir + "/" + implem + "_" + test + ".pcap"
            open(pcap_name, mode="w").close()
            subprocess.Popen(
                f"/bin/chmod o=xw {pcap_name}", shell=True, executable="/bin/bash"
            ).wait()
        return pcap_name

    def create_exp_folder(self):
        folders = [
            os.path.join(self.config["global_parameters"]["dir"], f)
            for f in os.listdir(self.config["global_parameters"]["dir"])
            if os.path.isdir(os.path.join(self.config["global_parameters"]["dir"], f))
        ]
        pcap_i = len(folders) + 1
        self.log.info(f"Experiment number: {pcap_i}")
        ivy_dir = os.path.join(self.config["global_parameters"]["dir"], str(pcap_i))
        self.log.info(f"Create folder: {ivy_dir}")
        os.mkdir(ivy_dir)
        return ivy_dir, pcap_i

    def setup_exp(self, implem):
        if self.config["global_parameters"]["dir"] is None:
            self.log.error("ERROR in implementation directory")
            exit(0)

        # test, run_id, pcap_name,iteration,j
        # Put an array of eventual extra argument for the test (TODO)
        # self.extra_args = [opt_name+'='+opt_val for opt_name,opt_val in self.ivy_options.items() if opt_val is not None]
        implem_dir_server, implem_dir_client = self.get_implementation_dir(implem)

        self.log.info("Server implementation directory: {}".format(implem_dir_server))
        self.log.info("Client implementation directory: {}".format(implem_dir_client))
        return implem_dir_server, implem_dir_client

    def get_exp_stats(self, implem, test, run_id, pcap_name, i):
        raise NotImplementedError

    def save_shadow_res(self, test, i, pcap_name, run_id):
        if self.config["net_parameters"].getboolean("shadow"):
            self.log.info("Saving Shadow results")
            shadow_data_src = "/app/shadow.data"
            shadow_data_dst = os.path.join(
                self.config["global_parameters"]["dir"], str(run_id), "shadow.data"
            )
            self.log.debug(
                f"Copying entire folder: {shadow_data_src} to {shadow_data_dst}"
            )
            shutil.copytree(shadow_data_src, shadow_data_dst)
            shutil.copyfile(
                "/app/shadow.log",
                os.path.join(
                    self.config["global_parameters"]["dir"], str(run_id), "shadow.log"
                ),
            )
            shutil.rmtree(shadow_data_src)
            os.remove("/app/shadow.log")
            shadow_data_dir = os.path.join(
                self.config["global_parameters"]["dir"], str(run_id), "shadow.data"
            )
            host_dirs = {
                "client": os.path.join(shadow_data_dir, "hosts/client"),
                "server": os.path.join(shadow_data_dir, "hosts/server"),
            }
            dest_dir = os.path.join(
                self.config["global_parameters"]["dir"], str(run_id)
            )

            if "client" in test.mode:
                patterns = [
                    ("client", "*.stdout", test.name + str(i) + ".out"),
                    ("client", "*.stderr", test.name + str(i) + ".err"),
                    ("server", "*.stdout", test.name + str(i) + ".iev"),
                    ("server", "*.stderr", "ivy_stderr.txt"),
                ]
            else:
                patterns = [
                    ("server", "*.stdout", test.name + str(i) + ".out"),
                    ("server", "*.stderr", test.name + str(i) + ".err"),
                    ("client", "*.stdout", test.name + str(i) + ".iev"),
                    ("client", "*.stderr", "ivy_stderr.txt"),
                ]

            for mode, pattern, dest_filename in patterns:
                self.log.debug(f"Matching pattern {pattern} in {host_dirs[mode]}")
                for file_path in glob.glob(os.path.join(host_dirs[mode], pattern)):
                    self.log.debug(
                        f"Copy {file_path} to {os.path.join(dest_dir, dest_filename)}"
                    )
                    shutil.copy(file_path, os.path.join(dest_dir, dest_filename))

            if "client" in test.mode:
                self.log.debug(f"Copy eth0.pcap to {pcap_name}")
                shutil.copy(
                    os.path.join(shadow_data_dir, "hosts/server/eth0.pcap"), pcap_name
                )
            elif "server" in test.mode:
                self.log.debug(f"Copy eth0.pcap to {pcap_name}")
                shutil.copy(
                    os.path.join(shadow_data_dir, "hosts/client/eth0.pcap"), pcap_name
                )

    def run_exp(self, implem):
        raise NotImplementedError
