import argparse


class ArgumentParserRunner:
    def __init__(self):
        self.parser = argparse.ArgumentParser(conflict_handler="resolve")

        self.group_exp = self.parser.add_argument_group()  # required=True
        self.group_exp.title = "Global parameters"
        self.group_exp.add_argument(
            "--dir",
            help="Output directory to create (default: temp/)",
            type=str,
            default=None,
        )
        self.group_exp.add_argument(
            "--build_dir",
            help="Build directory to create (default: build/)",
            type=str,
            default=None,
        )
        self.group_exp.add_argument(
            "--tests_dir",
            help="Tests directory to create (default: build/)",
            type=str,
            default=None,
        )
        self.group_exp.add_argument(
            "--iter",
            help="Number of iteration per test (default: 1)",
            type=int,
            default=1,
        )
        self.group_exp.add_argument(
            "--internal_iteration",
            help="Number of Ivy iteration per test (default: 100)",
            type=int,
            default=100,
        )
        self.group_exp.add_argument(
            "--getstats", help="Print all stats (default:True)", action="store_false"
        )
        self.group_exp.add_argument(
            "--compile", help="Compile Ivy tests (default:True)", action="store_false"
        )
        self.group_exp.add_argument(
            "--run",
            help="Launch or not the tested implementation (default:True)",
            action="store_false",
        )
        self.group_exp.add_argument(
            "--timeout", help="Timeout (default: 100 sec)", type=int, default=100
        )
        self.group_exp.add_argument(
            "--keep_alive",
            help="Keep alive Ivy implementation (default:False)",
            action="store_true",
        )
        self.group_exp.add_argument(
            "--update_ivy",
            help="Update <include> folder for picoTLS files of Ivy (defined by g++) (default:True)",
            action="store_false",
        )
        self.group_exp.add_argument(
            "--docker", help="Use docker (default:True)", action="store_false"
        )

        self.group_debug = self.parser.add_argument_group()  # required=True
        self.group_debug.title = "Debugging Ivy"
        self.group_debug.add_argument(
            "--gperf", help="gperf (default:False)", action="store_true"
        )
        self.group_debug.add_argument(
            "--gdb", help="Use gdb to debug (default:False)", action="store_true"
        )
        self.group_debug.add_argument(
            "--ptrace",
            help="Use ptrace to debug (default:False) - NOT IMPLEMENTED",
            action="store_true",
        )
        self.group_debug.add_argument(
            "--strace",
            help="Use strace to debug (default:False) - NOT IMPLEMENTED",
            action="store_true",
        )
        self.group_debug.add_argument(
            "--memprof",
            help="Perform memory profiling (default:False)",
            action="store_true",
        )

        self.group_net = self.parser.add_mutually_exclusive_group()  # required=True
        self.group_net.title = "Network type"
        self.group_net.add_argument(
            "--localhost",
            help="Use locahost network (default:True)",
            action="store_false",
        ).metavar = "net_parameters"
        self.group_net.add_argument(
            "--vnet",
            help="Use virtual network (default:False)",
            action="store_true",
        ).metavar = "net_parameters"
        self.group_net.add_argument(
            "--shadow",
            help="Use Shadow simulator (default:False)",
            action="store_true",
        ).metavar = "net_parameters"

        self.group_gui = self.parser.add_mutually_exclusive_group()  # required=True
        self.group_gui.title = "Usage type"
        self.group_gui.add_argument(
            "--webapp", help="WebApp UI (default:False)", action="store_true"
        )
        self.group_gui.add_argument(
            "--worker", help="Worker server mode (default:False)", action="store_true"
        )

        self.group_shadow = self.parser.add_argument_group()  # required=True
        self.group_shadow.title = "Shadow parameters"
        self.group_shadow.add_argument(
            "--loss", help="Shadow: loss (default:0)", type=float, default=0.01
        )
        self.group_shadow.add_argument(
            "--jitter", help="Shadow: jitter (default:0)", type=int, default=10
        )
        self.group_shadow.add_argument(
            "--latency", help="Shadow: latency (default:0)", type=int, default=10
        )

        self.group_quic = self.parser.add_argument_group()  # required=True
        self.group_quic.title = "QUIC verification with Ivy"
        # self.group_quic.add_argument(
        #     '--mode',
        #     help='Mode of experiments - "client" vs "server" (default) vs "mim"',
        #     type=str,
        #     choices=["server", "client", "mim"],
        #     default="server"
        # )
        self.group_quic.add_argument(
            "--nb_request",
            help="Number of request send by implementations (not always possible) (default: 10)",
            type=int,
            default=10,  # TODO enforce
        )
        self.group_quic.add_argument(
            "--initial_version",
            help="Initial version (default: 1)",
            type=int,
            choices=[1, 29, 28],
            default=1,
        )
        self.group_quic.add_argument(
            "--nclient",
            help="Number of client per test for server implementation (default: 1)",
            type=int,
            default=1,
        )
        self.group_quic.add_argument(
            "--alpn",
            help="alpn (default: hq-interop)",
            choices=["hq-interop", "hq-29", "hq-28"],
        )

        self.group_bgp = self.parser.add_mutually_exclusive_group()  # required=True
        self.group_bgp.title = "BGP verification with Ivy"

        self.group_mpong = self.parser.add_mutually_exclusive_group()  # required=True
        self.group_mpong.title = "MiniP verification with Ivy"

    def parse_arguments(self, allow_unk=False):
        args = None
        if not allow_unk:
            args = self.parser.parse_args()
        else:
            args, unknown = self.parser.parse_known_args()
        return args
