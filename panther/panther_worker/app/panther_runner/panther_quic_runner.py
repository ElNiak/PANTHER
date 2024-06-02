import os
import re
import sys
import subprocess
import requests
import time

from panther_runner.panther_runner import Runner
from panther_utils.panther_constant import *
from panther_tester.panther_quic_tester import QUICIvyTest


class QUICRunner(Runner):
    def __init__(
        self, config, protocol_config, current_protocol, implems, executed_test=[]
    ):
        super().__init__(
            config, protocol_config, current_protocol, implems, executed_test
        )

        subprocess.Popen(
            "echo '' >> " + SOURCE_DIR + "/tickets/ticket.bin",
            shell=True,
            executable="/bin/bash",
        ).wait()

        os.environ["INITIAL_VERSION"] = str(
            self.protocol_conf["quic_parameters"].getint("initial_version")
        )
        ENV_VAR["INITIAL_VERSION"] = str(
            self.protocol_conf["quic_parameters"].getint("initial_version")
        )

    def get_exp_stats(self, implem, test, run_id, pcap_name, i):
        if self.config["global_parameters"].getboolean("getstats"):
            self.log.info("Getting experiences stats:")
            import panther_stats.panther_quic_stats as stats

            with open(
                os.path.join(
                    os.path.join(self.config["global_parameters"]["dir"],str(run_id)),
                    test.name + str(i) + ".dat",
                ),
                "w",
            ) as out:
                save = os.getcwd()
                os.chdir(os.path.join(self.config["global_parameters"]["dir"],str(run_id)))
                stats.make_dat(test.name, out)
                os.chdir(save)
            filename = os.path.join(
                os.path.join(self.config["global_parameters"]["dir"],str(run_id)),
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
                        os.path.join(self.config["global_parameters"]["dir"],str(run_id)),
                        test.name + str(i) + ".iev",
                    ),
                    out,
                    self.protocol_conf["quic_parameters"].getint("initial_version"),
                )

    def run_exp(self, implem):
        implem_dir_server, implem_dir_client = self.setup_exp(implem=implem)
        self.log.info("Setup QUIC alpn:")
        os.environ["TEST_ALPN"] = (
            self.protocol_conf["quic_parameters"]["alpn"] if implem != "mvfst" else "hq"
        )
        ENV_VAR["TEST_ALPN"] = (
            self.protocol_conf["quic_parameters"]["alpn"] if implem != "mvfst" else "hq"
        )
        self.log.info("Setup SSL keylog file:")
        os.environ["SSLKEYLOGFILE"] = SOURCE_DIR + "/tls-keys/" + implem + "_key.log"
        ENV_VAR["SSLKEYLOGFILE"] = SOURCE_DIR + "/tls-keys/" + implem + "_key.log"
        # Main
        try:
            self.bar_total_test.start()
            all_tests = []
            self.log.info("Creating test configuration:")
            for mode in self.executed_tests.keys():
                for test in self.executed_tests[mode]:
                    all_tests.append(
                        QUICIvyTest(
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

            num_failures = 0
            for test in all_tests:
                # TODO check
                # if not test_pattern_obj.match(test.name):
                # if not self.test_pattern == test.name:
                #     continue

                initial_test = test
                number_ite_for_test = 1

                # Setup test-specific parameter
                if test.name == "quic_client_test_0rtt_mim_replay":
                    os.environ["ZERORTT_TEST"] = "true"
                    ENV_VAR["ZERORTT_TEST"] = "true"
                elif (
                    test.name == "quic_server_test_0rtt"
                    or test.name == "quic_client_test_0rtt"
                ):
                    os.environ["ZERORTT_TEST"] = "true"
                    ENV_VAR["ZERORTT_TEST"] = "true"
                    number_ite_for_test = 3
                else:
                    if "ZERORTT_TEST" in os.environ:
                        del os.environ["ZERORTT_TEST"]
                    if "ZERORTT_TEST" in ENV_VAR:
                        del ENV_VAR["ZERORTT_TEST"]

                if test.name == "quic_server_test_retry_reuse_key":
                    nclient = 2
                else:
                    nclient = self.protocol_conf["quic_parameters"].getint("nclient")

                if self.config["net_parameters"].getboolean("vnet"):
                    if (
                        "mim" in test.name
                        or "attack" in test.name
                        or "mim" in test.mode
                        or "attack" in test.mode
                    ):
                        subprocess.Popen(
                            "bash " + SOURCE_DIR + "/vnet_setup_mim.sh",
                            shell=True,
                            executable="/bin/bash",
                        ).wait()
                    else:
                        subprocess.Popen(
                            "bash  /app/scripts/vnet/vnet_setup.sh",
                            shell=True,
                            executable="/bin/bash",
                        ).wait()
                else:  # TODO check if still works here, was not there before (check old project commit if needed)
                    subprocess.Popen(
                        "bash  /app/scripts/vnet/vnet_reset.sh",
                        shell=True,
                        executable="/bin/bash",
                    ).wait()
                    # TODO check
                    # if "quic_client_test_version_negociation_mim" in test:
                    #     subprocess.Popen("bash "+ SOURCE_DIR + "/mim-setup.sh",
                    #                                         shell=True, executable="/bin/bash").wait()
                    # else:
                    #     subprocess.Popen("bash  /app/scripts/mim/mim-reset.sh",
                    #                                         shell=True, executable="/bin/bash").wait()

                for j in range(0, number_ite_for_test):
                    for i in range(0, self.iters):
                        if j == 1:  # TODO wtf
                            test.name = initial_test + "_app_close"
                        elif j == 2:
                            test.name = initial_test + "_co_close"

                        os.environ["CNT"] = str(self.current_executed_test_count)
                        ENV_VAR["CNT"] = str(self.current_executed_test_count)
                        # os.environ['RND'] = os.getenv("RANDOM")

                        subprocess.Popen(
                            "> " + SOURCE_DIR + "/tickets/ticket.bin",
                            shell=True,
                            executable="/bin/bash",
                        ).wait()

                        self.log.info("Test: " + test.name)
                        self.log.info("Implementation: " + implem)
                        self.log.info(
                            "Iteration: "
                            + str(i + 1)
                            + "/"
                            + str(self.config["global_parameters"].getint("iter"))
                        )

                        if self.config["net_parameters"].getboolean("vnet"):
                            subprocess.Popen(
                                "bash  /app/scripts/vnet/vnet_setup.sh",
                                shell=True,
                                executable="/bin/bash",
                            ).wait()
                        else:  # TODO check if still works here, was not there before (check old project commit if needed)
                            subprocess.Popen(
                                "bash  /app/scripts/vnet/vnet_reset.sh",
                                shell=True,
                                executable="/bin/bash",
                            ).wait()

                        exp_folder, run_id = self.create_exp_folder()
                        pcap_name = self.config_pcap(exp_folder, implem, test.name)
                        pcap_process = self.record_pcap(pcap_name)

                        self.log.info("Output folder:" + exp_folder)

                        ivy_out = exp_folder + "/ivy_stdout.txt"
                        ivy_err = exp_folder + "/ivy_stderr.txt"
                        sys.stdout = open(ivy_out, "w")
                        sys.stderr = open(ivy_err, "w")

                        self.log.info("Start run")

                        os.environ["TEST_TYPE"] = test.mode.split("_")[0]
                        ENV_VAR["TEST_TYPE"] = test.mode.split("_")[0]

                        status = False
                        try:
                            status = test.run(i, j, nclient, exp_folder)
                        except Exception as e:
                            print(e)
                        finally:  # In Runner.py
                            sys.stdout.close()
                            sys.stderr.close()
                            sys.stdout = sys.__stdout__
                            sys.stderr = sys.__stderr__

                            x = None
                            while x is None or x.status_code != 200:
                                try:
                                    print("Update count")
                                    x = requests.get(
                                        "http://" + self.webapp_ip + "/update-count"
                                    )
                                    self.log.info(x)
                                except Exception as e:
                                    time.sleep(5)
                                    print(e)

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

                            self.log.info("Kill thsark")
                            subprocess.Popen(
                                "sudo /usr/bin/pkill tshark",
                                shell=True,
                                executable="/bin/bash",
                            ).wait()
                            try:
                                pcap_process.kill()
                            except:
                                pass

                            if self.config["net_parameters"].getboolean("vnet"):
                                subprocess.Popen(
                                    "bash  /app/scripts/vnet/vnet_reset.sh",
                                    shell=True,
                                    executable="/bin/bash",
                                ).wait()

                            self.current_executed_test_count += 1
                            self.bar_total_test.update(self.current_executed_test_count)
                            subprocess.Popen(
                                "bash  /app/scripts/mim/mim-reset.sh",
                                shell=True,
                                executable="/bin/bash",
                            ).wait()
                            self.log.info("End run status: " + str(status))
                            if not status:
                                num_failures += 1

                            self.save_shadow_res(test, i, pcap_name, run_id)
                            self.save_shadow_binaries(implem, test, run_id)
                            self.get_exp_stats(implem, test, run_id, pcap_name, i)
                            # TODO send post message to update nyan cat

            # TODO check if need
            # self.remove_includes()
            # TODO check
            # subprocess.Popen("sudo /bin/cp -r "+ SOURCE_DIR +"/tls-keys/ " + self.config["global_parameters"]["dir"],
            #                     shell=True, executable="/bin/bash").wait()
            # subprocess.Popen("sudo /bin/cp -r "+ SOURCE_DIR +"/tickets/ " + self.config["global_parameters"]["dir"],
            #                     shell=True, executable="/bin/bash").wait()
            # subprocess.Popen("sudo /bin/cp -r "+ SOURCE_DIR +"/qlogs/ " + self.config["global_parameters"]["dir"],
            #                     shell=True, executable="/bin/bash").wait()
            self.bar_total_test.finish()
            self.current_executed_test_count = None
            if num_failures:
                self.log.info("error: {} tests(s) failed".format(num_failures))
            else:
                self.log.info("OK")
        except KeyboardInterrupt:
            self.log.info("terminated")
