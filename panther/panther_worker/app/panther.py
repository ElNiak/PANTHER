import logging
import subprocess
import sys
import tracemalloc

import requests
from plantuml import PlantUML
import configparser
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from panther_utils.panther_constant import *
from panther_config.panther_config import *

from panther_runner.panther_apt_runner import APTRunner
from panther_runner.panther_quic_runner import QUICRunner
from panther_runner.panther_minip_runner import MiniPRunner

from logger.CustomFormatter import ch

from argument_parser.ArgumentParserRunner import ArgumentParserRunner

DEBUG = True


class Panther:
    def __init__(self):
        # Setup cargo
        subprocess.Popen("", shell=True, executable="/bin/bash").wait()  # TODO source

        # Setup logger
        self.log = logging.getLogger("panther")
        self.log.setLevel(logging.INFO)
        if self.log.hasHandlers():
            self.log.handlers.clear()
        self.log.addHandler(ch)
        self.log.propagate = False

        # Setup argument parser
        self.args = ArgumentParserRunner().parse_arguments()

        # Setup environment variables
        for env_var in ENV_VAR:
            os.environ[env_var] = str(ENV_VAR[env_var])
            if DEBUG:
                self.log.info("ENV_VAR=" + env_var)
                self.log.info("ENV_VAL=" + str(ENV_VAR[env_var]))

        # Setup configuration
        self.log.info("Getting Experiment configuration:")
        (
            self.supported_protocols,
            self.current_protocol,
            self.tests_enabled,
            self.conf_implementation_enable,
            self.implementation_enable,
            self.protocol_model_path,
            self.protocol_results_path,
            self.protocol_test_path,
            self.config,
            self.protocol_conf,
        ) = get_experiment_config(None, False, False)

        self.log.info("Selected protocol: " + self.current_protocol)

        with os.scandir(self.protocol_results_path) as entries:
            self.total_exp_in_dir = sum(1 for entry in entries if entry.is_dir())
        self.current_exp_path = os.path.join(
            self.protocol_results_path, str(self.total_exp_in_dir)
        )

        self.available_test_modes = []
        self.included_files = list()

        if self.config["debug_parameters"].getboolean("memprof"):
            self.memory_snapshots = []

    def find_ivy_files(self):
        """
        Recursively find all .ivy files in the specified folder and its subfolders, excluding those with 'test' in the filename.
        
        :param root_folder: The root folder to start the search from.
        :return: A list of paths to the found .ivy files.
        """
        ivy_files = []
        for dirpath, _, filenames in os.walk(self.protocol_model_path):
            for f in filenames:
                if f.endswith(".ivy") and "test" not in f:
                    ivy_files.append(os.path.join(dirpath, f))
        return ivy_files


    def update_ivy_tool(self):
        # Note we use subprocess in order to get sudo rights
        os.chdir(SOURCE_DIR + "/panther-ivy/")
        execute_command("sudo python2.7 setup.py install")
        execute_command("sudo cp lib/libz3.so submodules/z3/build/python/z3")

        # TODO extract variable for path -> put in module path
        self.log.info(
            'Update "include" path of python with updated version of the TLS project from \n\t'
            + IVY_INCLUDE_PATH
        )
        files = [
            os.path.join(IVY_INCLUDE_PATH, f)
            for f in os.listdir(IVY_INCLUDE_PATH)
            if os.path.isfile(os.path.join(IVY_INCLUDE_PATH, f)) and f.endswith(".ivy")
        ]

        self.log.info(
            "Copying file to /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/"
        )
        for file in files:
            self.log.info("* " + file)
            execute_command(
                "sudo /bin/cp "
                + file
                + " /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/"
            )
        
        os.chdir(
            "/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/"
        )
        execute_command(
            "sudo /bin/cp -f -a "
            + "/app/panther-ivy/lib/*.a /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/lib",
            must_pass=False
        )

        if self.config["verified_protocol"].getboolean("quic"):
            self.log.info("Copying QUIC libraries")
            # TODO picotls add submodule
            execute_command(
                "sudo /bin/cp -f -a "
                + "/app/implementations/quic-implementations/picotls/*.a /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/lib"
            )
            execute_command(
                "sudo /bin/cp -f -a "
                + "/app/implementations/quic-implementations/picotls/*.a "
                + "/app/panther-ivy/ivy/lib"
            )
            execute_command(
                "sudo /bin/cp -f "
                + "/app/implementations/quic-implementations/picotls/include/picotls.h /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include"
            )
            execute_command(
                "sudo /bin/cp -f "
                + "/app/implementations/quic-implementations/picotls/include/picotls.h "
                + "/app/panther-ivy/ivy/include"
            )
            execute_command(
                "sudo /bin/cp -r -f "
                + "/app/implementations/quic-implementations/picotls/include/picotls/. /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/picotls"
            )

        os.chdir(SOURCE_DIR)

    def setup_ivy_model(self):
        self.log.info(
            'Update "include" path of python with updated version of the project from \n\t'
            + self.protocol_model_path
        )
        
        files = self.find_ivy_files()
        for file in files:
            self.log.info("* " + file)
            self.included_files.append(file)
            execute_command(
                "sudo /bin/cp "
                + file
                + " /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/"
            )
            
        if self.config["verified_protocol"].getboolean("quic"):
            execute_command(
                "sudo /bin/cp "
                + self.protocol_model_path 
                + "/quic_utils/quic_ser_deser.h"
                + " /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/",
            )

    def remove_includes(self):
        self.log.info('Reset "include" path of python')
        for file in self.included_files:
            self.log.info("* " + file)
            nameFileShort = file.split("/")[-1]
            execute_command(
                "sudo /bin/rm /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/"
                + nameFileShort
            )
        self.included_files = list()

    def build_tests(self, test_to_do={}):
        self.log.info("Number of test to compile: " + str(len(test_to_do)))
        self.log.info(test_to_do)
        assert len(test_to_do) > 0

        self.available_test_modes = test_to_do.keys()
        self.log.info(self.available_test_modes)
        for mode in self.available_test_modes:
            for file in test_to_do[mode]:
                if mode in file:  # TODO more beautiful
                    self.log.info(
                        "chdir in "
                        + str(os.path.join(self.config["global_parameters"]["tests_dir"],  mode + "s"))
                    )
                    os.chdir(
                        os.path.join(self.config["global_parameters"]["tests_dir"],  mode + "s")
                    )  
                    file = (
                        os.path.join(
                            self.config["global_parameters"]["tests_dir"], file
                        )
                        + ".ivy"
                    )
                    self.log.info("* " + file)
                    nameFileShort = file.split("/")[-1]
                    self.build_file(nameFileShort)
        os.chdir(SOURCE_DIR)
    
    def pair_compile_file(self, file, replacements):
        for old_name, new_name in replacements.items():
            if old_name in file:
                file = file.replace(old_name, new_name)
                self.compile_file(file)
                        
    def build_file(self, file):
        self.compile_file(file)
        if self.config["verified_protocol"].getboolean("quic"):
            # TODO add in config file, test that should be build and run in pair
            replacements = {
                "quic_server_test_0rtt": "quic_server_test_0rtt_stream",
                "quic_server_test_0rtt_stream": "quic_server_test_0rtt_stream_co_close",
                "quic_server_test_0rtt_stream_co_close": "quic_server_test_0rtt_stream_app_close",
                "quic_client_test_0rtt_invalid": "quic_client_test_0rtt_max",
                "quic_client_test_0rtt_add_val": "quic_client_test_0rtt_max_add_val",
                "quic_client_test_0rtt_mim_replay": "quic_client_test_0rtt_max",
                "quic_client_test_0rtt": "quic_client_test_0rtt_max",
                "quic_client_test_0rtt_max": "quic_client_test_0rtt_max_co_close",
                "quic_client_test_0rtt_max_co_close": "quic_client_test_0rtt_max_app_close",
                "quic_server_test_retry_reuse_key": "quic_server_test_retry",
            }

            self.pair_compile_file(file, replacements)

    def compile_file(self, file):
        if self.config["global_parameters"].getboolean("compile"):
            self.log.info("Building/Compiling file:")
            child = subprocess.Popen(
                "ivyc trace=false show_compiled=false target=test test_iters="
                + str(self.config["global_parameters"]["internal_iteration"])
                + "  "
                + file,
                shell=True,
                executable="/bin/bash",
            ).wait()
            rc = child
            self.log.info(rc)
            if rc != 0:
                try:
                    x = requests.get('http://panther-webapp/errored-experiment')
                    self.log.info(x)
                except:
                    pass
                exit(1)

            self.log.info("Moving built file in correct folder:")
            execute_command("/usr/bin/chmod +x " + file.replace(".ivy", ""))
            execute_command(
                "/bin/cp "
                + file.replace(".ivy", "")
                + " "
                + self.config["global_parameters"]["build_dir"]
            )
            execute_command(
                "/bin/cp "
                + file.replace(".ivy", ".cpp")
                + " "
                + self.config["global_parameters"]["build_dir"]
            )
            execute_command(
                "/bin/cp "
                + file.replace(".ivy", ".h")
                + " "
                + self.config["global_parameters"]["build_dir"]
            )
            execute_command("/bin/rm " + file.replace(".ivy", ""))
            execute_command("/bin/rm " + file.replace(".ivy", ".cpp"))
            execute_command("/bin/rm " + file.replace(".ivy", ".h"))

    def launch_experiments(self, implementations=None):
        try:
            build_dir = os.path.join(MODEL_DIR, self.current_protocol, "build/")
            if not os.path.isdir(build_dir):
                self.log.info(f"Creating directory: {build_dir}")
                os.mkdir(build_dir)
            if self.config["debug_parameters"].getboolean("memprof"):
                tracemalloc.start()

            if self.config["global_parameters"].getboolean("update_ivy"):
                self.update_ivy_tool()
            self.setup_ivy_model()

            # Set environement-specific env var
            if not self.config["global_parameters"].getboolean("docker"):
                os.environ["IS_NOT_DOCKER"] = "true"
                ENV_VAR["IS_NOT_DOCKER"] = "true"
            else:
                if "IS_NOT_DOCKER" in os.environ:
                    del os.environ["IS_NOT_DOCKER"]
                if "IS_NOT_DOCKER" in ENV_VAR:
                    del ENV_VAR["IS_NOT_DOCKER"]

            # Set network-specific env var
            if self.config["net_parameters"].getboolean("shadow"):
                ENV_VAR["LOSS"] = float(self.config["shadow_parameters"]["loss"])
                ENV_VAR["LATENCY"] = int(self.config["shadow_parameters"]["latency"])
                ENV_VAR["JITTER"] = int(self.config["shadow_parameters"]["jitter"])
                if DEBUG:
                    self.log.info(ENV_VAR["LOSS"])
                    self.log.info(ENV_VAR["LATENCY"])
                    self.log.info(ENV_VAR["JITTER"])

            if not self.config["global_parameters"].getboolean("docker"):
                execute_command(
                    "sudo sysctl -w net.core.rmem_max=2500000"
                )

            self.build_tests(test_to_do=self.tests_enabled)

            if implementations == None or implementations == []:
                self.log.error(
                    "TODO implement in local mode, for now only with docker (ERROR)"
                )
                # exit(0)
                # TODO implement in local mode, for now only with docker

            for implem in implementations:
                self.log.info(implem)
                self.log.info(self.implementation_enable.keys())
                if implem not in self.implementation_enable.keys():
                    self.log.info("Unknown implementation")
                    sys.stderr.write("nknown implementation: {}\n".format(implem))
                    # exit(1)

            if self.config["verified_protocol"].getboolean("apt"):
                self.log.info(self.config)
                self.log.info(self.protocol_conf)
                self.log.info(self.current_protocol)
                self.log.info(self.conf_implementation_enable)
                self.log.info(self.tests_enabled)
                # exit()
                runner = APTRunner(
                    self.config,
                    self.protocol_conf,
                    self.current_protocol,
                    self.conf_implementation_enable,
                    self.tests_enabled,
                )
            elif self.config["verified_protocol"].getboolean("quic"):
                runner = QUICRunner(
                    self.config,
                    self.protocol_conf,
                    self.current_protocol,
                    self.conf_implementation_enable,
                    self.tests_enabled,
                )
            elif self.config["verified_protocol"].getboolean("minip"):
                runner = MiniPRunner(
                    self.config,
                    self.protocol_conf,
                    self.current_protocol,
                    self.conf_implementation_enable,
                    self.tests_enabled,
                )
            else:
                self.log.info("No protocols selected")
                # exit(0)

            self.log.info("Starting experiments:")
            for implementation in implementations:
                self.log.info("- Starting tests for implementation: " + implementation)
                os.environ["TEST_IMPL"] = implementation
                ENV_VAR["TEST_IMPL"]    = implementation
                try:
                    runner.run_exp(implementation)
                    self.log.info("Experiments finished")
                except Exception as e:
                    print(e)
                    restore_config()
                    try:
                        x = requests.get('http://panther-webapp/errored-experiment')
                        self.log.info(x)
                    except:
                        pass
                finally:  # In Runner.py
                    if self.config["net_parameters"].getboolean("vnet"):
                        self.log.info("Reset vnet")
                        subprocess.Popen(
                            "bash  /app/scripts/vnet/vnet_reset.sh",
                            shell=True,
                            executable="/bin/bash",
                        ).wait()

            self.log.info("Experiments finished")

            if self.config["debug_parameters"].getboolean("memprof"):
                self.log.info("Memory profiling")
                snapshot = tracemalloc.take_snapshot()
                top_stats = snapshot.statistics("lineno")
                self.log.info("[ Top 50 ]")
                for stat in top_stats[:50]:
                    self.log.info(stat)

            if self.config["debug_parameters"].getboolean("ivy_process_tracer"):
                try:
                    self.generate_uml_trace()
                except Exception as e:
                    print(e)

            self.log.info("END 1")
            try:
                x = requests.get('http://panther-webapp/finish-experiment')
                self.log.info(x)
                # exit(0)
            except:
                pass
            # exit(0)
        except Exception as e: 
            print(e)
            try:
                x = requests.get('http://panther-webapp/errored-experiment')
                self.log.info(x)
            except:
                pass
            self.log.error("END 2")
            # exit(1)

    def generate_uml_trace(self):
        self.log.info("Generating PlantUML trace from ivy trace")
        plantuml_file = "/ivy_trace.txt"
        plantuml_obj = PlantUML(
            url="http://www.plantuml.com/plantuml/img/",
            basic_auth={},
            form_auth={},
            http_opts={},
            request_opts={},
        )
        plantuml_file_png = plantuml_file.replace(
            ".puml", ".png"
        )  # "media/" + str(nb_exp) + "_plantuml.png"
        plantuml_obj.processes_file(plantuml_file, plantuml_file_png)

    def stop_stdout(self):
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__


def main():
    experiments = ArgumentParserRunner().parse_arguments()
    experiments.launch_experiments()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
    finally:
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        execute_command("kill $(lsof -i udp) >/dev/null 2>&1")
        execute_command("sudo pkill tshark")
        execute_command("bash " + SOURCE_DIR + "/vnet_reset.sh")
        execute_command("/bin/kill $(/usr/bin/lsof -i udp) >/dev/null 2>&1")
        execute_command("sudo /usr/bin/pkill tshark")
        execute_command("sudo /usr/bin/pkill tini")
