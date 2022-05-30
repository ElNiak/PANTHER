from compileall import compile_file
import logging
import subprocess
import sys
import time
import progressbar
from h11 import SERVER
from utils.Runner import Runner
from utils.ArgumentsParser import ArgumentsParser
from utils.constants import *
from utils.CustomFormatter import CustomFormatter

# TODO refactor
# TODO change os.system with subprocess or with python funct
# TODO to finish
# TODO add barplot progression

import os

SOURCE_DIR =  os.getenv('PWD')
IMPLEM_DIR =  SOURCE_DIR + '/quic-implementations'

# Set environment variables
os.environ['PROOTPATH'] = SOURCE_DIR
os.environ['PATH'] = "/go/bin:${"+ os.getenv('PATH') +"}"

os.environ['ZRTT_SSLKEYLOG_FILE']  = SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/last_tls_key.key"
os.environ['RETRY_TOKEN_FILE']  = SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/last_retry_token.txt"
os.environ['NEW_TOKEN_FILE']  = SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/last_new_token.txt"
os.environ['ENCRYPT_TICKET_FILE'] = SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/last_encrypt_session_ticket.txt"
os.environ['SESSION_TICKET_FILE'] = SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/last_session_ticket_cb.txt"

os.system("$HOME/.cargo/env") # TODO source

MEMORY_PROFILING = False

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(CustomFormatter())
log = logging.getLogger("run_experiments")
log.setLevel(logging.INFO)
log.addHandler(ch)
log.propagate = False 

COMPILE = False

if MEMORY_PROFILING:
    # TODO take snapshot in build_scdgs()
    import tracemalloc 
    memory_snapshots = []

def update_includes_ptls():
    folder = SOURCE_DIR + "/QUIC-Ivy/ivy/include/1.7"
    log.info("Update \"include\" path of python with updated version of the TLS project from \n\t"+folder)
    files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.endswith(".ivy")]
    for file in files:
        log.info(" " + file)
        os.system("sudo cp "+ file +" /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/")
    os.system("sudo cp -f " + SOURCE_DIR + "/QUIC-Ivy/ivy/ivy_to_cpp.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_to_cpp.py")
    os.system("sudo cp -f " + SOURCE_DIR + "/QUIC-Ivy/ivy/ivy_solver.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_solver.py")
    os.system("sudo cp -f " + SOURCE_DIR + "/QUIC-Ivy/ivy/ivy_cpp_types.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_cpp_types.py")
    #cd /usr/local/lib/python2.7/dist-packages/ivy/

    os.chdir('/usr/local/lib/python2.7/dist-packages/ivy/')

    os.system("sudo python -m compileall ivy_to_cpp.py")
    os.system("sudo python -m compileall ivy_cpp_types.py")
    os.system("sudo python -m compileall ivy_solver.py")

    #echo "CP picotls lib"
    os.system("sudo cp -f " + SOURCE_DIR + "/quic-implementations/picotls/libpicotls-core.a /usr/local/lib/python2.7/dist-packages/ivy/lib")
    os.system("sudo cp -f " + SOURCE_DIR + "/quic-implementations/picotls/libpicotls-core.a " + SOURCE_DIR + "/QUIC-Ivy/ivy/lib")
    os.system("sudo cp -f " + SOURCE_DIR + "/quic-implementations/picotls/libpicotls-minicrypto.a /usr/local/lib/python2.7/dist-packages/ivy/lib")
    os.system("sudo cp -f " + SOURCE_DIR + "/quic-implementations/picotls/libpicotls-minicrypto.a " + SOURCE_DIR + "/QUIC-Ivy/ivy/lib")
    os.system("sudo cp -f " + SOURCE_DIR + "/quic-implementations/picotls/libpicotls-openssl.a /usr/local/lib/python2.7/dist-packages/ivy/lib")
    os.system("sudo cp -f " + SOURCE_DIR + "/quic-implementations/picotls/libpicotls-openssl.a " + SOURCE_DIR + "/QUIC-Ivy/ivy/lib")

    os.system("sudo cp -f " + SOURCE_DIR + "/ressources/include/picotls.h /usr/local/lib/python2.7/dist-packages/ivy/include")
    os.system("sudo cp -f " + SOURCE_DIR + "/ressources/include/picotls.h " + SOURCE_DIR + "/QUIC-Ivy/ivy/include")

    # cp -f " + SOURCE_DIR + "/quic-implementations/picotls/include/picotls.h /usr/local/lib/python2.7/dist-packages/ivy/include
    # cp -f " + SOURCE_DIR + "/quic-implementations/picotls/include/picotls.h " + SOURCE_DIR + "/QUIC-Ivy/ivy/include
    os.system("sudo cp -r -f " + SOURCE_DIR + "/quic-implementations/picotls/include/picotls/. /usr/local/lib/python2.7/dist-packages/ivy/include/picotls")
    os.system("sudo cp -r -f " + SOURCE_DIR + "/quic-implementations/picotls/include/picotls/. " + SOURCE_DIR + "/QUIC-Ivy/ivy/include/picotls")

    os.chdir(SOURCE_DIR)

def update_includes(included_files):
    path = SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic"
    log.info("Update \"include\" path of python with updated version of the project from \n\t"+path)
    subfolder = [os.path.join(path, f) for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    for folder in subfolder:
        files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.endswith(".ivy") and not "test" in f]
        for file in files:
            log.info(" " + file)
            included_files.append(file)
            os.system("sudo cp "+ file +" /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/")
    os.system("sudo cp "+ path + "/quic_utils/quic_ser_deser.h" +" /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/")

def remove_includes(included_files):
    log.info("Reset \"include\" path of python")
    for file in included_files:
        log.info(" " + file)
        nameFileShort = file.split("/")[-1]
        os.system("sudo rm /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/" + nameFileShort)

def build_tests(mode, categories):
    executed_tests = []
    if mode == "server":
        true_categories = TESTS_SERVER.keys()
    else:
        true_categories = TESTS_CLIENT.keys()
    folder = SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/quic_tests/" + mode +"_tests/"
    os.chdir(folder)
    if "all" in categories:
        files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.endswith(".ivy") and mode in f]
        for file in files:
            log.info(" " + file)
            nameFileShort = file.split("/")[-1]
            executed_tests.append(nameFileShort.replace(".ivy",""))
            build_file(nameFileShort)
    elif categories in true_categories:
        if mode == "server":
            log.info(TESTS_SERVER[categories])
            files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.replace(".ivy","") in TESTS_SERVER[categories]]
        else:
            log.info(TESTS_CLIENT[categories])
            files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.replace(".ivy","") in TESTS_CLIENT[categories]]
        for file in files:
            log.info(" " + file)
            nameFileShort = file.split("/")[-1]
            executed_tests.append(nameFileShort.replace(".ivy",""))
            build_file(nameFileShort)
    else:
        log.info(" " +categories)
        nameFileShort = categories.split("/")[-1]
        executed_tests.append(nameFileShort.replace(".ivy",""))
        build_file(nameFileShort)
    return executed_tests

def build_file(file):
    compile_file(file)
    if "quic_server_test_0rtt" in file:
        file = file.replace("quic_server_test_0rtt","quic_server_test_0rtt_stream")
        compile_file(file)
    elif "quic_client_test_0rtt" in file:
        file = file.replace("quic_client_test_0rtt","quic_client_test_0rtt_max")
        compile_file(file)
    elif "quic_server_test_retry_reuse_key" in file:
        file = file.replace("quic_server_test_retry_reuse_key","quic_server_test_retry")
        compile_file(file)

def compile_file(file):
    global COMPILE
    if COMPILE:
        os.system("ivyc target=test " + file)
        os.system("cp "+ file.replace('.ivy','')  + " "+ SOURCE_DIR +"/QUIC-Ivy/doc/examples/quic/build/")
        os.system("cp "+ file.replace('.ivy','.cpp')  + " "+ SOURCE_DIR +"/QUIC-Ivy/doc/examples/quic/build/")
        os.system("cp "+ file.replace('.ivy','.h')  + " "+ SOURCE_DIR +"/QUIC-Ivy/doc/examples/quic/build/")
        os.system("rm "+ file.replace('.ivy',''))
        os.system("rm "+ file.replace('.ivy','.cpp'))
        os.system("rm "+ file.replace('.ivy','.h'))

def main():
    global COMPILE
    args_parser = ArgumentsParser()
    args = args_parser.parse_arguments()
    log.info(args)
    COMPILE = args.compile
    included_files = list()
    if args.update_include_tls:
        update_includes_ptls()
    update_includes(included_files)
    
    os.environ['TEST_TYPE']     = args.mode
    os.environ['IS_NOT_DOCKER'] = "true" if args.not_docker  else "false"

    os.system("sudo sysctl -w net.core.rmem_max=2500000") # for quic-go
    
    executed_tests = build_tests(args.mode, args.categories)

    runner = Runner(args)

    implementations = args.implementations
    if implementations == None:
        implementations = IMPLEMENTATIONS.keys()

    bar_f = progressbar.ProgressBar(max_value=len(executed_tests)*len(implementations)*args.iter)
    bar_f.start()
    count_1 = 0
    for test in executed_tests:
        if test == "quic_server_test_0rtt" or test == "quic_client_test_0rtt":
            os.environ['ZERORTT_TEST']="true"
        else:
            if 'ZERORTT_TEST' in os.environ:
                del os.environ['ZERORTT_TEST']

        if test == "quic_client_test_version_negociation_mim":
            os.system("bash "+ SOURCE_DIR + "/mim-setup.sh")
        else:
            os.system("bash "+ SOURCE_DIR + "/mim-reset.sh")
        for implementation in implementations:  
            print(implementations)
            os.environ['TEST_IMPL'] = implementation
            os.environ['TEST_ALPN'] = "hq-29"
            os.environ['SSLKEYLOGFILE'] = SOURCE_DIR +"/tls-keys/"+implementation+"_key.log"
            for i in range(0,args.iter):
                log.info("Test: "+test)
                log.info("Implementation: "+implementation)
                log.info("Iteration: "+str(i+1) +"/" + str(args.iter))
                os.environ['CNT'] = str(count_1)
                #os.environ['RND'] = os.getenv("RANDOM")
                os.system("> "+ SOURCE_DIR +"/tickets/ticket.bin")
                path = SOURCE_DIR + '/QUIC-Ivy/doc/examples/quic/test/temp/'
                #print(path)
                folders = [os.path.join(path, f) for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
                #print(folders)
                pcap_i = len(folders)
                log.info(pcap_i)
                ivy_dir = path+str(pcap_i)
                pcap_name = ivy_dir +"_"+ implementation +"_"+ test +".pcap"
                os.system("touch "+pcap_name)
                os.system("sudo chmod o=xw "+ pcap_name)
                log.info("\tStart thsark")
                #time.sleep(10) # for server test 
                # TODO kill entual old quic implem
                p = subprocess.Popen(["sudo", "tshark", "-w",
                            pcap_name,
                            "-i", "lo", "-f", 'udp'],
                            stdout=sys.stdout)
                runner.quic_implementation = implementation
                os.system("mkdir " + ivy_dir)
                ivy_out = ivy_dir + '/ivy_stdout.txt'
                ivy_err = ivy_dir + '/ivy_stderr.txt'
                sys.stdout = open(ivy_out, 'w')
                sys.stderr = open(ivy_err, 'w')
                log.info("\tStart run")
                try:
                    runner.output_path = None
                    runner.run_exp(test,pcap_i,pcap_name,i)
                except Exception as e:
                    print(e)
                finally: # In Runner.py
                    sys.stdout.close()
                    sys.stderr.close()
                    sys.stdout = sys.__stdout__
                    sys.stderr = sys.__stderr__
                    os.system("tail -2 " + ivy_err)
                    os.system("tail -2 " + ivy_out)
                    os.system("kill $(lsof -i udp) >/dev/null 2>&1")
                    log.info("\tKill thsark")
                    os.system("sudo pkill tshark")
                    #p.kill()
                    count_1 += 1
                    bar_f.update(count_1)
    bar_f.finish()
    remove_includes(included_files)

if __name__ == "__main__":
    if MEMORY_PROFILING:
        tracemalloc.start()
    
    try:
        main()
    except Exception as e:
        print(e)
    finally:
        sys.stdout.close()
        sys.stderr.close() 
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        os.system("kill $(lsof -i udp) >/dev/null 2>&1") 
        os.system("sudo pkill tshark")

    if MEMORY_PROFILING:
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        log.info("[ Top 50 ]")
        for stat in top_stats[:50]:
            log.info(stat)