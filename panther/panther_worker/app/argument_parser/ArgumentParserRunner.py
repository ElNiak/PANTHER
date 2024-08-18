# argument_parser_runner.py
import argparse
import configparser

class ArgumentParserRunner:
    def __init__(self):
        self.parser = argparse.ArgumentParser(conflict_handler="resolve")

        self.add_global_parameters()
        self.add_debug_parameters()
        self.add_network_parameters()
        self.add_usage_parameters()
        self.add_shadow_parameters()
        self.add_vnetwork_parameters()
        self.add_quic_parameters()
        self.add_bgp_parameters()
        self.add_mpong_parameters()
        self.add_apt_custom_parameters()
        self.add_apt_mitm_parameters()
        self.add_apt_attacker_parameters()
        self.add_apt_victim_parameters()

    def add_global_parameters(self):
        group = self.parser.add_argument_group()
        group.title = "Global parameters"
        group.add_argument("--dir", help="Output directory to create (default: temp/)", type=str, default=None)
        group.add_argument("--build_dir", help="Build directory to create (default: build/)", type=str, default=None)
        group.add_argument("--tests_dir", help="Tests directory to create (default: build/)", type=str, default=None)
        group.add_argument("--iter", help="Number of iteration per test (default: 1)", type=int, default=1)
        group.add_argument("--internal_iteration", help="Number of Ivy iteration per test (default: 100)", type=int, default=100)
        group.add_argument("--getstats", help="Print all stats (default:True)", action="store_false")
        group.add_argument("--compile", help="Compile Ivy tests (default:True)", action="store_false")
        group.add_argument("--run", help="Launch or not the tested implementation (default:True)", action="store_false")
        group.add_argument("--timeout", help="Timeout (default: 100 sec)", type=int, default=100)
        group.add_argument("--keep_alive", help="Keep alive Ivy implementation (default:False)", action="store_true")
        group.add_argument("--update_ivy", help="Update <include> folder for picoTLS files of Ivy (defined by g++) (default:True)", action="store_false")
        group.add_argument("--docker", help="Use docker (default:True)", action="store_false")
        group.add_argument("--debug", help="Use Ivy debug event (default:False)", action="store_true")

    def add_debug_parameters(self):
        group = self.parser.add_argument_group()
        group.title = "Debugging Ivy"
        group.add_argument("--gperf", help="gperf (default:False)", action="store_true")
        group.add_argument("--gdb", help="Use gdb to debug (default:False)", action="store_true")
        group.add_argument("--ptrace", help="Use ptrace to debug (default:False) - NOT IMPLEMENTED", action="store_true")
        group.add_argument("--strace", help="Use strace to debug (default:False) - NOT IMPLEMENTED", action="store_true")
        group.add_argument("--memprof", help="Perform memory profiling (default:False)", action="store_true")

    def add_network_parameters(self):
        group = self.parser.add_mutually_exclusive_group()
        group.title = "Network type"
        group.add_argument("--localhost", help="Use locahost network (default:True)", action="store_false").metavar = "net_parameters"
        group.add_argument("--vnet", help="Use virtual network (default:False)", action="store_true").metavar = "net_parameters"
        group.add_argument("--shadow", help="Use Shadow simulator (default:False)", action="store_true").metavar = "net_parameters"

    def add_vnetwork_parameters(self):
        group = self.parser.add_argument_group()
        group.title = "VNET paramters"
        group.add_argument("--mitm", help="Use virtual network (default:True)", action="store_false")
        group.add_argument("--bridged", help="Virtual network in bridged mode (default:True)",  action="store_false")
        
    def add_usage_parameters(self):
        group = self.parser.add_mutually_exclusive_group()
        group.title = "Usage type"
        group.add_argument("--webapp", help="WebApp UI (default:False)", action="store_true")
        group.add_argument("--worker", help="Worker server mode (default:False)", action="store_true")

    def add_shadow_parameters(self):
        group = self.parser.add_argument_group()
        group.title = "Shadow parameters"
        group.add_argument("--loss", help="Shadow: loss (default:0)", type=float, default=0.0)
        group.add_argument("--jitter", help="Shadow: jitter (default:0)", type=int, default=0)
        group.add_argument("--latency", help="Shadow: latency (default:0)", type=int, default=0)

    def add_quic_parameters(self):
        group = self.parser.add_argument_group()
        group.title = "QUIC verification with Ivy"
        group.add_argument("--nb_request", help="Number of request send by implementations (default: 10)", type=int, default=10)
        group.add_argument("--initial_version", help="Initial version (default: 1)", type=int, choices=[1, 29, 28, 27], default=1)
        group.add_argument("--nclient", help="Number of client per test for server implementation (default: 1)", type=int, default=1)
        group.add_argument("--alpn", help="alpn (default: hq-interop)", choices=["hq-interop", "hq-29", "hq-28", "hq-27"], default="hq-interop")

    def add_bgp_parameters(self):
        group = self.parser.add_mutually_exclusive_group()
        group.title = "BGP verification"
        # Add BGP-specific arguments if needed, similar to how QUIC parameters are added

    def add_mpong_parameters(self):
        group = self.parser.add_mutually_exclusive_group()
        group.title = "MiniP verification"
        # Add MiniP-specific arguments if needed, similar to how QUIC parameters are added

    def add_apt_custom_parameters(self):
        group = self.parser.add_argument_group()
        group.title = "APT custom test parameters"
        group.add_argument("--mutate_packets", help="Mutate packets (default: False)", action="store_true")
        group.add_argument("--mutate_frames", help="Mutate frames (default: False)", action="store_true")
        group.add_argument("--replay_packets", help="Replay packets (default: False)", action="store_true")
        group.add_argument("--flooding", help="Flooding (default: False)", action="store_true")
        group.add_argument("--replay_frames", help="Replay frames (default: False)", action="store_true")
        group.add_argument("--loris", help="Loris attack (default: False)", action="store_true")
        
    def add_apt_mitm_parameters(self):
        group = self.parser.add_argument_group()
        group.title = "APT MitM parameters"
        group.add_argument("--mutate_packets", help="Mutate packets (default: False)", action="store_true")
        group.add_argument("--mutate_frames", help="Mutate frames (default: False)", action="store_true")
        group.add_argument("--replay_packets", help="Replay packets (default: False)", action="store_true")
        group.add_argument("--replay_frames", help="Replay frames (default: False)", action="store_true")
        group.add_argument("--loris", help="Loris attack (default: False)", action="store_true")
        group.add_argument("--spoof_server_ip", help="Spoof server IP (default: False)", action="store_true")
        group.add_argument("--spoof_client_ip", help="Spoof client IP (default: False)", action="store_true")
                
    def add_apt_attacker_parameters(self):
        group = self.parser.add_argument_group()
        group.title = "APT attacker parameters"
        group.add_argument("--mutate_packets", help="Mutate packets (default: False)", action="store_true")
        group.add_argument("--mutate_frames", help="Mutate frames (default: False)", action="store_true")
        group.add_argument("--replay_packets", help="Replay packets (default: False)", action="store_true")
        group.add_argument("--flooding", help="Flooding (default: False)", action="store_true")
        group.add_argument("--replay_frames", help="Replay frames (default: False)", action="store_true")
        group.add_argument("--loris", help="Loris attack (default: False)", action="store_true")
    
    def add_apt_victim_parameters(self):
        group = self.parser.add_argument_group()
        group.title = "APT victim parameters"
        
    def parse_arguments(self, allow_unk=False):
        args = None
        if not allow_unk:
            args = self.parser.parse_args()
        else:
            args, unknown = self.parser.parse_known_args()
        return args

# # Usage
# if __name__ == "__main__":
#     config_file = 'path/to/config.ini'
#     parser_runner = ArgumentParserRunner(config_file)
#     arguments = parser_runner.parse_arguments()
#     print(arguments)
