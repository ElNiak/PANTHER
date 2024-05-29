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

from pfv_tester.pfv_tester import IvyTest
from pfv_utils.pfv_constant import *

# On Windows, pexpect doesn't implement 'spawn'.
"""
Choose the process spawner for subprocess according to plateform
"""
if platform.system() == 'Windows':
    from pexpect.popen_spawn import PopenSpawn
    spawn = PopenSpawn
else:
    spawn = pexpect.spawn
# TODO replace print per log but save in file
# TODO add tested implemenatation name
class QUICIvyTest(IvyTest):
    def __init__(self,args,
                 implem_dir_server, 
                 implem_dir_client,
                 extra_args, 
                 implementation_name,
                 mode,
                 config, 
                 protocol_conf,
                 implem_conf,
                 current_protocol):
        
        super().__init__(args,implem_dir_server,implem_dir_client,extra_args,implementation_name,mode,config,protocol_conf,implem_conf,current_protocol)

        self.specials = {
            "quic_server_test_0rtt":"quic_server_test_0rtt_stream",
            "quic_client_test_new_token_address_validation":"quic_client_test_new_token_address_validation",
            "quic_client_test_0rtt":"quic_client_test_0rtt_max",
            "quic_client_test_0rtt_add_val":"quic_client_test_0rtt_max_add_val",
            "quic_client_test_0rtt_invalid":"quic_client_test_0rtt_max",
            "quic_client_test_0rtt_mim_replay":"quic_client_test_0rtt_max",
            "quic_server_test_retry_reuse_key":"quic_server_test_retry"
        }
        
        self.special_tests_compatible_impl = {
            "quic_server_test_retry_reuse_key":["picoquic-vuln","picoquic"],
            "quic_server_test_retry":["quant","quant-vuln", "picoquic-vuln","picoquic","aioquic","quiche","quinn","quic-go","mvfst"],
            "quic_client_test_version_negociation":["quant","quant-vuln", "picoquic-vuln","picoquic","aioquic","quiche","quinn","quic-go","lsquic","lsquic-vuln"],
        }
        
        # MORE config
        # TODO implem
        self.specials2 = {
            "quic_server_test_retry_reuse_key": {
                "picoquic-vuln":'./picoquicdemo -l "n"  -D -L -r',
                "picoquic":'./picoquicdemo -l - -r -D -L -q '+SOURCE_DIR +'/qlog/picoquic',
                "quant":IMPLEM_DIR.replace("$PROT",self.current_protocol)+'/quant/Debug/bin/server -x 1000 -d . -o -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant -l '+SOURCE_DIR +'/tls-keys/secret.log -r',
                "quant-vuln":IMPLEM_DIR.replace("$PROT",self.current_protocol)+'/quant-vuln/Debug/bin/server -x 1000 -d . -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant -l '+SOURCE_DIR +'/tls-keys/secret.log -r'
            },
            "quic_server_test_retry":{
                "quant":IMPLEM_DIR.replace("$PROT",self.current_protocol)+'/quant/Debug/bin/server -x 1000 -d . -o -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant -l '+SOURCE_DIR +'/tls-keys/secret.log -r',
                "quant-vuln":IMPLEM_DIR.replace("$PROT",self.current_protocol)+'/quant-vuln/Debug/bin/server -x 1000 -d . -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant -l '+SOURCE_DIR +'/tls-keys/secret.log -r',
                "picoquic":'./picoquicdemo -l "n" -D -L -q '+SOURCE_DIR +'/qlog/picoquic -r',
                "picoquic-vuln":'./picoquicdemo -l - -D -L -r',                
                "aioquic":'python3.9 examples/http3_server.py --quic-log '+SOURCE_DIR +'/qlogs/aioquic --certificate '+SOURCE_DIR +'/implementations/quic-implementations/aioquic/tests/ssl_cert.pem --private-key '+SOURCE_DIR +'/implementations/quic-implementations/aioquic/tests/ssl_key.pem  -v --retry --host 127.0.0.1 --port 4443 -l '+SOURCE_DIR +'/tls-keys/secret.log' ,
                "quiche":'cargo run --bin quiche-server --  --cert '+ SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/cert.pem --early-data --dump-packets '+SOURCE_DIR +'/qlogs/quiche/dump_packet.txt --key '+SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/priv.key --listen 127.0.0.1:4443',
                "quinn":'cargo run -vv --example server '+SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/index.html --keylog --stateless-retry --listen 127.0.0.1:4443',
                "quic-go":'./server -c '+SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/cert.pem -k '+SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/priv.key -r -p 4443 127.0.0.1',
                "mvfst": "./echo -mode=server -host=127.0.0.1 -port=4443  -v=10 -pr=true"
            },
            "quic_client_test_version_negociation":{
                "quant":IMPLEM_DIR.replace("$PROT",self.current_protocol) + '/quant/Debug/bin/client -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html',
                "quant-vuln":IMPLEM_DIR.replace("$PROT",self.current_protocol) + '/quant-vuln/Debug/bin/client -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html',
                "picoquic": './picoquicdemo -z -l - -D -L -a hq-interop localhost 4443' ,
                "aioquic":  'python3.9 examples/http3_client.py --version_negociation -l '+SOURCE_DIR +'/tls-keys/secret.log -v -q '+SOURCE_DIR +'/qlogs/aioquic/ --ca-certs tests/pycacert.pem -i --insecure --legacy-http https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html',
                "quiche": 'RUST_LOG="debug" cargo run --bin quiche-client -- https://localhost:4443/index.html --dump-json --no-verify --body / -n 5',
                "quic-go":'./client -X '+SOURCE_DIR +'/tls-keys/secret.log -V -P -v 127.0.0.1 4443',
                "lsquic":"./http_client -4 -Q hq-29 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8",
                "lsquic-vuln":"./http_client -4 -Q hq-29 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1 -o version=FF00001D -o scid_len=8"
            },
            "quic_client_test_version_negociation_mim_forge":{
                "quant":IMPLEM_DIR.replace("$PROT",self.current_protocol) + '/quant/Debug/bin/client -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html',
                "quant-vuln":IMPLEM_DIR.replace("$PROT",self.current_protocol) + '/quant-vuln/Debug/bin/client -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html',
                "picoquic": './picoquicdemo -G bbr -l - -D -L -a hq-interop -v 00000001 localhost 4443' , # CUBIC important for rtt
                "aioquic":  'python3.9 examples/http3_client.py --version_negociation -l '+SOURCE_DIR +'/tls-keys/secret.log -v -q '+SOURCE_DIR +'/qlogs/aioquic/ --ca-certs tests/pycacert.pem -i --insecure --legacy-http https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html',
                "quiche": 'RUST_LOG="debug" cargo run --bin quiche-client -- https://localhost:4443/index.html --dump-json --no-verify --body / -n 5',
                "quic-go":'./client -X '+SOURCE_DIR +'/tls-keys/secret.log -V -P -v 127.0.0.1 4443',
                "lsquic":"./http_client -4 -Q hq-29 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8",
                "lsquic-vuln":"./http_client -4 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8"
            },
            "quic_client_test_version_negociation_mim_manual":{
                "quant":IMPLEM_DIR.replace("$PROT",self.current_protocol) + '/quant/Debug/bin/client -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html',
                "quant-vuln":IMPLEM_DIR.replace("$PROT",self.current_protocol) + '/quant-vuln/Debug/bin/client -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html',
                "picoquic": './picoquicdemo -l - -D -L -a hq-29 localhost 4443' ,
                "aioquic":  'python3.9 examples/http3_client.py --version_negociation -l '+SOURCE_DIR +'/tls-keys/secret.log -v -q '+SOURCE_DIR +'/qlogs/aioquic/ --ca-certs tests/pycacert.pem -i --insecure --legacy-http https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html',
                "quiche": 'RUST_LOG="debug" cargo run --bin quiche-client -- https://localhost:4443/index.html --dump-json --no-verify --body / -n 5',
                "quic-go":'./client -X '+SOURCE_DIR +'/tls-keys/secret.log -V -P -v 127.0.0.1 4443',
                "lsquic":"./http_client -4 -Q hq-29 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8",
                "lsquic-vuln":"./http_client -4 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8"
            }
        }

        self.is_mim    = True if "mim"    in self.mode else False
        
        self.loop = {
            "quic_server_test_0rtt":2,
        }
           
    def update_implementation_command(self,i):
        # TODO add that in config file
        if i == 1:
            self.implem_cmd = self.implem_cmd.replace("4443","4444")
            if self.implementation_name == "mvfst":
                self.implem_cmd = self.implem_cmd + " -zrtt=true"
            elif self.implementation_name == "quiche":
                self.implem_cmd = self.implem_cmd + " --early-data"
        
        if i == 0 and  "quic_client_test_0rtt" in self.name:
            if self.implementation_name == "quic-go": # change port for 2d run directly in implem
                self.implem_cmd = self.implem_cmd.replace("./client -X", "./client -R -X")
            elif self.implementation_name == "quinn":
                self.implem_cmd = self.implem_cmd + " --zrtt"
                
        if self.config["net_parameters"].getboolean("vnet"):
            implem_cmd_copy = self.implem_cmd
            implem_cmd = "sudo ip netns exec implem " 
            # if self.implementation_name == "picoquic":
            #     implem_cmd = "cd " + IMPLEM_DIR.replace("$PROT",self.current_protocol) + '/picoquic;'  + implem_cmd + "cd " + IMPLEM_DIR.replace("$PROT",self.current_protocol) + '/picoquic;'
            envs = "env - "
            for env_var in ENV_VAR:
                if env_var != "PATH": # TODO remove it is useless
                    envs = envs + env_var + "=\"" + ENV_VAR[env_var] + "\" "
                else:
                    envs = envs + env_var + "=\"" + os.environ.get(env_var) + "\" "
            self.implem_cmd = self.implem_cmd + envs + implem_cmd_copy 
        else :
            self.implem_cmd = "exec " + self.implem_cmd
            self.implem_cmd = self.implem_cmd.replace("10.0.0.1","localhost")
            self.implem_cmd = self.implem_cmd.replace("10.0.0.3","localhost")
            self.implem_cmd = self.implem_cmd.replace("quic-implementations","XXXXXXXX")
            self.implem_cmd = self.implem_cmd.replace("implem","lo")
            self.implem_cmd = self.implem_cmd.replace("XXXXXXXX","quic-implementations")
            self.implem_cmd = self.implem_cmd.replace("VERSION","00000001" if ENV_VAR["INITIAL_VERSION"] == "1" else ("ff00001d" if ENV_VAR["INITIAL_VERSION"] == "29" else "ff00001c"))
            self.implem_cmd = self.implem_cmd.replace("ALPN",ENV_VAR["TEST_ALPN"])
    
    def generate_shadow_config(self):
        server_implem_args = self.implem_conf[0][self.implementation_name]["cert-param"] + " " + self.implem_conf[0][self.implementation_name]["cert-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[0][self.implementation_name]["key-param"] + " " + self.implem_conf[0][self.implementation_name]["key-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[0][self.implementation_name]["root-cert-param"] + " " + self.implem_conf[0][self.implementation_name]["root-cert-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[0][self.implementation_name]["log-param"] + " " + self.implem_conf[0][self.implementation_name]["log-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[0][self.implementation_name]["qlog-param"] + " " + self.implem_conf[0][self.implementation_name]["qlog-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[0][self.implementation_name]["secret-key-param"] + " " + self.implem_conf[0][self.implementation_name]["secret-key-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[0][self.implementation_name]["alpn"] + " " + self.implem_conf[0][self.implementation_name]["alpn-value"] \
            + " " + self.implem_conf[0][self.implementation_name]["version"] + " " + self.implem_conf[0][self.implementation_name]["version-value"] \
            + " " + self.implem_conf[0][self.implementation_name]["verbosity"] + " " + self.implem_conf[0][self.implementation_name]["addition-parameters"] \
            + " " + self.implem_conf[0][self.implementation_name]["source-format"].replace("[source]", 
                                                                                                self.implem_conf[0][self.implementation_name]["source"]
                                                                                    ).replace("[source-value]", 
                                                                                                self.implem_conf[0][self.implementation_name]["source-value"]
                                                                                    ).replace("[port]", 
                                                                                                self.implem_conf[0][self.implementation_name]["port"]
                                                                                    ).replace("[port-value]", 
                                                                                                self.implem_conf[0][self.implementation_name]["port-value"]) 
        
        # server_implem_args = server_implem_args.replace("implem","lo")
        server_implem_args = server_implem_args.replace("XXXXXXXX","quic-implementations")
        server_implem_args = server_implem_args.replace("VERSION","00000001" if ENV_VAR["INITIAL_VERSION"] == "1" else ("ff00001d" if ENV_VAR["INITIAL_VERSION"] == "29" else "ff00001c"))
        server_implem_args = server_implem_args.replace("ALPN",ENV_VAR["TEST_ALPN"])
        server_implem_args = re.sub('\s{2,}', ' ', server_implem_args)
        
        client_implem_args = self.implem_conf[1][self.implementation_name]["cert-param"] + " " + self.implem_conf[1][self.implementation_name]["cert-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[1][self.implementation_name]["key-param"] + " " + self.implem_conf[1][self.implementation_name]["key-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[1][self.implementation_name]["root-cert-param"] + " " + self.implem_conf[1][self.implementation_name]["root-cert-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[1][self.implementation_name]["log-param"] + " " + self.implem_conf[1][self.implementation_name]["log-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[1][self.implementation_name]["qlog-param"] + " " + self.implem_conf[1][self.implementation_name]["qlog-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[1][self.implementation_name]["secret-key-param"] + " " + self.implem_conf[1][self.implementation_name]["secret-key-file"] \
            + " " + self.implem_conf[1][self.implementation_name]["alpn"] + " " + self.implem_conf[1][self.implementation_name]["alpn-value"] \
            + " " + self.implem_conf[1][self.implementation_name]["version"] + " " + self.implem_conf[1][self.implementation_name]["version-value"] \
            + " " + self.implem_conf[1][self.implementation_name]["verbosity"] + " " + self.implem_conf[1][self.implementation_name]["addition-parameters"] \
            + " " + self.implem_conf[1][self.implementation_name]["destination-format"].replace("[destination]", 
                                                                                            self.implem_conf[1][self.implementation_name]["destination"]
                                                                                        ).replace("[destination-value]", 
                                                                                                    self.implem_conf[1][self.implementation_name]["destination-value"]
                                                                                        ).replace("[port]", 
                                                                                                    self.implem_conf[1][self.implementation_name]["port"]
                                                                                        ).replace("[port-value]", 
                                                                                                    self.implem_conf[1][self.implementation_name]["port-value"]) 
        
        # client_implem_args = client_implem_args.replace("implem","lo")
        client_implem_args = client_implem_args.replace("XXXXXXXX","quic-implementations")
        client_implem_args = client_implem_args.replace("VERSION","00000001" if ENV_VAR["INITIAL_VERSION"] == "1" else ("ff00001d" if ENV_VAR["INITIAL_VERSION"] == "29" else "ff00001c"))
        client_implem_args = client_implem_args.replace("ALPN",ENV_VAR["TEST_ALPN"])
        client_implem_args = re.sub('\s{2,}', ' ', client_implem_args)
        implem_env  = "" # TODO use a list of env

        ivy_args    = self.generate_tester_command(self.config["global_parameters"].getint("iter"),1).split("/")[-1].replace(self.name,"")
        ivy_env     = "" # TODO use a list of env
        
        # TODO use config file
        self.log.info("shadow test:")
        print("shadow test:")
        for env_var in ENV_VAR:
            print(env_var, ENV_VAR[env_var])
        if "client_test" in self.name:
            file = "/PFV/shadow_client_test.yml"
            file_temp = "/PFV/shadow_client_test_template.yml"
        else:
            file = "/PFV/shadow_server_test.yml"
            file_temp = "/PFV/shadow_server_test_template.yml"
        with open(file_temp, "r") as f:
            content = f.read() # todo replace
        with open(file, "w") as f:
            content = content.replace("<VERSION>", ENV_VAR["INITIAL_VERSION"])
            content = content.replace("<IMPLEMENTATION>", ENV_VAR["TEST_IMPL"])
            content = content.replace("<ALPN>", ENV_VAR["TEST_ALPN"])
            content = content.replace("<SSLKEYLOGFILE>", ENV_VAR["SSLKEYLOGFILE"])
            content = content.replace("<TEST_NAME>", self.name)
            content = content.replace("<JITTER>", str(ENV_VAR["JITTER"]))
            content = content.replace("<LATENCY>", str(ENV_VAR["LATENCY"]))
            content = content.replace("<LOSS>", str(float(ENV_VAR["LOSS"])))
            content = content.replace("<IMPLEM_PATH>", self.implem_dir_server +  "/" + self.implem_conf[0][self.implementation_name]["binary-name"] if not self.is_client else self.implem_dir_client +  "/" + self.implem_conf[1][self.implementation_name]["binary-name"])
            content = content.replace("<IMPLEM_ARGS>", server_implem_args     if not self.is_client else client_implem_args)
            content = content.replace("<BUILD_PATH>",self.config["global_parameters"]["build_dir"])
            content = content.replace("<TEST_ARGS>",ivy_args)
            self.log.info(content)
            print(content)
            f.write(content)
        os.chdir("/PFV")
        self.log.info("rm -r /PFV/shadow.data/ ")
        print("rm -r /PFV/shadow.data/ ")
        os.system("rm -r /PFV/shadow.data/ ")
        os.system("rm  /PFV/shadow.log ")
        self.log.info("command: RUST_BACKTRACE=1 shadow " + file + " > shadow.log")
        print("command: RUST_BACKTRACE=1 shadow " + file + " > shadow.log")
                        
        return file
    
    # TODO add if to avoid space in command
    # TODO Reorder config param to loop and generate command eaisier
    def generate_implementation_command(self):
        server_command = self.implem_conf[0][self.implementation_name]["binary-name"].replace("$IMPLEM_DIR",IMPLEM_DIR.replace("$PROT",self.current_protocol)+self.current_protocol).replace("$MODEL_DIR",MODEL_DIR+self.current_protocol) \
            + " " + self.implem_conf[0][self.implementation_name]["interface"] + " " + self.implem_conf[0][self.implementation_name]["interface-value"] \
            + " " + self.implem_conf[0][self.implementation_name]["cert-param"] + " " + self.implem_conf[0][self.implementation_name]["cert-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[0][self.implementation_name]["key-param"] + " " + self.implem_conf[0][self.implementation_name]["key-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[0][self.implementation_name]["root-cert-param"] + " " + self.implem_conf[0][self.implementation_name]["root-cert-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[0][self.implementation_name]["log-param"] + " " + self.implem_conf[0][self.implementation_name]["log-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[0][self.implementation_name]["qlog-param"] + " " + self.implem_conf[0][self.implementation_name]["qlog-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[0][self.implementation_name]["secret-key-param"] + " " + self.implem_conf[0][self.implementation_name]["secret-key-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[0][self.implementation_name]["alpn"] + " " + self.implem_conf[0][self.implementation_name]["alpn-value"] \
            + " " + self.implem_conf[0][self.implementation_name]["version"] + " " + self.implem_conf[0][self.implementation_name]["version-value"] \
            + " " + self.implem_conf[0][self.implementation_name]["verbosity"] + " " + self.implem_conf[0][self.implementation_name]["addition-parameters"] \
            + " " + self.implem_conf[0][self.implementation_name]["source-format"].replace("[source]", 
                                                                                                self.implem_conf[0][self.implementation_name]["source"]
                                                                                    ).replace("[source-value]", 
                                                                                                self.implem_conf[0][self.implementation_name]["source-value"]
                                                                                    ).replace("[port]", 
                                                                                                self.implem_conf[0][self.implementation_name]["port"]
                                                                                    ).replace("[port-value]", 
                                                                                                self.implem_conf[0][self.implementation_name]["port-value"]) 

        client_command = self.implem_conf[1][self.implementation_name]["binary-name"].replace("$IMPLEM_DIR",IMPLEM_DIR.replace("$PROT",self.current_protocol)+self.current_protocol).replace("$MODEL_DIR",MODEL_DIR+self.current_protocol)  \
            + " " + self.implem_conf[1][self.implementation_name]["interface"] + " " + self.implem_conf[1][self.implementation_name]["interface-value"] \
            + " " + self.implem_conf[1][self.implementation_name]["cert-param"] + " " + self.implem_conf[1][self.implementation_name]["cert-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[1][self.implementation_name]["key-param"] + " " + self.implem_conf[1][self.implementation_name]["key-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[1][self.implementation_name]["root-cert-param"] + " " + self.implem_conf[1][self.implementation_name]["root-cert-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[1][self.implementation_name]["log-param"] + " " + self.implem_conf[1][self.implementation_name]["log-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[1][self.implementation_name]["qlog-param"] + " " + self.implem_conf[1][self.implementation_name]["qlog-file"].replace("$SOURCE_DIR",SOURCE_DIR) \
            + " " + self.implem_conf[1][self.implementation_name]["secret-key-param"] + " " + self.implem_conf[1][self.implementation_name]["secret-key-file"] \
            + " " + self.implem_conf[1][self.implementation_name]["alpn"] + " " + self.implem_conf[1][self.implementation_name]["alpn-value"] \
            + " " + self.implem_conf[1][self.implementation_name]["version"] + " " + self.implem_conf[1][self.implementation_name]["version-value"] \
            + " " + self.implem_conf[1][self.implementation_name]["verbosity"] + " " + self.implem_conf[1][self.implementation_name]["addition-parameters"] \
            + " " + self.implem_conf[1][self.implementation_name]["destination-format"].replace("[destination]", 
                                                                                            self.implem_conf[1][self.implementation_name]["destination"]
                                                                                        ).replace("[destination-value]", 
                                                                                                    self.implem_conf[1][self.implementation_name]["destination-value"]
                                                                                        ).replace("[port]", 
                                                                                                    self.implem_conf[1][self.implementation_name]["port"]
                                                                                        ).replace("[port-value]", 
                                                                                                    self.implem_conf[1][self.implementation_name]["port-value"]) 
        client_command = re.sub('\s{2,}', ' ', client_command)
        server_command = re.sub('\s{2,}', ' ', server_command)
        if self.is_client:
            return [client_command ,server_command]
        else:
            return [server_command ,client_command]
    
    def start_implementation(self, i, out, err):
        if self.config["global_parameters"].getboolean("run"):
            if self.is_mim:
                pass
            else:
                self.log.info("Updating implementation:")
                print("Updating implementation:")
                self.update_implementation_command(i)
                self.log.info(self.implem_cmd)
                print(self.implem_cmd)
                if "quic_client_test_0rtt" in self.name and \
                    (self.implementation_name == "quinn" or self.implementation_name == "quic-go") \
                    and i == 1: 
                    pass 
                else:
                    qcmd =  ('sleep 5; ' if self.is_client and not self.config["net_parameters"].getboolean("shadow") else "") + self.implem_cmd # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +
                    qcmd = 'RUST_LOG="debug" RUST_BACKTRACE=1 ' + qcmd
                    self.log.info('implementation command: {}'.format(qcmd))
                    self.log.info("implementation diretory: {}".format(self.implem_dir_client if self.is_client else self.implem_dir_server))
                    self.log.info(self.config["net_parameters"].getboolean("shadow"))
                    print('implementation command: {}'.format(qcmd))
                    print("implementation diretory: {}".format(self.implem_dir_client if self.is_client else self.implem_dir_server))
                    print(self.config["net_parameters"].getboolean("shadow"))
                    if not self.config["net_parameters"].getboolean("shadow") :
                        self.log.info("not shadow test:")
                        print("not shadow test:")
                        self.implem_process = subprocess.Popen(qcmd,
                                                    cwd=(self.implem_dir_client if self.is_client else self.implem_dir_server),
                                                    stdout=out,
                                                    stderr=err,
                                                    shell=True, #self.is_client, 
                                                    preexec_fn=os.setsid)
                        self.log.info('implem_process pid: {}'.format(self.implem_process.pid))
                        print('implem_process pid: {}'.format(self.implem_process.pid))
                    else:
                        self.log.info("Generate shadow config")
                        print("Generate shadow config")
                        file = self.generate_shadow_config()
                        try:
                            os.system("RUST_BACKTRACE=1 shadow " + file + " > shadow.log")
                        except Exception as e:
                            print(e)                         
        # TODO check if it still work                
        if self.is_mim:
            qcmd = 'sleep 7; ' + "exec " + self.implem_cmd # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +
            qcmd = 'RUST_LOG="debug" RUST_BACKTRACE=1 ' + qcmd
            self.log.info('implementation command 1: {}'.format(qcmd))
            print('implementation command 1: {}'.format(qcmd))
            self.quic_process_1 = subprocess.Popen(qcmd,
                                                cwd=(self.implem_dir_client if self.is_client else self.implem_dir_server),
                                                stdout=out,
                                                stderr=err,
                                                shell=True, #self.is_client, 
                                                preexec_fn=os.setsid)
            self.log.info('quic_process_1 pid: {}'.format(self.quic_process_1.pid))
            print('quic_process_1 pid: {}'.format(self.quic_process_1.pid))
            qcmd = "exec " + self.implem_cmd_opposite # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +
            qcmd = 'RUST_LOG="debug" RUST_BACKTRACE=1 ' + qcmd
            self.log.info('implementation command 2: {}'.format(qcmd))
            print('implementation command 2: {}'.format(qcmd))
            self.quic_process_2 = subprocess.Popen(qcmd,
                                                cwd=(self.implem_dir_client if self.is_client else self.implem_dir_server),
                                                stdout=out,
                                                stderr=err,
                                                shell=True, #self.is_client, 
                                                preexec_fn=os.setsid)
            self.log.info('quic_process_2 pid: {}'.format(self.quic_process_2.pid))
            print('quic_process_2 pid: {}'.format(self.quic_process_2.pid))
        

    def start_tester(self,iteration,iev,i):
        self.log.info("Starting tester:")
        print("Starting tester:")
        ok = True
        if not self.config["net_parameters"].getboolean("shadow") :
            try:
                for iclient in range(0,self.nclient): # TODO for multiple implem client only
                    self.log.info("iclient = "+ str(iclient))
                    print("iclient = "+ str(iclient))
                    ok = ok and self.run_tester(iteration,iev,i,iclient)
            except KeyboardInterrupt:
                if not self.is_mim:
                    if self.config["global_parameters"].getboolean("run") and not self.config["global_parameters"].getboolean("keep_alive"):
                        if self.config["net_parameters"].getboolean("vnet"):
                            subprocess.Popen("/bin/bash "+ SOURCE_DIR + "/vnet_reset.sh", 
                            shell=True, executable="/bin/bash").wait()
                        self.implem_process.terminate()
                    raise KeyboardInterrupt
                else:
                    if self.config["global_parameters"].getboolean("run") and not self.config["global_parameters"].getboolean("keep_alive"):
                        if self.config["net_parameters"].getboolean("vnet"):
                            subprocess.Popen("/bin/bash "+ SOURCE_DIR + "/vnet_reset.sh", 
                            shell=True, executable="/bin/bash").wait()
                        self.quic_process_1.terminate()
                        self.quic_process_2.terminate()
                    raise KeyboardInterrupt
            
            if self.config["global_parameters"].getboolean("run") and not self.config["global_parameters"].getboolean("keep_alive") \
                and not (self.implementation_name == "quic-go" and  "quic_client_test_0rtt" in self.name):
                self.log.info("implem_process.terminate()")
                print("implem_process.terminate()")
                if not self.is_mim:
                    # The above code is terminating the process.
                    self.implem_process.terminate()
                    retcode = self.implem_process.wait()
                    self.log.info(retcode)
                    print(retcode)
                    if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                        iev.write('server_return_code({})\n'.format(retcode))
                        self.log.info("server return code: {}".format(retcode))
                        print("server return code: {}".format(retcode))
                        self.implem_process.kill()
                        return False
                else:
                    self.quic_process_1.terminate()
                    retcode = self.quic_process_1.wait()
                    self.log.info(retcode)
                    print(retcode)
                    if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                        iev.write('server_return_code({})\n'.format(retcode))
                        self.log.info("server return code: {}".format(retcode))
                        print("server return code: {}".format(retcode))
                        self.quic_process_1.kill()
                        return False
                    self.quic_process_2.terminate()
                    retcode = self.quic_process_2.wait()
                    self.log.info(retcode)
                    print(retcode)
                    if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                        iev.write('server_return_code({})\n'.format(retcode))
                        self.log.info("server return code: {}".format(retcode))
                        print("server return code: {}".format(retcode))
                        self.quic_process_2.kill()
                        return False
        return ok
    
    def stop_processes(self):
        self.log.info("Stop processes:")
        print("Stop processes:")
        if not self.is_mim:
            if self.implem_process != None:
                try:
                    #os.kill(implem_process.pid, 9)
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
            if self.quic_process_1 != None:
                try:
                    #os.kill(implem_process.pid, 9)
                    os.killpg(os.getpgid(self.quic_process_1.pid), signal.SIGTERM) 
                except OSError:
                    self.log.info("pid is unassigned")
                    print("pid is unassigned")
                    self.quic_process_1.kill()
            else:
                self.log.info("pid is in use")
                print("pid is in use")
                self.quic_process_1.kill()
                self.log.info("implem_process.kill()")
                print("implem_process.kill()")
            if self.quic_process_2 != None:
                try:
                    #os.kill(implem_process.pid, 9)
                    os.killpg(os.getpgid(self.quic_process_2.pid), signal.SIGTERM) 
                except OSError:
                    self.log.info("pid is unassigned")
                    print("pid is unassigned")
                    self.quic_process_2.kill()
            else:
                self.log.info("pid is in use")
                print("pid is in use")
                self.quic_process_2.kill()
                self.log.info("implem_process.kill()")
                print("implem_process.kill()")
        
        
    def generate_tester_command(self, iteration, iclient):
        strace_cmd, gperf_cmd, timeout_cmd = super().generate_tester_command(iteration, iclient)
        
        os.environ['TIMEOUT_IVY'] = str(self.config["global_parameters"].getint("timeout"))
        
        randomSeed = random.randint(0,1000)
        random.seed(datetime.now())
        
        prefix = ""

        # TODO config file
        initial_version = self.protocol_conf['quic_parameters'].getint("initial_version")
        send_co_close   = True
        send_app_close  = True 
        server_port       = 4443
        server_port_run_2 = 4444

        client_port     = 2*iteration+4987+iclient
        client_port_alt = 2*iteration+4988+iclient

        # TODO random ?
        # TODO bug when swap value, __arg problem i think
        if self.is_client: # BUG when cidlen != 8 check __ser
            server_cid = 0
            the_cid = server_cid + 1
            server_cid_2 = server_cid
            the_cid_2 = the_cid
        else:
            # server_cid = iteration
            # the_cid = server_cid + 1
            the_cid = iteration
            server_cid = the_cid + 1
            server_cid_2 = server_cid + 2
            the_cid_2 = the_cid + 2

        # TODO port for multiple clients

        if self.name  == "quic_server_test_0rtt":
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
        modify_packets = "true" if self.name == "quic_client_test_version_negociation_mim_modify" else "false"

        self.log.info(self.name)
        print(self.name)
        #time.sleep(5)
        if self.config["debug_parameters"].getboolean("gdb"):
            # TODO refactor
            prefix=" gdb --args "
        if self.config["net_parameters"].getboolean("vnet"):
            envs = "env - "
            for env_var in ENV_VAR:
                if env_var != "PATH": # TODO remove it is useless
                    envs = envs + env_var + "=\"" + ENV_VAR[env_var] + "\" "
                else:
                    envs = envs + env_var + "=\"" + os.environ.get(env_var) + "\" "
            prefix = "sudo ip netns exec ivy " + envs  + " " + strace_cmd + " " +  gperf_cmd + " " 
            ip_server = 0x0a000003 if not self.is_client else 0x0a000001
            ip_client = 0x0a000001 if not self.is_client else 0x0a000003
        elif self.config["net_parameters"].getboolean("shadow"):
            ip_server = 0x0b000002 if not self.is_client else 0x0b000001
            ip_client = 0x0b000001 if not self.is_client else 0x0b000002
        else:
            # prefix = strace_cmd + " "
            ip_server = 0x7f000001
            ip_client = ip_server


        if self.name in self.specials.keys(): # TODO build quic_server_test_stream
            first_test = self.specials[self.name]
            if self.name == "quic_client_test_0rtt" or self.name == "quic_server_test_0rtt":
                if self.j == 1:
                    first_test += "_app_close"
                elif self.j == 2:
                    first_test += "_co_close"
            return (' '.join(['{}{}{}/{} seed={} the_cid={} server_port={} iversion={} server_addr={} {}'.format(timeout_cmd,prefix,self.config["global_parameters"]["build_dir"],first_test,randomSeed,the_cid,server_port,initial_version,ip_server,''  
                if self.is_client else 'server_cid={} client_port={} client_port_alt={} client_addr={}'.format(server_cid,client_port,client_port_alt,ip_client))] + self.extra_args+ ([""] if self.config["net_parameters"].getboolean("vnet") else [""]))) + \
                ";sleep 1;" + \
                ' '.join(['{}{}{}/{} seed={} the_cid={} server_port={} iversion={} server_addr={} {}'.format(timeout_cmd,prefix,self.config["global_parameters"]["build_dir"],self.name,randomSeed,the_cid_2,server_port_run_2,initial_version,ip_server,''  # TODO port + iteration -> change imple
                if self.is_client else 'server_cid={} client_port={} client_port_alt={} client_addr={}'.format(server_cid_2,client_port,client_port_alt,ip_client))] + self.extra_args + ([""] if self.config["net_parameters"].getboolean("vnet") else [""]))
        else:
            return ' '.join(['{}{}{}/{} seed={} the_cid={} server_port={} iversion={} server_addr={} modify_packets={} {}'.format(timeout_cmd,prefix,self.config["global_parameters"]["build_dir"],self.name,randomSeed,the_cid,server_port,initial_version,ip_server,modify_packets,'' 
            if self.is_client else 'server_cid={} client_port={} client_port_alt={} client_addr={}'.format(server_cid,client_port,client_port_alt,ip_client))] + self.extra_args + ([""] if self.config["net_parameters"].getboolean("vnet") else [""])) #  TODO remove last param +[""] if self.config["net_parameters"].getboolean("vnet") else [""]
