import os

SOURCE_DIR =  os.getcwd()
IMPLEM_DIR =  SOURCE_DIR + '/quic-implementations'
QUIC_DIR   =  SOURCE_DIR + '/QUIC-Ivy/doc/examples/quic/'
RESULT_DIR =  SOURCE_DIR + '/QUIC-Ivy/doc/examples/quic/test/'

ENV_VAR = {
    "PROOTPATH": SOURCE_DIR,
    "PATH": os.getenv('PATH') + ":/go/bin", # "/go/bin:${"+ os.getenv('PATH') +"}", #
    "ZRTT_SSLKEYLOGFILE": SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/last_tls_key.txt",
    "RETRY_TOKEN_FILE": SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/last_retry_token.txt",
    "NEW_TOKEN_FILE": SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/last_new_token.txt",
    "ENCRYPT_TICKET_FILE": SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/last_encrypt_session_ticket.txt",
    "SESSION_TICKET_FILE": SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/last_session_ticket_cb.txt",
    "SAVED_PACKET": SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/saved_packet.txt",
    
    # "max_idle_timeout":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/max_idle_timeout.txt",
    # "max_ack_delay":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/max_ack_delay.txt",
    # "max_udp_payload_size":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/max_udp_payload_size.txt",
    # "max_datagram_frame_size":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/max_datagram_frame_size.txt",
    # "max_stream_data_bidi_local":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/max_stream_data_bidi_local.txt",
    # "max_stream_data_bidi_remote":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/max_stream_data_bidi_remote.txt",
    # "max_stream_data_uni":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/max_stream_data_uni.txt",
    "initial_max_stream_id_bidi":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/initial_max_stream_id_bidi.txt",
    # "initial_max_stream_id_uni":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/initial_max_stream_id_uni.txt",
    # "max_data":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/max_data.txt",
    # "max_bidi_streams":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/max_bidi_streams.txt",
    # "max_uni_streams":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/max_uni_streams.txt",
    
    "active_connection_id_limit":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/active_connection_id_limit.txt",
    "initial_max_stream_data_bidi_local":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/initial_max_stream_data_bidi_local.txt",
    "initial_max_stream_data_bidi_remote":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/initial_max_stream_data_bidi_remote.txt",
    "initial_max_stream_data_uni":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/initial_max_stream_data_uni.txt",   
    "initial_max_data":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/initial_max_data.txt",
    
    # "initial_max_bidi_streams":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/initial_max_bidi_streams.txt",
    # "initial_max_uni_streams":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/initial_max_uni_streams.txt",
    # "max_packet_size":  SOURCE_DIR + "/QUIC-Ivy/doc/examples/quic/max_packet_size.txt",
}


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
        "quic_server_test_attacker_reflection"
    ],
    "tp_ext": [
        "quic_server_test_version_negociation_ext",
        "quic_server_test_ext_min_ack_delay"
    ]
}

TESTS_MIM = {
    "attacks_test": [
        "quic_mim_test_forward"
    ]
}

# ptls_openssl_x25519
TESTS_CLIENT = {
    "global_test": [
        'quic_client_test_max'
        # 'quic_client_test_accept_maxdata',
        # 'quic_client_test_ext_min_ack_delay',
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
        "quic_client_test_version_negociation_mim_modify"
        # "quic_client_test_version_negociation_mim_forge",
        # "quic_client_test_mim"
        # "quic_client_test_mim_modify"
       # "quic_client_test_0rtt_mim_replay"

    ],
}
# TODO make interface dynamic

IMPLEMENTATIONS = {
    # Server:
    # Client: sometimes decryption problem
    "quant":[ # NOT available in RFC9000 06/06/22
        [QUIC_DIR, IMPLEM_DIR + '/quant/Debug/bin/server -i n1.0 -x 1000 -d . -o -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant -l '+SOURCE_DIR +'/tls-keys/secret.log'],
        [QUIC_DIR, IMPLEM_DIR + '/quant/Debug/bin/client -e 0xff00001d -i n1.0 -c false -r 10 -s '+SOURCE_DIR +'/tickets/ticket.bin -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://10.0.0.1:4443/index.html']
    ],
    # Server: quic_server_test_ncid_quant_vulne
    # Client: quic_client_test_version_negociation_mim 
    "quant-vuln":[
        [QUIC_DIR, IMPLEM_DIR + '/quant/Debug/bin/server -x 1000 -d . -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant-vuln -l '+SOURCE_DIR +'/tls-keys/secret.log'],
        [QUIC_DIR, IMPLEM_DIR + '/quant/Debug/bin/client -e 0xff00001c -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant-vuln -t 3600 -v 5  https://10.0.0.1:4443/index.html']
    ],
    # Server:
    # Client:
    "picoquic":[
        [IMPLEM_DIR + '/picoquic','./picoquicdemo -e n1.0 -a hq-29 -l - -D -L -q '+SOURCE_DIR +'/qlogs/picoquic'],
        [IMPLEM_DIR + '/picoquic','./picoquicdemo -n servername -e n1.0 -a hq-29 -T '+SOURCE_DIR +'/tickets/ticket.bin -v ff00001d -l - -D -L  10.0.0.1 4443']
    ],
    # Server: quic_server_test_retry_reuse_key
    # Client:
    "picoquic-vuln":[
        [IMPLEM_DIR + '/picoquic-vuln','./picoquicdemo -D -L'],
        [""]
    ],
    # Server:
    # Client:
    # "pquic":[
    #     [SOURCE_DIR + '/pquic','./picoquicdemo -D -L -l - '],
    #     [""]
    # ],
    # Server: Not working anymore (installation) tocheck => ok now, set 1 cpu to compile + TODO configure 0rtt, no session ticket -> OKK -> need shim local var
    # Client: Not working: unknown reason (ok now, vn condition problem) (todo 0rtt) -> check why few packet are sent -> +- ok now, somtime 0rtt done, sometime not
    "mvfst":[
        [IMPLEM_DIR + '/mvfst/_build/build/quic/samples/','./echo -mode=server -host=10.0.0.2 -port=4443  -v=10  '],
        [IMPLEM_DIR + '/mvfst/_build/build/quic/samples/','./echo -mode=client -host="10.0.0.1" -port=4443  -v=10 -stop_logging_if_full_disk']
    ],
    # Server: Internal error
    # Client:
    "lsquic":[
        [IMPLEM_DIR + '/lsquic/bin/','./http_server -c www.example.org/,'+SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/leaf_cert.pem,'+SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/leaf_cert.key -Q hq-interop -D -s 127.0.0.1:4443 -l event=debug,engine=debug -o version=00000001 -G '+SOURCE_DIR +'/tls-keys/'],
        [IMPLEM_DIR + '/lsquic/bin/','./http_client -0 '+SOURCE_DIR +'/tickets/ticket.bin -4 -Q hq-interop -R 10 -w 7 -r 7 -s 10.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1 -o version=00000001 -o scid_len=8']
    ],
    # Server: Internal error
    # Client:
    "lsquic-vuln":[
        [IMPLEM_DIR + '/lsquic-vuln/bin/','./http_server -c www.example.org/,'+SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/leaf_cert.pem,'+SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/leaf_cert.key -Q hq-interop -D -s 127.0.0.1:4443 -l event=debug,engine=debug -o version=ff00001d -G '+SOURCE_DIR +'/tls-keys/'],
        [IMPLEM_DIR + '/lsquic-vuln/bin/','./http_client -0 '+SOURCE_DIR +'/tickets/ticket.bin -4 -Q hq-29 -R 10 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1 -o version=ff00001d -o scid_len=8']
    ],
    # Server: error -> ok cert pb  + 0rtt need app_close and not co_close -> shim global var bugs
    # Client: 0rtt (todo -> ok now) + set max cid  (ok now)
    "quic-go":[
        [IMPLEM_DIR + '/quic-go/server/','./server -c '+SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/cert.pem -k '+SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/priv.key -p 4443 127.0.0.1'],
        [IMPLEM_DIR + '/quic-go/client/','./client -X '+SOURCE_DIR +'/tls-keys/secret.log -P -v 127.0.0.1 4443 ']
    ],
    # Server:
    # Client:
    "aioquic":[
        [IMPLEM_DIR + '/aioquic/','python3.9 examples/http3_server.py --quic-log '+SOURCE_DIR +'/qlogs/aioquic --certificate '+SOURCE_DIR +'/quic-implementations/aioquic/tests/ssl_cert.pem --private-key '+SOURCE_DIR +'/quic-implementations/aioquic/tests/ssl_key.pem  -v -v --host 127.0.0.1 --port 4443 -l '+SOURCE_DIR +'/tls-keys/secret.log'],
        [IMPLEM_DIR + '/aioquic/','python3.9 examples/http3_client.py --zero-rtt -s '+SOURCE_DIR +'/tickets/ticket.bin -l '+SOURCE_DIR +'/tls-keys/secret.log -v -q '+SOURCE_DIR +'/qlogs/aioquic/ --ca-certs tests/pycacert.pem -i --insecure --legacy-http https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html']
    ],
    # Server: cid 0x0 & 0x1 + comment 1 line in quic_frame
    # Client: Not working: unknown reason (ok now, check alpn + ignore cert) -> no co_close ? + 0rtt todo +- ok now
    "quinn":[ # TODO RUST_LOG="debug" RUST_BACKTRACE=1  server
        [IMPLEM_DIR + '/quinn/','cargo run -vv --example server '+SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/index.html --listen 127.0.0.1:4443'],
        [IMPLEM_DIR + '/quinn/','cargo run -vv --example client https://10.0.0.1:4443/index.html --keylog']
    ],
    # Server: 0rtt not working: 2 session ticket with unknown extension (ok now)
    # Client: 0rtt client not implemented in v0.0.7 -> update to 0.9.0  +- ok now, somtime 0rtt done, sometime not (check other version)
    "quiche":[ # TODO RUST_LOG="debug" RUST_BACKTRACE=1 
        [IMPLEM_DIR + '/quiche/','cargo run --bin quiche-server --  --root . --no-grease --cert '+ SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/cert.pem --early-data --dump-packets '+SOURCE_DIR +'/qlogs/quiche/dump_packet.txt --key '+SOURCE_DIR +'/QUIC-Ivy/doc/examples/quic/priv.key --no-retry --listen 127.0.0.1:4443' ],
        [IMPLEM_DIR + '/quiche/','cargo run --bin quiche-client -- https://10.0.0.1:4443/index.html --dump-json --session-file '+SOURCE_DIR +'/tickets/ticket.bin --wire-version 00000001 --no-verify --body / -n 5']
    ],
    # Server:
    # Client:
    # "chromium":[
    #     [IMPLEM_DIR + '/chromium/src','./out/Default/quic_server --port=4443 --quic_response_cache_dir=/tmp/quic-data/www.example.org   --certificate_file=net/tools/quic/certs/out/leaf_cert.pem --key_file=net/tools/quic/certs/out/leaf_cert.pkcs8 --quic-enable-version-99  --generate_dynamic_responses --allow_unknown_root_cert --v=1'],
    #     [IMPLEM_DIR + '/chromium/src','./out/Default/quic_client --host=127.0.0.1 --port=6121 --disable_certificate_verification  https://www.example.org/ --v=1 --quic_versions=h3-23']
    # ],
    # TODO quickly + minq
}
