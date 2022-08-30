from compileall import compile_file
import logging
import subprocess
import sys
import time
import progressbar
from utils.Runner import Runner
from utils.ArgumentParserRunner import ArgumentParserRunner
from utils.constants import *
from utils.CustomFormatter import CustomFormatter
from gui.results import UIvyQUICResults
from gui.standard import *
import tracemalloc 

# TODO refactor
# TODO change os.system with subprocess or with python funct
# TODO to finish
# TODO add barplot progression

import os


class ExperimentRunner:
    SOURCE_DIR =  os.getenv('PWD')
    IMPLEM_DIR =  SOURCE_DIR + '/quic-implementations'
    MEMORY_PROFILING = False
    COMPILE = False

    def __init__(self):
        # Set environment variables
        for env_var in ENV_VAR:
            os.environ[env_var] = ENV_VAR[env_var]
            print(env_var, ENV_VAR[env_var])
        subprocess.Popen("source $HOME/.cargo/env",shell=True, executable="/bin/bash").wait() # TODO source

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(CustomFormatter())
        self.log = logging.getLogger("run_experiments")
        self.log.setLevel(logging.INFO)
        self.log.addHandler(ch)
        self.log.propagate = False 
        self.included_files = list()


        if ExperimentRunner.MEMORY_PROFILING:
            # TODO take snapshot in build_scdgs()
            self.memory_snapshots = []

        args_parser = ArgumentParserRunner()
        self.args = args_parser.parse_arguments()
        self.log.info(self.args)

        os.environ['INITIAL_VERSION'] = str(self.args.initial_version)
        ENV_VAR["INITIAL_VERSION"] = str(self.args.initial_version)
        ExperimentRunner.COMPILE = self.args.compile

        self.executed_tests = []


    def update_includes_ptls(self):
        # Note we use subprocess in order to get sudo rights
        # TODO should use makefile
        folder = ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy/ivy/include/1.7"
        self.log.info("Update \"include\" path of python with updated version of the TLS project from \n\t"+folder)
        files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.endswith(".ivy")]
        for file in files:
            self.log.info(" " + file)
            subprocess.Popen("sudo /bin/cp "+ file +" /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo /bin/cp -f " + ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy/ivy/ivy_to_cpp.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_to_cpp.py", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo /bin/cp -f " + ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy/ivy/ivy_solver.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_solver.py", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo /bin/cp -f " + ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy/ivy/ivy_cpp_types.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_cpp_types.py", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo /bin/cp -f " + ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy/ivy/ivy_parser.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_parser.py", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo /bin/cp -f " + ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy/ivy/ivy_ast.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_ast.py", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo /bin/cp -f " + ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy/ivy/ivy_compiler.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_compiler.py", 
                                                    shell=True, executable="/bin/bash").wait()
        #cd /usr/local/lib/python2.7/dist-packages/ivy/

        os.chdir('/usr/local/lib/python2.7/dist-packages/ivy/')

        subprocess.Popen("sudo python -m compileall ivy_to_cpp.py", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo python -m compileall ivy_cpp_types.py", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo python -m compileall ivy_solver.py", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo python -m compileall ivy_parser.py", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo python -m compileall ivy_ast.py", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo python -m compileall ivy_compiler.py", 
                                                    shell=True, executable="/bin/bash").wait()

        #echo "CP picotls lib"
        subprocess.Popen("sudo /bin/cp -f -a " + ExperimentRunner.SOURCE_DIR + "/quic-implementations/picotls/*.a /usr/local/lib/python2.7/dist-packages/ivy/lib", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo /bin/cp -f -a " + ExperimentRunner.SOURCE_DIR + "/quic-implementations/picotls/*.a " + ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy/ivy/lib", 
                                                    shell=True, executable="/bin/bash").wait()                                          

        subprocess.Popen("sudo /bin/cp -f " + ExperimentRunner.SOURCE_DIR + "/quic-implementations/picotls/include/picotls.h /usr/local/lib/python2.7/dist-packages/ivy/include", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo /bin/cp -f " + ExperimentRunner.SOURCE_DIR + "/quic-implementations/picotls/include/picotls.h " + ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy/ivy/include", 
                                                    shell=True, executable="/bin/bash").wait()

        # cp -f " + ExperimentRunner.SOURCE_DIR + "/quic-implementations/picotls/include/picotls.h /usr/local/lib/python2.7/dist-packages/ivy/include
        # cp -f " + ExperimentRunner.SOURCE_DIR + "/quic-implementations/picotls/include/picotls.h " + ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy/ivy/include
        subprocess.Popen("sudo /bin/cp -r -f " + ExperimentRunner.SOURCE_DIR + "/quic-implementations/picotls/include/picotls/. /usr/local/lib/python2.7/dist-packages/ivy/include/picotls", 
                                                    shell=True, executable="/bin/bash").wait()
        # subprocess.Popen("sudo /bin/cp -r -f " + ExperimentRunner.SOURCE_DIR + "/quic-implementations/picotls/include/picotls/. " + ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy/ivy/include/picotls", 
        #                                             shell=True, executable="/bin/bash").wait()

        os.chdir(ExperimentRunner.SOURCE_DIR)

    def update_includes(self):
        path = ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic"
        self.log.info("Update \"include\" path of python with updated version of the project from \n\t"+path)
        subfolder = [os.path.join(path, f) for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        for folder in subfolder:
            files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.endswith(".ivy") and not "test" in f]
            for file in files:
                self.log.info(" " + file)
                self.included_files.append(file)
                subprocess.Popen("sudo /bin/cp "+ file +" /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/", 
                                                    shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo /bin/cp "+ path + "/quic_utils/quic_ser_deser.h" +" /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/", 
                                                    shell=True, executable="/bin/bash").wait()

    def remove_includes(self):
        self.log.info("Reset \"include\" path of python")
        for file in self.included_files:
            self.log.info(" " + file)
            nameFileShort = file.split("/")[-1]
            subprocess.Popen("sudo /bin/rm /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/" + nameFileShort, 
                                                    shell=True, executable="/bin/bash").wait()

    def build_tests(self,mode, categories):
        if mode == "server":
            true_categories = TESTS_SERVER.keys()
        elif mode == "mim":
            true_categories = TESTS_MIM.keys()
        else:
            true_categories = TESTS_CLIENT.keys()
        folder = ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/quic_tests/" + mode +"_tests/"
        os.chdir(folder)
        if "all" in categories:
            files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.endswith(".ivy") and mode in f]
            for file in files:
                self.log.info(" " + file)
                nameFileShort = file.split("/")[-1]
                self.executed_tests.append(nameFileShort.replace(".ivy",""))
                self.build_file(nameFileShort)
        elif categories in true_categories:
            if mode == "server":
                self.log.info(TESTS_SERVER[categories])
                files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.replace(".ivy","") in TESTS_SERVER[categories]]
            elif mode == "mim":
                self.log.info(TESTS_MIM[categories])
                files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.replace(".ivy","") in TESTS_MIM[categories]]
            else:
                self.log.info(TESTS_CLIENT[categories])
                files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.replace(".ivy","") in TESTS_CLIENT[categories]]
            for file in files:
                self.log.info(" " + file)
                nameFileShort = file.split("/")[-1]
                self.executed_tests.append(nameFileShort.replace(".ivy",""))
                self.build_file(nameFileShort)
        else:
            self.log.info(" " +categories)
            nameFileShort = categories.split("/")[-1]
            self.executed_tests.append(nameFileShort.replace(".ivy",""))
            self.build_file(nameFileShort)

    def build_file(self,file):
        self.compile_file(file)
        if "quic_server_test_0rtt" in file:
            file = file.replace("quic_server_test_0rtt","quic_server_test_0rtt_stream")
            self.compile_file(file)
            file = file.replace("quic_server_test_0rtt_stream","quic_server_test_0rtt_stream_co_close")
            self.compile_file(file)
            file = file.replace("quic_server_test_0rtt_stream_co_close","quic_server_test_0rtt_stream_app_close")
            self.compile_file(file)
        elif "quic_client_test_0rtt_invalid" in file:
            file = file.replace("quic_client_test_0rtt_invalid","quic_client_test_0rtt_max")
            self.compile_file(file)
        elif "quic_client_test_0rtt_add_val" in file:
            file = file.replace("quic_client_test_0rtt_add_val","quic_client_test_0rtt_max_add_val")
            self.compile_file(file)
        elif "quic_client_test_0rtt_mim_replay" in file:
            file = file.replace("quic_client_test_0rtt_mim_replay","quic_client_test_0rtt_max")
            self.compile_file(file)
        elif "quic_client_test_0rtt" in file:
            file = file.replace("quic_client_test_0rtt","quic_client_test_0rtt_max")
            self.compile_file(file)
            file = file.replace("quic_client_test_0rtt_max","quic_client_test_0rtt_max_co_close")
            self.compile_file(file)
            file = file.replace("quic_client_test_0rtt_max_co_close","quic_client_test_0rtt_max_app_close")
            self.compile_file(file)
        elif "quic_server_test_retry_reuse_key" in file:
            file = file.replace("quic_server_test_retry_reuse_key","quic_server_test_retry")
            self.compile_file(file)

    def compile_file(self,file):
        if ExperimentRunner.COMPILE:
            subprocess.Popen("ivyc target=test " + file, 
                                                    shell=True, executable="/bin/bash").wait()
            subprocess.Popen("/bin/cp "+ file.replace('.ivy','')  + " "+ ExperimentRunner.SOURCE_DIR +"/QUIC-Ivy/doc/examples/quic/build/", 
                                                    shell=True, executable="/bin/bash").wait()
            subprocess.Popen("/bin/cp "+ file.replace('.ivy','.cpp')  + " "+ ExperimentRunner.SOURCE_DIR +"/QUIC-Ivy/doc/examples/quic/build/", 
                                                    shell=True, executable="/bin/bash").wait()
            subprocess.Popen("/bin/cp "+ file.replace('.ivy','.h')  + " "+ ExperimentRunner.SOURCE_DIR +"/QUIC-Ivy/doc/examples/quic/build/", 
                                                    shell=True, executable="/bin/bash").wait()
            subprocess.Popen("/bin/rm "+ file.replace('.ivy',''), 
                                                    shell=True, executable="/bin/bash").wait()
            subprocess.Popen("/bin/rm "+ file.replace('.ivy','.cpp'), 
                                                    shell=True, executable="/bin/bash").wait()
            subprocess.Popen("/bin/rm "+ file.replace('.ivy','.h'), 
                                                    shell=True, executable="/bin/bash").wait()

    def launch_experiments(self):
        if ExperimentRunner.MEMORY_PROFILING:
            tracemalloc.start()
        
        if self.args.update_include_tls:
            self.update_includes_ptls()
        self.update_includes()
        
        os.environ['TEST_TYPE']     = self.args.mode
        ENV_VAR["TEST_TYPE"]        = self.args.mode
        if not self.args.docker:
            os.environ['IS_NOT_DOCKER'] = "true" 
            ENV_VAR["IS_NOT_DOCKER"]    = "true"
        else:
            if 'IS_NOT_DOCKER' in os.environ:
                del os.environ['IS_NOT_DOCKER']
            if 'IS_NOT_DOCKER' in ENV_VAR:
                del ENV_VAR['IS_NOT_DOCKER']
        subprocess.Popen("sudo sysctl -w net.core.rmem_max=2500000", 
                            shell=True, executable="/bin/bash").wait() # for quic-go
        if self.args.vnet:
            subprocess.Popen("bash "+ ExperimentRunner.SOURCE_DIR + "/vnet_setup.sh", 
                                                    shell=True, executable="/bin/bash").wait()
        else:
            subprocess.Popen("bash "+ ExperimentRunner.SOURCE_DIR + "/vnet_reset.sh", 
                                                    shell=True, executable="/bin/bash").wait()
        self.build_tests(self.args.mode, self.args.categories)

        runner = Runner(self.args)

        implementations = self.args.implementations
        if implementations == None:
            implementations = IMPLEMENTATIONS.keys()

        if  "quic_server_test_0rtt" in self.executed_tests or  "quic_client_test_0rtt" in self.executed_tests:
            bar_f = progressbar.ProgressBar(max_value=(len(self.executed_tests)+2)*len(implementations)*self.args.iter)
        else:
            bar_f = progressbar.ProgressBar(max_value=len(self.executed_tests)*len(implementations)*self.args.iter)
        bar_f.start()
        count_1 = 0
        for test in self.executed_tests:
            initial_test = test
            ni = 1
            if test == "quic_client_test_0rtt_mim_replay":
                os.environ['ZERORTT_TEST']="true" 
                ENV_VAR["ZERORTT_TEST"]="true"
            elif test == "quic_server_test_0rtt" or test == "quic_client_test_0rtt":
                os.environ['ZERORTT_TEST']="true" 
                ENV_VAR["ZERORTT_TEST"]="true"
                ni = 3
            else:
                if 'ZERORTT_TEST' in os.environ:
                    del os.environ['ZERORTT_TEST']
                if 'ZERORTT_TEST' in ENV_VAR:
                    del ENV_VAR["ZERORTT_TEST"]
            if test == "quic_server_test_retry_reuse_key": # TODO
                runner.nclient = 2
            else:
                runner.nclient = self.args.nclient
            # if "quic_client_test_version_negociation_mim" in test:
            #     subprocess.Popen("bash "+ ExperimentRunner.SOURCE_DIR + "/mim-setup.sh", 
            #                                         shell=True, executable="/bin/bash").wait()
            # else:
            #     subprocess.Popen("bash "+ ExperimentRunner.SOURCE_DIR + "/mim-reset.sh", 
            #                                         shell=True, executable="/bin/bash").wait()

            #if test == "quic_client_test_version_negociation_mim":
            #    subprocess.Popen("/bin/bash "+ ExperimentRunner.SOURCE_DIR + "/mim-setup.sh", 
            #                                        shell=True, executable="/bin/bash").wait()
            #else:
            #    subprocess.Popen("/bin/bash "+ ExperimentRunner.SOURCE_DIR + "/mim-reset.sh", 
            #                                        shell=True, executable="/bin/bash").wait()

            for j in range(0,ni):
                for implementation in implementations:  
                    print(implementations)
                    os.environ['TEST_IMPL'] = implementation
                    ENV_VAR["TEST_IMPL"] = implementation
                    os.environ['TEST_ALPN'] = self.args.alpn if implementation != "mvfst" else "hq"
                    ENV_VAR["TEST_ALPN"] = self.args.alpn if implementation != "mvfst" else "hq"
                    os.environ['SSLKEYLOGFILE'] = ExperimentRunner.SOURCE_DIR +"/tls-keys/"+implementation+"_key.log"
                    ENV_VAR["SSLKEYLOGFILE"] = ExperimentRunner.SOURCE_DIR +"/tls-keys/"+implementation+"_key.log"
                    for i in range(0,self.args.iter):
                        if j == 1:
                            test = initial_test + "_app_close"
                        elif j == 2:
                            test = initial_test + "_co_close"
                        self.log.info("Test: "+test)
                        self.log.info("Implementation: "+implementation)
                        self.log.info("Iteration: "+str(i+1) +"/" + str(self.args.iter))
                        os.environ['CNT'] = str(count_1)
                        ENV_VAR["CNT"] = str(count_1)
                        #os.environ['RND'] = os.getenv("RANDOM")
                        subprocess.Popen("> "+ ExperimentRunner.SOURCE_DIR +"/tickets/ticket.bin", 
                                                    shell=True, executable="/bin/bash").wait()
                        path = ExperimentRunner.SOURCE_DIR + '/QUIC-Ivy/doc/examples/quic/test/temp/'
                        #print(path)
                        folders = [os.path.join(path, f) for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
                        #print(folders)
                        pcap_i = len(folders)
                        self.log.info(pcap_i)
                        ivy_dir = path+str(pcap_i)
                        subprocess.Popen("/bin/mkdir " + ivy_dir, 
                                                    shell=True, executable="/bin/bash").wait()
                        pcap_name = ivy_dir +"/"+ implementation +"_"+ test +".pcap"
                        subprocess.Popen("touch "+pcap_name, 
                                                    shell=True, executable="/bin/bash").wait()
                        subprocess.Popen("sudo /bin/chmod o=xw "+ pcap_name, 
                                                    shell=True, executable="/bin/bash").wait()
                        self.log.info("\tStart thsark")
                        #time.sleep(10) # for server test 
                        # TODO kill entual old quic implem

                        if self.args.vnet:
                            interface = "vbridge"
                        else:
                            interface = "lo"
                        p = subprocess.Popen(["sudo", "tshark", "-w",
                                            pcap_name,
                                            "-i", interface, "-f", 'udp'],
                                            stdout=sys.stdout)
                        time.sleep(3)
                        runner.quic_implementation = implementation
                        
                        ivy_out = ivy_dir + '/ivy_stdout.txt'
                        ivy_err = ivy_dir + '/ivy_stderr.txt'
                        sys.stdout = open(ivy_out, 'w')
                        sys.stderr = open(ivy_err, 'w')
                        self.log.info("\tStart run")
                        try:
                            runner.output_path = None
                            runner.run_exp(initial_test,pcap_i,pcap_name,i,j)
                        except Exception as e:
                            print(e)
                        finally: # In Runner.py
                            sys.stdout.close()
                            sys.stderr.close()
                            sys.stdout = sys.__stdout__
                            sys.stderr = sys.__stderr__
                            subprocess.Popen("/usr/bin/tail -2 " + ivy_err, 
                                                    shell=True, executable="/bin/bash").wait()
                            subprocess.Popen("/usr/bin/tail -2 " + ivy_out, 
                                                    shell=True, executable="/bin/bash").wait()
                            #subprocess.Popen("/usr/bin/tail $(/usr/bin/lsof -i udp) >/dev/null 2>&1", # deadlock in docker todo
                            #                        shell=True, executable="/bin/bash").wait()
                            self.log.info("\tKill thsark")
                            subprocess.Popen("sudo /usr/bin/pkill tshark", 
                                                    shell=True, executable="/bin/bash").wait()
                            #p.kill()
                            count_1 += 1
                            bar_f.update(count_1)
                            subprocess.Popen("bash "+ ExperimentRunner.SOURCE_DIR + "/mim-reset.sh", 
                                                    shell=True, executable="/bin/bash").wait()
        if self.args.vnet:
            subprocess.Popen("bash "+ ExperimentRunner.SOURCE_DIR + "/vnet_reset.sh", 
                            shell=True, executable="/bin/bash").wait()
        bar_f.finish()
        self.remove_includes()
        subprocess.Popen("sudo /bin/cp -r "+ ExperimentRunner.SOURCE_DIR +"/tls-keys/ " + ExperimentRunner.SOURCE_DIR + '/QUIC-Ivy/doc/examples/quic/test/temp/', 
                            shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo /bin/cp -r "+ ExperimentRunner.SOURCE_DIR +"/tickets/ " + ExperimentRunner.SOURCE_DIR + '/QUIC-Ivy/doc/examples/quic/test/temp/', 
                            shell=True, executable="/bin/bash").wait()
        subprocess.Popen("sudo /bin/cp -r "+ ExperimentRunner.SOURCE_DIR +"/qlogs/ " + ExperimentRunner.SOURCE_DIR + '/QUIC-Ivy/doc/examples/quic/test/temp/', 
                            shell=True, executable="/bin/bash").wait()
        if ExperimentRunner.MEMORY_PROFILING:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            self.log.info("[ Top 50 ]")
            for stat in top_stats[:50]:
                self.log.info(stat)


def main():
    experiments = ExperimentRunner()
    if experiments.args.gui:
        from PyQt5 import QtWidgets
        app = QtWidgets.QApplication(sys.argv)
        IvyQUIC = QtWidgets.QMainWindow()
        ui = UIvyQUICExperiments(ExperimentRunner.SOURCE_DIR, experiments) #UIvyQUICResults(SOURCE_DIR)
        ui.setupUi(IvyQUIC)
        IvyQUIC.show()
        sys.exit(app.exec_())
    else:
        experiments.launch_experiments()

if __name__ == "__main__":    
    try:
        main()
    except Exception as e:
        print(e)
    finally:
        sys.stdout.close()
        sys.stderr.close() 
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__        subprocess.Popen("kill $(lsof -i udp) >/dev/null 2>&1") 
        subprocess.Popen("sudo pkill tshark")
        subprocess.Popen("bash "+ SOURCE_DIR + "/vnet_reset.sh", 
                        shell=True, executable="/bin/bash").wait()
        subprocess.Popen("/bin/kill $(/usr/bin/lsof -i udp) >/dev/null 2>&1") 
        subprocess.Popen("sudo /usr/bin/pkill tshark")


