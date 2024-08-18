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

from panther_utils.panther_vnet import *
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


# TODO replace print per log but save in file
# TODO add tested implemenatation name
class QUICIvyTest(IvyTest):
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

        # self.log.setLevel(int(os.environ["LOG_LEVEL"]))

        # TODO enforce
        self.special_tests_compatible_impl = {
            "quic_server_test_retry_reuse_key": ["picoquic-vuln", "picoquic"],
            "quic_server_test_retry": [
                "quant",
                "quant-vuln",
                "picoquic-vuln",
                "picoquic",
                "aioquic",
                "quiche",
                "quinn",
                "quic-go",
                "mvfst",
            ],
            "quic_client_test_version_negociation": [
                "quant",
                "quant-vuln",
                "picoquic-vuln",
                "picoquic",
                "aioquic",
                "quiche",
                "quinn",
                "quic-go",
                "lsquic",
                "lsquic-vuln",
            ],
        }

        # MORE config
        # TODO use config instead
        self.special_command_additions = {
            "quic_server_test_retry_reuse_key": {
                "picoquic-vuln": "-r",
                "picoquic": "-r",
                "quant": "-r",
                "quant-vuln": "-r",
            },
            "quic_server_test_retry": {
                "picoquic-vuln": "-r",
                "picoquic": "-r",
                "quant": "-r",
                "quant-vuln": "-r",
                "aioquic": "python3.9 examples/http3_server.py --quic-log "
                + SOURCE_DIR
                + "/qlogs/aioquic --certificate "
                + SOURCE_DIR
                + "/implementations/quic-implementations/aioquic/tests/ssl_cert.pem --private-key "
                + SOURCE_DIR
                + "/implementations/quic-implementations/aioquic/tests/ssl_key.pem  -v --retry --host 127.0.0.1 --port 4443 -l "
                + SOURCE_DIR
                + "/tls-keys/secret.log",
                "quiche": "cargo run --bin quiche-server --  --cert "
                + SOURCE_DIR
                + "/panther-ivy/protocol-testing/quic/cert.pem --early-data --dump-packets "
                + SOURCE_DIR
                + "/qlogs/quiche/dump_packet.txt --key "
                + SOURCE_DIR
                + "/panther-ivy/protocol-testing/quic/priv.key --listen 127.0.0.1:4443",
                "quinn": "cargo run -vv --example server "
                + SOURCE_DIR
                + "/panther-ivy/protocol-testing/quic/index.html --keylog --stateless-retry --listen 127.0.0.1:4443",
                "quic-go": "./server -c "
                + SOURCE_DIR
                + "/panther-ivy/protocol-testing/quic/cert.pem -k "
                + SOURCE_DIR
                + "/panther-ivy/protocol-testing/quic/priv.key -r -p 4443 127.0.0.1",
                "mvfst": "./echo -mode=server -host=127.0.0.1 -port=4443  -v=10 -pr=true",
            },
            "quic_client_test_version_negociation": {
                "quant": IMPLEM_DIR.replace("$PROT", self.current_protocol)
                + "/quant/Debug/bin/client -c false -r 10 -l "
                + SOURCE_DIR
                + "/tls-keys/secret.log -q "
                + SOURCE_DIR
                + "/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html",
                "quant-vuln": IMPLEM_DIR.replace("$PROT", self.current_protocol)
                + "/quant-vuln/Debug/bin/client -c false -r 10 -l "
                + SOURCE_DIR
                + "/tls-keys/secret.log -q "
                + SOURCE_DIR
                + "/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html",
                "picoquic": "./picoquicdemo -z -l - -D -L -a hq-interop localhost 4443",
                "aioquic": "python3.9 examples/http3_client.py --version_negociation -l "
                + SOURCE_DIR
                + "/tls-keys/secret.log -v -q "
                + SOURCE_DIR
                + "/qlogs/aioquic/ --ca-certs tests/pycacert.pem -i --insecure --legacy-http https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html",
                "quiche": 'RUST_LOG="debug" cargo run --bin quiche-client -- https://localhost:4443/index.html --dump-json --no-verify --body / -n 5',
                "quic-go": "./client -X "
                + SOURCE_DIR
                + "/tls-keys/secret.log -V -P -v 127.0.0.1 4443",
                "lsquic": "./http_client -4 -Q hq-29 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8",
                "lsquic-vuln": "./http_client -4 -Q hq-29 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1 -o version=FF00001D -o scid_len=8",
            },
            "quic_client_test_version_negociation_mim_forge": {
                "quant": IMPLEM_DIR.replace("$PROT", self.current_protocol)
                + "/quant/Debug/bin/client -c false -r 10 -l "
                + SOURCE_DIR
                + "/tls-keys/secret.log -q "
                + SOURCE_DIR
                + "/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html",
                "quant-vuln": IMPLEM_DIR.replace("$PROT", self.current_protocol)
                + "/quant-vuln/Debug/bin/client -c false -r 10 -l "
                + SOURCE_DIR
                + "/tls-keys/secret.log -q "
                + SOURCE_DIR
                + "/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html",
                "picoquic": "./picoquicdemo -G bbr -l - -D -L -a hq-interop -v 00000001 localhost 4443",  # CUBIC important for rtt
                "aioquic": "python3.9 examples/http3_client.py --version_negociation -l "
                + SOURCE_DIR
                + "/tls-keys/secret.log -v -q "
                + SOURCE_DIR
                + "/qlogs/aioquic/ --ca-certs tests/pycacert.pem -i --insecure --legacy-http https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html",
                "quiche": 'RUST_LOG="debug" cargo run --bin quiche-client -- https://localhost:4443/index.html --dump-json --no-verify --body / -n 5',
                "quic-go": "./client -X "
                + SOURCE_DIR
                + "/tls-keys/secret.log -V -P -v 127.0.0.1 4443",
                "lsquic": "./http_client -4 -Q hq-29 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8",
                "lsquic-vuln": "./http_client -4 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8",
            },
            "quic_client_test_version_negociation_mim_manual": {
                "quant": IMPLEM_DIR.replace("$PROT", self.current_protocol)
                + "/quant/Debug/bin/client -c false -r 10 -l "
                + SOURCE_DIR
                + "/tls-keys/secret.log -q "
                + SOURCE_DIR
                + "/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html",
                "quant-vuln": IMPLEM_DIR.replace("$PROT", self.current_protocol)
                + "/quant-vuln/Debug/bin/client -c false -r 10 -l "
                + SOURCE_DIR
                + "/tls-keys/secret.log -q "
                + SOURCE_DIR
                + "/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html",
                "picoquic": "./picoquicdemo -l - -D -L -a hq-29 localhost 4443",
                "aioquic": "python3.9 examples/http3_client.py --version_negociation -l "
                + SOURCE_DIR
                + "/tls-keys/secret.log -v -q "
                + SOURCE_DIR
                + "/qlogs/aioquic/ --ca-certs tests/pycacert.pem -i --insecure --legacy-http https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html",
                "quiche": 'RUST_LOG="debug" cargo run --bin quiche-client -- https://localhost:4443/index.html --dump-json --no-verify --body / -n 5',
                "quic-go": "./client -X "
                + SOURCE_DIR
                + "/tls-keys/secret.log -V -P -v 127.0.0.1 4443",
                "lsquic": "./http_client -4 -Q hq-29 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8",
                "lsquic-vuln": "./http_client -4 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8",
            },
        }

        self.is_mim = True if "mim" in self.mode else False  # TODO

        self.loop = {
            "quic_server_test_0rtt": 2,
        }
        
        
        self.is_attacker_client = True if ("attacker" in self.mode and "client" in self.mode) else False  # TODO
        self.is_attacker_server = True if ("attacker" in self.mode and "server" in self.mode) else False

    def generate_shadow_config(self):
        server_implem_args = (
            self.implem_conf[0][self.implementation_name]["cert-param"]
            + " "
            + self.implem_conf[0][self.implementation_name]["cert-file"]
            + " "
            + self.implem_conf[0][self.implementation_name]["key-param"]
            + " "
            + self.implem_conf[0][self.implementation_name]["key-file"]
            + " "
            + self.implem_conf[0][self.implementation_name]["root-cert-param"]
            + " "
            + self.implem_conf[0][self.implementation_name]["root-cert-file"]
            + " "
            + self.implem_conf[0][self.implementation_name]["log-param"]
            + " "
            + self.implem_conf[0][self.implementation_name]["log-file"]
            + " "
            + self.implem_conf[0][self.implementation_name]["qlog-param"]
            + " "
            + self.implem_conf[0][self.implementation_name]["qlog-file"]
            + " "
            + self.implem_conf[0][self.implementation_name]["secret-key-param"]
            + " "
            + self.implem_conf[0][self.implementation_name]["secret-key-file"]
            + " "
            + self.implem_conf[0][self.implementation_name]["alpn"]
            + " "
            + self.implem_conf[0][self.implementation_name]["alpn-value"]
            + " "
            + self.implem_conf[0][self.implementation_name]["version"]
            + " "
            + self.implem_conf[0][self.implementation_name]["version-value"]
            + " "
            + self.implem_conf[0][self.implementation_name]["verbosity"]
            + " "
            + self.implem_conf[0][self.implementation_name]["addition-parameters"]
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

        # server_implem_args = server_implem_args.replace("implem","lo")
        server_implem_args = server_implem_args.replace(
            "XXXXXXXX", "quic-implementations"
        )
        server_implem_args = server_implem_args.replace(
            "VERSION",
            (
                "00000001"
                if ENV_VAR["INITIAL_VERSION"] == "1"
                else ("ff00001d" if ENV_VAR["INITIAL_VERSION"] == "29" 
                else "ff00001c")
            ),
        )
        server_implem_args = server_implem_args.replace("ALPN", ENV_VAR["TEST_ALPN"])
        server_implem_args = re.sub("\s{2,}", " ", server_implem_args)

        server_implem_args = (
            server_implem_args.replace("$MODEL_DIR", MODEL_DIR)
            .replace("$SOURCE_DIR", SOURCE_DIR)
            .replace("$IMPLEM_DIR", self.implem_dir_server + "/")
        )

        client_implem_args = (
            self.implem_conf[1][self.implementation_name]["cert-param"]
            + " "
            + self.implem_conf[1][self.implementation_name]["cert-file"]
            + " "
            + self.implem_conf[1][self.implementation_name]["key-param"]
            + " "
            + self.implem_conf[1][self.implementation_name]["key-file"]
            + " "
            + self.implem_conf[1][self.implementation_name]["root-cert-param"]
            + " "
            + self.implem_conf[1][self.implementation_name]["root-cert-file"]
            + " "
            + self.implem_conf[1][self.implementation_name]["log-param"]
            + " "
            + self.implem_conf[1][self.implementation_name]["log-file"]
            + " "
            + self.implem_conf[1][self.implementation_name]["qlog-param"]
            + " "
            + self.implem_conf[1][self.implementation_name]["qlog-file"]
            + " "
            + self.implem_conf[1][self.implementation_name]["secret-key-param"]
            + " "
            + self.implem_conf[1][self.implementation_name]["secret-key-file"]
            + " "
            + self.implem_conf[1][self.implementation_name]["alpn"]
            + " "
            + self.implem_conf[1][self.implementation_name]["alpn-value"]
            + " "
            + self.implem_conf[1][self.implementation_name]["version"]
            + " "
            + self.implem_conf[1][self.implementation_name]["version-value"]
            + " "
            + self.implem_conf[1][self.implementation_name]["verbosity"]
            + " "
            + self.implem_conf[1][self.implementation_name]["addition-parameters"]
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

        # client_implem_args = client_implem_args.replace("implem","lo")
        client_implem_args = client_implem_args.replace(
            "XXXXXXXX", "quic-implementations"
        )
        client_implem_args = client_implem_args.replace(
            "VERSION",
            (
                "00000001"
                if ENV_VAR["INITIAL_VERSION"] == "1"
                else ("ff00001d" if ENV_VAR["INITIAL_VERSION"] == "29" else "ff00001c")
            ),
        )
        client_implem_args = client_implem_args.replace("ALPN", ENV_VAR["TEST_ALPN"])
        client_implem_args = re.sub("\s{2,}", " ", client_implem_args)

        client_implem_args = (
            client_implem_args.replace("$MODEL_DIR", MODEL_DIR)
            .replace("$SOURCE_DIR", SOURCE_DIR)
            .replace("$IMPLEM_DIR", self.implem_dir_server + "/")
        )
        implem_env = ""  # TODO use a list of env

        if self.is_mim:
            server_implem_args = server_implem_args.replace("11.0.0.1","11.0.0.2")
            server_implem_args = server_implem_args.replace("11.0.0.3","11.0.0.2")
            client_implem_args = client_implem_args.replace("11.0.0.1","11.0.0.3")
            client_implem_args = client_implem_args.replace("11.0.0.2","11.0.0.3")
        elif self.is_attacker_client:
            server_implem_args = server_implem_args.replace("11.0.0.1","11.0.0.2")
            server_implem_args = server_implem_args.replace("11.0.0.3","11.0.0.2")
            client_implem_args = client_implem_args.replace("11.0.0.2","11.0.0.1")
            client_implem_args = client_implem_args.replace("11.0.0.3","11.0.0.1")
        elif self.is_attacker_server:
            server_implem_args = server_implem_args.replace("11.0.0.2","11.0.0.1")
            server_implem_args = server_implem_args.replace("11.0.0.3","11.0.0.1")
            client_implem_args = client_implem_args.replace("11.0.0.1","11.0.0.2")
            client_implem_args = client_implem_args.replace("11.0.0.3","11.0.0.2")
                
        ivy_args = (
            self.generate_tester_command(
                self.config["global_parameters"].getint("iter"), 1
            )
            .split("/")[-1]
            .replace(self.name, "")
        )
        ivy_env = ""  # TODO use a list of en

        # TODO use config file
        self.log.info(f"Shadow test for {self.name}")
        print(f"Shadow test for {self.name}")
        for env_var in ENV_VAR:
            print(env_var, ENV_VAR[env_var])
        if  self.is_mim or self.is_attacker_client or self.is_attacker_server:    
            file = "/app/shadow_attacker_test.yml"
            file_temp = "/app/shadow_attacker_test_template.yml"
        elif "client_test" in self.name:
            file = "/app/shadow_client_test.yml"
            file_temp = "/app/shadow_client_test_template.yml"
        else:
            file = "/app/shadow_server_test.yml"
            file_temp = "/app/shadow_server_test_template.yml"

        with open(file_temp, "r") as f:
            self.log.debug(f"Read Shadow template file {file_temp}:")
            content = f.read()
            self.log.debug(content)
        with open(file, "w") as f:
            self.log.debug(f"Writing Shadow final config {file}:")
            content = content.replace("<VERSION>", ENV_VAR["INITIAL_VERSION"])
            content = content.replace("<IMPLEMENTATION>", ENV_VAR["TEST_IMPL"])
            content = content.replace("<ALPN>", ENV_VAR["TEST_ALPN"])
            content = content.replace("<SSLKEYLOGFILE>", ENV_VAR["SSLKEYLOGFILE"])
            content = content.replace("<TEST_NAME>", self.name)
            content = content.replace("<JITTER>", str(ENV_VAR["JITTER"]))
            content = content.replace("<LATENCY>", str(ENV_VAR["LATENCY"]))
            content = content.replace("<LOSS>", str(float(ENV_VAR["LOSS"])))
            if  self.is_mim or self.is_attacker_client or self.is_attacker_server:     
                content = content.replace(
                    "<IMPLEM_SERVER_PATH>",
                    (
                        self.implem_dir_server
                        + "/"
                        + self.implem_conf[0][self.implementation_name]["binary-name"]
                    ),
                )
                content = content.replace(
                    "<IMPLEM_SERVER_ARGS>",
                    server_implem_args,
                )


                content = content.replace(
                    "<IMPLEM_CLIENT_PATH>",
                    (
                        self.implem_dir_client
                        + "/"
                        + self.implem_conf[1][self.implementation_name]["binary-name"]
                    ),
                )
                content = content.replace(
                    "<IMPLEM_CLIENT_ARGS>",
                     client_implem_args,
                )
                
                content = content.replace(
                    "<BUILD_PATH>", self.config["global_parameters"]["build_dir"]
                )
                content = content.replace("<TEST_ARGS>", ivy_args)
                self.log.debug(content)
                print(content)
                f.write(content)
            else:
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
                self.log.debug(content)
                print(content)
                f.write(content)
        os.chdir("/app")
        self.log.debug("rm -r /app/shadow.data/ ")
        print("rm -r /app/shadow.data/ ")
        os.system("rm -r /app/shadow.data/ ")
        os.system("rm  /app/shadow.log ")

        self.log.info("command: RUST_BACKTRACE=1 shadow " + file + " > shadow.log")
        print("command: RUST_BACKTRACE=1 shadow " + file + " > shadow.log")

        return file

    def update_implementation_command(self, i, is_target=False):
        self.log.debug(f"Update implementation before {self.implem_cmd}")

        # TODO add that in config file
        # 0rtt case:
        if i == 1:
            self.implem_cmd = self.implem_cmd.replace("4443", "4444")
            if self.implementation_name == "mvfst":
                self.implem_cmd = self.implem_cmd + " -zrtt=true"
            elif self.implementation_name == "quiche":
                self.implem_cmd = self.implem_cmd + " --early-data"

        if i == 0 and ("quic_client_test_0rtt" in self.name or "quic_mim_test_replay_0rtt" in self.name):
            if (
                self.implementation_name == "quic-go"
            ):  # change port for 2d run directly in implem
                self.implem_cmd = self.implem_cmd.replace(
                    "./client -X", "./client -R -X"
                )
            elif self.implementation_name == "quinn":
                self.implem_cmd = self.implem_cmd + " --zrtt"
                        
        # Retry case:
        if (
            "quic_server_test_retry_reuse_key" in self.name
            or "quic_server_test_retry" in self.name
        ):
            pass

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
                        self.implem_cmd = self.implem_cmd.replace("11.0.0.1", client_addr)
                        self.implem_cmd = self.implem_cmd.replace("11.0.0.3", client_addr)

                        self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.1", server_addr)
                        self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.3", server_addr)
                    elif self.is_attacker_client:
                        self.implem_cmd = self.implem_cmd.replace("11.0.0.1", client_addr)
                        self.implem_cmd = self.implem_cmd.replace("11.0.0.3", client_addr)

                        self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.1", server_addr)
                        self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.2", server_addr)
                    elif self.is_attacker_server:
                        self.implem_cmd = self.implem_cmd.replace("11.0.0.1", server_addr)
                        self.implem_cmd = self.implem_cmd.replace("11.0.0.3", server_addr)

                        self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.1", client_addr)
                        self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.3", client_addr)
                else:
                    self.log.error("Not implemented in non-bridged mode")
                    exit(1)
                    # self.implem_cmd = self.implem_cmd.replace("11.0.0.1", "10.0.0.5")
                    # self.implem_cmd = self.implem_cmd.replace("11.0.0.3", "10.0.0.5")

                    # self.implem_cmd_opposite = self.implem_cmd_opposite.replace(
                    #     "11.0.0.1", "10.0.0.6"
                    # )
                    # self.implem_cmd_opposite = self.implem_cmd_opposite.replace(
                    #     "11.0.0.3", "10.0.0.6"
                    # )
                netns_server = "tested_server"
                if is_target:
                    netns_server = "tested_tserver"
                maxreplace = 1
                self.implem_cmd = (
                    f"sudo ip netns exec {netns_server} " + envs + self.implem_cmd
                )
                old = "implem"
                if self.name == "mim_server_test_0rtt":
                    if self.implementation_name == "picoquic":
                        new = "implem -z"
                        self.implem_cmd = new.join(self.implem_cmd.rsplit(old, maxreplace))
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
                if self.name == "mim_server_test_0rtt":
                    if self.implementation_name == "picoquic":
                        new = "implem -z"
                        self.implem_cmd_opposite = new.join(self.implem_cmd_opposite.rsplit(old, maxreplace))
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
        elif self.config["net_parameters"].getboolean("shadow"):
            if self.is_mim:
                self.implem_cmd = self.implem_cmd.replace("11.0.0.1","11.0.0.3")
                self.implem_cmd = self.implem_cmd.replace("11.0.0.3","11.0.0.3")
                self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.1","11.0.0.3")
                self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.2","11.0.0.3")
            elif self.is_attacker_client:
                self.implem_cmd = self.implem_cmd.replace("11.0.0.1","11.0.0.2")
                self.implem_cmd = self.implem_cmd.replace("11.0.0.3","11.0.0.2")
                self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.2","11.0.0.1")
                self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.3","11.0.0.1")
            elif self.is_attacker_server:
                self.implem_cmd = self.implem_cmd.replace("11.0.0.2","11.0.0.1")
                self.implem_cmd = self.implem_cmd.replace("11.0.0.3","11.0.0.1")
                self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.1","11.0.0.2")
                self.implem_cmd_opposite = self.implem_cmd_opposite.replace("11.0.0.3","11.0.0.2")
        else:
            self.implem_cmd = (
                "RUST_LOG='debug' RUST_BACKTRACE=1 exec " + self.implem_cmd
            )
            self.implem_cmd = self.implem_cmd.replace(
                "10.0.0.1",
                "localhost"
                if self.implem_conf[0][self.implementation_name]["localhost"] == "true"
                else "127.0.0.1",
            )
            self.implem_cmd = self.implem_cmd.replace(
                "10.0.0.3",
                "localhost"
                if self.implem_conf[0][self.implementation_name]["localhost"] == "true"
                else "127.0.0.1",
            )
            self.implem_cmd = self.implem_cmd.replace(
                "11.0.0.1",
                "localhost"
                if self.implem_conf[0][self.implementation_name]["localhost"] == "true"
                else "127.0.0.1",
            )
            self.implem_cmd = self.implem_cmd.replace(
                "11.0.0.3",
                "localhost"
                if self.implem_conf[0][self.implementation_name]["localhost"] == "true"
                else "127.0.0.1",
            )
            # self.implem_cmd = self.implem_cmd.replace(
            #     "quic-implementations", "XXXXXXXX"
            # )
            maxreplace = 1
            old = "implem"
            new = "lo"
            self.implem_cmd = new.join(self.implem_cmd.rsplit(old, maxreplace))
            # self.implem_cmd.replace("implem", "lo")
            # self.implem_cmd = self.implem_cmd.replace(
            #     "XXXXXXXX", "quic-implementations"
            # )
            # self.implem_cmd = self.implem_cmd.replace(
            #     "VERSION",
            #     (
            #         "00000001"
            #         if ENV_VAR["INITIAL_VERSION"] == "1"
            #         else (
            #             "ff00001d" if ENV_VAR["INITIAL_VERSION"] == "29" else "ff00001c"
            #         )
            #     ),
            # )
            # self.implem_cmd = self.implem_cmd.replace("ALPN", ENV_VAR["TEST_ALPN"])
            self.log.debug(f"Update implementation after {self.implem_cmd}")

    # TODO add if to avoid space in command
    # TODO Reorder config param to loop and generate command eaisier
    def generate_implementation_command(self):
        self.log.info(f"Generate implementation command for {self.implementation_name}")
        
        self.log.info(self.implem_conf)
        server_implem_args = (
            self.implem_conf[0][self.implementation_name]["binary-name"]
            + " "
            + (
                self.implem_conf[0][self.implementation_name]["retry"]
                if "retry" in self.name
                else ""
            )
            + (
                self.implem_conf[0][self.implementation_name]["version-negociation"]
                if "version_negociation" in self.name
                else ""
            )
            + self.implem_conf[0][self.implementation_name]["cert-param"]
            + " "
            + self.implem_conf[0][self.implementation_name]["cert-file"]
            + " "
            + self.implem_conf[0][self.implementation_name]["key-param"]
            + " "
            + self.implem_conf[0][self.implementation_name]["key-file"]
            + " "
            + self.implem_conf[0][self.implementation_name]["root-cert-param"]
            + " "
            + self.implem_conf[0][self.implementation_name]["root-cert-file"]
            + " "
            + self.implem_conf[0][self.implementation_name]["log-param"]
            + " "
            + self.implem_conf[0][self.implementation_name]["log-file"]
            + " "
            + self.implem_conf[0][self.implementation_name]["qlog-param"]
            + " "
            + self.implem_conf[0][self.implementation_name]["qlog-file"]
            + " "
            + self.implem_conf[0][self.implementation_name]["secret-key-param"]
            + " "
            + self.implem_conf[0][self.implementation_name]["secret-key-file"]
            + " "
            + self.implem_conf[0][self.implementation_name]["alpn"]
            + " "
            + self.implem_conf[0][self.implementation_name]["alpn-value"]
            + " "
            + self.implem_conf[0][self.implementation_name]["version"]
            + " "
            + self.implem_conf[0][self.implementation_name]["version-value"]
            + " "
            + self.implem_conf[0][self.implementation_name]["verbosity"]
            + " "
            + self.implem_conf[1][self.implementation_name]["interface"]
            + " "
            + self.implem_conf[1][self.implementation_name]["interface-value"]
            + " "
            + self.implem_conf[0][self.implementation_name]["addition-parameters"]
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

        # server_implem_args = server_implem_args.replace("implem","lo")
        server_implem_args = server_implem_args.replace(
            "XXXXXXXX", "quic-implementations"
        )
        server_implem_args = server_implem_args.replace(
            "VERSION",
            (
                "00000001"
                if ENV_VAR["INITIAL_VERSION"] == "1"
                else ("ff00001d" if ENV_VAR["INITIAL_VERSION"] == "29" else "ff00001c")
            ),
        )
        server_implem_args = server_implem_args.replace("ALPN", ENV_VAR["TEST_ALPN"])
        server_implem_args = (
            server_implem_args.replace("$MODEL_DIR", MODEL_DIR)
            .replace("$SOURCE_DIR", SOURCE_DIR)
            .replace("$IMPLEM_DIR", self.implem_dir_server + "/")
        )
        server_implem_args = re.sub("\s{2,}", " ", server_implem_args)

        client_implem_args = (
            self.implem_conf[1][self.implementation_name]["binary-name"]
            + " "
            + (
                self.implem_conf[1][self.implementation_name]["versionnegociation"]
                if "version_negociation" in self.name
                else ""
            )
            + self.implem_conf[1][self.implementation_name]["cert-param"]
            + " "
            + self.implem_conf[1][self.implementation_name]["cert-file"]
            + " "
            + self.implem_conf[1][self.implementation_name]["key-param"]
            + " "
            + self.implem_conf[1][self.implementation_name]["key-file"]
            + " "
            + self.implem_conf[1][self.implementation_name]["root-cert-param"]
            + " "
            + self.implem_conf[1][self.implementation_name]["root-cert-file"]
            + " "
            + self.implem_conf[1][self.implementation_name]["log-param"]
            + " "
            + self.implem_conf[1][self.implementation_name]["log-file"]
            + " "
            + self.implem_conf[1][self.implementation_name]["qlog-param"]
            + " "
            + self.implem_conf[1][self.implementation_name]["qlog-file"]
            + " "
            + self.implem_conf[1][self.implementation_name]["secret-key-param"]
            + " "
            + self.implem_conf[1][self.implementation_name]["secret-key-file"]
            + " "
            + self.implem_conf[1][self.implementation_name]["alpn"]
            + " "
            + self.implem_conf[1][self.implementation_name]["alpn-value"]
            + " "
            + self.implem_conf[1][self.implementation_name]["version"]
            + " "
            + self.implem_conf[1][self.implementation_name]["version-value"]
            + " "
            + self.implem_conf[1][self.implementation_name]["verbosity"]
            + " "
            + self.implem_conf[1][self.implementation_name]["interface"]
            + " "
            + self.implem_conf[1][self.implementation_name]["interface-value"]
            + " "
            + self.implem_conf[1][self.implementation_name]["addition-parameters"]
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

        # client_implem_args = client_implem_args.replace("implem","lo")
        client_implem_args = client_implem_args.replace(
            "XXXXXXXX", "quic-implementations"
        )
        client_implem_args = client_implem_args.replace(
            "VERSION",
            (
                "00000001"
                if ENV_VAR["INITIAL_VERSION"] == "1"
                else ("ff00001d" if ENV_VAR["INITIAL_VERSION"] == "29" else "ff00001c")
            ),
        )
        client_implem_args = client_implem_args.replace("ALPN", ENV_VAR["TEST_ALPN"])
        client_implem_args = (
            client_implem_args.replace("$MODEL_DIR", MODEL_DIR)
            .replace("$SOURCE_DIR", SOURCE_DIR)
            .replace("$IMPLEM_DIR", self.implem_dir_server + "/")
        )
        client_implem_args = re.sub("\s{2,}", " ", client_implem_args)

        self.log.debug(f"Server implem args: {server_implem_args}")
        self.log.debug(f"Client implem args: {client_implem_args}")
        if self.is_client:
            return [client_implem_args, server_implem_args]
        else:
            return [server_implem_args, client_implem_args]

    def set_process_limits(self):
        # Create a new session
        os.setsid()

    def start_target_implementation(self, i, out, err):
        """_summary_

        Args:
            i (_type_): _description_
            out (_type_): _description_
            err (_type_): _description_
        """
        if self.config["global_parameters"].getboolean("run"):
            if self.is_mim:
                self.log.info("Man in the middle test")
                pass
            elif self.is_attacker_client:
                self.log.info("Attacker client test")
                pass
            elif self.is_attacker_server:
                self.log.info("Attacker server test")
                pass
            else:
                self.log.info("Updating implementation:")
                print("Updating implementation:")
                self.update_implementation_command(i,True)
                self.log.info(self.implem_cmd)
                print(self.implem_cmd)
                if (
                    "quic_client_test_0rtt" in self.name
                    and (
                        self.implementation_name == "quinn"
                        or self.implementation_name == "quic-go"
                    )
                    and i == 1
                ):
                    pass
                else:
                    qcmd = (
                        "sleep 5; "
                        if self.is_client
                        and not self.config["net_parameters"].getboolean("shadow")
                        else ""
                    ) + self.implem_cmd  # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +

                    self.log.info("Implementation command: {}".format(qcmd))
                    self.log.info(
                        "Implementation diretory: {}".format(
                            self.implem_dir_client
                            if self.is_client
                            else self.implem_dir_server
                        )
                    )
                    self.log.info(self.config["net_parameters"].getboolean("shadow"))
                    print("Implementation command: {}".format(qcmd))
                    print(
                        "Implementation diretory: {}".format(
                            self.implem_dir_client
                            if self.is_client
                            else self.implem_dir_server
                        )
                    )
                    print(self.config["net_parameters"].getboolean("shadow"))
                    if not self.config["net_parameters"].getboolean("shadow"):
                        self.log.debug("Not shadow test:")
                        print("Not shadow test:")
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
                        print("implem_process pid: {}".format(self.implem_process.pid))
                    else:
                        self.log.info("Generate shadow config")
                        print("Generate shadow config")
                        file = self.generate_shadow_config()
                        try:
                            os.system(
                                "RUST_BACKTRACE=1 shadow " + file + " > shadow.log"
                            )
                        except Exception as e:
                            print(e)
        # TODO check if it still work
        if self.is_mim:
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
                    # https://stackoverflow.com/questions/78293129/c-programs-fail-with-asan-addresssanitizerdeadlysignal
                    # echo 0 | sudo tee /proc/sys/kernel/randomize_va_space
                    os.system("ip netns exec tested_client echo 0 | sudo tee /proc/sys/kernel/randomize_va_space")
                    os.system("ip netns exec tested_server echo 0 | sudo tee /proc/sys/kernel/randomize_va_space")
                    qcmd = (
                    self.implem_cmd
                    )  # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +
                else:
                    qcmd = (
                        "RUST_LOG='debug' RUST_BACKTRACE=1  exec "
                        + self.implem_cmd
                    )

                self.log.info("Implementation command server: {}".format(qcmd))
                print("Implementation command server: {}".format(qcmd))
                self.quic_process_1 = subprocess.Popen(
                    qcmd,
                    cwd=(self.implem_dir_server),
                    stdout=out,
                    stderr=err,
                    shell=True,  # self.is_client,
                    preexec_fn=self.set_process_limits,
                )
                self.log.info("quic_process_1 pid: {}".format(self.quic_process_1.pid))
                print("quic_process_1 pid: {}".format(self.quic_process_1.pid))
                if self.implementation_name == "quant": # TODO clearner
                    qcmd = (
                        "sleep 10; "
                        + " "
                        + self.implem_cmd_opposite
                    )
                else:
                    qcmd = (
                        "sleep 10; "
                        + "RUST_LOG='debug' RUST_BACKTRACE=1  exec "
                        + self.implem_cmd_opposite
                    )  
                
                self.log.info("Implementation command client: {}".format(qcmd))
                print("Implementation command client: {}".format(qcmd))
                with self.open_out(self.name + "_client.out") as out_c:
                    with self.open_out(self.name + "_client.err") as err_c:
                        self.quic_process_2 = subprocess.Popen(
                            qcmd,
                            cwd=(self.implem_dir_client),
                            stdout=out_c,
                            stderr=err_c,
                            shell=True,  # self.is_client,
                            preexec_fn=self.set_process_limits,
                        )
                self.log.info("quic_process_2 pid: {}".format(self.quic_process_2.pid))
                print("quic_process_2 pid: {}".format(self.quic_process_2.pid))
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
                self.quic_process_1 = subprocess.Popen(
                    qcmd,
                    cwd=(self.implem_dir_server),
                    stdout=out,
                    stderr=err,
                    shell=True,
                    preexec_fn=self.set_process_limits,
                )
                self.log.info("quic_process_1 pid: {}".format(self.quic_process_1.pid))
                print("quic_process_1 pid: {}".format(self.quic_process_1.pid))
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
                self.quic_process_1 = subprocess.Popen(
                    qcmd,
                    cwd=(self.implem_dir_client),
                    stdout=out,
                    stderr=err,
                    shell=True,
                    preexec_fn=self.set_process_limits,
                )
                self.log.info("quic_process_1 pid: {}".format(self.quic_process_1.pid))
                print("quic_process_1 pid: {}".format(self.quic_process_1.pid))
     
     
    def start_implementation(self, i, out, err):
        """_summary_

        Args:
            i (_type_): _description_
            out (_type_): _description_
            err (_type_): _description_
        """
        if self.config["global_parameters"].getboolean("run"):
            if self.is_mim:
                self.log.info("Man in the middle test")
                pass
            elif self.is_attacker_client:
                self.log.info("Attacker client test")
                pass
            elif self.is_attacker_server:
                self.log.info("Attacker server test")
                pass
            else:
                self.log.info("Updating implementation:")
                print("Updating implementation:")
                self.update_implementation_command(i)
                self.log.info(self.implem_cmd)
                print(self.implem_cmd)
                if (
                    "quic_client_test_0rtt" in self.name
                    and (
                        self.implementation_name == "quinn"
                        or self.implementation_name == "quic-go"
                    )
                    and i == 1
                ):
                    pass
                else:
                    qcmd = (
                        "sleep 5; "
                        if self.is_client
                        and not self.config["net_parameters"].getboolean("shadow")
                        else ""
                    ) + self.implem_cmd  # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +

                    self.log.info("Implementation command: {}".format(qcmd))
                    self.log.info(
                        "Implementation diretory: {}".format(
                            self.implem_dir_client
                            if self.is_client
                            else self.implem_dir_server
                        )
                    )
                    self.log.info(self.config["net_parameters"].getboolean("shadow"))
                    print("Implementation command: {}".format(qcmd))
                    print(
                        "Implementation diretory: {}".format(
                            self.implem_dir_client
                            if self.is_client
                            else self.implem_dir_server
                        )
                    )
                    print(self.config["net_parameters"].getboolean("shadow"))
                    if not self.config["net_parameters"].getboolean("shadow"):
                        self.log.debug("Not shadow test:")
                        print("Not shadow test:")
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
                        print("implem_process pid: {}".format(self.implem_process.pid))
                    else:
                        self.log.info("Generate shadow config")
                        print("Generate shadow config")
                        file = self.generate_shadow_config()
                        try:
                            os.system(
                                "RUST_BACKTRACE=1 shadow " + file + " > shadow.log"
                            )
                        except Exception as e:
                            print(e)
        # TODO check if it still work
        if self.is_mim:
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
                    # https://stackoverflow.com/questions/78293129/c-programs-fail-with-asan-addresssanitizerdeadlysignal
                    # echo 0 | sudo tee /proc/sys/kernel/randomize_va_space
                    os.system("ip netns exec tested_client echo 0 | sudo tee /proc/sys/kernel/randomize_va_space")
                    os.system("ip netns exec tested_server echo 0 | sudo tee /proc/sys/kernel/randomize_va_space")
                    qcmd = (
                    self.implem_cmd
                    )  # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +
                else:
                    qcmd = (
                        "RUST_LOG='debug' RUST_BACKTRACE=1  exec "
                        + self.implem_cmd
                    )

                self.log.info("Implementation command server: {}".format(qcmd))
                print("Implementation command server: {}".format(qcmd))
                self.quic_process_1 = subprocess.Popen(
                    qcmd,
                    cwd=(self.implem_dir_server),
                    stdout=out,
                    stderr=err,
                    shell=True,  # self.is_client,
                    preexec_fn=self.set_process_limits,
                )
                self.log.info("quic_process_1 pid: {}".format(self.quic_process_1.pid))
                print("quic_process_1 pid: {}".format(self.quic_process_1.pid))
                if self.implementation_name == "quant": # TODO clearner
                    qcmd = (
                        "sleep 10; "
                        + " "
                        + self.implem_cmd_opposite
                    )
                else:
                    qcmd = (
                        "sleep 10; "
                        + "RUST_LOG='debug' RUST_BACKTRACE=1  exec "
                        + self.implem_cmd_opposite
                    )  
                if "quic_mim_test_replay_0rtt" in self.name:
                    self.log.info("Implementation command client: {}".format(qcmd))
                    print("Implementation command client: {}".format(qcmd))
                    with self.open_out(self.name + "_pre_client.out") as out_c:
                        with self.open_out(self.name + "_pre_client.err") as err_c:
                            self.quic_process_pre = subprocess.Popen(
                                qcmd,
                                cwd=(self.implem_dir_client),
                                stdout=out_c,
                                stderr=err_c,
                                shell=True,  # self.is_client,
                                preexec_fn=self.set_process_limits,
                            )
                    self.log.info("quic_process_pre pid: {}".format(self.quic_process_pre.pid))
                    print("quic_process_pre pid: {}".format(self.quic_process_pre.pid))
                    self.log.info("Implementation command client: {}".format(qcmd))
                    print("Implementation command client: {}".format(qcmd))
                    with self.open_out(self.name + "_client.out") as out_c:
                        with self.open_out(self.name + "_client.err") as err_c:
                            self.quic_process_2 = subprocess.Popen(
                                qcmd.replace("sleep 10; ","sleep 50; "),
                                cwd=(self.implem_dir_client),
                                stdout=out_c,
                                stderr=err_c,
                                shell=True,  # self.is_client,
                                preexec_fn=self.set_process_limits,
                            )
                    self.log.info("quic_process_2 pid: {}".format(self.quic_process_2.pid))
                    print("quic_process_2 pid: {}".format(self.quic_process_2.pid))
                else:
                    self.log.info("Implementation command client: {}".format(qcmd))
                    print("Implementation command client: {}".format(qcmd))
                    with self.open_out(self.name + "_client.out") as out_c:
                        with self.open_out(self.name + "_client.err") as err_c:
                            self.quic_process_2 = subprocess.Popen(
                                qcmd,
                                cwd=(self.implem_dir_client),
                                stdout=out_c,
                                stderr=err_c,
                                shell=True,  # self.is_client,
                                preexec_fn=self.set_process_limits,
                            )
                    self.log.info("quic_process_2 pid: {}".format(self.quic_process_2.pid))
                    print("quic_process_2 pid: {}".format(self.quic_process_2.pid))
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
                self.quic_process_1 = subprocess.Popen(
                    qcmd,
                    cwd=(self.implem_dir_server),
                    stdout=out,
                    stderr=err,
                    shell=True,
                    preexec_fn=self.set_process_limits,
                )
                self.log.info("quic_process_1 pid: {}".format(self.quic_process_1.pid))
                print("quic_process_1 pid: {}".format(self.quic_process_1.pid))
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
                self.quic_process_1 = subprocess.Popen(
                    qcmd,
                    cwd=(self.implem_dir_client),
                    stdout=out,
                    stderr=err,
                    shell=True,
                    preexec_fn=self.set_process_limits,
                )
                self.log.info("quic_process_1 pid: {}".format(self.quic_process_1.pid))
                print("quic_process_1 pid: {}".format(self.quic_process_1.pid))
                
    def start_tester(self, iteration, iev, i):
        self.log.info("Starting tester:")
        print("Starting tester:")
        ok = True
        if not self.config["net_parameters"].getboolean("shadow"):
            try:
                for iclient in range(
                    0, self.nclient
                ):  # TODO for multiple implem client only
                    self.log.debug("iclient = " + str(iclient))
                    print("iclient = " + str(iclient))
                    ok = ok and self.run_tester(iteration, iev, i, iclient)
            except KeyboardInterrupt:
                if not self.is_mim and not self.is_attacker_client and not self.is_attacker_server:
                    if self.config["global_parameters"].getboolean(
                        "run"
                    ) and not self.config["global_parameters"].getboolean("keep_alive"):
                        if self.config["net_parameters"].getboolean("vnet"):
                            if "mim" in self.name or "attack" in self.name:
                                run_steps(reset_mim, ignore_errors=True)
                            else:
                                run_steps(reset, ignore_errors=True)
                        self.implem_process.terminate()
                    raise KeyboardInterrupt
                else:
                    if self.config["global_parameters"].getboolean(
                        "run"
                    ) and not self.config["global_parameters"].getboolean("keep_alive"):
                        if self.config["net_parameters"].getboolean("vnet"):
                            if "mim" in self.name or "attack" in self.name:
                                run_steps(reset_mim, ignore_errors=True)
                            else:
                                run_steps(reset, ignore_errors=True)
                        self.quic_process_1.terminate()
                        self.quic_process_2.terminate()
                    raise KeyboardInterrupt

            if (
                self.config["global_parameters"].getboolean("run")
                and not self.config["global_parameters"].getboolean("keep_alive")
                and not (
                    self.implementation_name == "quic-go"
                    and "quic_client_test_0rtt" in self.name
                )
            ):
                self.log.info("self.stop_processes()")
                print("self.stop_processes()")
                if not self.is_mim and not self.is_attacker_client and not self.is_attacker_server:
                    # The above code is terminating the process.
                    self.implem_process.terminate()
                    retcode = self.implem_process.wait()
                    self.log.info(retcode)
                    print(retcode)
                    if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                        iev.write("server_return_code({})\n".format(retcode))
                        self.log.info("server return code: {}".format(retcode))
                        print("server return code: {}".format(retcode))
                        self.implem_process.kill()
                        return False
                else:
                    if self.is_attacker_client or self.is_attacker_server or self.is_mim:
                        self.quic_process_1.terminate()
                        retcode = self.quic_process_1.wait()
                        self.log.info(retcode)
                        print(retcode)
                        if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                            iev.write("server_return_code({})\n".format(retcode))
                            self.log.info("server return code: {}".format(retcode))
                            print("server return code: {}".format(retcode))
                            self.quic_process_1.kill()
                            return False
                    self.quic_process_2.terminate()
                    retcode = self.quic_process_2.wait()
                    self.log.info(retcode)
                    print(retcode)
                    if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                        iev.write("server_return_code({})\n".format(retcode))
                        self.log.info("server return code: {}".format(retcode))
                        print("server return code: {}".format(retcode))
                        self.quic_process_2.kill()
                        return False
        return ok

    def stop_processes(self):
        self.log.info("Stop processes:")
        print("Stop processes:")
        if not self.is_mim and not self.is_attacker_client and not self.is_attacker_server:
            if self.implem_process != None:
                try:
                    # os.kill(implem_process.pid, 9)
                    os.killpg(os.getpgid(self.implem_process.pid), signal.SIGTERM)
                except OSError:
                    self.log.info("pid is unassigned")
                    print("pid is unassigned")
                    self.implem_process.kill()
            else:
                self.log.info("pid is in use")
                print("pid is in use")
                self.implem_process.kill()
                self.log.info("implem_process.kill()")
                print("implem_process.kill()")
        else:
            if self.quic_process_1 is not None:
                try:
                    self.quic_process_1.terminate()
                    try:
                        retcode = self.quic_process_1.wait(timeout=10)  # Timeout after 10 seconds
                    except subprocess.TimeoutExpired:
                        self.log.info("Process did not terminate in time, killing it forcefully.")
                        self.quic_process_1.kill()
                        retcode = self.quic_process_1.wait()  # Wait again after killing
                    self.log.info(f"Process terminated with return code: {retcode}")
                    print(f"Process terminated with return code: {retcode}")
                    if retcode not in [-15, 0]:  # If not terminated by SIGTERM or normal exit
                        self.quic_process_1.kill()
                        self.log.info("Process killed due to non-zero exit code.")
                except Exception as e:
                    self.log.error(f"Failed to terminate process: {e}")
                    print(f"Failed to terminate process: {e}")
                    
            
            if self.quic_process_2 is not None:
                try:
                    self.quic_process_2.terminate()
                    try:
                        retcode = self.quic_process_2.wait(timeout=10)  # Timeout after 10 seconds
                    except subprocess.TimeoutExpired:
                        self.log.info("Process did not terminate in time, killing it forcefully.")
                        self.quic_process_2.kill()
                        retcode = self.quic_process_2.wait()  # Wait again after killing
                    self.log.info(f"Process terminated with return code: {retcode}")
                    print(f"Process terminated with return code: {retcode}")
                    if retcode not in [-15, 0]:  # If not terminated by SIGTERM or normal exit
                        self.quic_process_2.kill()
                        self.log.info("Process killed due to non-zero exit code.")
                except Exception as e:
                    self.log.error(f"Failed to terminate process: {e}")
                    print(f"Failed to terminate process: {e}")


    def generate_tester_command(self, iteration, iclient):
        strace_cmd, gperf_cmd, timeout_cmd = super().generate_tester_command(
            iteration, iclient
        )
        
        self.log.info("Generating tester command: {}".format(self.name))

        os.environ["TIMEOUT_IVY"] = str(
            self.config["global_parameters"].getint("timeout")
        )

        ENV_VAR["PROTOCOL_TESTED"] = self.current_protocol

        timeout_cmd = ("sleep 5; " if not self.is_client else "") + timeout_cmd

        randomSeed = random.randint(0, 1000)
        random.seed(datetime.now())

        prefix = ""

        # TODO config file
        initial_version = self.protocol_conf["quic_parameters"].getint(
            "initial_version"
        )
        send_co_close = True
        send_app_close = True
        server_port = 4443
        server_port_run_2 = 4444

        client_port = 2 * iteration + 4987 + iclient
        client_port_alt = 2 * iteration + 4988 + iclient

        # TODO random ?
        # TODO bug when swap value, __arg problem i think
        if self.is_client:  # BUG when cidlen != 8 check __ser
            server_cid = 0
            the_cid = server_cid + 1
            server_cid_2 = server_cid
            the_cid_2 = the_cid
        else:
            # server_cid = iteration
            # the_cid = server_cid + 1
            the_cid = iteration+1
            server_cid = the_cid*100 + 1
            server_cid_2 = server_cid + 2
            the_cid_2 = the_cid + 2

        # TODO port for multiple clients

        if self.name == "quic_server_test_0rtt" or self.name == "mim_server_test_0rtt":
            server_port_run_2 = 4443

        if self.name == "quic_server_test_retry_reuse_key":
            n_clients = 2
            server_port_run_2 = 4443
            server_cid = 1
            the_cid = server_cid + 1
            # the_cid = iteration
            # server_cid = the_cid + 1
            server_cid_2 = server_cid + 2
            the_cid_2 = the_cid + 2

        # Only for mim agent for now
        modify_packets = (
            "true"
            if self.name == "quic_client_test_version_negociation_mim_modify"
            else "false"
        )

        self.log.info(self.name)
        print(self.name)
        # time.sleep(5)
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

        if self.config["net_parameters"].getboolean("vnet"):
            self.log.debug("Prefix added: vnet")
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
            if self.is_mim:
                if self.config["vnet_parameters"].getboolean("bridged"):
                    ip_client = 0x0B000002
                    ip_server = 0x0B000003
                else:
                    ip_server = 0x0B000004
                    ip_client = 0x0B000002
            elif self.is_attacker_client:
                ip_client = 0x0B000002
                ip_server = 0x0B000003
            elif self.is_attacker_server:
                ip_client = 0x0B000002
                ip_server = 0x0B000003
            else:
                ip_server = 0x0B000002 if not self.is_client else 0x0B000001
                ip_client = 0x0B000001 if not self.is_client else 0x0B000002
        else:
            ip_server = 0x7F000001
            ip_client = ip_server

        self.log.debug(f"Prefix of tester command: {prefix}")

        if self.name in QUIC_PAIRED_TEST.keys():  # TODO build quic_server_test_stream
            first_test = QUIC_PAIRED_TEST[self.name]
            if (
                self.name == "quic_client_test_0rtt"
                or self.name == "quic_server_test_0rtt"
            ):
                if self.j == 1:
                    first_test += "_app_close"
                elif self.j == 2:
                    first_test += "_co_close"
            return (
                (
                    " ".join(
                        [
                            "{}{}{}/{} seed={} the_cid={} server_port={} iversion={} server_addr={} {}".format(
                                timeout_cmd,
                                prefix,
                                self.config["global_parameters"]["build_dir"],
                                first_test,
                                randomSeed,
                                the_cid,
                                server_port,
                                initial_version,
                                ip_server,
                                (
                                    ""
                                    if self.is_client
                                    else "server_cid={} client_port={} client_port_alt={} client_addr={}".format(
                                        server_cid,
                                        client_port,
                                        client_port_alt,
                                        ip_client,
                                    )
                                ),
                            )
                        ]
                        + self.extra_args
                        + (
                            [""]
                            if self.config["net_parameters"].getboolean("vnet")
                            else [""]
                        )
                    )
                )
                + ";sleep 1;"
                + " ".join(
                    [
                        "{}{}{}/{} seed={} the_cid={} server_port={} iversion={} server_addr={} {}".format(
                            timeout_cmd,
                            prefix,
                            self.config["global_parameters"]["build_dir"],
                            self.name,
                            randomSeed,
                            the_cid_2,
                            server_port_run_2,
                            initial_version,
                            ip_server,
                            (
                                ""  # TODO port + iteration -> change imple
                                if self.is_client
                                else "server_cid={} client_port={} client_port_alt={} client_addr={}".format(
                                    server_cid_2,
                                    client_port,
                                    client_port_alt,
                                    ip_client,
                                )
                            ),
                        )
                    ]
                    + self.extra_args
                    + (
                        [""]
                        if self.config["net_parameters"].getboolean("vnet")
                        else [""]
                    )
                )
            )
        else:
            return " ".join(
                [
                    "{}{}{}/{} seed={} the_cid={} server_port={} iversion={} server_addr={} modify_packets={} {}".format(
                        timeout_cmd,
                        prefix,
                        self.config["global_parameters"]["build_dir"],
                        self.name,
                        randomSeed,
                        the_cid,
                        server_port,
                        initial_version,
                        ip_server,
                        modify_packets,
                        (
                            ""
                            if self.is_client
                            else "server_cid={} client_port={} client_port_alt={} client_addr={}".format(
                                server_cid, client_port, client_port_alt, ip_client
                            )
                        ),
                    )
                ]
                + self.extra_args
                + ([""] if self.config["net_parameters"].getboolean("vnet") else [""])
            )  #  TODO remove last param +[""] if self.config["net_parameters"].getboolean("vnet") else [""]
