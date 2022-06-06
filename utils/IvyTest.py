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
    def __init__(self,dir,args, is_client, run, keep_alive, time, gdb, 
                 quic_dir,output_path,extra_args, implementation_name,
                 nclient):
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
        self.nclient = nclient
        self.j = 0

        self.specials = {
            "quic_server_test_0rtt":"quic_server_test_0rtt_stream",
            "quic_client_test_new_token_address_validation":"quic_client_test_new_token_address_validation",
            "quic_client_test_0rtt":"quic_client_test_0rtt_max",
            "quic_client_test_0rtt_add_val":"quic_client_test_0rtt_max_add_val",
            "quic_client_test_0rtt_invalid":"quic_client_test_0rtt_max",
            "quic_server_test_retry_reuse_key":"quic_server_test_retry"
        }

    def run(self,iteration,quic_cmd,j): 
        self.j = j
        print('{}/{} ({}) ...'.format(self.dir,self.name,iteration))
        status = self.run_expect(iteration,quic_cmd)
        print('PASS' if status else 'FAIL')
        return status
    
    def run_expect(self,iteration,quic_cmd):
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
        with self.open_out(self.name+str(iteration)+'.out') as out:
            with self.open_out(self.name+str(iteration)+'.err') as err:
                with self.open_out(self.name+str(iteration)+'.iev') as iev:
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
                                qcmd =  ('/bin/sleep 5; ' if self.is_client else "") + "exec " + quic_cmd # if self.is_client else quic_cmd.split()  #if is client 'sleep 5; ' +
                                # if not self.is_client:
                                #     qcmd.insert(0,"exec")
                                print('implementation command: {}'.format(qcmd))
                                quic_process = subprocess.Popen(qcmd,
                                                            cwd=self.quic_dir,
                                                            stdout=out,
                                                            stderr=err,
                                                            shell=True, #self.is_client, 
                                                            preexec_fn=os.setsid)
                                print('quic_process pid: {}'.format(quic_process.pid))
                        # Always launch the test itself that will apply (test_client_max eg)
                        try:
                            ok = True
                            for iclient in range(0,self.nclient):
                                print("iclient = "+ str(iclient))
                                ok = ok and self.expect(iteration,iev,i,iclient)
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
                            print(retcode)
                            if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                                iev.write('server_return_code({})\n'.format(retcode))
                                print("server return code: {}".format(retcode))
                                quic_process.kill()
                                return False
            if quic_process != None:
                try:
                    #os.kill(quic_process.pid, 9)
                    os.killpg(os.getpgid(quic_process.pid), signal.SIGTERM) 
                except OSError:
                    print("pid is unassigned")
                    quic_process.kill()
                else:
                    print("pid is in use")
                    quic_process.kill()
                    print("quic_process.kill()")
            
            return ok
    # Allow to launh the c++ test (test_client_max e.g)             
    def expect(self,iteration,iev,i,iclient):
        command = self.command(iteration,iclient)
        print(command)
        #time.sleep(5)
        if "quic_client_test_0rtt" in command:
            commands = command.split(";")
            if i == 1:
                i += 1
            command = commands[i]
            sleep(1)
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
    
    def command(self, iteration, iclient):
        import platform
        timeout_cmd = '' if platform.system() == 'Windows' else 'timeout {} '.format(self.time)
        randomSeed = random.randint(0,1000)
        random.seed(datetime.now())
        prefix = ""

        # TODO 
        initial_version = 0 
        send_co_close   = True
        send_app_close  = True 


        server_port   = 4443
        server_port_2 = 4444

        client_port   = 2*iteration+4987+iclient
        client_port_2 = 2*iteration+4988+iclient

        # TODO random ?
        # TODO bug when swap value, __arg problem i think
        if self.is_client: # BUG when cidlen != 8 check __ser
            server_cid = 0
            the_cid = server_cid + 1
            server_cid_2 = server_cid
            the_cid_2 = the_cid
        else:
            server_cid = iteration
            the_cid = server_cid + 1
            # the_cid = iteration
            # server_cid = the_cid + 1
            server_cid_2 = server_cid + 2
            the_cid_2 = the_cid + 2

        # TODO port for multiple clients

        if self.name  == "quic_server_test_0rtt":
            server_port_2 = 4443

        print(self.name)
        #time.sleep(5)
        if self.gdb:
            # TODO refactor
            prefix=" gdb --args "
        if self.name in self.specials.keys(): # TODO build quic_server_test_stream
            first_test = self.specials[self.name]
            if self.name == "quic_client_test_0rtt" or self.name == "quic_server_test_0rtt":
                if self.j == 1:
                    first_test += "_app_close"
                elif self.j == 2:
                    first_test += "_co_close"
            return (' '.join(['{}{}{}/{} seed={} the_cid={} server_port={} {}'.format(timeout_cmd,prefix,self.dir,first_test,randomSeed,the_cid,server_port,''  
                if self.is_client else 'server_cid={} client_port={} client_port_alt={}'.format(server_cid,client_port,client_port_2))] + self.extra_args)) + \
                ";sleep 1;" + \
                ' '.join(['{}{}{}/{} seed={} the_cid={} server_port={} {}'.format(timeout_cmd,prefix,self.dir,self.name,randomSeed,the_cid_2,server_port_2,''  # TODO port + iteration -> change imple
                if self.is_client else 'server_cid={} client_port={} client_port_alt={}'.format(server_cid_2,client_port,client_port_2))] + self.extra_args)
        else:
            return ' '.join(['{}{}{}/{} seed={} the_cid={} server_port={} {}'.format(timeout_cmd,prefix,self.dir,self.name,randomSeed,the_cid,server_port,'' 
            if self.is_client else 'server_cid={} client_port={} client_port_alt={}'.format(server_cid,client_port,client_port_2))] + self.extra_args)
  
