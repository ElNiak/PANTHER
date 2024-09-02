# This script runs a sequence of tests on the picoquicdemo server.

import random
import pexpect
import os
import sys
import subprocess
import signal
from datetime import datetime
import platform
from time import sleep

from panther_tester.panther_tester import IvyTest
from panther_utils.panther_constant import *

# On Windows, pexpect doesn't implement 'spawn'.
"""
Choose the process spawner for subprocess according to plateform
"""
if platform.system() == "Windows":
    from pexpect.popen_spawn import PopenSpawn

    spawn = PopenSpawn
else:
    spawn = pexpect.spawn


# TODO add tested implemenatation name
class BGPIvyTest(IvyTest):
    def __init__(
        self,
        args,
        implem_dir_server,
        implem_dir_client,
        extra_args,
        implementation_name,
        mode,
        config,
        protocol_conf,
        implem_conf,
        current_protocol,
    ):

        super().__init__(
            args,
            implem_dir_server,
            implem_dir_client,
            extra_args,
            implementation_name,
            mode,
            config,
            protocol_conf,
            implem_conf,
            current_protocol,
        )
        self.log.setLevel(int(os.environ["LOG_LEVEL"]))

    def update_implementation_command(self, i):
        return i

    # TODO add if to avoid space in command
    # TODO Reorder config param to loop and generate command eaisier
    def generate_implementation_command(self):
        server_command = """
frr defaults traditional
log syslog informational
debug bgp neighbor
ipv6 forwarding
!
ip route 10.0.0.1/32 10.0.0.3
!
service integrated-vtysh-config
!
    router bgp 2
    bgp ebgp-requires-policy
    neighbor 10.0.0.1 remote-as 1
    neighbor 10.0.0.1 description Router1
    neighbor 10.0.0.1 ebgp-multihop 5
    network 10.0.0.3 mask 255.255.255.255
    !
    address-family ipv4 unicast
    redistribute connected
    neighbor 10.0.0.1 route-map IMPORT in
    neighbor 10.0.0.1 route-map EXPORT out
    exit-address-family
    !
route-map EXPORT deny 100
!
route-map EXPORT permit 1
 match interface implem
!
route-map IMPORT deny 1
!
line vty
!
"""  # TODO now only for frr
        client_command = server_command

        if self.is_client:
            return [client_command, server_command]
        else:
            return [server_command, client_command]

    def start_implementation(self, i, out, err):
        if self.run:
            self.update_implementation_command(i)
            self.log.info(self.implem_cmd)

            if not self.config["net_parameters"].getboolean("shadow"):
                self.log.info("not shadow test:")
                self.log.info("Update bgp config:")
                qcmd = (
                    """
                        cat > /etc/frr/frr.conf << EOL
                        """
                    + self.implem_cmd
                )

                subprocess.Popen(qcmd, shell=True)
                # os.system("/bin/bash -c 'source /usr/lib/frr/frrcommon.sh && /usr/lib/frr/watchfrr $(daemon_list)'")
                # os.system("/usr/lib/frr/frr-reload")
                self.implem_process = subprocess.Popen(
                    "(ip netns exec implem /usr/bin/tini -- bash start_daemon.sh) &",
                    shell=True,
                    preexec_fn=os.setsid,
                    stdout=out,
                    stderr=err,
                ).wait()
                sleep(5)
                os.system("vtysh -c 'show ip bgp summary'")
                os.system("vtysh -c 'show ip bgp'")
                # self.log.info('implem_process pid: {}'.format(self.implem_process.pid))
            else:
                # TODO use config file
                self.log.info("shadow test:")
                if "client_test" in self.name:
                    file = "/app/shadow_client_test.yml"
                    file_temp = "/app/shadow_client_test_template.yml"
                else:
                    file = "/app/shadow_server_test.yml"
                    file_temp = "/app/shadow_server_test_template.yml"
                with open(file_temp, "r") as f:
                    content = f.read()  # todo replace
                with open(file, "w") as f:
                    content = content.replace("<IMPLEMENTATION>", ENV_VAR["TEST_IMPL"])
                    content = content.replace("<ALPN>", ENV_VAR["TEST_ALPN"])
                    content = content.replace(
                        "<SSLKEYLOGFILE>", ENV_VAR["SSLKEYLOGFILE"]
                    )
                    content = content.replace("<TEST_NAME>", self.name)
                    content = content.replace("<JITTER>", str(ENV_VAR["JITTER"]))
                    content = content.replace("<LATENCY>", str(ENV_VAR["LATENCY"]))
                    content = content.replace("<LOSS>", str(float(ENV_VAR["LOSS"])))
                    self.log.info(content)
                    f.write(content)
                os.chdir("/app")
                self.log.info("rm -r /app/shadow.data/ ")
                os.system("rm -r /app/shadow.data/ ")
                os.system("rm  /app/shadow.log ")
                self.log.info(
                    "command: RUST_BACKTRACE=1 shadow " + file + " > shadow.log"
                )
                try:
                    os.system("RUST_BACKTRACE=1 shadow " + file + " > shadow.log")
                except:
                    pass

    def start_tester(self, iteration, iev, i):
        self.log.info("Starting tester:")
        ok = True
        if not self.config["net_parameters"].getboolean("shadow"):
            try:
                for iclient in range(
                    0, self.nclient
                ):  # TODO for multiple implem client only
                    self.log.info("iclient = " + str(iclient))
                    ok = ok and self.run_tester(iteration, iev, i, iclient)
            except KeyboardInterrupt:
                if self.run and not self.config["global_parameters"].getboolean(
                    "keep_alive"
                ):
                    self.log.info("cool kill")
                    if self.config["net_parameters"].getboolean("vnet"):
                        subprocess.Popen(
                            "/bin/bash " + SOURCE_DIR + "/vnet_reset.sh",
                            shell=True,
                            executable="/bin/bash",
                        ).wait()
                    self.implem_process.terminate()
                raise KeyboardInterrupt

            if self.run and not self.config["global_parameters"].getboolean(
                "keep_alive"
            ):
                self.log.info("implem_process.terminate()")
                # The above code is terminating the process.
                self.implem_process.terminate()
                retcode = self.implem_process.wait()
                self.log.info(retcode)
                if retcode != -15 and retcode != 0:  # if not exit on SIGTERM...
                    iev.write("server_return_code({})\n".format(retcode))
                    self.log.info("server return code: {}".format(retcode))
                    self.implem_process.kill()
                    return False

    def stop_processes(self):
        self.log.info("Stop processes:")
        if self.implem_process != None:
            try:
                # os.kill(implem_process.pid, 9)
                os.killpg(os.getpgid(self.implem_process.pid), signal.SIGTERM)
            except OSError:
                self.log.info("pid is unassigned")
                self.implem_process.kill()
            else:
                self.log.info("pid is in use")
                self.implem_process.kill()
                self.log.info("implem_process.kill()")

    def generate_tester_command(self, iteration, iclient):
        strace_cmd, gperf_cmd, timeout_cmd = super().generate_tester_command(
            iteration, iclient
        )

        os.environ["TIMEOUT_IVY"] = str(
            self.config["global_parameters"].getint("timeout")
        )

        randomSeed = random.randint(0, 1000)
        random.seed(datetime.now())

        prefix = ""
        speaker_id = 1
        speaker_id_impl = 2  # TODO

        print(self.name)
        # time.sleep(5)
        if self.config["debug_parameters"].getboolean("gdb"):
            # TODO refactor
            prefix = " gdb --args "
        if self.config["net_parameters"].getboolean("vnet"):
            envs = "env - "
            for env_var in ENV_VAR:
                if env_var != "PATH":  # TODO remove it is useless
                    envs = envs + env_var + '="' + str(ENV_VAR[env_var]) + '" '
                else:
                    envs = envs + env_var + '="' + os.environ.get(env_var) + '" '
            prefix = (
                "sudo ip netns exec ivy "
                + envs
                + " "
                + (
                    strace_cmd
                    if self.config["debug_parameters"].getboolean("strace")
                    else ""
                )
                + " "
                + gperf_cmd
                + " "
            )
            ip_server = 0x0A000003 if not self.is_client else 0x0A000001
            ip_client = 0x0A000001 if not self.is_client else 0x0A000003
        elif self.config["net_parameters"].getboolean("shadow"):
            ip_server = 0x0B000002 if not self.is_client else 0x0B000001
            ip_client = 0x0B000001 if not self.is_client else 0x0B000002
        else:
            # prefix = strace_cmd + " "
            ip_server = 0x7F000001
            ip_client = ip_server

        return " ".join(
            [
                "{}{}{}/{} seed={} speaker_id={} speaker_addr={}  {}".format(
                    timeout_cmd,
                    prefix,
                    self.config["global_parameters"]["build_dir"],
                    self.name,
                    randomSeed,
                    speaker_id,
                    ip_client,
                    (
                        ""
                        if self.is_client
                        else "speaker_impl_id={}  speaker_impl_addr={}".format(
                            speaker_id_impl, ip_server
                        )
                    ),
                )
            ]
            + self.extra_args
            + ([""] if self.config["net_parameters"].getboolean("vnet") else [""])
        )
