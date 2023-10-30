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
import logging

from pfv_utils.pfv_constant import *
from logger.CustomFormatter import ch

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
class IvyTest(object):
    def __init__(self, args,
                 implem_dir_server, 
                 implem_dir_client,
                 extra_args, 
                 implementation_name,
                 mode,
                 config, 
                 protocol_conf,
                 implem_conf,
                 current_protocol):
        
        # Setup logger
        self.log = logging.getLogger("pfv-test")
        self.log.setLevel(logging.INFO)
        if (self.log.hasHandlers()):
            self.log.handlers.clear()
        self.log.addHandler(ch)
        self.log.propagate = False 
        
        self.dir = ""
        self.name,self.res,self.opts = args[0],args[-1],args[1:-1]
        self.implem_dir_server = implem_dir_server
        self.implem_dir_client = implem_dir_client
        self.extra_args = extra_args
        self.implementation_name = implementation_name
        self.mode = mode
        self.j = 0
        self.nclient = 0
        self.config = config
        self.protocol_conf = protocol_conf
        self.implem_conf = implem_conf
        self.current_protocol = current_protocol
        
        self.implem_cmd = ""
        self.implem_cmd_original = ""
        self.implem_cmd_opposite = ""
        self.implem_cmd_opposite_original = ""       
        self.loop = {}
        
        self.implem_process = None
        self.is_client = True if "client" in self.mode else False
        
    def restore_implementation_command(self):
        self.implem_cmd = self.implem_cmd_original
        self.implem_cmd_opposite = self.implem_cmd_opposite_original
        
    def run(self,iteration,j, nclient, exp_folder): 
        self.j = j
        self.nclient = nclient
        self.dir = exp_folder
        implem_cmds = self.generate_implementation_command() 
        self.implem_cmd  = implem_cmds[0]
        # We have to launch the tested quic ourself
        if not self.config["global_parameters"].getboolean("run"):
            self.implem_cmd = 'true'
        self.implem_cmd_original = self.implem_cmd
        self.log.info('implementation command: {}'.format(self.implem_cmd)) 
        print('implementation command: {}'.format(self.implem_cmd)) 
        self.implem_cmd_opposite  = implem_cmds[1]
        self.implem_cmd_opposite_original = self.implem_cmd_opposite
        self.log.info('{}/{} ({}) ...'.format(self.dir,self.name,iteration))
        print('{}/{} ({}) ...'.format(self.dir,self.name,iteration))
        status = self.run_expect(iteration)
        self.log.info('PASS' if status else 'FAIL')
        print('PASS' if status else 'FAIL')
        return status
    
    def prep_gperf(self,iteration):
        if self.config["debug_parameters"].getboolean("gperf"):
            f = open(os.path.join(self.dir,self.name+str(iteration))+'_cpu.prof', "w")
            f.write("")
            f.close()
            f = open(os.path.join(self.dir,self.name+str(iteration))+'_heap.prof', "w")
            f.write("")
            f.close()  
    
    def generate_shadow_config(self):
        raise NotImplementedError
    
    def run_gperf(self, command):
        if self.config["debug_parameters"].getboolean("gperf"):
            self.log.info("GPERF - CPU analysis:")
            print("GPERF - CPU analysis:")
            os.system("pprof --pdf "+ command + " " + os.path.join(self.config["global_parameters"]["dir"],self.name+str(i))+'_cpu.prof > ' + os.path.join(self.config["global_parameters"]["dir"],self.name+str(i))+'_cpu.pdf')
            self.log.info("GPERF - HEAP analysis:")
            print("GPERF - HEAP analysis:")
            os.system("pprof --pdf "+ command + " " + os.path.join(self.config["global_parameters"]["dir"],self.name+str(i))+'_heap.prof >' + os.path.join(self.config["global_parameters"]["dir"],self.name+str(i))+'_heap.pdf')
    
    def run_expect(self,iteration):
        self.implem_process = None
        ok = True
        with self.open_out(self.name+str(iteration)+'.out') as out:
            with self.open_out(self.name+str(iteration)+'.err') as err:
                with self.open_out(self.name+str(iteration)+'.iev') as iev:
                    self.prep_gperf(iteration)
                    # If run => Launch the quic entity tested 
                    looped = 1
                    # TODO refactor
                    for name in self.loop.keys():
                        if name in self.name:
                            looped = self.loop[name]
                    self.log.info("looped: {}".format(looped))   
                    print("looped: {}".format(looped))       
                    for i in range(0, looped):
                        self.log.info("Resetting the implementation command")
                        print("Resetting the implementation command")
                        self.restore_implementation_command()
                        self.log.info("Starting the implementation")
                        print("Starting the implementation")
                        self.start_implementation(i,out,err)
                        if not self.config["net_parameters"].getboolean("shadow"):
                            self.log.info("Starting the tester")
                            print("Starting the tester")
                            ok = self.start_tester(iteration,iev,i)
            if not self.config["net_parameters"].getboolean("shadow"):
                self.log.info("Stopping the processes")
                print("Stopping the processes")
                self.stop_processes()
            return ok         
    
    def start_implementation(self, i, out, err):
        raise NotImplementedError
    
    def start_tester(self,iteration,iev,i):
        raise NotImplementedError
    
    def stop_processes(self):
        raise NotImplementedError
    
    def run_tester(self,iteration,iev,i,iclient):
        command = self.generate_tester_command(iteration,iclient)
        self.log.info(command)
        print(command)
        #time.sleep(5)
        for name in self.loop.keys():
            if name in command:
                commands = command.split(";")
                if i == 1:
                    i += 1
                command = commands[i]
        sleep(1)
        self.log.info("command is {} from {}\n".format(command,self.name))
        print("command is {} from {}\n".format(command,self.name))
        if platform.system() != 'Windows':
            oldcwd = os.getcwd()
            os.chdir(self.config["global_parameters"]["build_dir"])
            proc = subprocess.Popen('sleep 3;'+command,
                cwd=self.config["global_parameters"]["build_dir"],
                stdout=iev,
                stderr=sys.stderr,
                shell=True)
            os.chdir(oldcwd)
            try:
                #proc.terminate()
                retcode = proc.wait()
            except KeyboardInterrupt:
                self.log.info('terminating client process {}'.format(proc.pid))
                print('terminating client process {}'.format(proc.pid))
                proc.terminate()
                raise KeyboardInterrupt
            if retcode == 124:
                self.log.info('timeout')
                print('timeout')
                iev.write('timeout\n')
                #sleep(1)
                return False
            if retcode != 0:
                iev.write('ivy_return_code({})\n'.format(retcode))
                self.log.info('client return code: {}'.format(retcode))
                print('client return code: {}'.format(retcode))
            if  self.config["debug_parameters"].getboolean("gperf"):
                os.system("pprof --pdf "+ self.dir+"/"+self.name + " "+ os.path.join(self.dir,self.name+str(iteration))+'_cpu.prof > ' + os.path.join(self.dir,self.name+str(iteration))+'_cpu.pdf')
            #     os.system("pprof --pdf "+ command + " "+ os.path.join(self.dir,self.name+str(iteration))+'_heap.prof >' + os.path.join(self.dir,self.name+str(iteration))+'_heap.pdf')
            #sleep(1)
            return retcode == 0
        else:
            oldcwd = os.getcwd()
            os.chdir(self.dir)
            child = spawn(command)
            os.chdir(oldcwd)
            child.logfile = iev
            try:
                child.expect(self.res,timeout=100)
                child.close()
                self.log.info("tester exit status: {}".format(child.exitstatus))
                self.log.info("tester signal status: {}".format(child.signalstatus))
                print("tester exit status: {}".format(child.exitstatus))
                print("tester signal status: {}".format(child.signalstatus))
                return True
            except pexpect.EOF:
                self.log.info(child.before)
                print(child.before)
                return False
            except pexpect.exceptions.TIMEOUT:
                self.log.info('timeout')
                print('timeout')
                child.terminate()
                child.close()
                return False
            except KeyboardInterrupt:
                self.log.info('terminating tester process')
                print('terminating tester process')
                child.kill(signal.SIGINT)
                child.close()
                raise KeyboardInterrupt
            

  
    def open_out(self,name):
        self.log.info(os.path.join(self.dir,name))
        print(os.path.join(self.dir,name))
        return open(os.path.join(self.dir,name),"w")
    
    # Produce the command to launch the test generated from the .ivy in the /build folder
    def update_implementation_command(self):
        raise NotImplementedError
    
    def generate_implementation_command(self):
        raise NotImplementedError
    
    def generate_tester_command(self, iteration, iclient):
        import platform
        self.log.info("Generating tester command")
        print("Generating tester command")
        #"strace -e sendto" # TODO strace -e sendto
        strace_cmd = "strace -k -e '!nanosleep,getitimer,alarm,setitimer,gettimeofday,times,rt_sigtimedwait,utime,adjtimex,settimeofday,time'"
        # 'HEAPPROFILE='+ os.path.join(self.dir,self.name+str(iteration)) +'_heap.prof '
        gperf_cmd = "LD_PRELOAD=/usr/local/lib/libprofiler.so CPUPROFILE="+ os.path.join(self.dir,self.name+str(iteration)) + '_cpu.prof ' if  self.config["debug_parameters"].getboolean("gperf") else ""
        timeout_cmd = '' if platform.system() == 'Windows' else 'timeout {} '.format(self.config["global_parameters"].getint("timeout"))
        os.environ['TIMEOUT_IVY'] = str(self.config["global_parameters"].getint("timeout"))
        
        return strace_cmd, gperf_cmd, timeout_cmd