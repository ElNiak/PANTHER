from compileall import compile_file
import logging
import subprocess
import sys
import time
import progressbar
from h11 import SERVER
from utils.Runner import Runner
from utils.ArgumentParserRunner import ArgumentParserRunner
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

os.environ['active_connection_id_limit'] = SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/active_connection_id_limit.txt"
os.environ['initial_max_stream_id_bidi'] = SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/initial_max_stream_id_bidi.txt"
os.environ['initial_max_stream_data_bidi_local'] = SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/initial_max_stream_data_bidi_local.txt"
os.environ['initial_max_data'] = SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/initial_max_data.txt"
os.environ['initial_max_stream_data_bidi_remote'] = SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/initial_max_stream_data_bidi_remote.txt"
os.environ['initial_max_stream_data_uni'] = SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/initial_max_stream_data_uni.txt"


subprocess.Popen("$HOME/.cargo/env",shell=True, executable="/bin/bash").wait() # TODO source

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
        subprocess.Popen("sudo /bin/cp "+ file +" /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/", 
                                                shell=True, executable="/bin/bash").wait()
    subprocess.Popen("sudo /bin/cp -f " + SOURCE_DIR + "/QUIC-Ivy/ivy/ivy_to_cpp.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_to_cpp.py", 
                                                shell=True, executable="/bin/bash").wait()
    subprocess.Popen("sudo /bin/cp -f " + SOURCE_DIR + "/QUIC-Ivy/ivy/ivy_solver.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_solver.py", 
                                                shell=True, executable="/bin/bash").wait()
    subprocess.Popen("sudo /bin/cp -f " + SOURCE_DIR + "/QUIC-Ivy/ivy/ivy_cpp_types.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_cpp_types.py", 
                                                shell=True, executable="/bin/bash").wait()
    #cd /usr/local/lib/python2.7/dist-packages/ivy/

    os.chdir('/usr/local/lib/python2.7/dist-packages/ivy/')

    subprocess.Popen("sudo python -m compileall ivy_to_cpp.py", 
                                                shell=True, executable="/bin/bash").wait()
    subprocess.Popen("sudo python -m compileall ivy_cpp_types.py", 
                                                shell=True, executable="/bin/bash").wait()
    subprocess.Popen("sudo python -m compileall ivy_solver.py", 
                                                shell=True, executable="/bin/bash").wait()

    #echo "CP picotls lib"
    subprocess.Popen("sudo /bin/cp -f " + SOURCE_DIR + "/quic-implementations/picotls/libpicotls-core.a /usr/local/lib/python2.7/dist-packages/ivy/lib", 
                                                shell=True, executable="/bin/bash").wait()
    subprocess.Popen("sudo /bin/cp -f " + SOURCE_DIR + "/quic-implementations/picotls/libpicotls-core.a " + SOURCE_DIR + "/QUIC-Ivy/ivy/lib", 
                                                shell=True, executable="/bin/bash").wait()
    subprocess.Popen("sudo /bin/cp -f " + SOURCE_DIR + "/quic-implementations/picotls/libpicotls-minicrypto.a /usr/local/lib/python2.7/dist-packages/ivy/lib", 
                                                shell=True, executable="/bin/bash").wait()
    subprocess.Popen("sudo /bin/cp -f " + SOURCE_DIR + "/quic-implementations/picotls/libpicotls-minicrypto.a " + SOURCE_DIR + "/QUIC-Ivy/ivy/lib", 
                                                shell=True, executable="/bin/bash").wait()
    subprocess.Popen("sudo /bin/cp -f " + SOURCE_DIR + "/quic-implementations/picotls/libpicotls-openssl.a /usr/local/lib/python2.7/dist-packages/ivy/lib", 
                                                shell=True, executable="/bin/bash").wait()
    subprocess.Popen("sudo /bin/cp -f " + SOURCE_DIR + "/quic-implementations/picotls/libpicotls-openssl.a " + SOURCE_DIR + "/QUIC-Ivy/ivy/lib", 
                                                shell=True, executable="/bin/bash").wait()

    subprocess.Popen("sudo /bin/cp -f " + SOURCE_DIR + "/ressources/include/picotls.h /usr/local/lib/python2.7/dist-packages/ivy/include", 
                                                shell=True, executable="/bin/bash").wait()
    subprocess.Popen("sudo /bin/cp -f " + SOURCE_DIR + "/ressources/include/picotls.h " + SOURCE_DIR + "/QUIC-Ivy/ivy/include", 
                                                shell=True, executable="/bin/bash").wait()

    # cp -f " + SOURCE_DIR + "/quic-implementations/picotls/include/picotls.h /usr/local/lib/python2.7/dist-packages/ivy/include
    # cp -f " + SOURCE_DIR + "/quic-implementations/picotls/include/picotls.h " + SOURCE_DIR + "/QUIC-Ivy/ivy/include
    subprocess.Popen("sudo /bin/cp -r -f " + SOURCE_DIR + "/quic-implementations/picotls/include/picotls/. /usr/local/lib/python2.7/dist-packages/ivy/include/picotls", 
                                                shell=True, executable="/bin/bash").wait()
    subprocess.Popen("sudo /bin/cp -r -f " + SOURCE_DIR + "/quic-implementations/picotls/include/picotls/. " + SOURCE_DIR + "/QUIC-Ivy/ivy/include/picotls", 
                                                shell=True, executable="/bin/bash").wait()

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
            subprocess.Popen("sudo /bin/cp "+ file +" /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/", 
                                                shell=True, executable="/bin/bash").wait()
    subprocess.Popen("sudo /bin/cp "+ path + "/quic_utils/quic_ser_deser.h" +" /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/", 
                                                shell=True, executable="/bin/bash").wait()

def remove_includes(included_files):
    log.info("Reset \"include\" path of python")
    for file in included_files:
        log.info(" " + file)
        nameFileShort = file.split("/")[-1]
        subprocess.Popen("sudo /bin/rm /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/" + nameFileShort, 
                                                shell=True, executable="/bin/bash").wait()

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
        file = file.replace("quic_server_test_0rtt_stream","quic_server_test_0rtt_stream_co_close")
        compile_file(file)
        file = file.replace("quic_server_test_0rtt_stream_co_close","quic_server_test_0rtt_stream_app_close")
        compile_file(file)
    elif "quic_client_test_0rtt_invalid" in file:
        file = file.replace("quic_client_test_0rtt_invalid","quic_client_test_0rtt_max")
        compile_file(file)
    elif "quic_client_test_0rtt_add_val" in file:
        file = file.replace("quic_client_test_0rtt_add_val","quic_client_test_0rtt_max_add_val")
        compile_file(file)
    elif "quic_client_test_0rtt" in file:
        file = file.replace("quic_client_test_0rtt","quic_client_test_0rtt_max")
        compile_file(file)
        file = file.replace("quic_client_test_0rtt_max","quic_client_test_0rtt_max_co_close")
        compile_file(file)
        file = file.replace("quic_client_test_0rtt_max_co_close","quic_client_test_0rtt_max_app_close")
        compile_file(file)
    elif "quic_server_test_retry_reuse_key" in file:
        file = file.replace("quic_server_test_retry_reuse_key","quic_server_test_retry")
        compile_file(file)

def compile_file(file):
    global COMPILE
    if COMPILE:
        subprocess.Popen("ivyc target=test " + file, 
                                                shell=True, executable="/bin/bash").wait()
        subprocess.Popen("/bin/cp "+ file.replace('.ivy','')  + " "+ SOURCE_DIR +"/QUIC-Ivy/doc/examples/quic/build/", 
                                                shell=True, executable="/bin/bash").wait()
        subprocess.Popen("/bin/cp "+ file.replace('.ivy','.cpp')  + " "+ SOURCE_DIR +"/QUIC-Ivy/doc/examples/quic/build/", 
                                                shell=True, executable="/bin/bash").wait()
        subprocess.Popen("/bin/cp "+ file.replace('.ivy','.h')  + " "+ SOURCE_DIR +"/QUIC-Ivy/doc/examples/quic/build/", 
                                                shell=True, executable="/bin/bash").wait()
        subprocess.Popen("/bin/rm "+ file.replace('.ivy',''), 
                                                shell=True, executable="/bin/bash").wait()
        subprocess.Popen("/bin/rm "+ file.replace('.ivy','.cpp'), 
                                                shell=True, executable="/bin/bash").wait()
        subprocess.Popen("/bin/rm "+ file.replace('.ivy','.h'), 
                                                shell=True, executable="/bin/bash").wait()

def main():
    global COMPILE
    args_parser = ArgumentParserRunner()
    args = args_parser.parse_arguments()
    log.info(args)
    COMPILE = args.compile
    included_files = list()
    if args.update_include_tls:
        update_includes_ptls()
    update_includes(included_files)
    
    os.environ['TEST_TYPE']     = args.mode
    if not args.docker:
        os.environ['IS_NOT_DOCKER'] = "true" 
    else:
        if 'IS_NOT_DOCKER' in os.environ:
            del os.environ['IS_NOT_DOCKER']
    subprocess.Popen("sudo sysctl -w net.core.rmem_max=2500000", 
                        shell=True, executable="/bin/bash").wait() # for quic-go
    
    executed_tests = build_tests(args.mode, args.categories)

    runner = Runner(args)

    implementations = args.implementations
    if implementations == None:
        implementations = IMPLEMENTATIONS.keys()

    if  "quic_server_test_0rtt" in executed_tests or  "quic_client_test_0rtt" in executed_tests:
        bar_f = progressbar.ProgressBar(max_value=(len(executed_tests)+2)*len(implementations)*args.iter)
    else:
        bar_f = progressbar.ProgressBar(max_value=len(executed_tests)*len(implementations)*args.iter)
    bar_f.start()
    count_1 = 0
    for test in executed_tests:
        initial_test = test
        ni = 1
        if test == "quic_server_test_0rtt" or test == "quic_client_test_0rtt":
            os.environ['ZERORTT_TEST']="true" 
            ni = 3
        else:
            if 'ZERORTT_TEST' in os.environ:
                del os.environ['ZERORTT_TEST']

        #if test == "quic_client_test_version_negociation_mim":
        #    subprocess.Popen("/bin/bash "+ SOURCE_DIR + "/mim-setup.sh", 
        #                                        shell=True, executable="/bin/bash").wait()
        #else:
        #    subprocess.Popen("/bin/bash "+ SOURCE_DIR + "/mim-reset.sh", 
        #                                        shell=True, executable="/bin/bash").wait()

        for j in range(0,ni):
            for implementation in implementations:  
                print(implementations)
                os.environ['TEST_IMPL'] = implementation
                os.environ['TEST_ALPN'] = "hq-29"
                os.environ['SSLKEYLOGFILE'] = SOURCE_DIR +"/tls-keys/"+implementation+"_key.log"
                for i in range(0,args.iter):
                    if j == 1:
                        test = initial_test + "_app_close"
                    elif j == 2:
                        test = initial_test + "_co_close"
                    log.info("Test: "+test)
                    log.info("Implementation: "+implementation)
                    log.info("Iteration: "+str(i+1) +"/" + str(args.iter))
                    os.environ['CNT'] = str(count_1)
                    #os.environ['RND'] = os.getenv("RANDOM")
                    subprocess.Popen("> "+ SOURCE_DIR +"/tickets/ticket.bin", 
                                                shell=True, executable="/bin/bash").wait()
                    path = SOURCE_DIR + '/QUIC-Ivy/doc/examples/quic/test/temp/'
                    #print(path)
                    folders = [os.path.join(path, f) for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
                    #print(folders)
                    pcap_i = len(folders)
                    log.info(pcap_i)
                    ivy_dir = path+str(pcap_i)
                    pcap_name = ivy_dir +"_"+ implementation +"_"+ test +".pcap"
                    subprocess.Popen("touch "+pcap_name, 
                                                shell=True, executable="/bin/bash").wait()
                    subprocess.Popen("sudo /bin/chmod o=xw "+ pcap_name, 
                                                shell=True, executable="/bin/bash").wait()
                    log.info("\tStart thsark")
                    #time.sleep(10) # for server test 
                    # TODO kill entual old quic implem
                    p = subprocess.Popen(["sudo", "tshark", "-w",
                                pcap_name,
                                "-i", "lo", "-f", 'udp'],
                                stdout=sys.stdout)
                    runner.quic_implementation = implementation
                    subprocess.Popen("/bin/mkdir " + ivy_dir, 
                                                shell=True, executable="/bin/bash").wait()
                    ivy_out = ivy_dir + '/ivy_stdout.txt'
                    ivy_err = ivy_dir + '/ivy_stderr.txt'
                    sys.stdout = open(ivy_out, 'w')
                    sys.stderr = open(ivy_err, 'w')
                    log.info("\tStart run")
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
                        subprocess.Popen("/bin/tail -2 " + ivy_err, 
                                                shell=True, executable="/bin/bash").wait()
                        subprocess.Popen("/bin/tail -2 " + ivy_out, 
                                                shell=True, executable="/bin/bash").wait()
                        subprocess.Popen("/bin/kill $(lsof -i udp) >/dev/null 2>&1", 
                                                shell=True, executable="/bin/bash").wait()
                        log.info("\tKill thsark")
                        subprocess.Popen("sudo /bin/pkill tshark", 
                                                shell=True, executable="/bin/bash").wait()
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
        subprocess.Popen("/bin/kill $(lsof -i udp) >/dev/null 2>&1") 
        subprocess.Popen("sudo /bin/pkill tshark")

    if MEMORY_PROFILING:
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        log.info("[ Top 50 ]")
        for stat in top_stats[:50]:
            log.info(stat)
