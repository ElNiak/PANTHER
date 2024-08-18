import datetime
import os
import sys
import pandas as pd
from scapy.all import *

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

import ivy_utils.ivy_ev_parser as ev
import ivy_utils.ivy_utils as iu
from panther_utils.panther_constant import *

specials = [  # TODO
    "quic_server_test_0rtt",
    "quic_client_test_0rtt",
    "quic_server_test_retry_reuse_key",
]

counts = [
    ["frame.ack", "frame.ack.handle"],
    ["frame.stream", "frame.stream.handle"],
    ["frame.crypto", "frame.crypto.handle"],
    ["frame.rst_stream", "frame.rst_stream.handle"],
    ["frame.connection_close", "frame.connection_close.handle"],
    ["packet_event", "packet_event"],
    ["packet_event_retry", "packet_event_retry"],
    ["packet_event_vn", "packet_event_vn"],
    ["packet_event_0rtt", "packet_event_0rtt"],
    ["packet_event_coal_0rtt", "packet_event_coal_0rtt"],
    ["recv_packet", "recv_packet"],
    ["recv_packet_retry", "recv_packet_retry"],
    ["recv_packet_vn", "recv_packet_vn"],
    ["recv_packet_0rtt", "recv_packet_0rtt"],
    ["undecryptable_packet_event", "undecryptable_packet_event"],
    ["app_send_event", "app_send_event"],
    ["tls_recv_event", "tls_recv_event"],
    ["max stream offset", "frame.stream.handle({offset:$1})", "maxz", "%($1)s"],
    [
        "max stream data",
        "frame.stream.handle({offset:$1,length:$2})",
        "maxz",
        "%($1)s + %($2)s",
    ],
    ["ivy error", "ivy_return_code"],
    ["server error", "server_return_code"],
    ["server_ack", "show_frame(*,*,*,*,{frame.ack:*})"],
    ["server_stream", "show_frame(*,*,*,*,{frame.stream:*})"],
]


def count(x):
    return len(x)


def maxz(x):
    return 0 if len(x) == 0 else max(x)


def update_csv(
    run_id, implem_name, mode, test_name, pcapFile, OutputFile, out, initial_version
):

    try:
        df = pd.read_csv(RESULT_DIR.replace("$PROT", "minip") + "/temp/data.csv")
        print(df)
    except:
        df = pd.DataFrame(
            columns=[
                "Run",
                "Implementation",
                "Mode",
                "TestName",
                "isPass",
                "ErrorIEV",
                "OutputFile",
                "packet_event",
                "packet_event_retry",
                "packet_event_vn",
                "packet_event_0rtt",
                "packet_event_coal_0rtt",
                "frame.stream",
                "ivy_error",  # TODO get error code + client version
                "implementation_error",
                "app_send_event",
                "tls_recv_event",
                "recv_packet",
                "recv_packet_retry",
                "handshake_done",
                "tls.finished",
                "recv_packet_vn",
                "recv_packet_0rtt",
                "undecryptable_packet_event",
                "version_not_found_event",
                "date",
                "initial_version",
            ]
        )  # TODO add frame type

    iev_content = out.read()

    splitted_iev = iev_content.splitlines()
    error_iev = (
        splitted_iev[-1] + (" " + splitted_iev[-2])
        if len(splitted_iev) > 1
        and (
            "test_completed" in splitted_iev[-2]
            or "assumption_failed" in splitted_iev[-2]
        )
        else ""
    )

    packets = rdpcap(pcapFile)
    nPkt = len(packets)

    threshold = 1
    if test_name in specials:
        threshold = 2

    # TODO special case for "error" tests

    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    {
                        "Run": run_id,
                        "Implementation": implem_name,
                        "Mode": mode,
                        "TestName": test_name,
                        "isPass": (
                            True
                            if iev_content.count("test_completed") == threshold
                            else False
                        ),
                        "ErrorIEV": error_iev,
                        "NbPktSend": nPkt,
                        "OutputFile": OutputFile,
                        "packet_event": iev_content.count("packet_event"),
                        "packet_event_retry": iev_content.count("packet_event_retry"),
                        "packet_event_vn": iev_content.count("packet_event_vn"),
                        "packet_event_0rtt": iev_content.count("packet_event_0rtt"),
                        "packet_event_coal_0rtt": iev_content.count(
                            "packet_event_coal_0rtt"
                        ),
                        "frame.stream": iev_content.count("frame.stream.handle"),
                        "ivy_error": iev_content.count(
                            "ivy_return_code"
                        ),  # TODO get error code + client version
                        "implementation_error": iev_content.count("server_return_code"),
                        "app_send_event": iev_content.count("app_send_event"),
                        "tls_recv_event": iev_content.count("tls_recv_event"),
                        "recv_packet": iev_content.count("recv_packet"),
                        "recv_packet_retry": iev_content.count("recv_packet_retry"),
                        "recv_packet_vn": iev_content.count("recv_packet_vn"),
                        "recv_packet_0rtt": iev_content.count("recv_packet_0rtt"),
                        "undecryptable_packet_event": iev_content.count(
                            "undecryptable_packet_event"
                        ),
                        "handshake_done": iev_content.count(
                            "frame.handshake_done.handle"
                        ),
                        "tls.finished": iev_content.count("tls.finished"),
                        "version_not_found": iev_content.count(
                            "version_not_found_event"
                        ),
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "initial_version": initial_version,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    print(df)

    df.to_csv(RESULT_DIR.replace("$PROT", "minip") + "/temp/data.csv", index=False)


def merge_dats():
    pass  # TODO


def make_dat(fbase, out):
    import chardet  # $ pip install chardet

    out.write("file," + ",".join(l[0] for l in counts) + "\n")
    files = sorted(
        [n for n in os.listdir(".") if n.startswith(fbase) and n.endswith(".iev")]
    )
    for fn in files:
        try:
            f = open(fn, "r")
        except:
            print("not found: %s" % fn)
            # sys.exit(1)
            f = open(fn, "w")
            f.write("")
            f.close()
            f = open(fn, "r")

        with iu.ErrorPrinter():
            with iu.SourceFile(fn):
                s = f.read()
                evs = ev.parse(s)

        vals = []
        for line in counts:
            name, patstring = line[:2]
            op = line[2] if len(line) >= 3 else "count"
            expr = line[3] if len(line) >= 4 else "None"
            pats = ev.parse(patstring)
            res = ev.bind(ev.EventGen()(evs), pats)
            col = [eval(expr % b) for e, b in res]
            s = op + "(" + str(col) + ")"
            sum = eval(s)
            vals.append(sum)
        out.write(fn + "," + ",".join(str(v) for v in vals) + "\n")


def main():
    import sys

    def usage():
        print("usage: \n  {} <file>.iev ".format(sys.argv[0]))
        sys.exit(1)

    if len(sys.argv) != 2:
        usage()
    fbase = sys.argv[1]
    make_dat(fbase, sys.stdout)


if __name__ == "__main__":
    main()
