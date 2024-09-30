import os
import re
import sys
import subprocess
import requests
import configparser
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from panther_runner.panther_runner import Runner
from panther_utils.panther_constant import *
from panther_tester.panther_apt_tester import APTIvyTest
from panther_utils.panther_vnet import *


class APTRunner(Runner):
    def __init__(
        self, config, protocol_config, current_protocol, implems, executed_test=[]
    ):
        super().__init__(
            config, protocol_config, current_protocol, implems, executed_test
        )
        self.log.setLevel(int(os.environ["LOG_LEVEL"]))

    def get_exp_stats(self, implem, test, run_id, pcap_name, i):
        if self.config["global_parameters"].getboolean("getstats"):
            self.log.debug("Getting APT experiences stats:")
            import panther_stats.panther_apt_stats as stats

            protocol = self.apt_conf["protocol_origins"][self.current_implementation]
            try:
                with open(
                    os.path.join(
                        os.path.join(self.config["global_parameters"]["dir"], str(run_id)),
                        test.name + str(i) + ".dat",
                    ),
                    "w",
                ) as out:
                    save = os.getcwd()
                    os.chdir(
                        os.path.join(self.config["global_parameters"]["dir"], str(run_id))
                    )
                    stats.make_dat(test.name, out)
                    os.chdir(save)
            except Exception as e:
                self.log.error("Error getting APT experiences DAT stats")
                self.log.error(e)
            
            try:
                filename = os.path.join(
                    os.path.join(self.config["global_parameters"]["dir"], str(run_id)),
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
                            os.path.join(
                                self.config["global_parameters"]["dir"], str(run_id)
                            ),
                            test.name + str(i) + ".iev",
                        ),
                        out,
                        self.protocol_conf[protocol + "_parameters"].getint(
                            "initial_version"
                        ),
                    )
            except Exception as e:
                self.log.error("Error getting APT experiences CSV stats")
                self.log.error(e)

    def run_exp(self, implem):
        self.current_implementation = implem  # TODO I always consider only one implementation BUT il will change ?
        self.apt_conf = self.protocol_conf
        protocol = self.apt_conf["protocol_origins"][self.current_implementation]
        self.protocol_conf = configparser.ConfigParser(allow_no_value=True)
        self.protocol_conf.read(
            "configs/" + protocol + "/" + protocol + "_config.ini"
        )
        
        self.log.info(f"Running experiment for {implem} with protocol {protocol}")
        if "-" in protocol:
            implem_dir_server = []
            implem_dir_client = []  
            protocols = protocol.split("-") 
    
            implementations = implem.split("-")
            for p in range(len(protocols)):
                self.log.debug(f"Protocol - {protocols[p]}")
                self.log.debug(f"Implementation - {implementations[p]}")
                
                self.protocol_conf = configparser.ConfigParser(allow_no_value=True)
                self.protocol_conf.read(
                    "configs/" + protocols[p] + "/" + protocols[p] + "_config.ini"
                )

                if protocols[p] == "quic":
                    subprocess.Popen(
                        "echo '' > " + SOURCE_DIR + "/tickets/"+ implementations[p] +"_ticket.bin",
                            shell=True,
                            executable="/bin/bash",
                    ).wait()
                    self.log.debug("Setup QUIC:")
                    alpn = (
                        self.protocol_conf["quic_parameters"]["alpn"]
                        if implementations[p] != "mvfst"
                        else "hq"
                    )
                    self.log.debug(f"Setup QUIC alpn - {alpn}")
                    os.environ["TEST_ALPN"] = alpn
                    ENV_VAR["TEST_ALPN"] = alpn

                    keylog_file = SOURCE_DIR + "/tls-keys/" + implementations[p] + "_key.log"
                    # subprocess.Popen(
                    #     "echo '' >> " + keylog_file,
                    #         shell=True,
                    #         executable="/bin/bash",
                    # ).wait()
                    self.log.debug(f"Setup SSL keylog file - {keylog_file}")
                    os.environ["SSLKEYLOGFILE"] = keylog_file
                    ENV_VAR["SSLKEYLOGFILE"] = keylog_file

                    initial_version = str(
                        self.protocol_conf["quic_parameters"].getint("initial_version")
                    )
                    self.log.debug(f"Setup Initial Version - {initial_version}")
                    os.environ["INITIAL_VERSION"] = initial_version
                    ENV_VAR["INITIAL_VERSION"] = initial_version

                elif protocols[p] == "minip":
                    self.log.debug("Setup MINIP:")
                else:
                    self.log.error("Unknown protocol")
                    raise Exception("Unknown protocol")
            #     implem_dir_server_inter, implem_dir_client_inter = self.setup_exp(implementations[p])
            #     implem_dir_client.append(implem_dir_client_inter)
            #     implem_dir_server.append(implem_dir_server_inter)
            # protocol = protocols
            # implem = implementations
            self.log.debug(f"Implem dir server - {implem_dir_server}")
            self.log.debug(f"Implem dir client - {implem_dir_client}")
            self.log.debug(f"Extra args - {self.extra_args}")
            self.log.debug(f"Implem - {implem}")
            self.log.debug(f"Protocol - {protocols}")
            self.log.debug(f"Implementations - {implementations}")
            protocol = self.apt_conf["protocol_origins"][implementations[0]]
            self.protocol_conf = configparser.ConfigParser(allow_no_value=True)
            self.protocol_conf.read(
                "configs/" + protocol + "/" + protocol + "_config.ini"
            )
            protocol_target = self.apt_conf["protocol_origins"][implementations[1]]
            self.target_implem_conf = configparser.ConfigParser(allow_no_value=True)
            self.target_implem_conf.read(
                "configs/" + protocol_target + "/" + protocol_target + "_config.ini"
            )
        else:
            if protocol == "quic":
                subprocess.Popen(
                    "echo '' > " + SOURCE_DIR + "/tickets/"+ implem +"_ticket.bin",
                        shell=True,
                        executable="/bin/bash",
                ).wait()
                self.log.debug("Setup QUIC:")
                alpn = (
                    self.protocol_conf["quic_parameters"]["alpn"]
                    if implem != "mvfst"
                    else "hq"
                )
                self.log.debug(f"Setup QUIC alpn - {alpn}")
                os.environ["TEST_ALPN"] = alpn
                ENV_VAR["TEST_ALPN"] = alpn

                keylog_file = SOURCE_DIR + "/tls-keys/" + implem + "_key.log"
                # subprocess.Popen(
                #     "echo '' >> " + keylog_file,
                #         shell=True,
                #         executable="/bin/bash",
                # ).wait()
                self.log.debug(f"Setup SSL keylog file - {keylog_file}")
                os.environ["SSLKEYLOGFILE"] = keylog_file
                ENV_VAR["SSLKEYLOGFILE"] = keylog_file

                initial_version = str(
                    self.protocol_conf["quic_parameters"].getint("initial_version")
                )
                self.log.debug(f"Setup Initial Version - {initial_version}")
                os.environ["INITIAL_VERSION"] = initial_version
                ENV_VAR["INITIAL_VERSION"] = initial_version

            elif protocol == "minip":
                self.log.debug("Setup MINIP:")
            else:
                self.log.error("Unknown protocol")
                raise Exception("Unknown protocol")
        
        implem_dir_server, implem_dir_client = self.setup_exp(implem=implem)

        
        self.log.debug(f"Implem dir server - {implem_dir_server}")
        self.log.debug(f"Implem dir client - {implem_dir_client}")
        self.log.debug(f"Extra args - {self.extra_args}")
        self.log.debug(f"Implem - {implem}")
        self.log.debug(f"Protocol - {protocol}")
        
        if len(implem_dir_server) == 2:
            try:
                self.bar_total_test.start()
                all_tests = []
                self.log.debug(f"Executed tests - {self.executed_tests}")
                self.log.debug(f"Implem dir server - {implem_dir_server}")
                self.log.debug(f"Implem dir client - {implem_dir_client}")
                self.log.debug(f"Extra args - {self.extra_args}")
                self.log.debug(f"Implem - {implem}")
                self.log.debug(f"Protocol - {protocol}")
                self.log.debug(f"Implementations - {implementations}")
                self.log.debug(f"Protocol target - {protocol_target}")
                self.log.debug(f"Implem dir server - {implem_dir_server[1]}")
                self.log.debug(f"Implem dir client - {implem_dir_client[1]}")
                self.log.debug(f"Target implem conf - {self.target_implem_conf}")
                

                for mode in self.executed_tests.keys():
                    for test in self.executed_tests[mode]:
                        all_tests.append(
                            APTIvyTest(
                                [test, "test_completed"],
                                implem_dir_server[0],
                                implem_dir_client[0],
                                self.extra_args,
                                implem,
                                mode,
                                self.config,
                                self.protocol_conf,
                                self.implems[implementations[0]],
                                self.current_protocol,
                                self.apt_conf,
                                protocol_target,
                                implem_dir_server[1],
                                implem_dir_client[1],
                                self.implems[implementations[1]],
                            )
                        )
                self.log.debug(f"Creating test configuration:\n{all_tests}")
                num_failures = 0
                for test in all_tests:
                    self.log.debug(f"Test - {test.name}")
                    number_ite_for_test = 1
                    try:
                        if protocol == "quic":
                            if test.name == "quic_client_test_0rtt_mim_replay" or \
                                test.name == "quic_mim_test_replay_0rtt" or \
                                    test.name == "mim_server_test_replay":
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
                            pass
                        else:  # TODO check if still works here, was not there before (check old project commit if needed)
                            pass
                        try:
                            for j in range(0, number_ite_for_test):
                                for i in range(0, self.iters):
                                    os.environ["CNT"] = str(self.current_executed_test_count)
                                    ENV_VAR["CNT"]    = str(self.current_executed_test_count)
                                    # os.environ['RND'] = os.getenv("RANDOM")

                                    nclient = 1
                                    self.log.info("*" * 50)
                                    self.log.info(
                                        f"\n-Test: {test.name}\n-Implementation:{implem}\n-Iteration: {i+1}/{self.config['global_parameters'].getint('iter')}"
                                    )
                                    self.log.debug(str(self.config))
                                    # TODO check if still works here, was not there before (check old project commit if needed)
                                    if self.config["net_parameters"].getboolean("vnet"):
                                        if self.config["vnet_parameters"].getboolean("mitm"):
                                            if self.config["vnet_parameters"].getboolean("bridged"):
                                                run_steps(setup_mim_bridged, ignore_errors=True)
                                            else:
                                                run_steps(setup_mim, ignore_errors=True)
                                        else:
                                            run_steps(setup, ignore_errors=True)
                                    else:
                                        if self.config["vnet_parameters"].getboolean("mitm"):
                                            if self.config["vnet_parameters"].getboolean("bridged"):
                                                run_steps(reset_mim_bridged, ignore_errors=True)
                                            else:
                                                run_steps(reset_mim, ignore_errors=True)
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
                                    test_splitted = test.mode.split("_")
                                    self.log.debug(f"Test mode - {test.mode} - {test_splitted}")
                                    os.environ["TEST_TYPE"] = test_splitted[0]
                                    ENV_VAR["TEST_TYPE"]    = test_splitted[0]
                                    if test_splitted[0] == "attacker":
                                        os.environ["TEST_TYPE"] = test_splitted[0] + "_" + test_splitted[1]
                                        ENV_VAR["TEST_TYPE"]    = test_splitted[0] + "_" + test_splitted[1]

                                    status = False
                                    try:
                                        status = test.run(i, j, nclient, exp_folder)
                                    except Exception as e:
                                        self.log.error(e)
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
                                                self.log.debug("Update count")
                                                x = requests.get(
                                                    "http://" + self.webapp_ip + "/update-count"
                                                )
                                                self.log.debug(x)
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
                                        try:
                                            self.save_shadow_res(test, i, pcap_name, run_id)
                                            self.save_shadow_binaries(implem, test, run_id)
                                        except Exception as e:
                                            self.log.error("Error saving shadow res")
                                            self.log.error(e)

                                        try:
                                            self.get_exp_stats(implem, test, run_id, pcap_name, i)
                                        except Exception as e:
                                            self.log.error("Error getting exp stats")
                                            # self.log.error(e)

                                        if self.config["net_parameters"].getboolean("vnet"):
                                            self.log.debug("Reset vnet")
                                            if self.config["vnet_parameters"].getboolean("mitm"):
                                                if self.config["vnet_parameters"].getboolean(
                                                    "bridged"
                                                ):
                                                    run_steps(reset_mim_bridged, ignore_errors=True)
                                                else:
                                                    run_steps(reset_mim, ignore_errors=True)
                                            else:
                                                run_steps(reset, ignore_errors=True)
                        except KeyboardInterrupt:
                            self.log.error("terminated")
                            break
                        except Exception as e:
                            self.log.error(e)
                    except Exception as e:
                        self.log.error(e)
                # TODO check if need
                # self.remove_includes()

                self.bar_total_test.finish()
                self.current_executed_test_count = None
                if num_failures:
                    self.log.error("error: {} tests(s) failed".format(num_failures))
                else:
                    self.log.info("OK")
            except KeyboardInterrupt:
                self.log.error("terminated")
        else:
            try:
                self.bar_total_test.start()
                all_tests = []

                for mode in self.executed_tests.keys():
                    for test in self.executed_tests[mode]:
                        all_tests.append(
                            APTIvyTest(
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
                                self.apt_conf,
                            )
                        )
                self.log.debug(f"Creating test configuration:\n{all_tests}")
                num_failures = 0
                for test in all_tests:
                    self.log.debug(f"Test - {test.name}")
                    number_ite_for_test = 1
                    try:
                        if protocol == "quic":
                            if test.name == "quic_client_test_0rtt_mim_replay" or \
                                test.name == "quic_mim_test_replay_0rtt":
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
                            pass
                        else:  # TODO check if still works here, was not there before (check old project commit if needed)
                            pass
                        try:
                            for j in range(0, number_ite_for_test):
                                for i in range(0, self.iters):
                                    os.environ["CNT"] = str(self.current_executed_test_count)
                                    ENV_VAR["CNT"]    = str(self.current_executed_test_count)
                                    # os.environ['RND'] = os.getenv("RANDOM")

                                    nclient = 1
                                    self.log.info("*" * 50)
                                    self.log.info(
                                        f"\n-Test: {test.name}\n-Implementation:{implem}\n-Iteration: {i+1}/{self.config['global_parameters'].getint('iter')}"
                                    )
                                    self.log.debug(str(self.config))
                                    # TODO check if still works here, was not there before (check old project commit if needed)
                                    if self.config["net_parameters"].getboolean("vnet"):
                                        if self.config["vnet_parameters"].getboolean("mitm"):
                                            if self.config["vnet_parameters"].getboolean("bridged"):
                                                run_steps(setup_mim_bridged, ignore_errors=True)
                                            else:
                                                run_steps(setup_mim, ignore_errors=True)
                                        else:
                                            run_steps(setup, ignore_errors=True)
                                    else:
                                        if self.config["vnet_parameters"].getboolean("mitm"):
                                            if self.config["vnet_parameters"].getboolean("bridged"):
                                                run_steps(reset_mim_bridged, ignore_errors=True)
                                            else:
                                                run_steps(reset_mim, ignore_errors=True)
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
                                    test_splitted = test.mode.split("_")
                                    self.log.debug(f"Test mode - {test.mode} - {test_splitted}")
                                    os.environ["TEST_TYPE"] = test_splitted[0]
                                    ENV_VAR["TEST_TYPE"]    = test_splitted[0]
                                    if test_splitted[0] == "attacker":
                                        os.environ["TEST_TYPE"] = test_splitted[0] + "_" + test_splitted[1]
                                        ENV_VAR["TEST_TYPE"]    = test_splitted[0] + "_" + test_splitted[1]

                                    status = False
                                    try:
                                        status = test.run(i, j, nclient, exp_folder)
                                    except Exception as e:
                                        self.log.error(e)
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
                                                self.log.debug("Update count")
                                                x = requests.get(
                                                    "http://" + self.webapp_ip + "/update-count"
                                                )
                                                self.log.debug(x)
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
                                        try:
                                            self.save_shadow_res(test, i, pcap_name, run_id)
                                            self.save_shadow_binaries(implem, test, run_id)
                                        except Exception as e:
                                            self.log.error("Error saving shadow res")
                                            self.log.error(e)

                                        try:
                                            self.get_exp_stats(implem, test, run_id, pcap_name, i)
                                        except Exception as e:
                                            self.log.error("Error getting exp stats")
                                            # self.log.error(e)

                                        if self.config["net_parameters"].getboolean("vnet"):
                                            self.log.debug("Reset vnet")
                                            if self.config["vnet_parameters"].getboolean("mitm"):
                                                if self.config["vnet_parameters"].getboolean(
                                                    "bridged"
                                                ):
                                                    run_steps(reset_mim_bridged, ignore_errors=True)
                                                else:
                                                    run_steps(reset_mim, ignore_errors=True)
                                            else:
                                                run_steps(reset, ignore_errors=True)
                        except KeyboardInterrupt:
                            self.log.error("terminated")
                            break
                        except Exception as e:
                            self.log.error(e)
                    except Exception as e:
                        self.log.error(e)
                # TODO check if need
                # self.remove_includes()

                self.bar_total_test.finish()
                self.current_executed_test_count = None
                if num_failures:
                    self.log.error("error: {} tests(s) failed".format(num_failures))
                else:
                    self.log.info("OK")
            except KeyboardInterrupt:
                self.log.error("terminated")
