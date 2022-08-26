from struct import pack
from plantuml import PlantUML
import re

def generate_graph_input(ivy_trace_path,plantuml_path):
    with open(ivy_trace_path, 'r') as ivy_trace:
        with open(plantuml_path, 'w') as plantuml_file:
            plantuml_file.write('@startuml' + '\n')
            plantuml_file.write('title '  + ivy_trace_path + '\n')
            plantuml_file.write('skinparam sequenceMessageAlign center' + '\n')
            
            endpoints = {}

            for line in ivy_trace:
                if line.startswith('< recv_packet(') or line.startswith('> packet_event('):
                    # print(line)
                    brackets = re.findall(r"\{(.+?)\}", line)
                    

                    source_address      = brackets[0]
                    destination_address = brackets[1]

                    source_address_name      = "IvyAgent" if line.startswith('< recv_packet(') else 'TestedAgent'
                    destination_address_name = "IvyAgent" if line.startswith('> packet_event(') else 'TestedAgent'

                    if source_address not in endpoints:
                        print(source_address)
                        endpoints[source_address] = "\"" + source_address_name +  str(len(endpoints)) + '\"'
                    if destination_address not in endpoints:
                        print(destination_address)
                        endpoints[destination_address] = "\"" + destination_address_name +  str(len(endpoints)) + '\"'
                        
                    packet  = "Initial" if "initial" in brackets[2] else ("Handshake" if "handshake" in brackets[2] else ("One RTT" if "one_rtt" in brackets[2] else ("Zero RTT" if "zero_rtt" in brackets[2] else "Unknown")))
                    packet += " Packet** \\n"

                    packet = "**" + packet 
                    
                    
                    brackets[2] = line[line.rfind("payload"):]
                    #print(brackets[2])
                    packet_payload = brackets[2].split('payload:[{')[1]
                    packet_contents = brackets[2].split('payload:[{')[0].split(',')
                    for elem in packet_contents:
                        packet += elem + "\\n"

                    plantuml_file.write(endpoints[source_address] + ' --> ' + endpoints[destination_address] + ' : ' + packet + '\n')
                    
                    if line.startswith('< recv_packet('):
                        plantuml_file.write("note left" + '\n')
                    else:
                        plantuml_file.write("note right" + '\n')
                    print(brackets)
                    print("\n")
                    
                    if packet_payload != "":
                        packet_payload += "}"
                        packet_frames = packet_payload.split("},{")
                        for frames in packet_frames:
                            frames = frames.replace("}","]")
                            frames = frames.replace("{","[")
                            #print(frames)
                            frames = frames[0:(frames.rfind("data:") + len("data:") if "data" in frames else len(frames))]  + "...]"
                            plantuml_file.write(frames + '\n')
                    plantuml_file.write("end note" + '\n\n')
                    #exit(0)


            plantuml_file.write('@enduml' + '\n')


path = "/home/user/Documents/QUIC-RFC9000/QUIC-Ivy/doc/examples/quic/test/temp/45/quic_client_test_version_negociation_mim_modify0.iev"
plantuml_file = "/home/user/Documents/QUIC-RFC9000/plantuml.puml"
generate_graph_input(path, plantuml_file)
plantuml_obj = PlantUML(url="http://www.plantuml.com/plantuml/img/",  basic_auth={}, form_auth={}, http_opts={}, request_opts={})
plantuml_obj.processes_file(plantuml_file, "/home/user/Documents/QUIC-RFC9000/plantuml.png")