# This script runs a sequence of tests on the picoquicdemo server. 

from curses import qiflush
import random
from unittest import skip
import pexpect
import os
import sys
import subprocess
import signal
from datetime import datetime
import platform
from time import sleep
from .constants import *

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
    def __init__(self,dir,args, is_client, run, keep_alive, time, gdb, quic_dir,output_path,extra_args, implementation_name):
        self.dir,self.name,self.res,self.opts = dir,args[0],args[-1],args[1:-1]
        self.is_client = is_client
        self.runn = run
        self.keep_alive = keep_alive
        self.time = time
        self.gdb = gdb
        self.quic_dir = quic_dir
        self.output_path = output_path
        self.extra_args = extra_args
        self.implementation_name = implementation_name

    def run(self,test_command,quic_cmd): 
        print('{}/{} ({}) ...'.format(self.dir,self.name,test_command))
        status = self.run_expect(test_command,quic_cmd)
        print('PASS' if status else 'FAIL')
        return status
    
    def run_expect(self,test_command,quic_cmd):
        # Useless ? self.preprocess_commands() == []
        for pc in self.preprocess_commands():
            print('executing: {}'.format(pc))
            child = spawn(pc)
            child.logfile = sys.stdout
            child.expect(pexpect.EOF)
            child.close()
            if child.exitstatus != 0:
                print(child.before)
                return False
        quic_process = None
        with self.open_out(self.name+str(test_command)+'.out') as out:
            with self.open_out(self.name+str(test_command)+'.err') as err:
                with self.open_out(self.name+str(test_command)+'.iev') as iev:
                    # If run => Launch the quic entity tested 
                    looped = 1
                    # TODO refactor
                    if "quic_client_test_0rtt" in self.name: #  and not "./client -X" in quic_cmd
                        looped = 2
                    for i in range(0, looped):
                        if self.run:
                            if i == 1:
                                quic_cmd = quic_cmd.replace("4443","4444")
                                if self.implementation_name == "mvfst":
                                    quic_cmd = quic_cmd + " -zrtt=true"
                                elif self.implementation_name == "quiche":
                                    quic_cmd = quic_cmd + " --early-data"
                            
                            if i == 0 and  "quic_client_test_0rtt" in self.name:
                                if self.implementation_name == "quic-go": # change port for 2d run directly in implem
                                    quic_cmd = quic_cmd.replace("./client -X", "./client -R -X")
                                elif self.implementation_name == "quinn":
                                    quic_cmd = quic_cmd + " --zrtt"
                            
                            if "quic_client_test_0rtt" in self.name and (self.implementation_name == "quinn" or self.implementation_name == "quic-go") and i == 1: # 
                                pass 
                            else:
                                qcmd = 'sleep 5; ' + quic_cmd if self.is_client else quic_cmd.split() 
                                print('implementation command: {}'.format(qcmd))
                                quic_process = subprocess.Popen(qcmd,
                                                            cwd=self.quic_dir,
                                                            stdout=out,
                                                            stderr=err,
                                                            shell=self.is_client)
                                print('quic_process pid: {}'.format(quic_process.pid))
                        # Always launch the test itself that will apply (test_client_max eg)
                        try:
                            ok = self.expect(test_command,iev,i)
                        except KeyboardInterrupt:
                            if self.run and not self.keep_alive:
                                print("cool kill")
                                quic_process.terminate()
                            raise KeyboardInterrupt
                        # If run => get exit status of process 
                        if self.run and not self.keep_alive and not (self.implementation_name == "quic-go" and  "quic_client_test_0rtt" in self.name):
                            print("quic_process.terminate()")
                            quic_process.terminate()
                            retcode = quic_process.wait()
                            if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                                iev.write('server_return_code({})\n'.format(retcode))
                                print("server return code: {}".format(retcode))
                                #quic_process.kill()
                                return False
            # if quic_process != None:
            #     print("quic_process.kill()")
            #     sleep(1)
            #     quic_process.kill()
            return ok
    # Allow to launh the c++ test (test_client_max e.g)             
    def expect(self,test_command,iev,i):
        command = self.command(test_command)
        print(command)
        #time.sleep(5)
        if "quic_client_test_0rtt" in command:
            commands = command.split(";")
            command = commands[i]
            print("command is {} from {}\n".format(command,self.name))
        if platform.system() != 'Windows':
            oldcwd = os.getcwd()
            os.chdir(self.dir)
            proc = subprocess.Popen('sleep 3;'+command,
                cwd=QUIC_DIR,
                stdout=iev,
                stderr=sys.stderr,
                shell=True)
            os.chdir(oldcwd)
            try:
                #proc.terminate()
                retcode = proc.wait()
            except KeyboardInterrupt:
                print('terminating client process {}'.format(proc.pid))
                proc.terminate()
                raise KeyboardInterrupt
            if retcode == 124:
                print('timeout')
                iev.write('timeout\n')
                #sleep(1)
                return False
            if retcode != 0:
                iev.write('ivy_return_code({})\n'.format(retcode))
                print('client return code: {}'.format(retcode))
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
                print("tester exit status: {}".format(child.exitstatus))
                print("tester signal status: {}".format(child.signalstatus))
                return True
            except pexpect.EOF:
                print(child.before)
                return False
            except pexpect.exceptions.TIMEOUT:
                print('timeout')
                child.terminate()
                child.close()
                return False
            except KeyboardInterrupt:
                print('terminating tester process')
                child.kill(signal.SIGINT)
                child.close()
                raise KeyboardInterrupt
    def preprocess_commands(self):
        return []
  
    def open_out(self,name):
        print(os.path.join(self.output_path,name))
        return open(os.path.join(self.output_path,name),"w")
    # Produce the command to launch the test generated from the .ivy in the /build folder
    
    def command(self, test_command):
        import platform
        timeout_cmd = '' if platform.system() == 'Windows' else 'timeout {} '.format(self.time)
        randomSeed = random.randint(0,1000)
        random.seed(datetime.now())
        prefix = ""
        print(self.name)
        #time.sleep(5)
        if self.gdb:
            # TODO refactor
            prefix=" gdb --args "
        if self.name == "quic_server_test_0rtt": # TODO build quic_server_test_stream
            return (' '.join(['{}{}{}/{} seed={} the_cid={} {}'.format(timeout_cmd,prefix,self.dir,"quic_server_test_0rtt_stream",randomSeed,0,'' 
            if self.is_client else 'server_cid={} client_port={} client_port_alt={}'.format(1,2*test_command+4987,2*test_command+4988))] + self.extra_args)) + ";sleep 1;" +' '.join(['{}{}{}/{} seed={} the_cid={} {}'.format(timeout_cmd,prefix,self.dir,self.name,randomSeed,0,'' 
            if self.is_client else 'server_cid={} client_port={} client_port_alt={}'.format(1,2*test_command+4987,2*test_command+4988))] + self.extra_args)
        elif self.name == "quic_server_test_retry_reuse_key":
            return (' '.join(['{}{}{}/{} seed={} the_cid={} {}'.format(timeout_cmd,prefix,self.dir,"quic_server_test_retry",randomSeed,0,'' 
            if self.is_client else 'server_cid={} client_port={} client_port_alt={}'.format(1,2*test_command+4987,2*test_command+4988))] + self.extra_args)) + ";" +' '.join(['{}{}{}/{} seed={} the_cid={} {}'.format(timeout_cmd,prefix,self.dir,self.name,randomSeed,0,'' 
            if self.is_client else 'server_cid={} client_port={} client_port_alt={}'.format(1,2*test_command+4989,2*test_command+4988))] + self.extra_args)
        elif self.name == "quic_client_test_0rtt":
            return (' '.join(['{}{}{}/{} seed={} the_cid={} {}'.format(timeout_cmd,prefix,self.dir,"quic_client_test_0rtt_max",randomSeed,0,'' 
            if self.is_client else 'server_cid={} client_port={} client_port_alt={}'.format(1,2*test_command+4987,2*test_command+4988))] + self.extra_args)) + ";" +' '.join(['{}{}{}/{} seed={} the_cid={} {}'.format(timeout_cmd,prefix,self.dir,self.name,randomSeed,0,'' 
            if self.is_client else 'server_cid={} client_port={} client_port_alt={}'.format(1,2*test_command+4989,2*test_command+4988))] + self.extra_args)
        else:
            return ' '.join(['{}{}{}/{} seed={} the_cid={} {}'.format(timeout_cmd,prefix,self.dir,self.name,randomSeed,0,'' 
            if self.is_client else 'server_cid={} client_port={} client_port_alt={}'.format(1,2*test_command+4987,2*test_command+4988))] + self.extra_args)
  