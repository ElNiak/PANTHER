# This script runs a sequence of tests on the picoquicdemo server. 

import pexpect
import os
import sys
import imp
import subprocess
import re
import time
import signal
import random
from datetime import datetime
import platform

# On Windows, pexpect doesn't implement 'spawn'.
"""
Choose the process spawner for subprocess according to plateform
"""
if platform.system() == 'Windows':
    from pexpect.popen_spawn import PopenSpawn
    spawn = PopenSpawn
else:
    spawn = pexpect.spawn

scdir = os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH','') + '/quic-implementations')
scdircr = os.environ.get('QUIC_IMPL_DIR',os.environ.get('HOME','') + '/TVOQE_Perso/quic')
servers = [
    ['picoquic',[scdir+'/picoquic','./picoquicdemo -l - -D -L -q '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/qlogs/picoquic']], # -b myqlog.bins _pico.log -r
    ['pquic',[scdir+'/pquic','./picoquicdemo -l - -D -L']],
    ['quant',['..', scdir+'/quant/Debug/bin/server -d . -o -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/qlogs/quant -l '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/tls-keys/secret.log']], # -o
    ['winquic',['..','true']],
    ['minq',['..','go run '+ scdir + '/go/src/github.com/ekr/minq/bin/server/main.go']],
    ['chromium',[scdircr+'/chromium/src','./out/Default/quic_server --port=4443 --quic_response_cache_dir=/tmp/quic-data/www.example.org   --certificate_file=net/tools/quic/certs/out/leaf_cert.pem --key_file=net/tools/quic/certs/out/leaf_cert.pkcs8 --quic-enable-version-99  --generate_dynamic_responses --allow_unknown_root_cert --v=1']], # --quic_versions=h3-25
    #['quic-go',[scdir +'/quic-go/server/','./server -c '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/quic/certs/cert.pem -k '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/quic/certs/priv.key -l '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'logs.txt -p 4443 127.0.0.1']],
    ['quic-go',[scdir+'/quic-go/server/','./server -c '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.pem -k '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.key -p 4443 127.0.0.1']], # -c '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.pem -k '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.key
    ['aioquic',[scdir +'/aioquic/','python3 examples/http3_server.py --quic-log '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/qlogs/aioquic --certificate '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/quic-implementations/aioquic/tests/ssl_cert.pem --private-key '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/quic-implementations/aioquic/tests/ssl_key.pem  -v --host 127.0.0.1 --port 4443 -l '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/tls-keys/secret.log']], #127.0.0.1
    ['quiche',[scdir+'/quiche/','cargo run --manifest-path=tools/apps/Cargo.toml --bin quiche-server --  --cert tools/apps/src/bin/cert.crt --early-data --dump-packets '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/qlogs/quiche/dump_packet.txt --key tools/apps/src/bin/cert.key --no-retry --listen 127.0.0.1:4443' ]], #--early-data 
    ['mvfst',[scdir+'/mvfst/_build/build/quic/samples/','./echo -mode=server -host=127.0.0.1 -port=4443  -v=10 -pr=false ']],
    ['lsquic',[scdir+'/lsquic/bin/','./http_server -c www.example.org/,'+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.pem,'+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.key -Q hq-29 -D -s 127.0.0.1:4443 -l event=debug,engine=debug -o version=FF00001D -G '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/tls-keys/']],
    ['quinn',[scdir+'/quinn/','cargo run -vv --example server '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/index.html --keylog --listen 127.0.0.1:4443']], # home/chris/TVOQE_UPGRADE_27/QUIC-Ivy/doc/examples/quic/
    ['quicly',[scdir+'/quicly/','./cli -l '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/tls-keys/secret.log -a hq-29 -c '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.pem -k '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.key 127.0.0.1 4443']],
]

clients = [
    ['picoquic',[scdir + '/picoquic','./picoquicdemo -v ff00001d -l - -D -L -a hq-29 localhost 4443']], # -b myqlog.bin -R ff00001d -v ff00001e 
    ['pquic',[scdir + '/pquic','./picoquicdemo -D -L -v ff00001d localhost 4443 ']],
    ['quant',['..',scdir + '/quant/Debug/bin/client -e 0xff00001d -c false -r 20 -l '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/tls-keys/secret.log -q '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html']], #-c leaf_cert.pem '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.pem -o -u -c leaf_cert.pem -c keypair.pem -a  -c false -u  -e 0xff00001d
    ['winquic',['..','true']], 
    ['minq',['..','go run '+ scdir + '/go/src/github.com/ekr/minq/bin/client/main.go ']],
    ['chromium',[scdircr + '/chromium/src','./out/Default/quic_client --host=127.0.0.1 --port=6121 --disable_certificate_verification  https://www.example.org/ --v=1 --quic_versions=h3-23']],
    ['aioquic',[scdir + '/aioquic','python3 examples/http3_client.py -l '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/tls-keys/secret.log -v -q '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/qlogs/aioquic/ --ca-certs tests/pycacert.pem -i --insecure --legacy-http https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html https://localhost:4443/index.html']], #--ca-certs tests/pycacert.pem --ca-certs '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.pem --insecure 
    ['quic-go',[scdir +'/quic-go/client/','./client -X '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/tls-keys/secret.log -P -G 5000000 -v 127.0.0.1 4443 ']], #--secure -R 
    ['quiche',[scdir + '/quiche/','cargo run --manifest-path=tools/apps/Cargo.toml --bin quiche-client -- https://localhost:4443/index.html --dump-json --wire-version ff00001d --no-verify --body / -n 20']],
    # pipe for mvfst
    # mkdir tmp; mkfifo tmp/input.pipe; nohup ./basicsample  tmp/user.out 2> tmp/nohup.err
    ['mvfst',[scdir + '/mvfst/_build/build/quic/samples/','./echo -mode=client -host="127.0.0.1" -port=4443 -pr=true -v=10 -stop_logging_if_full_disk ']], # echo "HELOOOOO" > 
    ['lsquic',[scdir+ '/lsquic/bin/','./http_client -4 -Q hq-29 -R 50 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1 -o version=FF00001D']], #-C '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.pem -W -g -j -i 1000  -n 1 -r 1 -a -4  -r 20 index.html index.html index.html index.html index.html index.html index.html  -C '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.pem
    ['quinn',[scdir+ '/quinn/','cargo run -vv --example client https://localhost:4443/index.html --ca '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.pem ']], #--keylog --ca '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/QUIC-Ivy/doc/examples/quic/leaf_cert.pem
]

#List of available server's tests 
#Purpose of "test_completed"
server_tests = [
    ['..',
      [
      ['quic_server_test_stream','test_completed'],
	  ['quic_server_test_handshake_done_error','test_completed'],
      ['quic_server_test_reset_stream','test_completed'],
      ['quic_server_test_connection_close','test_completed'],
      ['quic_server_test_stop_sending','test_completed'],
      ['quic_server_test_max','test_completed'],
	  ['quic_server_test_token_error','test_completed'],
	  ['quic_server_test_tp_error','test_completed'],
	  ['quic_server_test_double_tp_error','test_completed'],
	  ['quic_server_test_tp_acticoid_error','test_completed'],
	  ['quic_server_test_tp_limit_acticoid_error','test_completed'],
	  ['quic_server_test_blocked_streams_maxstream_error','test_completed'],
	  ['quic_server_test_retirecoid_error','test_completed'],
	  ['quic_server_test_newcoid_zero_error','test_completed'],
	  ['quic_server_test_accept_maxdata','test_completed'],
	  ['quic_server_test_no_icid','test_completed'],
	  ['quic_server_test_ext_min_ack_delay','test_completed'],
	  ['quic_server_test_tp_limit_newcoid','test_completed'],
	  ['quic_server_test_unkown','test_completed'],
      ['quic_server_test_stream_limit_error','test_completed'],
      ['quic_server_test_crypto_limit_error','test_completed'],
      ['quic_server_test_newconnectionid_error','test_completed'],
      ['quic_server_test_newcoid_rtp_error','test_completed'],
      ['quic_server_test_newcoid_length_error','test_completed'],
      ['quic_server_test_new_token_error','test_completed'],
      ['quic_server_test_stop_sending_error','test_completed'],
      ['quic_server_test_tp_unkown','test_completed'],
      ['quic_client_test_limit_max_error','test_completed'],
      ['quic_server_test_max_error','test_completed'],
      ['quic_server_test_max_limit_error','test_completed'],
      ['quic_server_test_version_negociation','test_completed'],
      ['quic_server_test_version_negociation_ext','test_completed'],
      ['quic_server_test_retry','test_completed'],
      ]
    ],
]

#List of available client's tests 
client_tests = [
    ['..',
      [
      ['quic_client_test_stream','test_completed'],
      ['quic_client_test_max','test_completed'],
	  ['quic_client_test_token_error','test_completed'],
	  ['quic_client_test_tp_error','test_completed'],
	  ['quic_client_test_double_tp_error','test_completed'],
	  ['quic_client_test_tp_acticoid_error','test_completed'],
	  ['quic_client_test_tp_limit_acticoid_error','test_completed'],
	  ['quic_client_test_blocked_streams_maxstream_error','test_completed'],
	  ['quic_client_test_retirecoid_error','test_completed'],
	  ['quic_client_test_newcoid_zero_error','test_completed'],
	  ['quic_client_test_accept_maxdata','test_completed'],
	  ['quic_client_test_tp_prefadd_error','test_completed'],
	  ['quic_client_test_no_odci','test_completed'],
	  ['quic_client_test_ext_min_ack_delay','test_completed'],
	  ['quic_client_test_stateless_reset_token','test_completed'],
	  ['quic_client_test_handshake_done_error','test_completed'],

      ['quic_client_test_unkown','test_completed'],
      ['quic_client_test_tp_unkown','test_completed'],
      ['quic_client_test_limit_max_error','test_completed'],
      ['quic_client_test_new_token_error','test_completed'],
      ['quic_client_test_version_negociation','test_completed'],
      ['quic_client_test_retry','test_completed'],
      ]
    ],
]

output_path = None       # Output directory of tests (iev)
iters = 100              # Number of iteration per test
quic_name = 'winquic'    # Name of the client/server tested
getstats = False         # Print all stats
run = True               # For server/client's test, launch or not the server/client
test_pattern = '*'       # Test to launch regex, * match all test
time = 100               # Timeout
is_client = False        # True -> client tested <=> False -> server tested

# server_addr=0xc0a80101 client_addr=0xc0a80102
# Can be added in the command to parametrize more the command line
ivy_options = {'server_addr':None,'client_addr':None,'max_stream_data':None,'initial_max_streams_bidi':None}

all_tests = []
quic_cmd = None
quic_dir = None
extra_args = []

import sys

# @post print how to use test.py
def usage():
    print """usage:
    {} [option...]
options:
    dir=<output directory to create>
    iters=<number of iterations>
    {{client,server}}={{picoquic,quant,winquic}}
    test=<test name pattern>
    stats={{true,false}}
    run={{true,false}}
    """.format(sys.argv[0])
    sys.exit(1)

def open_out(name):
    return open(os.path.join(output_path,name),"w")

def sleep():
    return
    if quic_name == 'winquic':
        st = 20
        print 'sleeping for {}'.format(st)
        time.sleep(st)
    if quic_name == 'aioquic':
        st = 20
        print 'sleeping for {}'.format(st)
        time.sleep(st)

class Test(object):
    def __init__(self,dir,args):
        self.dir,self.name,self.res,self.opts = dir,args[0],args[-1],args[1:-1]
    
    def run(self,test_command):
        print '{}/{} ({}) ...'.format(self.dir,self.name,test_command)
        status = self.run_expect(test_command)
        print 'PASS' if status else 'FAIL'
        return status
    
    def run_expect(self,test_command):
        # Useless ? self.preprocess_commands() == []
        for pc in self.preprocess_commands():
            print 'executing: {}'.format(pc)
            child = spawn(pc)
            child.logfile = sys.stdout
            child.expect(pexpect.EOF)
            child.close()
            if child.exitstatus != 0:
#            if child.wait() != 0:
                print child.before
                return False
        with open_out(self.name+str(test_command)+'.out') as out:
            with open_out(self.name+str(test_command)+'.err') as err:
                with open_out(self.name+str(test_command)+'.iev') as iev:
                    # If run => Launch the quic entity tested 
                    if run:
                        qcmd = 'sleep 4; ' + quic_cmd if is_client else quic_cmd.split() 
                        print 'implementation command: {}'.format(qcmd)
                        quic_process = subprocess.Popen(qcmd,
                                                  cwd=quic_dir,
                                                  stdout=out,
                                                  stderr=err,
                                                  shell=is_client)
                        print 'quic_process pid: {}'.format(quic_process.pid)
                    # Always launch the test itself that will apply (test_client_max eg)
                    try:
                        ok = self.expect(test_command,iev)
                    except KeyboardInterrupt:
                        if run:
                            quic_process.terminate()
                        raise KeyboardInterrupt
                    # If run => get exit status of process
                    if run:
                        quic_process.terminate()
                        retcode = quic_process.wait()
                        if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                            iev.write('server_return_code({})\n'.format(retcode))
                            print "server return code: {}".format(retcode)
                            return False
                    return ok
    # Allow to launh the c++ test (test_client_max e.g)             
    def expect(self,test_command,iev):
        command = self.command(test_command)
        print command
        if platform.system() != 'Windows':
            oldcwd = os.getcwd()
            os.chdir(self.dir)
            proc = subprocess.Popen('sleep 3;'+command,stdout=iev,shell=True)
            os.chdir(oldcwd)
            try:
                retcode = proc.wait()
            except KeyboardInterrupt:
                print 'terminating client process {}'.format(proc.pid)
                proc.terminate()
                raise KeyboardInterrupt
            if retcode == 124:
                print 'timeout'
                iev.write('timeout\n')
                sleep()
                return False
            if retcode != 0:
                iev.write('ivy_return_code({})\n'.format(retcode))
                print 'client return code: {}'.format(retcode)
            sleep()
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
                print "tester exit status: {}".format(child.exitstatus)
                print "tester signal status: {}".format(child.signalstatus)
                return True
            except pexpect.EOF:
                print child.before
                return False
            except pexpect.exceptions.TIMEOUT:
                print 'timeout'
                child.terminate()
                child.close()
                return False
            except KeyboardInterrupt:
                print 'terminating tester process'
                child.kill(signal.SIGINT)
                child.close()
                raise KeyboardInterrupt
    def preprocess_commands(self):
        return []
        
class IvyTest(Test):
    # Produce the command to launch the test generated from the .ivy in the /build folder
    def command(self,test_command):
        import platform
        timeout_cmd = '' if platform.system() == 'Windows' else 'timeout {} '.format(time)
        randomSeed = random.randint(0,1000)
        random.seed(datetime.now())
        return ' '.join(['{}./build/{} seed={} the_cid={} {}'.format(timeout_cmd,self.name,randomSeed,0,'' if is_client else 'server_cid={} client_port={} client_port_alt={}'.format(1,2*test_command+4987,2*test_command+4988))] + extra_args)

def get_tests(cls,arr):
    for checkd in arr:
        dir,checkl = checkd
        for check in checkl:
            all_tests.append(cls(dir,check))

def main():
    global output_path, is_client, run, quic_cmd, quic_dir, extra_args, getstats
    # Parse the arguments
    for arg in sys.argv[1:]:
        vals = arg.split('=')
        if len(vals) != 2:
            usage()
        name,val = vals
        if name == 'dir':
            output_path = val
        elif name == 'iters':
            try:
                iters = int(val)
            except:
                usage()
        elif name == 'server':
            quic_name = val
        elif name == 'client':
            quic_name = val
            is_client = True
        elif name == 'stats':
            if val not in ['true','false']:
                usage()
            getstats = val == 'true'
        elif name == 'run':
            if val not in ['true','false']:
                usage()
            run = val == 'true'
        elif name == 'test':
            test_pattern = val
        elif name == 'time':
            time = val
        elif name in ivy_options:
            ivy_options[name] = val
        else:
            usage()

    # If no output path specified, put the results in the temp folder 
    # of the ivy project
    if output_path is None:
        idx = 0
        while True:
            path = os.path.join('temp',str(idx))
            if not os.path.exists(path):
                output_path = path
                break
            idx = idx + 1

    print 'output directory: {}'.format(output_path)
    # Check if the pattern is good, and get the regex object      
    try:
        test_pattern_obj = re.compile(test_pattern)
    except:
        sys.stderr.write('bad regular expression\n')
        exit(1)

    #Create the output directory
    try:  
        os.mkdir(output_path)
    except OSError:  
        sys.stderr.write('cannot create directory "{}"\n'.format(output_path))
        exit(1)

    # Put an array of eventual extra argument for the test
    extra_args = [opt_name+'='+opt_val for opt_name,opt_val in ivy_options.iteritems() if opt_val is not None]

    # Dict with implementation matched with corresponding command
    quic = dict(clients if is_client else servers)
    if quic_name not in quic:
        sys.stderr.write('unknown implementation: {}\n'.format(quic_name))
        exit(1)
    quic_dir,quic_cmd = quic[quic_name]

    #We have to launch the tested quic ourself
    if not run:
        quic_cmd = 'true'

    print 'implementation directory: {}'.format(quic_dir)
    print 'implementation command: {}'.format(quic_cmd)


    # Main   
    try:
        get_tests(IvyTest,client_tests if is_client else server_tests)

        num_failures = 0
        for test in all_tests:
            #if not test_pattern_obj.match(test.name):
            if not test_pattern == test.name:
                continue
            for test_command in range(0,iters):
		        #todo refactor
                if "quic_server_test_retry" in test.name: 
                    if quic_name == "quant":
                        quic_cmd = scdir+'/quant/Debug/bin/server -r -d . -o -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/qlogs/quant -l '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/tls-keys/secret.log'
                    elif quic_name == "picoquic":
                        quic_cmd = './picoquicdemo -r -l - -D -L -q '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/qlog/picoquic' 
                if "quic_server_test_version_negociation" in test.name: 
                    if quic_name == "quant":
                        quic_cmd = scdir+'/quant/Debug/bin/server -d . -o -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/qlogs/quant -l '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/tls-keys/secret.log'
                    elif quic_name == "picoquic":
                        quic_cmd = './picoquicdemo -l - -D -L -q '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/qlog/picoquic' 

                if "quic_client_test_retry" in test.name: #TODO 
                    if quic_name == "quant":
                        quic_cmd = scdir + '/quant/Debug/bin/client -e 0xff00001d -c false -r 20 -l '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/tls-keys/secret.log -q '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html'
                    elif quic_name == "picoquic":
                        quic_cmd = './picoquicdemo -v ff00001d -l - -D -L -a hq-29 localhost 4443' 
                if "quic_client_test_version_negociation" in test.name:
                    if quic_name == "quant":
                        quic_cmd = scdir + '/quant/Debug/bin/client -c false -r 20 -l '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/tls-keys/secret.log -q '+os.environ.get('QUIC_IMPL_DIR',os.environ.get('PROOTPATH',''))+'/qlogs/quant -t 3600 -v 5  https://localhost:4443/index.html'
                    elif quic_name == "picoquic":
                        quic_cmd = './picoquicdemo -l - -D -L -a hq-29 localhost 4443' 
                status = test.run(test_command)
                if not status:
                    num_failures += 1
            if getstats:
                import stats
                with open_out(test.name+'.dat') as out:
                    save = os.getcwd()
                    os.chdir(output_path)
                    stats.doit(test.name,out)
                    os.chdir(save)
        if num_failures:
            print 'error: {} tests(s) failed'.format(num_failures)
        else:
            print 'OK'
    except KeyboardInterrupt:
        print 'terminated'


main()

# for checkd in checks:
#     dir,checkl = checkd
#     for check in checkl:
#         name,res = check
#         print '{}/{} ...'.format(dir,name)
#         child = pexpect.spawn('timeout 100 ivy_check {}.ivy'.format(name))
#         try:
#             child.expect(res)
#             print 'PASS'
#         except pexpect.EOF:
#             print child.before
#             print 'FAIL'
        
