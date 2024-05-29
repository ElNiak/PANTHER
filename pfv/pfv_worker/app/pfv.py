import logging
import subprocess
import sys
import tracemalloc  
from plantuml import PlantUML
import configparser
import os

from pfv_utils.pfv_constant import *

from pfv_runner.pfv_quic_runner import QUICRunner
from pfv_runner.pfv_minip_runner import MiniPRunner

from logger.CustomFormatter import ch

from argument_parser.ArgumentParserRunner import ArgumentParserRunner

DEBUG = True

class PFV:
    def __init__(self):    
        # Setup cargo
        subprocess.Popen("source $HOME/.cargo/env",shell=True, executable="/bin/bash").wait() # TODO source

        # Setup logger
        self.log = logging.getLogger("pfv")
        self.log.setLevel(logging.INFO)
        if (self.log.hasHandlers()):
            self.log.handlers.clear()
        self.log.addHandler(ch)
        self.log.propagate = False 
        
        # Setup argument parser
        self.args =  ArgumentParserRunner().parse_arguments()
        
        # Setup environment variables
        for env_var in ENV_VAR:
            os.environ[env_var] = str(ENV_VAR[env_var])
            self.log.info("ENV_VAR="+ env_var)
            self.log.info("ENV_VAL="+ str(ENV_VAR[env_var]))
        
        self.ivy_include_path = SOURCE_DIR + "/Protocols-Ivy/ivy/include/1.7/"
                
        # Setup configuration
        self.log.info("START SETUP CONFIGURATION")
        self.current_protocol = ""
        self.config = self.setup_config()
        self.log.info("SELECTED PROTOCOL: " + self.current_protocol)
        self.is_apt = self.config["global_parameters"].getboolean("apt")
        self.log.info("Advanced Persistent Threat: " + str(self.is_apt))
        self.protocol_conf = self.setup_protocol_parameters(self.current_protocol,SOURCE_DIR)
        self.log.info("END SETUP PROTOCOL PARAMETERS")
        
        self.total_exp_in_dir = len(os.listdir(self.config["global_parameters"]["dir"])) - 2
        self.current_exp_path = self.config["global_parameters"]["dir"] + str(self.total_exp_in_dir)
                
        self.current_count = 0
        self.current_implem = None
        self.available_modes = []
        
        self.included_files = list()

        if self.config["debug_parameters"].getboolean("memprof"):
            self.memory_snapshots = []
            
    def setup_config(self, init=False, protocol=None):
        config = configparser.ConfigParser(allow_no_value=True)
        config.read('configs/config.ini')
            
        self.key_path = SOURCE_DIR + "/tls-keys/"
        self.implems = {}
        self.current_protocol =  ""
        self.supported_protocols = config["verified_protocol"].keys()
        for p in config["verified_protocol"].keys():
            if config["verified_protocol"].getboolean(p):
                self.current_protocol = p
                break
        return config
    
    def setup_protocol_parameters(self,protocol, dir_path, init=False):
        self.tests = {}
        self.implems = {}
        protocol_conf = configparser.ConfigParser(allow_no_value=True)
        for envar in P_ENV_VAR[protocol]:
            os.environ[envar] = P_ENV_VAR[protocol][envar]
            self.log.info("ENV_VAR="+ envar)
            self.log.info("ENV_VAL="+  P_ENV_VAR[protocol][envar])

        protocol_conf.read('configs/'+protocol+'/'+protocol+'_config.ini')
        # TODO change var name at the end
        if  self.is_apt:
            self.ivy_model_path = dir_path + "/Protocols-Ivy/protocol-testing/apt/"
            self.config.set('global_parameters', "tests_dir", dir_path + "/Protocols-Ivy/protocol-testing/apt/apt_tests/")
            self.config.set('global_parameters', "dir"      , dir_path + "/Protocols-Ivy/protocol-testing/apt/test/temp/")
            self.config.set('global_parameters', "build_dir", dir_path + "/Protocols-Ivy/protocol-testing/apt/build/")
        else:
            self.ivy_model_path = dir_path + "/Protocols-Ivy/protocol-testing/" + protocol
            self.config.set('global_parameters', "tests_dir", dir_path + "/Protocols-Ivy/protocol-testing/apt/"+ protocol +"/"+protocol +"_tests/")
            self.config.set('global_parameters', "dir"      , dir_path + "/Protocols-Ivy/protocol-testing/apt/"+ protocol +"/test/temp/")
            self.config.set('global_parameters', "build_dir", dir_path + "/Protocols-Ivy/protocol-testing/apt/"+ protocol +"/build/")
        
        self.log.info("Protocol: " + protocol)
        for cate in protocol_conf.keys():
            if "test" in cate:
                self.log.info("Current category: " + cate)
                self.tests[cate] = []
                for test in protocol_conf[cate]:
                    self.log.info("Current test: " + test)
                    if protocol_conf[cate].getboolean(test):
                        self.log.info("Adding test: " + test)
                        self.tests[cate].append(test)
        
        implem_config_path_server = 'configs/'+protocol+'/implem-server'
        implem_config_path_client = 'configs/'+protocol+'/implem-client'
        
        for file_path in os.listdir(implem_config_path_server):
            # check if current file_path is a file
            if os.path.isfile(os.path.join(implem_config_path_server, file_path)):
                implem_name = file_path.replace(".ini","") 
                implem_conf_server = configparser.ConfigParser(allow_no_value=True)
                implem_conf_server.read(os.path.join(implem_config_path_server, file_path))
                implem_conf_client = configparser.ConfigParser(allow_no_value=True)
                implem_conf_client.read(os.path.join(implem_config_path_client, file_path))
                self.implems[implem_name] = [implem_conf_server, implem_conf_client]
        return protocol_conf
    
    def update_ivy(self):
        # Note we use subprocess in order to get sudo rights
        os.chdir(SOURCE_DIR + "/Protocols-Ivy/")
        os.system("sudo python2.7 setup.py install")
        os.system("sudo cp lib/libz3.so submodules/z3/build/python/z3")
        # TODO extract variable for path -> put in module path
        self.log.info("Update \"include\" path of python with updated version of the TLS project from \n\t"+self.ivy_include_path)
        files = [os.path.join(self.ivy_include_path, f) for f in os.listdir(self.ivy_include_path) if os.path.isfile(os.path.join(self.ivy_include_path, f)) and f.endswith(".ivy")]
        self.log.info("Copying file to /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/")
        for file in files:
            self.log.info(" " + file)
            subprocess.Popen("sudo /bin/cp "+ file +" /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/", 
                                                    shell=True, executable="/bin/bash").wait()
        
        os.chdir('/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/')
        subprocess.Popen("sudo /bin/cp -f -a " + SOURCE_DIR + "/Protocols-Ivy/lib/*.a /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/lib", 
                                                    shell=True, executable="/bin/bash").wait()

        
        if self.config["verified_protocol"].getboolean("quic"):
            self.log.info("Copying QUIC libraries")
            subprocess.Popen("sudo /bin/cp -f -a " + SOURCE_DIR + "/implementations/quic-implementations/picotls/*.a /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/lib", 
                                                        shell=True, executable="/bin/bash").wait()
            subprocess.Popen("sudo /bin/cp -f -a " + SOURCE_DIR + "/implementations/quic-implementations/picotls/*.a " + SOURCE_DIR + "/Protocols-Ivy/ivy/lib", 
                                                        shell=True, executable="/bin/bash").wait()                                          

            subprocess.Popen("sudo /bin/cp -f " + SOURCE_DIR + "/implementations/quic-implementations/picotls/include/picotls.h /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include", 
                                                        shell=True, executable="/bin/bash").wait()
            subprocess.Popen("sudo /bin/cp -f " + SOURCE_DIR + "/implementations/quic-implementations/picotls/include/picotls.h " + SOURCE_DIR + "/Protocols-Ivy/ivy/include", 
                                                        shell=True, executable="/bin/bash").wait()
            subprocess.Popen("sudo /bin/cp -r -f " + SOURCE_DIR + "/implementations/quic-implementations/picotls/include/picotls/. /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/picotls", 
                                                        shell=True, executable="/bin/bash").wait()
    
        os.chdir(SOURCE_DIR)

    def setup_ivy_model(self):
        self.log.info("Update \"include\" path of python with updated version of the project from \n\t"+self.ivy_model_path)
        subfolder = [os.path.join(self.ivy_model_path, f) for f in os.listdir(self.ivy_model_path) if os.path.isdir(os.path.join(self.ivy_model_path, f))]
        for folder in subfolder:
            files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.endswith(".ivy") and not "test" in f] # TODO find more elegant way to avoid copy test files
            for file in files:
                self.log.info(" " + file)
                self.included_files.append(file)
                subprocess.Popen("sudo /bin/cp "+ file +" /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/", 
                                                    shell=True, executable="/bin/bash").wait()
        if self.config["verified_protocol"].getboolean("quic"):
            subprocess.Popen("sudo /bin/cp "+ (self.ivy_model_path if not self.is_apt else self.ivy_model_path + "/quic") + "/quic_utils/quic_ser_deser.h" +" /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/", 
                                                        shell=True, executable="/bin/bash").wait()
        
    def remove_includes(self):
        self.log.info("Reset \"include\" path of python")
        for file in self.included_files:
            self.log.info(" " + file)
            nameFileShort = file.split("/")[-1]
            subprocess.Popen("sudo /bin/rm /usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/" + nameFileShort, 
                                                    shell=True, executable="/bin/bash").wait()
        self.included_files = list()   

    def build_tests(self,test_to_do={}):
        self.log.info("Number of test to compile: " + str(len(test_to_do)))
        self.log.info(test_to_do)
        assert len(test_to_do) > 0
        self.available_modes = test_to_do.keys()
        self.log.info(self.available_modes)
        for mode in self.available_modes:
            for file in test_to_do[mode]:
                if mode in file: # TODO more beautiful
                    self.log.info("chdir in " + self.config["global_parameters"]["tests_dir"] + mode+ "s")
                    os.chdir(self.config["global_parameters"]["tests_dir"] + mode+ "s") # TODO either add "s" in config or change folder
                    file = os.path.join(self.config["global_parameters"]["tests_dir"], file) + ".ivy"
                    self.log.info(" " + file)
                    nameFileShort = file.split("/")[-1]
                    self.build_file(nameFileShort)
        os.chdir(SOURCE_DIR)

    def build_file(self,file):
        self.compile_file(file)
        if self.config["verified_protocol"].getboolean("quic"):
            # TODO add in config file, test that should be build and run in pair
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
        if self.config["global_parameters"].getboolean("compile"):
            self.log.info("Building/Compiling file:")
            child= subprocess.Popen("ivyc trace=false show_compiled=false target=test test_iters="+ str(self.config["global_parameters"]["internal_iteration"]) + "  " + file, 
                                                    shell=True, executable="/bin/bash").wait()
            rc = child
            self.log.info(rc)
            if rc != 0:
                exit(1)
            
            self.log.info("Moving built file in correct folder:")
            subprocess.Popen("/usr/bin/chmod +x "+ file.replace('.ivy',''), 
                                                    shell=True, executable="/bin/bash").wait()
            subprocess.Popen("/bin/cp "+ file.replace('.ivy','')  + " "+ self.config["global_parameters"]["build_dir"], 
                                                    shell=True, executable="/bin/bash").wait()
            subprocess.Popen("/bin/cp "+ file.replace('.ivy','.cpp')  + " "+ self.config["global_parameters"]["build_dir"], 
                                                    shell=True, executable="/bin/bash").wait()
            subprocess.Popen("/bin/cp "+ file.replace('.ivy','.h')  + " "+ self.config["global_parameters"]["build_dir"], 
                                                    shell=True, executable="/bin/bash").wait()
            subprocess.Popen("/bin/rm "+ file.replace('.ivy',''), 
                                                    shell=True, executable="/bin/bash").wait()
            subprocess.Popen("/bin/rm "+ file.replace('.ivy','.cpp'), 
                                                    shell=True, executable="/bin/bash").wait()
            subprocess.Popen("/bin/rm "+ file.replace('.ivy','.h'), 
                                                    shell=True, executable="/bin/bash").wait()

    def launch_experiments(self, implementations=None):        
        if self.config["debug_parameters"].getboolean("memprof"):
            tracemalloc.start()
            
        if self.config["global_parameters"].getboolean("update_ivy"):
            self.update_ivy()
        self.setup_ivy_model()
            
        # Set environement-specific env var
        if not self.config["global_parameters"].getboolean("docker"):
            os.environ['IS_NOT_DOCKER'] = "true" 
            ENV_VAR["IS_NOT_DOCKER"]    = "true"
        else:
            if 'IS_NOT_DOCKER' in os.environ:
                del os.environ['IS_NOT_DOCKER']
            if 'IS_NOT_DOCKER' in ENV_VAR:
                del ENV_VAR['IS_NOT_DOCKER']
        
        # Set network-specific env var
        if self.config["net_parameters"].getboolean("shadow"):
            ENV_VAR["LOSS"]    = float(self.config["shadow_parameters"]["loss"])
            ENV_VAR["LATENCY"] = int(self.config["shadow_parameters"]["latency"])
            ENV_VAR["JITTER"]  = int(self.config["shadow_parameters"]["jitter"])
            if DEBUG:
                self.log.info(ENV_VAR["LOSS"])
                self.log.info(ENV_VAR["LATENCY"])
                self.log.info(ENV_VAR["JITTER"])
        
        if not self.config["global_parameters"].getboolean("docker"):  
            subprocess.Popen("sudo sysctl -w net.core.rmem_max=2500000", 
                                shell=True, executable="/bin/bash").wait() # for quic-go
        
            
        self.build_tests(test_to_do=self.tests)
        

        if implementations == None or implementations == []:
            self.log.error("TODO implement in local mode, for now only with docker (ERROR)")
            sys.exit(0)
            # TODO implement in local mode, for now only with docker

        for implem in implementations:
            self.log.info(implem)
            self.log.info(self.implems.keys())
            if implem not in self.implems.keys():
                self.log.info("unknown implementation")
                sys.stderr.write('unknown implementation: {}\n'.format(implem))
                exit(1)

        if self.config["verified_protocol"].getboolean("quic"):
            runner = QUICRunner(self.config, self.protocol_conf, self.current_protocol, self.implems, self.tests)
        elif self.config["verified_protocol"].getboolean("minip"):
            runner = MiniPRunner(self.config, self.protocol_conf, self.current_protocol, self.implems, self.tests)
        else:
            self.log.info("No protocols selected")
            exit(0)
                    
        for implementation in implementations:  
            self.log.info(implementation)
            os.environ['TEST_IMPL'] = implementation
            ENV_VAR["TEST_IMPL"]    = implementation
            try:
                runner.run_exp(implementation)
            except Exception as e:
                print(e)
                with open('configs/'+implementation+'/'+self.current_protocol+'_config.ini', 'w') as configfile:
                    with open('configs/'+implementation+'/default_'+self.current_protocol+'_config.ini', "r") as default_config:
                        default_settings = default_config.read()
                        configfile.write(default_settings)
            finally: # In Runner.py
                sys.stdout.close()
                sys.stderr.close()
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                if self.config["net_parameters"].getboolean("vnet"):
                    self.log.info("Reset vnet")
                    subprocess.Popen("bash "+ SOURCE_DIR + "/vnet_reset.sh", 
                                    shell=True, executable="/bin/bash").wait()
        
        self.log.info("END 1 ")
        if self.config["debug_parameters"].getboolean("memprof"):
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            self.log.info("[ Top 50 ]")
            for stat in top_stats[:50]:
                self.log.info(stat)
        
        if self.config["debug_parameters"].getboolean("ivy_process_tracer"):
            try:
                self.log.info("Generating PlantUML trace from ivy trace")
                plantuml_file = "/ivy_trace.txt"
                plantuml_obj = PlantUML(url="http://www.plantuml.com/plantuml/img/",  basic_auth={}, form_auth={}, http_opts={}, request_opts={})
                plantuml_file_png = plantuml_file.replace('.puml', '.png') #"media/" + str(nb_exp) + "_plantuml.png"
                plantuml_obj.processes_file(plantuml_file,  plantuml_file_png)
                self.log.info("done")
            except Exception as e:
                print(e)

        self.log.info("END 1")
        exit(0)

def main():
    experiments = ArgumentParserRunner().parse_arguments()
    if experiments.webapp:
        from webapp.pfv_server import PFVServer
        app = PFVServer(SOURCE_DIR)
        app.run()
        sys.exit(app.exec_())
    elif experiments.worker:
        from webapp.pfv_client import PFVClient
        app = PFVClient(SOURCE_DIR)
        app.run()
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
        sys.stderr = sys.__stderr__       
        subprocess.Popen("kill $(lsof -i udp) >/dev/null 2>&1") 
        subprocess.Popen("sudo pkill tshark")
        subprocess.Popen("bash "+ SOURCE_DIR + "/vnet_reset.sh", 
                        shell=True, executable="/bin/bash").wait()
        subprocess.Popen("/bin/kill $(/usr/bin/lsof -i udp) >/dev/null 2>&1") 
        subprocess.Popen("sudo /usr/bin/pkill tshark")
        subprocess.Popen("sudo /usr/bin/pkill tini")


