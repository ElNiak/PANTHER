import os

SOURCE_DIR =  os.getcwd()
IMPLEM_DIR =  SOURCE_DIR + '/quic-implementations'
QUIC_DIR   =  SOURCE_DIR + '/Protocols-Ivy/doc/examples/quic/'
RESULT_DIR =  SOURCE_DIR + '/Protocols-Ivy/doc/examples/quic/test/'
IVY_DIR    =   SOURCE_DIR + '/Protocols-Ivy'
ENV_VAR = {
    "IVY_INCLUDE_PATH":"${IVY_INCLUDE_PATH}:/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7",
    "Z3_LIBRARY_DIRS": IVY_DIR + "/submodules/z3/build",
    "Z3_LIBRARY_PATH": IVY_DIR + "/submodules/z3/build;",
    "LD_LIBRARY_PATH":"${LD_LIBRARY_PATH}:" + IVY_DIR +"/submodules/z3/build",
    "PROOTPATH": SOURCE_DIR,
    "PYTHONPATH": "${PYTHONPATH}:" + IMPLEM_DIR + "/aioquic:"+IVY_DIR+"/submodules/z3/build/python",
    #"PATH": os.getenv('PATH') + ":/go/bin", # "/go/bin:${"+ os.getenv('PATH') +"}", #
    "ZRTT_SSLKEYLOGFILE": SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/last_tls_key.txt",
    "RETRY_TOKEN_FILE": SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/last_retry_token.txt",
    "NEW_TOKEN_FILE": SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/last_new_token.txt",
    "ENCRYPT_TICKET_FILE": SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/last_encrypt_session_ticket.txt",
    "SESSION_TICKET_FILE": SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/last_session_ticket_cb.txt",
    "SAVED_PACKET": SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/saved_packet.txt",
    
    # "max_idle_timeout":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/max_idle_timeout.txt",
    # "max_ack_delay":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/max_ack_delay.txt",
    # "max_udp_payload_size":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/max_udp_payload_size.txt",
    # "max_datagram_frame_size":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/max_datagram_frame_size.txt",
    # "max_stream_data_bidi_local":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/max_stream_data_bidi_local.txt",
    # "max_stream_data_bidi_remote":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/max_stream_data_bidi_remote.txt",
    # "max_stream_data_uni":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/max_stream_data_uni.txt",
    "initial_max_stream_id_bidi":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/initial_max_stream_id_bidi.txt",
    # "initial_max_stream_id_uni":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/initial_max_stream_id_uni.txt",
    # "max_data":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/max_data.txt",
    # "max_bidi_streams":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/max_bidi_streams.txt",
    # "max_uni_streams":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/max_uni_streams.txt",
    
    "active_connection_id_limit":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/active_connection_id_limit.txt",
    "initial_max_stream_data_bidi_local":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/initial_max_stream_data_bidi_local.txt",
    "initial_max_stream_data_bidi_remote":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/initial_max_stream_data_bidi_remote.txt",
    "initial_max_stream_data_uni":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/initial_max_stream_data_uni.txt",   
    "initial_max_data":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/initial_max_data.txt",
    
    # "initial_max_bidi_streams":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/initial_max_bidi_streams.txt",
    # "initial_max_uni_streams":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/initial_max_uni_streams.txt",
    # "max_packet_size":  SOURCE_DIR + "/Protocols-Ivy/doc/examples/quic/max_packet_size.txt",
    #"LD_LIBRARY_PATH": os.getenv('LD_LIBRARY_PATH') + ":" + IVY_DIR +"/submodules/z3/build", # "/go/bin:${"+ os.getenv('PATH') +"}", #
    "PATH": os.getenv('PATH') + ":/go/bin:" + IVY_DIR +"/submodules/z3/build", # "/go/bin:${"+ os.getenv('PATH') +"}", #
    #"PYTHONPATH": os.getenv('PYTHONPATH') + ":"+  IVY_DIR +"/submodules/z3/build/python",
}

# cp lib/libz3.so submodules/z3/build/python/z3
# cp lib/libz3.so submodules/z3/build/python/z3; export IVY_INCLUDE_PATH=IVY_INCLUDE_PATH:/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7;export Z3_LIBRARY_DIRS=$PWD/submodules/z3/build; export Z3_LIBRARY_PATH=$PWD/submodules/z3/build; export PATH=$PATH:$PWD/submodules/z3/build; export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$PWD/submodules/z3/build; export PYTHONPATH=$PYTHONPATH:$PWD/submodules/z3/build/python; ivy ui=cti doc/examples/client_server_example.ivy
# cp lib/libz3.so submodules/z3/build/python/z3; export IVY_INCLUDE_PATH=IVY_INCLUDE_PATH:/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7;export Z3_LIBRARY_DIRS=$PWD/submodules/z3/build; export Z3_LIBRARY_PATH=$PWD/submodules/z3/build; export PATH=$PATH:$PWD/submodules/z3/build; export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$PWD/submodules/z3/build; export PYTHONPATH=$PYTHONPATH:$PWD/submodules/z3/build/python; cd doc/examples/quic/quic_tests/server_tests; ivy ui=cti show_compiled=false pedantic=true isolate_mode=test isolate=this quic_server_test_stream.ivy; cd ../../../../..
# cp lib/libz3.so submodules/z3/build/python/z3; export IVY_INCLUDE_PATH=IVY_INCLUDE_PATH:/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7;export Z3_LIBRARY_DIRS=$PWD/submodules/z3/build; export Z3_LIBRARY_PATH=$PWD/submodules/z3/build; export PATH=$PATH:$PWD/submodules/z3/build; export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$PWD/submodules/z3/build; export PYTHONPATH=$PYTHONPATH:$PWD/submodules/z3/build/python; cd doc/examples/quic/quic_tests/server_tests; ivy ui=cti show_compiled=false pedantic=true isolate_mode=extract isolate=this quic_server_test_stream.ivy; cd ../../../../..
# cp lib/libz3.so submodules/z3/build/python/z3; export IVY_INCLUDE_PATH=IVY_INCLUDE_PATH:/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7;export Z3_LIBRARY_DIRS=$PWD/submodules/z3/build; export Z3_LIBRARY_PATH=$PWD/submodules/z3/build; export PATH=$PATH:$PWD/submodules/z3/build; export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$PWD/submodules/z3/build; export PYTHONPATH=$PYTHONPATH:$PWD/submodules/z3/build/python; cd doc/examples/quic/quic_tests/server_tests; ivy ui=cti show_compiled=false pedantic=true isolate_mode=test isolate=extract quic_server_test_stream.ivy; cd ../../../../..

# cp lib/libz3.so submodules/z3/build/python/z3; export IVY_INCLUDE_PATH=IVY_INCLUDE_PATH:/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7;export Z3_LIBRARY_DIRS=$PWD/submodules/z3/build; export Z3_LIBRARY_PATH=$PWD/submodules/z3/build; export PATH=$PATH:$PWD/submodules/z3/build; export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$PWD/submodules/z3/build; export PYTHONPATH=$PYTHONPATH:$PWD/submodules/z3/build/python; cd doc/examples/quic/quic_tests/server_tests; ivy_check diagnose=true show_compiled=false pedantic=true isolate_mode=test isolate=this quic_server_test_stream.ivy; cd ../../../../..
# cp lib/libz3.so submodules/z3/build/python/z3; export IVY_INCLUDE_PATH=IVY_INCLUDE_PATH:/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7;export Z3_LIBRARY_DIRS=$PWD/submodules/z3/build; export Z3_LIBRARY_PATH=$PWD/submodules/z3/build; export PATH=$PATH:$PWD/submodules/z3/build; export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$PWD/submodules/z3/build; export PYTHONPATH=$PYTHONPATH:$PWD/submodules/z3/build/python; cd doc/examples/quic/quic_tests/server_tests; ivy_check diagnose=true show_compiled=false pedantic=true trusted=false  trace=true isolate_mode=test isolate=this quic_server_test_stream.ivy; cd ../../../../..

# ptls_openssl_secp256r1
TESTS_SERVER = {
    # key = category of test
    "global_test": [
        'quic_server_test_stream'
        #'quic_server_test_stream_migration'
        # 'quic_server_test_max',
        # 'quic_server_test_accept_maxdata',
        # 'quic_server_test_reset_stream',
        # 'quic_server_test_connection_close',
        # 'quic_server_test_stop_sending',
    ],
    "unknow_test": [
        'quic_server_test_unknown',
        'quic_server_test_unknown_tp',
    ],
    "tp_error_test": [
        'quic_server_test_double_tp_error',
        'quic_server_test_tp_error',
        'quic_server_test_tp_acticoid_error',
        'quic_server_test_no_icid',
    ],
    "prot_error_test": [
        'quic_server_test_token_error',
        'quic_server_test_new_token_error',
        'quic_server_test_handshake_done_error',
        'quic_server_test_newconnectionid_error',
        'quic_server_test_max_limit_error',
    ],
    "field_error_test": [
        'quic_server_test_blocked_streams_maxstream_error',
        'quic_server_test_retirecoid_error',
        'quic_server_test_stream_limit_error',
        'quic_server_test_newcoid_length_error',
        'quic_server_test_newcoid_rtp_error',
        'quic_server_test_max_error',
    ],
    "0rtt_test": [
        "quic_server_test_0rtt"
    ],
    "retry_test": [
        "quic_server_test_retry"
    ],
    "vn_test": [
        "quic_server_test_version_negociation"
    ],
    "attacks_test": [
        # "quic_server_test_stream_vuln", #  picoquic draft 28
        # 'quic_server_test_retry_reuse_key' # double clients: picoquic draft 28 -> logs directly in implem folder + check draft tp code
        # "quic_server_test_ncid_quant_vulne" # quant draft 29
        "quic_server_test_mim"
        #"quic_server_test_attacker_reflection"
    ],
    "tp_ext": [
        "quic_server_test_version_negociation_ext",
        "quic_server_test_ext_min_ack_delay"
    ],
    "recover_test": [
        "quic_server_test_deadconnection",
        "quic_server_test_deadconnection_no_sleep",
        "quic_server_test_deadconnection_signal",
        "quic_server_test_deadconnection_no_sleep_migration",
        "quic_server_test_deadconnection_no_sleep_validation",
        "quic_server_test_timeout",
        "quic_server_test_timeout_no_sleep",
        "quic_server_test_timeout_no_sleep_migration",
        "quic_server_test_timeout_no_sleep_validation",
        "quic_server_test_loss_recovery",
        "quic_server_test_congestion_control",
        "ping_server_test"
    ]
}

TESTS_MIM = {
    "attacks_test": [
        "quic_mim_test_forward"
    ]
}

TESTS_CUSTOM = []

# ptls_openssl_x25519
TESTS_CLIENT = {
    "global_test": [
        'quic_client_test_max',
        # 'quic_client_test_accept_maxdata',
        'quic_client_test_ext_min_ack_delay',
    ],
    "unknow_test": [
        'quic_client_test_unknown',
        'quic_client_test_unknown_tp',
    ],
    "tp_error_test": [
        'quic_client_test_double_tp_error',
        'quic_client_test_tp_error',
        'quic_client_test_tp_acticoid_error',
        'quic_client_test_no_ocid',
    ],
    "prot_error_test": [
        'quic_client_test_new_token_error',
        'quic_client_test_max_limit_error',
    ],
    "field_error_test": [
        'quic_client_test_blocked_streams_maxstream_error',
        'quic_client_test_retirecoid_error',
    ],
    "0rtt_test": [
        "quic_client_test_0rtt"
        # "quic_client_test_0rtt_invalid"
    ],
    "address_validation": [
        "quic_client_test_new_token_address_validation",
        "quic_client_test_0rtt_add_val"
    ],
    "retry_test": [
        "quic_client_test_retry"
    ],
    "vn_test": [
        "quic_client_test_version_negociation"
    ],
    "attacks_test": [
        # "quic_client_test_version_negociation_mim_modify",
        # "quic_client_test_version_negociation_mim_forge",
        "quic_client_test_mim"
        # "quic_client_test_mim_modify",
        # "quic_client_test_0rtt_mim_replay"

    ],
    "recover_test": [
        "quic_client_test_deadconnection",
        "quic_client_test_deadconnection_signal",
        "quic_client_test_deadconnection_no_sleep",
        "quic_client_test_deadconnection_no_sleep_validation",
        "quic_client_test_timeout",
        "quic_client_test_timeout_no_sleep",
        "quic_client_test_timeout_no_sleep_validation",
        "quic_client_test_loss_recovery",
        "quic_client_test_congestion_control",
        "ping_client_test"
    ]
}
# TODO make interface dynamic

# TODO automatic in compose
# TODO seems useless
IMPLEMENTATIONS_PORTS = {
    "ivy":49150,
    "quant":49152,
    "quant-vuln":49153,
    "picoquic":49154,
    "picoquic-vuln":49155,
    "mvfst":49156,
    "lsquic":49157,
    "lsquic-vuln":49158,
    "quic-go":49159,
    "aioquic":49160,
    "quinn":49161,
    "quiche":49162,
}


IMPLEMENTATIONS = {
    # Server:
    # Client: sometimes decryption problem
    # "quant":[ # NOT available in RFC9000 06/06/22
    #     [QUIC_DIR, IMPLEM_DIR + '/quant/Debug/bin/server -i implem -x 1000 -d . -o -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant -l '+SOURCE_DIR +'/tls-keys/secret.log'],
    #     [QUIC_DIR, IMPLEM_DIR + '/quant/Debug/bin/client -e 0xVERSION -i implem -c false -r 10 -s '+SOURCE_DIR +'/tickets/ticket.bin -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://10.0.0.1:4443/index.html']
    # ],
    # # Server: quic_server_test_ncid_quant_vulne
    # # Client: quic_client_test_version_negociation_mim 
    # "quant-vuln":[
    #     [QUIC_DIR, IMPLEM_DIR + '/quant/Debug/bin/server -x 1000 -d . -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant-vuln -l '+SOURCE_DIR +'/tls-keys/secret.log'],
    #     [QUIC_DIR, IMPLEM_DIR + '/quant/Debug/bin/client -e VERSION -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant-vuln -t 3600 -v 5  https://10.0.0.1:4443/index.html']
    # ],
    # # Server:
    # # Client:
    # "picoquic":[
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -e implem -a ALPN -l - -D -L -q '+SOURCE_DIR +'/qlogs/picoquic'],
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -n servername -e implem -a ALPN -T '+SOURCE_DIR +'/tickets/ticket.bin -v VERSION -l - -D -L  10.0.0.1 4443']
    # ],
    # Server:
    # Client:
    "picoquic-shadow":[
        [IMPLEM_DIR + '/picoquic','./picoquicdemo -e implem -a ALPN -l - -D -L -q '+SOURCE_DIR +'/qlogs/picoquic'],
        [IMPLEM_DIR + '/picoquic','./picoquicdemo -n servername -e implem -a ALPN -T '+SOURCE_DIR +'/tickets/ticket.bin -v VERSION -l - -D -L  10.0.0.1 4443']
    ],
    # # Server:
    # # Client:
    # "picoquic-old-shadow":[
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -e implem -a ALPN -l - -D -L -q '+SOURCE_DIR +'/qlogs/picoquic'],
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -n servername -e implem -a ALPN -T '+SOURCE_DIR +'/tickets/ticket.bin -v VERSION -l - -D -L  10.0.0.1 4443']
    # ],
    # # Server:
    # # Client:
    # "picoquic-shadow-bad":[
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -e implem -a ALPN -l - -D -L -q '+SOURCE_DIR +'/qlogs/picoquic'],
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -n servername -e implem -a ALPN -T '+SOURCE_DIR +'/tickets/ticket.bin -v VERSION -l - -D -L  10.0.0.1 4443']
    # ],
    # # picoquic-no-retransmission-shadow
    # "picoquic-no-retransmission-shadow":[
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -e implem -a ALPN -l - -D -L -q '+SOURCE_DIR +'/qlogs/picoquic'],
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -n servername -e implem -a ALPN -T '+SOURCE_DIR +'/tickets/ticket.bin -v VERSION -l - -D -L  10.0.0.1 4443']
    # ],
    # # Server: quic_server_test_retry_reuse_key
    # # Client:
    # "picoquic-vuln":[
    #     [IMPLEM_DIR + '/picoquic-vuln','./picoquicdemo -D -L'],
    #     [""]
    # ],
    # Server: 
    # Client:
    "ping-pong":[
        [IMPLEM_DIR + '/miniP_server','./miniP_server -i 11.0.0.2 -p "4443"'],
        [IMPLEM_DIR + '/miniP_server','./miniP_client -i 11.0.0.1 -p "4987"']
    ],
    # "ping-pong-flaky":[
    #     [IMPLEM_DIR + '/miniP_server','./miniP_server -i 11.0.0.2 -p "4443"'],
    #     [IMPLEM_DIR + '/miniP_server','./miniP_client -i 11.0.0.1 -p "4987"']
    # ],
    # "ping-pong-fail":[
    #     [IMPLEM_DIR + '/miniP_server','./miniP_server -i 11.0.0.2 -p "4443"'],
    #     [IMPLEM_DIR + '/miniP_server','./miniP_client -i 11.0.0.1 -p "4987"']
    # ],
    # Server:
    # Client:
    # "pquic":[
    #     [SOURCE_DIR + '/pquic','./picoquicdemo -D -L -l - '],
    #     [""]
    # ],
    # Server: Not working anymore (installation) tocheck => ok now, set 1 cpu to compile + TODO configure 0rtt, no session ticket -> OKK -> need shim local var
    # Client: Not working: unknown reason (ok now, vn condition problem) (todo 0rtt) -> check why few packet are sent -> +- ok now, somtime 0rtt done, sometime not
    # "mvfst":[
    #     [IMPLEM_DIR + '/mvfst/_build/build/quic/samples/','./echo -mode=server -host=10.0.0.3 -port=4443  -v=10  '],
    #     [IMPLEM_DIR + '/mvfst/_build/build/quic/samples/','./echo -mode=client -host="10.0.0.1" -port=4443  -v=10 -stop_logging_if_full_disk']
    # ],
    # # Server: Internal error
    # # Client:
    # "lsquic":[
    #     [IMPLEM_DIR + '/lsquic/bin/','./http_server -c www.example.org/,'+SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/leaf_cert.pem,'+SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/leaf_cert.key -Q ALPN -D -s 127.0.0.1:4443 -l event=debug,engine=debug -o version=VERSION -G '+SOURCE_DIR +'/tls-keys/'],
    #     [IMPLEM_DIR + '/lsquic/bin/','./http_client -0 '+SOURCE_DIR +'/tickets/ticket.bin -4 -Q ALPN -R 10 -w 7 -r 7 -s 10.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1 -o version=VERSION -o scid_len=8']
    # ],
    # # Server: Internal error
    # # Client:
    # "lsquic-vuln":[
    #     [IMPLEM_DIR + '/lsquic-vuln/bin/','./http_server -c www.example.org/,'+SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/leaf_cert.pem,'+SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/leaf_cert.key -Q ALPN -D -s 127.0.0.1:4443 -l event=debug,engine=debug -o version=VERSION -G '+SOURCE_DIR +'/tls-keys/'],
    #     [IMPLEM_DIR + '/lsquic-vuln/bin/','./http_client -0 '+SOURCE_DIR +'/tickets/ticket.bin -4 -Q ALPN -R 10 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1 -o version=VERSION -o scid_len=8']
    # ],
    # # Server: error -> ok cert pb  + 0rtt need app_close and not co_close -> shim global var bugs
    # # Client: 0rtt (todo -> ok now) + set max cid  (ok now)
    # "quic-go":[
    #     [IMPLEM_DIR + '/quic-go/server/','./server -c '+SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/cert.pem -k '+SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/priv.key -p 4443 127.0.0.1'],
    #     [IMPLEM_DIR + '/quic-go/client/','./client -X '+SOURCE_DIR +'/tls-keys/secret.log -P -v 127.0.0.1 4443 ']
    # ],
    # # Server:
    # # Client:
    # "aioquic":[
    #     [IMPLEM_DIR + '/aioquic/','python3.9 examples/http3_server.py --quic-log '+SOURCE_DIR +'/qlogs/aioquic --certificate '+SOURCE_DIR +'/quic-implementations/aioquic/tests/ssl_cert.pem --private-key '+SOURCE_DIR +'/quic-implementations/aioquic/tests/ssl_key.pem  -v -v --host 127.0.0.1 --port 4443 -l '+SOURCE_DIR +'/tls-keys/secret.log'],
    #     [IMPLEM_DIR + '/aioquic/','python3.9 examples/http3_client.py --zero-rtt -s '+SOURCE_DIR +'/tickets/ticket.bin -l '+SOURCE_DIR +'/tls-keys/secret.log -v -q '+SOURCE_DIR +'/qlogs/aioquic/ --ca-certs tests/pycacert.pem -i --insecure --legacy-http https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html']
    # ],
    # # Server: cid 0x0 & 0x1 + comment 1 line in quic_frame
    # # Client: Not working: unknown reason (ok now, check alpn + ignore cert) -> no co_close ? + 0rtt todo +- ok now
    # "quinn":[ # TODO RUST_LOG="debug" RUST_BACKTRACE=1  server
    #     [IMPLEM_DIR + '/quinn/','cargo run -vv --example server '+SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/index.html --listen 127.0.0.1:4443'],
    #     [IMPLEM_DIR + '/quinn/','cargo run -vv --example client https://10.0.0.1:4443/index.html --keylog']
    # ],
    # # Server: 0rtt not working: 2 session ticket with unknown extension (ok now)
    # # Client: 0rtt client not implemented in v0.0.7 -> update to 0.9.0  +- ok now, somtime 0rtt done, sometime not (check other version)
    # "quiche":[ # TODO RUST_LOG="debug" RUST_BACKTRACE=1 
    #     [IMPLEM_DIR + '/quiche/','cargo run --bin quiche-server --  --root . --no-grease --cert '+ SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/cert.pem --early-data --dump-packets '+SOURCE_DIR +'/qlogs/quiche/dump_packet.txt --key '+SOURCE_DIR +'/Protocols-Ivy/doc/examples/quic/priv.key --no-retry --listen 127.0.0.1:4443' ],
    #     [IMPLEM_DIR + '/quiche/','cargo run --bin quiche-client -- https://10.0.0.1:4443/index.html --dump-json --session-file '+SOURCE_DIR +'/tickets/ticket.bin --wire-version VERSION --no-verify --body / -n 5']
    # ],
    # Server:
    # Client:
    # "chromium":[
    #     [IMPLEM_DIR + '/chromium/src','./out/Default/quic_server --port=4443 --quic_response_cache_dir=/tmp/quic-data/www.example.org   --certificate_file=net/tools/quic/certs/out/leaf_cert.pem --key_file=net/tools/quic/certs/out/leaf_cert.pkcs8 --quic-enable-version-99  --generate_dynamic_responses --allow_unknown_root_cert --v=1'],
    #     [IMPLEM_DIR + '/chromium/src','./out/Default/quic_client --host=127.0.0.1 --port=6121 --disable_certificate_verification  https://www.example.org/ --v=1 --quic_versions=h3-23']
    # ],
    # TODO quickly + minq
}
