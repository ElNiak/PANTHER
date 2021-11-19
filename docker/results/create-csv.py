from datetime import date
import pandas as pd
import os
import scandir

server_tests = [
    'quic_server_test_stream',
    'quic_server_test_handshake_done_error',
    'quic_server_test_reset_stream',
    'quic_server_test_connection_close',
    'quic_server_test_stop_sending',
    'quic_server_test_max',
    'quic_server_test_token_error',
    'quic_server_test_tp_error',
    'quic_server_test_double_tp_error',
    'quic_server_test_tp_acticoid_error',
    'quic_server_test_tp_limit_acticoid_error',
    'quic_server_test_blocked_streams_maxstream_error',
    'quic_server_test_retirecoid_error',
    'quic_server_test_newcoid_zero_error',
    'quic_server_test_accept_maxdata',
    'quic_server_test_unkown',
    'quic_server_test_tp_limit_newcoid',
    'quic_server_test_ext_min_ack_delay',
    'quic_server_test_no_icid',
    'quic_server_test_stream_limit_error',
    'quic_server_test_crypto_limit_error',
    'quic_server_test_newconnectionid_error',
    'quic_server_test_newcoid_rtp_error',
    'quic_server_test_newcoid_length_error',
    'quic_server_test_new_token_error',
    'quic_server_test_stop_sending_error',
    'quic_server_test_unkown_tp',
    'quic_server_test_max_limit_error',
    'quic_server_test_max_error'
]

# List of available client's tests
client_tests = [
    'quic_client_test_max',
    'quic_client_test_token_error',
    'quic_client_test_tp_error',
    'quic_client_test_double_tp_error',
    'quic_client_test_tp_acticoid_error',
    'quic_client_test_tp_limit_acticoid_error',
    'quic_client_test_blocked_streams_maxstream_error',
    'quic_client_test_retirecoid_error',
    'quic_client_test_newcoid_zero_error',
    'quic_client_test_accept_maxdata',
    'quic_client_test_tp_prefadd_error',
    'quic_client_test_handshake_done_error',
    'quic_client_test_stateless_reset_token',
    'quic_client_test_ext_min_ack_delay',
    'quic_client_test_no_odci',
    'quic_client_test_tp_unknown',
    'quic_client_test_stream',
    'quic_client_test_unkown_tp',
    'quic_client_test_max_limit_error'
    'quic_client_test_new_token_error'
]

frame = pd.DataFrame(
    columns=["Run", "Implementation", "Mode", "TestName", "Status", "ErrorIEV", "OutputFile"])


def readlastline(filename):
    last = ""
    second_last = ""
    with open(filename, 'r') as f:
        lines = f.read().splitlines()
        if len(lines) > 0:
            last = lines[-1]
        if len(lines) > 1:
            second_last = lines[-2]
    return last, second_last


foldername = "/results/temp/"  #"/home/chris/Toward-verification-of-QUIC-extensions/installer/TVOQE/results/errors/server/local/mvfst_server_newcoid/temp/" 
# foldername = "/home/student/Toward-verification-of-QUIC-extensions/installer/TVOQE"
# foldername = "/results/temp/"
subfolders = [f.path for f in scandir.scandir(foldername) if f.is_dir()]
run = 0
for fol in subfolders:
    for file in os.listdir(fol):
        if file.endswith(".iev"):
            fullPath = os.path.join(fol, file)
            out = file.replace(".iev", ".out")
            err = file.replace(".iev", ".err")
            mode = "client"
            test_name = ""
            match = ""
            if "server" in file:
                mode = "server"
                for n in server_tests:
                    if n in file:
                        test_name = file.replace('.iev', '')
                        break
                if os.path.isfile('res_server.txt'):
                    with open(os.path.join(fol, "res_server.txt"), "r") as f:
                        for li in f:
                            if "implementation command:" in li:
                                match = li.replace(
                                    "implementation command:", "")
                                break
                else:
                    m = False
                    with open(os.path.join(fol, out), "r") as f:
                        content = f.read()
                        if "Picoquic" in content:
                            match = "picoquic"
                            m = True
                        if "quic-go" in content:
                            match = "quic-go"
                            m = True
                    if not m :
                        with open(os.path.join(fol, err), "r") as f:
                            try:
                                content = f.read()
                                if "Using selector: EpollSelector" in content:
                                    match = "aioquic"
                                elif "EventBase.cpp" in content:
                                    match = "mvfst"
                                elif "quant" in content:
                                    match = "quant"
                                elif "quinn" in content or "Running `target/debug/examples/server /QUIC-Ivy/doc/examples/quic/" in content:
                                    match = "quinn"
                                elif "quiche" in content:
                                    match = "quiche"
                                elif "[NOTICE] Document root is not set" in content:
                                    match = "lsquic"
                            except:
                                  match = "quant"

            else:
                for n in client_tests:
                    if n in file:
                        test_name = file.replace('.iev', '')
                        break
                if os.path.isfile('res_client.txt'):
                    with open(os.path.join(fol, "res_client.txt"), "r") as f:
                        for li in f:
                            if "implementation command:" in li:
                                match = li.replace("implementation command:", "")
                                break
                else:
                    m = False
                    with open(os.path.join(fol, out), "r") as f:
                        content = f.read()
                        if "Picoquic" in content:
                            match = "picoquic"
                            m = True
                        if "quic-go" in content:
                            match = "quic-go"
                            m = True
                    if not m :
                            try:
                                content = f.read()
                                if "Using selector: EpollSelector" in content:
                                    match = "aioquic"
                                elif "EventBase.cpp" in content:
                                    match = "mvfst"
                                elif "quant" in content:
                                    match = "quant"
                                elif "quinn" in content:
                                    match = "quinn"
                                elif "quiche" in content:
                                    match = "quiche"
                                elif "[NOTICE] Document root is not set" in content:
                                    match = "lsquic"
                            except:
                                  match = "quant"
            outPath = os.path.join(fol, out)
            err = file.replace(".iev", ".err")
            errPath = os.path.join(fol, err)
            with open(fullPath, "r") as f:
                last, second_last = readlastline(fullPath)
                if last in "test_completed\n":
                    frame = frame.append(
                        {"Run": run,
                         "Implementation": match,
                         "Mode": mode,
                         "TestName": test_name,
                         "isPass": True,
                         "ErrorIEV": "",
                         "NbPktSend": 0,  # TODO
                         "OutputFile": fullPath}, ignore_index=True)
                else:
                    frame = frame.append(
                        {"Run": run,
                         "Implementation": match,
                         "Mode": mode,
                         "TestName": test_name,
                         "isPass": False,
                         "ErrorIEV": last+"+"+second_last,
                         "NbPktSend": 0,  # TODO
                         "OutputFile": fullPath}, ignore_index=True)
                run += 1


today = date.today()
# Month abbreviation, day and year
d4 = today.strftime("%b-%d-%Y")
print("d4 =", d4)
frame.to_csv(d4+'.csv', index=False)
