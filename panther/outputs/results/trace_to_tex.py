from scapy.all import *
import threading
import multiprocessing
from datetime import date
import pandas as pd
import os
import scandir
import pyshark


def replace_tag(fr):
    frame = ""
    if "TLS" in fr:
        frame = "CRYPTO"
    elif "PATH_RESPONSE" in fr:
        frame = "PR"
    elif "PADDING" in fr:
        frame = "PADDING"
    elif "PATH_CHALLENGE" in fr:
        frame = "PC"
    elif "HANDSHAKE_DONE" in fr:
        frame = "DONE"
    elif "NEW_TOKEN" in fr:
        frame = "NT"
    elif "MAX_STREAM" in fr:
        frame = "MS"
    elif "STREAM" in fr:
        print(fr)
        stream_id = fr.split(" ")[1]
        stream_id = stream_id.split("=")[1]
        frame = "STREAM(" + stream_id + ")"
    elif "NEW_CONNECTION_ID" in fr:
        frame = "NCI"
    elif "RETIRE_CONNECTION_ID" in fr:
        frame = "RCI"
    else:
        frame = fr
    return frame


def write_header_tex(writer):
    writer.write('\\begin{table}[h!]\n')
    writer.write('\centering\n')
    writer.write('\label{tab:my-table}\n')
    writer.write('\\resizebox{\\textwidth}{!}{%\n')
    writer.write('\\begin{tabular}{|cclll|}\n')
    writer.write('\hline\n')
    writer.write('\multicolumn{1}{|c|}{\\textbf{src}} & \multicolumn{1}{c|}{\\textbf{dst}} & \multicolumn{1}{c|}{\\textbf{time}} & \multicolumn{1}{}{} & \multicolumn{1}{c|}{\\textbf{Information}} \\\\ \hline \n')


def write_footer_tex(writer):
    writer.write('\hline\n')
    writer.write('\end{tabular}%\n')
    writer.write('}\n')
    writer.write('\end{table}\n')


def get_line(frames, last_pnum, pkt, pkt_len, pkt_type, dcid):
    line = ""
    if pkt_type == '0' and hasattr(pkt.quic, "long_packet_type"):
        pkt_t = "Initial"
        scid = pkt.quic.scid.replace(":", "")
        line = str(pkt_len) + ", " + pkt_t + ", DCID=" + str(dcid) + ", SCID=" + str(
            scid) + ", PKT: " + str(last_pnum) + ", " + frames
    elif hasattr(pkt.quic, "vn.unused"):
        pkt_t = "Version Negotiation"
        scid = pkt.quic.scid.replace(":", "")
        line = str(pkt_len) + ", " + pkt_t + ", DCID=" + str(dcid) + ", SCID=" + str(
            scid) + ", SV: " + str(pkt.quic.supported_version) 
    elif pkt_type == '0':
        pkt_t = "Protected Payload (KP0)"
        line = str(pkt_len) + ", " + pkt_t + ", DCID=" + str(dcid) + \
            ", PKT: " + str(last_pnum) + ", " + frames
    elif pkt_type == '2':
        pkt_t = "Handshake"
        scid = pkt.quic.scid.replace(":", "")
        line = str(pkt_len) + ", " + pkt_t + ", DCID=" + str(dcid) + ", SCID=" + str(
            scid) + ", PKT: " + str(last_pnum) + ", " + frames
    return line


def write_line(f, dst_port, src_port, line):
    if src_port == "4443":
        f.write('\\rowcolor{LightCyan} ' + str(src_port) + " & " + str(
            dst_port) + " &  & \multicolumn{1}{c}{} &")
        f.write(line)
        f.write('\\\\ \n')
    else:
        f.write('\\rowcolor{lightgreen} ' + str(src_port) + " & " + str(
            dst_port) + " &  & \multicolumn{1}{c}{} &")
        f.write(line)
        f.write('\\\\ \n')


foldername = "/home/user/Documents/QUIC-FormalVerification/results/traces/"
subfolders = [f.path for f in scandir.scandir(foldername) if f.is_dir()]
run = 0


for fol in subfolders:
    for file in os.listdir(fol):
        print(file)
        if file.endswith(".pcapng") or file.endswith(".pcap"):
            end = ".pcapng"
            if file.endswith(".pcap"):
                end = ".pcap"
            file = str(fol) + "/" + file
            outputFile = file.replace(end, ".txt")
            override_prefs = {}

            for filessl in os.listdir(fol):
                if filessl.endswith(".log"):
                    override_prefs["tls.keylog_file"] = str(
                        fol) + "/" + filessl
                    print(override_prefs["tls.keylog_file"])

            cap = pyshark.FileCapture(
                file,
                override_prefs=override_prefs,
                display_filter="udp.port == 4443",
                disable_protocol="http2",
                decode_as={"udp.port==4443": "quic"},
            )

            cap.set_debug()
            packets = []
            try:
                for p in cap:
                    packets.append(p)
                cap.close()
            except Exception as e:
                print(e)

            if override_prefs["tls.keylog_file"] is not None:
                for p in packets:
                    if hasattr(p["quic"], "decryption_failed"):
                        print("At least one QUIC packet could not be decrypted")
                        print(p)
                        break

            f = open(outputFile, "w")
            write_header_tex(f)

            frames = ""
            last_pnum = "0"
            last_srcport = "0"
            last_dstport = "0"
            last_dstid = "0"
            last_srcid = "0"
            first = True
            coal = False

            for pkt in packets:
                print(pkt.quic.__dict__)
                # for layer in pkt:
                # if layer.layer_name == 'quic':

                dst_port = pkt.udp.dstport
                src_port = pkt.udp.srcport

                pkt_len = pkt.quic.packet_length
                pkt_type = pkt.quic.header_form
                if hasattr(pkt.quic, "long_packet_type"):
                    pkt_type = pkt.quic.long_packet_type

                # if hasattr(pkt.quic, "quic.supported_version"):
                #     cid = pkt.quic.dcid.replace(":", "")
                #     pkt_t = ""
                if not hasattr(pkt.quic, "quic.connection.unknown"):
                    dcid = pkt.quic.dcid.replace(":", "")
                    pkt_t = ""
                    if hasattr(pkt.quic, "packet_number"):
                        pkt_num = pkt.quic.packet_number
                    else:
                        frames = " Protected Payload (KP0)  (Undecryptable) "  
                        line = get_line(frames, last_pnum, pkt,
                                    pkt_len, pkt_type, dcid)
                        write_line(f, dst_port, src_port, line)
                        continue
                else:
                    frames = " Protected Payload (KP0)  (Undecryptable) "  
                    line = get_line(frames, last_pnum, pkt,
                                    pkt_len, pkt_type, dcid)
                    write_line(f, dst_port, src_port, line)
                    continue

                scid = None
                line = ""
                try:
                    fr = pkt.quic.frame
                    frame = replace_tag(fr)
                    frames = frame 
                    line = get_line(frames, pkt_num, pkt,
		                            pkt_len, pkt_type, dcid)
                    write_line(f, dst_port, src_port, line)
                except:
                    pass

            write_footer_tex(f)
            f.close()

"""

                if first:
                    last_pnum = pkt.quic.packet_number
                    last_srcport = src_port
                    last_dstport = dst_port
                    last_dstid = dcid
                    last_srcid = scid
                    fr = pkt.quic.frame
                    frame = replace_tag(fr)
                    frames = frames + frame + " "
                    first = False
                    line = get_line(frames, last_pnum, pkt, pkt_len, pkt_type, dcid)
                    write_line(f, dst_port, src_port, line)
                    coal = False
                elif last_pnum == pkt_num:
                    coal = True
                    fr = pkt.quic.frame
                    frame = replace_tag(fr)
                    frames = frames + frame + " "
                else:
                    print(src_port)
                    print(coal)
                    print(last_dstid)
                    print(dcid)
                    line = get_line(frames, last_pnum, pkt,
                                    pkt_len, pkt_type, dcid)
                    if coal:
                        write_line(f, last_dstport, last_srcport, line)
                    else:
                        #if coal: #"Protected Payload (KP0)" in frames and last_dstid == dcid
                        write_line(f, dst_port, src_port, line)
                        # elif last_dstid == dcid:
                        #    write_line(f, dst_port, src_port, line)
                        #else:
                        # write_line(f, last_dstport, last_srcport, line)
                    last_pnum = pkt_num
                    last_srcport = src_port
                    last_dstport = dst_port
                    last_dstid = dcid
                    last_srcid = scid
                    fr = pkt.quic.frame
                    frame = replace_tag(fr)
                    frames = frame + " "
                    coal = False
"""
