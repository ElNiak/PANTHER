Finish config from:

IMPLEMENTATIONS = {
    # Server:
    # Client: sometimes decryption problem
    # quant:[ # NOT available in RFC9000 06/06/22
    #     [QUIC_DIR, IMPLEM_DIR + '/quant/Debug/bin/server -i implem -x 1000 -d . -o -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant -l '+SOURCE_DIR +'/tls-keys/secret.log'],
    #     [QUIC_DIR, IMPLEM_DIR + '/quant/Debug/bin/client -e 0xVERSION -i implem -c false -r 10 -s '+SOURCE_DIR +'/tickets/ticket.bin -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant -t 3600 -v 5  https://10.0.0.1:4443/index.html']
    # ],
    # # Server: quic_server_test_ncid_quant_vulne
    # # Client: quic_client_test_version_negociation_mim 
    # quant-vuln:[
    #     [QUIC_DIR, IMPLEM_DIR + '/quant/Debug/bin/server -x 1000 -d . -c leaf_cert.pem -k leaf_cert.key -p 4443 -t 3600 -v 5 -q '+SOURCE_DIR +'/qlogs/quant-vuln -l '+SOURCE_DIR +'/tls-keys/secret.log'],
    #     [QUIC_DIR, IMPLEM_DIR + '/quant/Debug/bin/client -e VERSION -c false -r 10 -l '+SOURCE_DIR +'/tls-keys/secret.log -q '+SOURCE_DIR +'/qlogs/quant-vuln -t 3600 -v 5  https://10.0.0.1:4443/index.html']
    # ],
    # # Server:
    # # Client:
    # picoquic:[
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -e implem -a ALPN -l - -D -L -q '+SOURCE_DIR +'/qlogs/picoquic'],
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -n servername -e implem -a ALPN -T '+SOURCE_DIR +'/tickets/ticket.bin -v VERSION -l - -D -L  10.0.0.1 4443']
    # ],
    # Server:
    # Client:
    picoquic-shadow:[
        [IMPLEM_DIR + '/picoquic','./picoquicdemo -e implem -a ALPN -l - -D -L -q '+SOURCE_DIR +'/qlogs/picoquic'],
        [IMPLEM_DIR + '/picoquic','./picoquicdemo -n servername -e implem -a ALPN -T '+SOURCE_DIR +'/tickets/ticket.bin -v VERSION -l - -D -L  10.0.0.1 4443']
    ],
    # # Server:
    # # Client:
    # picoquic-old-shadow:[
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -e implem -a ALPN -l - -D -L -q '+SOURCE_DIR +'/qlogs/picoquic'],
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -n servername -e implem -a ALPN -T '+SOURCE_DIR +'/tickets/ticket.bin -v VERSION -l - -D -L  10.0.0.1 4443']
    # ],
    # # Server:
    # # Client:
    # picoquic-shadow-bad:[
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -e implem -a ALPN -l - -D -L -q '+SOURCE_DIR +'/qlogs/picoquic'],
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -n servername -e implem -a ALPN -T '+SOURCE_DIR +'/tickets/ticket.bin -v VERSION -l - -D -L  10.0.0.1 4443']
    # ],
    # # picoquic-no-retransmission-shadow
    # picoquic-no-retransmission-shadow:[
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -e implem -a ALPN -l - -D -L -q '+SOURCE_DIR +'/qlogs/picoquic'],
    #     [IMPLEM_DIR + '/picoquic','./picoquicdemo -n servername -e implem -a ALPN -T '+SOURCE_DIR +'/tickets/ticket.bin -v VERSION -l - -D -L  10.0.0.1 4443']
    # ],
    # # Server: quic_server_test_retry_reuse_key
    # # Client:
    # picoquic-vuln:[
    #     [IMPLEM_DIR + '/picoquic-vuln','./picoquicdemo -D -L'],
    #     []
    # ],
    # Server: 
    # Client:
    ping-pong:[
        [IMPLEM_DIR + '/miniP_server','./miniP_server -i 11.0.0.2 -p 4443'],
        [IMPLEM_DIR + '/miniP_server','./miniP_client -i 11.0.0.1 -p 4987']
    ],
    # ping-pong-flaky:[
    #     [IMPLEM_DIR + '/miniP_server','./miniP_server -i 11.0.0.2 -p 4443'],
    #     [IMPLEM_DIR + '/miniP_server','./miniP_client -i 11.0.0.1 -p 4987']
    # ],
    # ping-pong-fail:[
    #     [IMPLEM_DIR + '/miniP_server','./miniP_server -i 11.0.0.2 -p 4443'],
    #     [IMPLEM_DIR + '/miniP_server','./miniP_client -i 11.0.0.1 -p 4987']
    # ],
    # Server:
    # Client:
    # pquic:[
    #     [SOURCE_DIR + '/pquic','./picoquicdemo -D -L -l - '],
    #     []
    # ],
    # Server: Not working anymore (installation) tocheck => ok now, set 1 cpu to compile + TODO configure 0rtt, no session ticket -> OKK -> need shim local var
    # Client: Not working: unknown reason (ok now, vn condition problem) (todo 0rtt) -> check why few packet are sent -> +- ok now, somtime 0rtt done, sometime not
    # mvfst:[
    #     [IMPLEM_DIR + '/mvfst/_build/build/quic/samples/','./echo -mode=server -host=10.0.0.3 -port=4443  -v=10  '],
    #     [IMPLEM_DIR + '/mvfst/_build/build/quic/samples/','./echo -mode=client -host=10.0.0.1 -port=4443  -v=10 -stop_logging_if_full_disk']
    # ],
    # # Server: Internal error
    # # Client:
    # lsquic:[
    #     [IMPLEM_DIR + '/lsquic/bin/','./http_server -c www.example.org/,'+SOURCE_DIR +'/QUIC-Ivy-Attacker/doc/examples/quic/leaf_cert.pem,'+SOURCE_DIR +'/QUIC-Ivy-Attacker/doc/examples/quic/leaf_cert.key -Q ALPN -D -s 127.0.0.1:4443 -l event=debug,engine=debug -o version=VERSION -G '+SOURCE_DIR +'/tls-keys/'],
    #     [IMPLEM_DIR + '/lsquic/bin/','./http_client -0 '+SOURCE_DIR +'/tickets/ticket.bin -4 -Q ALPN -R 10 -w 7 -r 7 -s 10.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1 -o version=VERSION -o scid_len=8']
    # ],
    # # Server: Internal error
    # # Client:
    # lsquic-vuln:[
    #     [IMPLEM_DIR + '/lsquic-vuln/bin/','./http_server -c www.example.org/,'+SOURCE_DIR +'/QUIC-Ivy-Attacker/doc/examples/quic/leaf_cert.pem,'+SOURCE_DIR +'/QUIC-Ivy-Attacker/doc/examples/quic/leaf_cert.key -Q ALPN -D -s 127.0.0.1:4443 -l event=debug,engine=debug -o version=VERSION -G '+SOURCE_DIR +'/tls-keys/'],
    #     [IMPLEM_DIR + '/lsquic-vuln/bin/','./http_client -0 '+SOURCE_DIR +'/tickets/ticket.bin -4 -Q ALPN -R 10 -w 7 -r 7 -s 127.0.0.1:4443 -t -l event=debug,engine=debug -p /1.html /2.html /3.html /4.html /5.html /6.html /7.html -H 127.0.0.1 -o version=VERSION -o scid_len=8']
    # ],
    # # Server: error -> ok cert pb  + 0rtt need app_close and not co_close -> shim global var bugs
    # # Client: 0rtt (todo -> ok now) + set max cid  (ok now)
    # quic-go:[
    #     [IMPLEM_DIR + '/quic-go/server/','./server -c '+SOURCE_DIR +'/QUIC-Ivy-Attacker/doc/examples/quic/cert.pem -k '+SOURCE_DIR +'/QUIC-Ivy-Attacker/doc/examples/quic/priv.key -p 4443 127.0.0.1'],
    #     [IMPLEM_DIR + '/quic-go/client/','./client -X '+SOURCE_DIR +'/tls-keys/secret.log -P -v 127.0.0.1 4443 ']
    # ],
    # # Server:
    # # Client:
    # aioquic:[
    #     [IMPLEM_DIR + '/aioquic/','python3.9 examples/http3_server.py --quic-log '+SOURCE_DIR +'/qlogs/aioquic --certificate '+SOURCE_DIR +'/quic-implementations/aioquic/tests/ssl_cert.pem --private-key '+SOURCE_DIR +'/quic-implementations/aioquic/tests/ssl_key.pem  -v -v --host 127.0.0.1 --port 4443 -l '+SOURCE_DIR +'/tls-keys/secret.log'],
    #     [IMPLEM_DIR + '/aioquic/','python3.9 examples/http3_client.py --zero-rtt -s '+SOURCE_DIR +'/tickets/ticket.bin -l '+SOURCE_DIR +'/tls-keys/secret.log -v -q '+SOURCE_DIR +'/qlogs/aioquic/ --ca-certs tests/pycacert.pem -i --insecure --legacy-http https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html https://10.0.0.1:4443/index.html']
    # ],
    # # Server: cid 0x0 & 0x1 + comment 1 line in quic_frame
    # # Client: Not working: unknown reason (ok now, check alpn + ignore cert) -> no co_close ? + 0rtt todo +- ok now
    # quinn:[ # TODO RUST_LOG=debug RUST_BACKTRACE=1  server
    #     [IMPLEM_DIR + '/quinn/','cargo run -vv --example server '+SOURCE_DIR +'/QUIC-Ivy-Attacker/doc/examples/quic/index.html --listen 127.0.0.1:4443'],
    #     [IMPLEM_DIR + '/quinn/','cargo run -vv --example client https://10.0.0.1:4443/index.html --keylog']
    # ],
    # # Server: 0rtt not working: 2 session ticket with unknown extension (ok now)
    # # Client: 0rtt client not implemented in v0.0.7 -> update to 0.9.0  +- ok now, somtime 0rtt done, sometime not (check other version)
    # quiche:[ # TODO RUST_LOG=debug RUST_BACKTRACE=1 
    #     [IMPLEM_DIR + '/quiche/','cargo run --bin quiche-server --  --root . --no-grease --cert '+ SOURCE_DIR +'/QUIC-Ivy-Attacker/doc/examples/quic/cert.pem --early-data --dump-packets '+SOURCE_DIR +'/qlogs/quiche/dump_packet.txt --key '+SOURCE_DIR +'/QUIC-Ivy-Attacker/doc/examples/quic/priv.key --no-retry --listen 127.0.0.1:4443' ],
    #     [IMPLEM_DIR + '/quiche/','cargo run --bin quiche-client -- https://10.0.0.1:4443/index.html --dump-json --session-file '+SOURCE_DIR +'/tickets/ticket.bin --wire-version VERSION --no-verify --body / -n 5']
    # ],
    # Server:
    # Client:
    # chromium:[
    #     [IMPLEM_DIR + '/chromium/src','./out/Default/quic_server --port=4443 --quic_response_cache_dir=/tmp/quic-data/www.example.org   --certificate_file=net/tools/quic/certs/out/leaf_cert.pem --key_file=net/tools/quic/certs/out/leaf_cert.pkcs8 --quic-enable-version-99  --generate_dynamic_responses --allow_unknown_root_cert --v=1'],
    #     [IMPLEM_DIR + '/chromium/src','./out/Default/quic_client --host=127.0.0.1 --port=6121 --disable_certificate_verification  https://www.example.org/ --v=1 --quic_versions=h3-23']
    # ],
    # TODO quickly + minq
}
