from cProfile import run
import os 
import re
import sys
from .constants import * 
from .IvyTest import IvyTest

class Runner:
    def __init__(self, args):
        self.output_path = args.dir    # Output directory of tests (iev)
        self.iters = 1 #args.iter         # Number of iteration per test
        self.quic_implementation = None     # Name of the client/server tested
        self.getstats = args.getstats  # Print all stats
        self.run = args.run            # For server/client's test, launch or not the server/client
        self.test_pattern = '*'        # Test to launch regex, * match all test
        self.time = args.timeout       # Timeout
        self.is_client = False if args.mode == "server" else True     # True -> client tested <=> False -> server tested
        self.is_mim    = True  if args.mode == "mim"    else False     # True -> client tested <=> False -> server tested
        print("is_mim = " + str(self.is_mim))
        self.vnet = True if args.vnet else False
        self.keep_alive = args.keep_alive
        self.gdb = args.gdb
        self.nclient = args.nclient
        self.initial_version = args.initial_version
        if args.mode == "client":
            self.nclient = 1
        # server_addr=0xc0a80101 client_addr=0xc0a80102
        # Can be added in the command to parametrize more the command line
        self.ivy_options = {'server_addr':None,'client_addr':None,'max_stream_data':None,'initial_max_streams_bidi':None}

        self.extra_args = []
        self.all_tests = []

        self.specials = {
            "quic_server_test_retry_reuse_key": {
                "picoquic-vuln":'./picoquicdemo -l "n"  -D -L -r',
                "picoquic":'./picoquicdemo -l - -r -D -L -q '+SOURCE_DIR +'/qlog/picoquic',
                "quant":IMPLEM_DIR+'/quant/Debug/bin/server -x 1000 -d . -o -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant -l '+SOURCE_DIR +'/tls-keys/secret.log -r',
                "quant-vuln":IMPLEM_DIR+'/quant-vuln/Debug/bin/server -x 1000 -d . -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant -l '+SOURCE_DIR +'/tls-keys/secret.log -r'
            },
            "quic_server_test_retry":{
                "quant":IMPLEM_DIR+'/quant/Debug/bin/server -x 1000 -d . -o -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant -l '+SOURCE_DIR +'/tls-keys/secret.log -r',
                "quant-vuln":IMPLEM_DIR+'/quant-vuln/Debug/bin/server -x 1000 -d . -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant -l '+SOURCE_DIR +'/tls-keys/secret.log -r',
                "picoquic":'./picoquicdemo -l "n" -D -L -q '+SOURCE_DIR +'/qlog/picoquic -r',
                "picoquic-vuln":'./picoquicdemo -l - -D -L -r',                
                "aioquic":'python3.9 examples/http3_server.py --quic-log '+SOURCE_DIR +'/qlogs/aioquic --certificate '+SOURCE_DIR +'/quic-implementations/aioquic/tests/ssl_cert.pem --private-key '+SOURCE_DIR +'/quic-implementations/aioquic/tests/ssl_key.pem  -v --retry --host 127.0.0.1 --port 4443 -l '+SOURCE_DIR +'/tls-keys/secret.log' ,
                "quiche":'cargo run --bin quiche-server --  --cert '+ SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/cert.pem --early-data --dump-packets '+SOURCE_DIR +'/qlogs/quiche/dump_packet.txt --key '+SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/priv.key --listen 127.0.0.1:4443',
                "quinn":'cargo run -vv --example server '+SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/index.html --keylog --stateless-retry --listen 127.0.0.1:4443',
                "quic-go":'./server -c '+SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/cert.pem -k '+SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/priv.key -r -p 4443 127.0.0.1',
                "mvfst": "./echo -mode=server -host=127.0.0.1 -port=4443  -v=10 -pr=true"
            },
            "quic_client_test_version_negociation":{
                "quant":IMPLEM_DIR + '/quant/Debug/bin/client -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html',
                "quant-vuln":IMPLEM_DIR + '/quant-vuln/Debug/bin/client -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html',
                "picoquic": './picoquicdemo -z -l - -D -L -a hq-interop localhost 4443' ,
                "aioquic":  'python3.9 examples/http3_client.py --version_negociation -l '+SOURCE_DIR +'/tls-keys/secret.log -v -q '+SOURCE_DIR +'/qlogs/aioquic/ --ca-certs tests/pycacert.pem -i --insecure --legacy-http https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html',
                "quiche": 'RUST_LOG="debug" cargo run --bin quiche-client -- https://localhost:4443/index.html --dump-json --no-verify --body / -n 5',
                "quic-go":'./client -X '+SOURCE_DIR +'/tls-keys/secret.log -V -P -v 127.0.0.1 4443',
                "lsquic":"./http_client -4 -Q hq-29 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8",
                "lsquic-vuln":"./http_client -4 -Q hq-29 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1 -o version=FF00001D -o scid_len=8"
            },
            "quic_client_test_version_negociation_mim_forge":{
                "quant":IMPLEM_DIR + '/quant/Debug/bin/client -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html',
                "quant-vuln":IMPLEM_DIR + '/quant-vuln/Debug/bin/client -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html',
                "picoquic": './picoquicdemo -G bbr -l - -D -L -a hq-interop -v 00000001 localhost 4443' , # CUBIC important for rtt
                "aioquic":  'python3.9 examples/http3_client.py --version_negociation -l '+SOURCE_DIR +'/tls-keys/secret.log -v -q '+SOURCE_DIR +'/qlogs/aioquic/ --ca-certs tests/pycacert.pem -i --insecure --legacy-http https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html',
                "quiche": 'RUST_LOG="debug" cargo run --bin quiche-client -- https://localhost:4443/index.html --dump-json --no-verify --body / -n 5',
                "quic-go":'./client -X '+SOURCE_DIR +'/tls-keys/secret.log -V -P -v 127.0.0.1 4443',
                "lsquic":"./http_client -4 -Q hq-29 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8",
                "lsquic-vuln":"./http_client -4 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8"
            },
            "quic_client_test_version_negociation_mim_manual":{
                "quant":IMPLEM_DIR + '/quant/Debug/bin/client -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html',
                "quant-vuln":IMPLEM_DIR + '/quant-vuln/Debug/bin/client -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html',
                "picoquic": './picoquicdemo -l - -D -L -a hq-29 localhost 4443' ,
                "aioquic":  'python3.9 examples/http3_client.py --version_negociation -l '+SOURCE_DIR +'/tls-keys/secret.log -v -q '+SOURCE_DIR +'/qlogs/aioquic/ --ca-certs tests/pycacert.pem -i --insecure --legacy-http https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html',
                "quiche": 'RUST_LOG="debug" cargo run --bin quiche-client -- https://localhost:4443/index.html --dump-json --no-verify --body / -n 5',
                "quic-go":'./client -X '+SOURCE_DIR +'/tls-keys/secret.log -V -P -v 127.0.0.1 4443',
                "lsquic":"./http_client -4 -Q hq-29 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8",
                "lsquic-vuln":"./http_client -4 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1  -o scid_len=8"
            }
        }

    def run_exp(self, test, run_id, pcap_name,iteration,j,do_gperf):
        if self.output_path is None:
            path = SOURCE_DIR  + '/QUIC-Ivy/doc/examples/quic/test/temp/' 
            path = os.path.join(path,str(run_id))
            print("is_mim = " + str(self.is_mim))
            print("path = " + path)
            if not os.path.exists(path):
                #Create the output directory
                try:  
                    os.mkdir(self.output_path)
                except OSError:  
                    sys.stderr.write('cannot create directory "{}"\n'.format(self.output_path))
                    #exit(1)
            self.output_path = path
        
        # Put an array of eventual extra argument for the test
        self.extra_args = [opt_name+'='+opt_val for opt_name,opt_val in self.ivy_options.items() if opt_val is not None]

        # Dict with implementation matched with corresponding command
        if self.quic_implementation not in IMPLEMENTATIONS:
            sys.stderr.write('unknown implementation: {}\n'.format(self.quic_implementation))
            exit(1)

        quic_dir, quic_cmd = IMPLEMENTATIONS[self.quic_implementation][1 if self.is_client else 0]
        quic_dir_opposite, quic_cmd_opposite = IMPLEMENTATIONS[self.quic_implementation][0 if self.is_client else 1]

    

        #quic_cmd = quic_cmd.replace("./","/")
        #quic_dir = quic_cmd # TODO
        #We have to launch the tested quic ourself
        if not self.run:
            quic_cmd = 'true'

        print('implementation directory: {}'.format(quic_dir))
        print('implementation command: {}'.format(quic_cmd))

        # Main   
        try:
            # TODO refactor
            dir = SOURCE_DIR + '/QUIC-Ivy/doc/examples/quic/build'
            print(test)
            checkl = [test]
            self.all_tests.clear() # TODO
            self.all_tests.append(IvyTest(dir,[test,"test_completed"],self.is_client,self.run, 
                                                self.keep_alive, self.time, self.gdb, 
                                                quic_dir,self.output_path,self.extra_args,
                                                self.quic_implementation,self.nclient,
                                                self.initial_version, self.is_mim,self.vnet, do_gperf))
            print(self.all_tests)
            num_failures = 0
            for test in self.all_tests:
                #if not test_pattern_obj.match(test.name):
                # if not self.test_pattern == test.name:
                #     continue
                for test_command in range(0,self.iters):
                    quic_cmd_upt = self.update_command(test)
                    quic_cmd = quic_cmd if quic_cmd_upt == "" else quic_cmd_upt
                    print(quic_cmd)
                    status = test.run(iteration,quic_cmd,j,quic_cmd_opposite)
                    print(status)
                    if not status:
                        num_failures += 1
                if self.getstats:
                    import utils.stats as stats
                    with open(os.path.join(self.output_path,test.name+str(iteration)+'.dat'),"w") as out:
                        save = os.getcwd()
                        os.chdir(self.output_path)
                        stats.make_dat(test.name,out)
                        os.chdir(save)
                    with open(os.path.join(self.output_path,test.name+str(iteration)+'.iev'),"r") as out:
                        stats.update_csv(run_id,self.quic_implementation, "client" if self.is_client else "server", 
                                test.name,pcap_name,os.path.join(self.output_path,
                                test.name+str(iteration)+'.iev'),out)
                # if self.do_gperf:
                #     os.system("pprof --pdf "+ command + " "+ os.path.join(self.output_path,self.name+str(iteration))+'_cpu.prof > ' + os.path.join(self.output_path,self.name+str(iteration))+'_cpu.pdf')
                #     # os.system("pprof --pdf "+ command + " "+ os.path.join(self.output_path,self.name+str(iteration))+'_heap.prof >' + os.path.join(self.output_path,self.name+str(iteration))+'_heap.pdf')
            #
            if num_failures:
                print('error: {} tests(s) failed'.format(num_failures))
            else:
                print('OK')
        except KeyboardInterrupt:
            print('terminated')

    def update_command(self, test):
        # TODO refactor
        quic_cmd = ""

        for key,val in self.specials.items():
            if key == test.name:
                quic_cmd = val[self.quic_implementation]
      
        return quic_cmd