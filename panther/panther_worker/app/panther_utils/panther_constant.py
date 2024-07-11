import os
import logging
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

logging.basicConfig(level=logging.INFO)

SOURCE_DIR = "/app"
IMPLEM_DIR = os.path.join(SOURCE_DIR, "implementations", "$PROT-implementations")
RESULT_DIR = os.path.join(
    SOURCE_DIR, "panther-ivy", "protocol-testing", "$PROT", "test"
)
IVY_DIR = os.path.join(SOURCE_DIR, "panther-ivy")

# Ivy related
IVY_INCLUDE_PATH = os.path.join(SOURCE_DIR, "panther-ivy", "ivy", "include", "1.7")
MODEL_DIR = os.path.join(SOURCE_DIR, "panther-ivy", "protocol-testing")

# QUIC related
TLS_KEY_PATH = os.path.join(SOURCE_DIR, "tls-keys")
QUIC_TICKET_PATH = os.path.join(SOURCE_DIR, "tickets")
QLOGS_PATH = os.path.join(SOURCE_DIR, "qlogs")

logging.info(f"SOURCE_DIR: {SOURCE_DIR}")
logging.info(f"IMPLEM_DIR: {IMPLEM_DIR}")
logging.info(f"RESULT_DIR: {RESULT_DIR}")
logging.info(f"IVY_DIR: {IVY_DIR}")
logging.info(f"MODEL_DIR: {MODEL_DIR}")
logging.info(f"IVY_INCLUDE_PATH: {IVY_INCLUDE_PATH}")
logging.info(f"TLS_KEY_PATH: {TLS_KEY_PATH}")
logging.info(f"QUIC_TICKET_PATH: {QUIC_TICKET_PATH}")
logging.info(f"QLOGS_PATH: {QLOGS_PATH}")

ENV_VAR = {
    "IVY_INCLUDE_PATH": "${IVY_INCLUDE_PATH}:/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7",
    "Z3_LIBRARY_DIRS": IVY_DIR + "/submodules/z3/build",
    "Z3_LIBRARY_PATH": IVY_DIR + "/submodules/z3/build;",
    "LD_LIBRARY_PATH": "${LD_LIBRARY_PATH}:" + IVY_DIR + "/submodules/z3/build",
    "PROOTPATH": SOURCE_DIR,
    "PYTHONPATH": "${PYTHONPATH}:/app/implementations/quic-implementations/aioquic/src/:"
    + IVY_DIR
    + "/submodules/z3/build/python",
    "PATH": os.getenv("PATH")
    + ":/go/bin:"
    + IVY_DIR
    + "/submodules/z3/build",  # "/go/bin:${"+ os.getenv('PATH') +"}", #
}

QUIC_PAIRED_TEST = {
    "quic_server_test_0rtt": "quic_server_test_0rtt_stream",
    "quic_server_test_0rtt_stream": "quic_server_test_0rtt_stream_co_close",
    "quic_server_test_0rtt_stream_co_close": "quic_server_test_0rtt_stream_app_close",
    "quic_client_test_0rtt_invalid": "quic_client_test_0rtt_max",
    "quic_client_test_0rtt_add_val": "quic_client_test_0rtt_max_add_val",
    "quic_client_test_0rtt_mim_replay": "quic_client_test_0rtt_max",
    "quic_client_test_0rtt": "quic_client_test_0rtt_max",
    "quic_client_test_0rtt_max": "quic_client_test_0rtt_max_co_close",
    "quic_client_test_0rtt_max_co_close": "quic_client_test_0rtt_max_app_close",
    "quic_server_test_retry_reuse_key": "quic_server_test_retry",
}

P_ENV_VAR = {
    "quic": {
        "ZRTT_SSLKEYLOGFILE": SOURCE_DIR
        + "/panther-ivy/protocol-testing/quic/last_tls_key.txt",
        "RETRY_TOKEN_FILE": SOURCE_DIR
        + "/panther-ivy/protocol-testing/quic/last_retry_token.txt",
        "NEW_TOKEN_FILE": SOURCE_DIR
        + "/panther-ivy/protocol-testing/quic/last_new_token.txt",
        "ENCRYPT_TICKET_FILE": SOURCE_DIR
        + "/panther-ivy/protocol-testing/quic/last_encrypt_session_ticket.txt",
        "SESSION_TICKET_FILE": SOURCE_DIR
        + "/panther-ivy/protocol-testing/quic/last_session_ticket_cb.txt",
        "SAVED_PACKET": SOURCE_DIR
        + "/panther-ivy/protocol-testing/quic/saved_packet.txt",
        "initial_max_stream_id_bidi": SOURCE_DIR
        + "/panther-ivy/protocol-testing/quic/initial_max_stream_id_bidi.txt",
        "active_connection_id_limit": SOURCE_DIR
        + "/panther-ivy/protocol-testing/quic/active_connection_id_limit.txt",
        "initial_max_stream_data_bidi_local": SOURCE_DIR
        + "/panther-ivy/protocol-testing/quic/initial_max_stream_data_bidi_local.txt",
        "initial_max_stream_data_bidi_remote": SOURCE_DIR
        + "/panther-ivy/protocol-testing/quic/initial_max_stream_data_bidi_remote.txt",
        "initial_max_stream_data_uni": SOURCE_DIR
        + "/panther-ivy/protocol-testing/quic/initial_max_stream_data_uni.txt",
        "initial_max_data": SOURCE_DIR
        + "/panther-ivy/protocol-testing/quic/initial_max_data.txt",
        "INITIAL_VERSION": "1",
    },
    "bgp": {},
    "minip": {},
    "apt": {},
}
