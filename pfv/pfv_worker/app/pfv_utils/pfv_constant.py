import os

SOURCE_DIR = os.getcwd()
IMPLEM_DIR = SOURCE_DIR + "/app/implementations/$PROT-implementations/"
RESULT_DIR = SOURCE_DIR + "/app/pfv-ivy/protocol-testing/$PROT/test/"
IVY_DIR = SOURCE_DIR + "/app/pfv-ivy/"
MODEL_DIR = SOURCE_DIR + "/app/pfv-ivy/protocol-testing/"


ENV_VAR = {
    "IVY_INCLUDE_PATH": "${IVY_INCLUDE_PATH}:/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7",
    "Z3_LIBRARY_DIRS": IVY_DIR + "/submodules/z3/build",
    "Z3_LIBRARY_PATH": IVY_DIR + "/submodules/z3/build;",
    "LD_LIBRARY_PATH": "${LD_LIBRARY_PATH}:" + IVY_DIR + "/submodules/z3/build",
    "PROOTPATH": SOURCE_DIR,
    "PYTHONPATH": "${PYTHONPATH}:"
    + IMPLEM_DIR
    + "/aioquic:"
    + IVY_DIR
    + "/submodules/z3/build/python",
    "PATH": os.getenv("PATH")
    + ":/go/bin:"
    + IVY_DIR
    + "/submodules/z3/build",  # "/go/bin:${"+ os.getenv('PATH') +"}", #
}


P_ENV_VAR = {
    "quic": {
        "ZRTT_SSLKEYLOGFILE": SOURCE_DIR
        + "/pfv-ivy/doc/examples/quic/last_tls_key.txt",
        "RETRY_TOKEN_FILE": SOURCE_DIR
        + "/pfv-ivy/doc/examples/quic/last_retry_token.txt",
        "NEW_TOKEN_FILE": SOURCE_DIR + "/pfv-ivy/doc/examples/quic/last_new_token.txt",
        "ENCRYPT_TICKET_FILE": SOURCE_DIR
        + "/pfv-ivy/doc/examples/quic/last_encrypt_session_ticket.txt",
        "SESSION_TICKET_FILE": SOURCE_DIR
        + "/pfv-ivy/doc/examples/quic/last_session_ticket_cb.txt",
        "SAVED_PACKET": SOURCE_DIR + "/pfv-ivy/doc/examples/quic/saved_packet.txt",
        "initial_max_stream_id_bidi": SOURCE_DIR
        + "/pfv-ivy/doc/examples/quic/initial_max_stream_id_bidi.txt",
        "active_connection_id_limit": SOURCE_DIR
        + "/pfv-ivy/doc/examples/quic/active_connection_id_limit.txt",
        "initial_max_stream_data_bidi_local": SOURCE_DIR
        + "/pfv-ivy/doc/examples/quic/initial_max_stream_data_bidi_local.txt",
        "initial_max_stream_data_bidi_remote": SOURCE_DIR
        + "/pfv-ivy/doc/examples/quic/initial_max_stream_data_bidi_remote.txt",
        "initial_max_stream_data_uni": SOURCE_DIR
        + "/pfv-ivy/doc/examples/quic/initial_max_stream_data_uni.txt",
        "initial_max_data": SOURCE_DIR
        + "/pfv-ivy/doc/examples/quic/initial_max_data.txt",
        "INITIAL_VERSION": "1",
    },
    "bgp": {},
    "minip": {},
    "apt": {},
}
