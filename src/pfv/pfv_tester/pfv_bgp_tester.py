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

# TODO add tested implemenatation name
class BGPIvyTest(IvyTest):
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
           
    def update_implementation_command(self,i):
        pass
    
    # TODO add if to avoid space in command
    # TODO Reorder config param to loop and generate command eaisier
    def generate_implementation_command(self):
        server_command = ""
        client_command = ""
        
        if self.is_client:
            return [client_command ,server_command]
        else:
            return [server_command ,client_command]
    
    def start_implementation(self, i, out, err):
        if self.run:
            self.implem_cmd = self.update_implementation_command(i)
            self.log.info(self.implem_cmd)
            qcmd =  ('sleep 5; ' if self.is_client and not self.config["net_parameters"].getboolean("shadow") else "") + self.implem_cmd # if self.is_client else implem_cmd.split()  #if is client 'sleep 5; ' +
            qcmd = 'RUST_LOG="debug" RUST_BACKTRACE=1 ' + qcmd
            self.log.info('implementation command: {}'.format(qcmd))
            if not self.config["net_parameters"].getboolean("shadow") :
                self.log.info("not shadow test:")
                implem_process = subprocess.Popen(qcmd,
                                            cwd=(self.implem_dir_client if self.is_client else self.implem_dir_server),
                                            stdout=out,
                                            stderr=err,
                                            shell=True, #self.is_client, 
                                            preexec_fn=os.setsid)
                self.log.info('implem_process pid: {}'.format(implem_process.pid))
            else:
                # TODO use config file
                self.log.info("shadow test:")
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
                    self.log.info(content)
                    f.write(content)
                os.chdir("/PFV")
                self.log.info("rm -r /PFV/shadow.data/ ")
                os.system("rm -r /PFV/shadow.data/ ")
                os.system("rm  /PFV/shadow.log ")
                self.log.info("command: RUST_BACKTRACE=1 shadow " + file + " > shadow.log")
                try:
                    os.system("RUST_BACKTRACE=1 shadow " + file + " > shadow.log")
                except:
                    pass                         


    def start_tester(self,iteration,iev,i):
        self.log.info("Starting tester:")
        ok = True
        if not self.config["net_parameters"].getboolean("shadow") :
            try:
                for iclient in range(0,self.nclient): # TODO for multiple implem client only
                    self.log.info("iclient = "+ str(iclient))
                    ok = ok and self.run_tester(iteration,iev,i,iclient)
            except KeyboardInterrupt:
                if self.run and not self.keep_alive:
                    self.log.info("cool kill")
                    if self.config["net_parameters"].getboolean("vnet"):
                        subprocess.Popen("/bin/bash "+ SOURCE_DIR + "/vnet_reset.sh", 
                        shell=True, executable="/bin/bash").wait()
                    self.implem_process.terminate()
                raise KeyboardInterrupt
            
            if self.run and not self.keep_alive:
                self.log.info("implem_process.terminate()")
                # The above code is terminating the process.
                self.implem_process.terminate()
                retcode = self.implem_process.wait()
                self.log.info(retcode)
                if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                    iev.write('server_return_code({})\n'.format(retcode))
                    self.log.info("server return code: {}".format(retcode))
                    self.implem_process.kill()
                    return False
    
    def stop_processes(self):
        self.log.info("Stop processes:")
        if self.implem_process != None:
            try:
                #os.kill(implem_process.pid, 9)
                os.killpg(os.getpgid(self.implem_process.pid), signal.SIGTERM) 
            except OSError:
                self.log.info("pid is unassigned")
                self.implem_process.kill()
            else:
                self.log.info("pid is in use")
                self.implem_process.kill()
                self.log.info("implem_process.kill()")
       
    def generate_tester_command(self, iteration, iclient):
        strace_cmd, gperf_cmd, timeout_cmd = super().generate_tester_command(iteration, iclient)
        
        os.environ['TIMEOUT_IVY'] = str(self.config["global_parameters"].getint("timeout"))
        
        randomSeed = random.randint(0,1000)
        random.seed(datetime.now())

        return ""