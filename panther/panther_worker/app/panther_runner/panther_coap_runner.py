import os
import re
import sys
import subprocess
import requests
import time

from panther_runner.panther_runner import Runner
from panther_utils.panther_constant import *
from panther_tester.panther_coap_tester import CoAPIvyTest
from panther_utils.panther_vnet import *


class CoAPRunner(Runner):
    def __init__(
        self, config, protocol_config, current_protocol, implems, executed_test=[]
    ):
        super().__init__(
            config, protocol_config, current_protocol, implems, executed_test
        )
        self.log.setLevel(int(os.environ["LOG_LEVEL"]))

    def get_exp_stats(self, implem, test, run_id, pcap_name, i):
        if self.config["global_parameters"].getboolean("getstats"):
            self.log.debug("Getting experiences stats:")
            import panther_stats.panther_coap_stats as stats

            with open(
                os.path.join(
                    self.config["global_parameters"]["dir"] + str(run_id),
                    test.name + str(i) + ".dat",
                ),
                "w",
            ) as out:
                save = os.getcwd()
                os.chdir(self.config["global_parameters"]["dir"] + str(run_id))
                stats.make_dat(test.name, out)
                os.chdir(save)
            filename = os.path.join(
                self.config["global_parameters"]["dir"] + str(run_id),
                test.name + str(i) + ".iev",
            )
            with open(filename, "r") as out:
                stats.update_csv(
                    run_id,
                    implem,
                    test.mode,
                    test.name,
                    pcap_name,
                    os.path.join(
                        self.config["global_parameters"]["dir"] + str(run_id),
                        test.name + str(i) + ".iev",
                    ),
                    out,
                    self.protocol_conf["coap_parameters"].getint("initial_version"),
                )

    def run_exp(self, implem):
        implem_dir_server, implem_dir_client = self.setup_exp(implem=implem)

        # Main
        try:
            self.bar_total_test.start()
            all_tests = []
            for mode in self.executed_tests.keys():
                for test in self.executed_tests[mode]:
                    all_tests.append(
                        CoAPIvyTest(
                            [test, "test_completed"],
                            implem_dir_server,
                            implem_dir_client,
                            self.extra_args,
                            implem,
                            mode,
                            self.config,
                            self.protocol_conf,
                            self.implems[implem],
                            self.current_protocol,
                        )
                    )

            self.log.debug(f"Creating test configuration:\n{all_tests}")
            num_failures = 0
            for test in all_tests:
                # TODO check
                # if not test_pattern_obj.match(test.name):
                # if not self.test_pattern == test.name:
                #     continue

                initial_test = test
                number_ite_for_test = 1

                # Setup test-specific parameter
                # TODO

                if self.config["net_parameters"].getboolean("vnet"):
                    pass
                else:  # TODO check if still works here, was not there before (check old project commit if needed)
                    pass

                for j in range(0, number_ite_for_test):
                    for i in range(0, self.iters):
                        os.environ["CNT"] = str(self.current_executed_test_count)
                        ENV_VAR["CNT"] = str(self.current_executed_test_count)
                        # os.environ['RND'] = os.getenv("RANDOM")
                        nclient = 1
                        self.log.info("*" * 20)
                        self.log.info(
                            f"\n-Test: {test.name}\n-Implementation:{implem}\n-Iteration: {i+1}/{self.config['global_parameters'].getint('iter')}"
                        )

                        # TODO check if still works here, was not there before (check old project commit if needed)
                        if self.config["net_parameters"].getboolean("vnet"):
                            run_steps(setup, ignore_errors=True)
                        else:
                            run_steps(reset, ignore_errors=True)

                        exp_folder, run_id = self.create_exp_folder()
                        pcap_name = self.config_pcap(exp_folder, implem, test.name)
                        pcap_process = self.record_pcap(pcap_name)

                        self.log.info("Output folder:" + exp_folder)

                        ivy_out = exp_folder + "/ivy_stdout.txt"
                        ivy_err = exp_folder + "/ivy_stderr.txt"
                        sys.stdout = open(ivy_out, "w")
                        sys.stderr = open(ivy_err, "w")

                        os.environ["TEST_TYPE"] = test.mode.split("_")[0]
                        ENV_VAR["TEST_TYPE"] = test.mode.split("_")[0]

                        status = False
                        try:
                            status = test.run(i, j, nclient, exp_folder)
                        except Exception as e:
                            print(e)
                        finally:  # In Runner.py
                            try:
                                x = requests.get("http://panther-webapp/update-count")
                                self.log.debug(x)
                            except:
                                pass
                            sys.stdout.close()
                            sys.stderr.close()
                            sys.stdout = sys.__stdout__
                            sys.stderr = sys.__stderr__

                            x = None
                            while x is None or x.status_code != 200:
                                try:
                                    x = requests.get(
                                        "http://" + self.webapp_ip + "/update-count"
                                    )
                                    self.log.debug(x)
                                except Exception as e:
                                    time.sleep(5)
                                    self.log.error(e)

                            subprocess.Popen(
                                "/usr/bin/tail -2 " + ivy_err,
                                shell=True,
                                executable="/bin/bash",
                            ).wait()
                            subprocess.Popen(
                                "/usr/bin/tail -2 " + ivy_out,
                                shell=True,
                                executable="/bin/bash",
                            ).wait()
                            # subprocess.Popen("/usr/bin/tail $(/usr/bin/lsof -i udp) >/dev/null 2>&1", # deadlock in docker todo
                            #                        shell=True, executable="/bin/bash").wait()

                            self.log.debug("pkill tshark")
                            subprocess.Popen(
                                "sudo /usr/bin/pkill tshark",
                                shell=True,
                                executable="/bin/bash",
                            ).wait()
                            try:
                                pcap_process.kill()
                            except:
                                pass

                            self.current_executed_test_count += 1
                            self.bar_total_test.update(self.current_executed_test_count)
                            self.log.info(f"Test status - {status}")
                            if not status:
                                num_failures += 1

                            self.save_shadow_res(test, i, pcap_name, run_id)
                            self.save_shadow_binaries(implem, test, run_id)
                            self.get_exp_stats(implem, test, run_id, pcap_name, i)

            # TODO check if need
            # self.remove_includes()
            # TODO check
            # subprocess.Popen("sudo /bin/cp -r "+ SOURCE_DIR +"/tls-keys/ " + self.config['global_parameters']["dir"],
            #                     shell=True, executable="/bin/bash").wait()
            # subprocess.Popen("sudo /bin/cp -r "+ SOURCE_DIR +"/tickets/ " + self.config['global_parameters']["dir"],
            #                     shell=True, executable="/bin/bash").wait()
            # subprocess.Popen("sudo /bin/cp -r "+ SOURCE_DIR +"/qlogs/ " + self.config['global_parameters']["dir"],
            #                     shell=True, executable="/bin/bash").wait()
            self.bar_total_test.finish()
            self.current_executed_test_count = None
            if num_failures:
                self.log.error("error: {} tests(s) failed".format(num_failures))
            else:
                self.log.info("OK")
        except KeyboardInterrupt:
            self.log.error("terminated")
