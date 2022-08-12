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
                 nclient,initial_version, is_mim, vnet):
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
        self.initial_version = initial_version
        self.j = 0
        self.is_mim = is_mim
        self.vnet = vnet

        self.specials = {
            "quic_server_test_0rtt":"quic_server_test_0rtt_stream",
            "quic_client_test_new_token_address_validation":"quic_client_test_new_token_address_validation",
            "quic_client_test_0rtt":"quic_client_test_0rtt_max",
            "quic_client_test_0rtt_add_val":"quic_client_test_0rtt_max_add_val",
            "quic_client_test_0rtt_invalid":"quic_client_test_0rtt_max",
            "quic_client_test_0rtt_mim_replay":"quic_client_test_0rtt_max",
            "quic_server_test_retry_reuse_key":"quic_server_test_retry"
        }

    def run(self,iteration,quic_cmd,j,quic_cmd_opposite): 
        self.j = j
        print('{}/{} ({}) ...'.format(self.dir,self.name,iteration))
        status = self.run_expect(iteration,quic_cmd,quic_cmd_opposite)
        print('PASS' if status else 'FAIL')
        return status
    
    def run_expect(self,iteration,quic_cmd,quic_cmd_opposite):
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
                            if self.is_mim:
                                pass
                            else:
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
                                
                                if "quic_client_test_0rtt" in self.name and (self.implementation_name == "quinn" or  \
                                    self.implementation_name == "quic-go") and i == 1: # 
                                    print("Fuck")
                                    pass 
                                else:
                                    if self.vnet:
                                        quic_cmd_copy = quic_cmd
                                        quic_cmd = "sudo ip netns exec n1 " 
                                        # if self.implementation_name == "picoquic":
                                        #     quic_cmd = "cd " + IMPLEM_DIR + '/picoquic;'  + quic_cmd + "cd " + IMPLEM_DIR + '/picoquic;'
                                        envs = "env - "
                                        for env_var in ENV_VAR:
                                            if env_var != "PATH": # TODO remove it is useless
                                                envs = envs + env_var + "=\"" + ENV_VAR[env_var] + "\" "
                                            else:
                                                envs = envs + env_var + "=\"" + os.environ.get(env_var) + "\" "
                                        quic_cmd = quic_cmd + envs + quic_cmd_copy 
                                    else :
                                        quic_cmd = "exec " + quic_cmd
                                        quic_cmd = quic_cmd.replace("10.0.0.1","localhost")
                                        quic_cmd = quic_cmd.replace("10.0.0.2","localhost")
                                        quic_cmd = quic_cmd.replace("n1.0","lo")

                                    qcmd =  ('sleep 5; ' if self.is_client else "") + quic_cmd # if self.is_client else quic_cmd.split()  #if is client 'sleep 5; ' +
                                    # if not self.is_client:
                                    #     qcmd.insert(0,"exec")

                                    if "quiche" in self.implementation_name or "quinn" in self.implementation_name:
                                        qcmd = 'RUST_LOG="debug" RUST_BACKTRACE=1 ' + qcmd
                                    print('implementation command: {}'.format(qcmd))
                                    quic_process = subprocess.Popen(qcmd,
                                                                cwd=self.quic_dir,
                                                                stdout=out,
                                                                stderr=err,
                                                                shell=True, #self.is_client, 
                                                                preexec_fn=os.setsid)
                                    print('quic_process pid: {}'.format(quic_process.pid))
                            # Always launch the test itself that will apply (test_client_max eg)
                        
                                                # If run => get exit status of process 
                        if self.is_mim:
                            qcmd = 'sleep 7; ' + "exec " + quic_cmd # if self.is_client else quic_cmd.split()  #if is client 'sleep 5; ' +
                            # if not self.is_client:
                            #     qcmd.insert(0,"exec")
                            if "quiche" in self.implementation_name or "quinn" in self.implementation_name:
                                qcmd = 'RUST_LOG="debug" RUST_BACKTRACE=1 ' + qcmd
                            print('implementation command 1: {}'.format(qcmd))
                            quic_process_1 = subprocess.Popen(qcmd,
                                                                cwd=self.quic_dir,
                                                                stdout=out,
                                                                stderr=err,
                                                                shell=True, #self.is_client, 
                                                                preexec_fn=os.setsid)
                            print('quic_process_1 pid: {}'.format(quic_process_1.pid))
                            qcmd = "exec " + quic_cmd_opposite # if self.is_client else quic_cmd.split()  #if is client 'sleep 5; ' +
                            # if not self.is_client:
                            #     qcmd.insert(0,"exec")
                            if "quiche" in self.implementation_name or "quinn" in self.implementation_name:
                                qcmd = 'RUST_LOG="debug" RUST_BACKTRACE=1 ' + qcmd
                            print('implementation command 2: {}'.format(qcmd))
                            quic_process_2 = subprocess.Popen(qcmd,
                                                                cwd=self.quic_dir,
                                                                stdout=out,
                                                                stderr=err,
                                                                shell=True, #self.is_client, 
                                                                preexec_fn=os.setsid)
                            print('quic_process_2 pid: {}'.format(quic_process_2.pid))
                        try:
                            ok = True
                            for iclient in range(0,self.nclient): # TODO for multiple implem client only
                                print("iclient = "+ str(iclient))
                                ok = ok and self.expect(iteration,iev,i,iclient)
                        except KeyboardInterrupt:
                            if not self.is_mim:
                                if self.run and not self.keep_alive:
                                    print("cool kill")
                                    if self.vnet:
                                        subprocess.Popen("/bin/bash "+ SOURCE_DIR + "/vnet_reset.sh", 
                                        shell=True, executable="/bin/bash").wait()
                                    quic_process.terminate()
                                raise KeyboardInterrupt
                            else:
                                if self.run and not self.keep_alive:
                                    print("cool kill")
                                    if self.vnet:
                                        subprocess.Popen("/bin/bash "+ SOURCE_DIR + "/vnet_reset.sh", 
                                        shell=True, executable="/bin/bash").wait()
                                    quic_process_1.terminate()
                                    quic_process_2.terminate()
                                raise KeyboardInterrupt
                        
                        if self.run and not self.keep_alive and not (self.implementation_name == "quic-go" and  "quic_client_test_0rtt" in self.name):
                            print("quic_process.terminate()")
                            if not self.is_mim:
                                quic_process.terminate()
                                retcode = quic_process.wait()
                                print(retcode)
                                if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                                    iev.write('server_return_code({})\n'.format(retcode))
                                    print("server return code: {}".format(retcode))
                                    quic_process.kill()
                                    return False
                            else:
                                quic_process_1.terminate()
                                retcode = quic_process_1.wait()
                                print(retcode)
                                if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                                    iev.write('server_return_code({})\n'.format(retcode))
                                    print("server return code: {}".format(retcode))
                                    quic_process_1.kill()
                                    return False
                                quic_process_2.terminate()
                                retcode = quic_process_2.wait()
                                print(retcode)
                                if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                                    iev.write('server_return_code({})\n'.format(retcode))
                                    print("server return code: {}".format(retcode))
                                    quic_process_2.kill()
                                    return False
            if not self.is_mim:
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
            else:
                if quic_process_1 != None:
                    try:
                        #os.kill(quic_process.pid, 9)
                        os.killpg(os.getpgid(quic_process_1.pid), signal.SIGTERM) 
                    except OSError:
                        print("pid is unassigned")
                        quic_process_1.kill()
                    else:
                        print("pid is in use")
                        quic_process_1.kill()
                        print("quic_process.kill()")
                if quic_process_2 != None:
                    try:
                        #os.kill(quic_process.pid, 9)
                        os.killpg(os.getpgid(quic_process_2.pid), signal.SIGTERM) 
                    except OSError:
                        print("pid is unassigned")
                        quic_process_2.kill()
                    else:
                        print("pid is in use")
                        quic_process_2.kill()
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
            os.chdir(QUIC_DIR)
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
        strace_cmd = "strace -e sendto" # TODO
        timeout_cmd = '' if platform.system() == 'Windows' else 'timeout {} '.format(self.time)
        randomSeed = random.randint(0,1000)
        random.seed(datetime.now())
        prefix = ""

        # TODO 
        initial_version = self.initial_version
        send_co_close   = True
        send_app_close  = True 


        server_port   = 4443
        server_port_run_2 = 4444

        client_port   = 2*iteration+4987+iclient
        client_port_alt = 2*iteration+4988+iclient

        n_clients = self.nclient # TODO add param

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

        print(self.name)
        #time.sleep(5)
        if self.gdb:
            # TODO refactor
            prefix=" gdb --args "
        if self.vnet:
            envs = "env - "
            for env_var in ENV_VAR:
                if env_var != "PATH": # TODO remove it is useless
                    envs = envs + env_var + "=\"" + ENV_VAR[env_var] + "\" "
                else:
                    envs = envs + env_var + "=\"" + os.environ.get(env_var) + "\" "
            prefix = "sudo ip netns exec n0 " + envs 
            ip_server = 0x0a000002 if not self.is_client else 0x0a000001
            ip_client = 0x0a000001 if not self.is_client else 0x0a000002
        else:
            ip_server = 0x7f000001
            ip_client = ip_server


        if self.name in self.specials.keys(): # TODO build quic_server_test_stream
            first_test = self.specials[self.name]
            if self.name == "quic_client_test_0rtt" or self.name == "quic_server_test_0rtt":
                if self.j == 1:
                    first_test += "_app_close"
                elif self.j == 2:
                    first_test += "_co_close"
            return (' '.join(['{}{}{}/{} seed={} the_cid={} server_port={} iversion={} server_addr={} {}'.format(timeout_cmd,prefix,self.dir,first_test,randomSeed,the_cid,server_port,initial_version,ip_server,''  
                if self.is_client else 'server_cid={} client_port={} client_port_alt={} client_addr={}'.format(server_cid,client_port,client_port_alt,ip_client))] + self.extra_args+ ([""] if self.vnet else [""]))) + \
                ";sleep 1;" + \
                ' '.join(['{}{}{}/{} seed={} the_cid={} server_port={} iversion={} server_addr={} {}'.format(timeout_cmd,prefix,self.dir,self.name,randomSeed,the_cid_2,server_port_run_2,initial_version,ip_server,''  # TODO port + iteration -> change imple
                if self.is_client else 'server_cid={} client_port={} client_port_alt={} client_addr={}'.format(server_cid_2,client_port,client_port_alt,ip_client))] + self.extra_args + ([""] if self.vnet else [""]))
        else:
            return ' '.join(['{}{}{}/{} seed={} the_cid={} server_port={} iversion={} server_addr={} modify_packets={} {}'.format(timeout_cmd,prefix,self.dir,self.name,randomSeed,the_cid,server_port,initial_version,ip_server,modify_packets,'' 
            if self.is_client else 'server_cid={} client_port={} client_port_alt={} client_addr={}'.format(server_cid,client_port,client_port_alt,ip_client))] + self.extra_args + ([""] if self.vnet else [""])) #  TODO remove last param +[""] if self.vnet else [""]
