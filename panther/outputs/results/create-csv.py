from datetime import date
import pandas as pd
import os
import scandir

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

def lines_that_contain(string, filename):
    with open(filename, 'r',encoding = "ISO-8859-1") as f:
        lines = f.read().splitlines()
        return [line for line in lines if string in line]


foldername = "/home/user/Documents/QUIC-FormalVerification/results/client-retry-vn-3/"  #"/home/chris/Toward-verification-of-QUIC-extensions/installer/TVOQE/results/errors/server/local/mvfst_server_newcoid/temp/" 
# foldername = "/home/student/Toward-verification-of-QUIC-extensions/installer/TVOQE"
# foldername = "/results/temp/"
subfolders = [f.path for f in scandir.scandir(foldername) if f.is_dir()]
run = 0
for fol in subfolders:
    #print(fol)
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
                test_name = file.replace('.iev', '')
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
                                elif "quinn" in content or "Running `target/debug/examples/server /panther-ivy/doc/examples/quic/" in content:
                                    match = "quinn"
                                elif "quiche" in content:
                                    match = "quiche"
                                elif "[NOTICE] Document root is not set" in content:
                                    match = "lsquic"
                            except:
                                  match = "quant"

            else:
                test_name = file.replace('.iev', '')
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
                contents = f.read()
                last, second_last = readlastline(fullPath)
                errors = []
                if not "server" in file and os.path.isfile('res_client.txt'):
                    errors = lines_that_contain("require",os.path.join(fol, "res_client.txt"))
                elif os.path.isfile('res_server.txt'):
                    errors = lines_that_contain("require",os.path.join(fol, "res_server.txt"))
                if len(errors) > 0:
                    last = errors[0].replace('"    ',"")
                    second_last = ""
                if "frame.connection_close:" in contents:
                    start_index = contents.find("frame.connection_close:")
                    end_index = contents.find(",",start_index)
                    last = contents[start_index:end_index+1].replace(",","") + "}"
                    second_last = ""
                last = last.replace("\n","").replace("    ","").replace(",","").replace(";","")
                second_last = second_last.replace("\n","").replace("    ","").replace(",","").replace(";","")
                if "test_completed" in contents:
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
