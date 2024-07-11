import subprocess
import panther_utils.netns
import logging

logger = logging.getLogger(__name__)

ivy_prefix = "ip netns exec ivy"

setup = [
    # Create new network namespaces named "ivy" and "implem"
    "ip netns add ivy",
    "ip netns add implem",
    # Create a pair of connected virtual Ethernet (veth) interfaces named "ivy" and "implem"
    "ip link add ivy type veth peer name implem",
    # Assign one end of the veth pair ("ivy") to the "ivy" namespace
    "ip link set ivy    netns ivy",
    # Assign the other end of the veth pair ("implem") to the "implem" namespace
    "ip link set implem netns implem",
    # Assign IP addresses to the veth interfaces within their respective namespaces
    "ip netns exec ivy    ip addr add 10.0.0.1/24 dev ivy",
    "ip netns exec implem ip addr add 10.0.0.2/24 dev implem",
    # Bring up the veth interfaces in their respective namespaces
    "ip netns exec ivy    ip link set ivy up",
    "ip netns exec implem ip link set implem up",
    # Ensure the veth interfaces are up (redundant but ensures the interfaces are active)
    "ip netns exec ivy    ip link set dev ivy up",
    "ip netns exec implem ip link set dev implem up",
    # Bring up the loopback interfaces within the namespaces
    "ip netns exec ivy    ip link set dev lo up",
    "ip netns exec implem ip link set dev lo up",
    "ip netns exec ivy           ip addr",
    "ip netns exec implem        ip addr",
    "ip netns exec ivy           ip route",
    "ip netns exec implem        ip route",
    # Test connectivity by pinging from the "ivy" namespace to its own veth interface
    "ip netns exec ivy ping 10.0.0.1 -c1",
    # Test connectivity by pinging from the "ivy" namespace to the "implem" namespace
    "ip netns exec ivy    ping -I ivy 10.0.0.2 -c1",
    # Test connectivity by pinging from the "implem" namespace to the "ivy" namespace
    "ip netns exec implem ping -I implem 10.0.0.1 -c1",
    # Test connectivity by pinging from the "implem" namespace to its own veth interface
    "ip netns exec implem ping 10.0.0.1 -c1",
]

reset = [
    # Delete the network namespaces named "ivy" and "implem"
    "ip netns del ivy",
    "ip netns del implem",
]

# Ivy spec send on lo
# Ivy mim spec send on lo to reach Ivy spec
# Ivy mim spec send on ivy to reach implem
# implem send on implem to reach ivy mim spec
setup_mim_ivy = [
    # Create new network namespaces named "ivy" and "implem"
    "ip netns add ivy",
    "ip netns add implem",
    # Create a pair of connected virtual Ethernet (veth) interfaces named "ivy" and "implem"
    "ip link add ivy type veth peer name implem",
    # Assign one end of the veth pair ("ivy") to the "ivy" namespace
    "ip link set ivy    netns ivy",
    # Assign the other end of the veth pair ("implem") to the "implem" namespace
    "ip link set implem netns implem",
    # Assign multiple IP addresses to interfaces within the "ivy" namespace
    "ip netns exec ivy ip addr add 10.0.0.1/24 dev lo",  # Add IP address to loopback interface
    "ip netns exec ivy ip addr add 10.0.0.2/24 dev ivy",  # Add IP address to veth interface
    "ip netns exec ivy ip addr add 10.0.0.3/24 dev lo",  # Add another IP address to loopback interface
    # Assign an IP address to the veth interface within the "implem" namespace
    "ip netns exec implem ip addr add 10.0.0.3/24 dev implem",
    # Bring up the veth interfaces in their respective namespaces
    "ip netns exec ivy    ip link set ivy up",
    "ip netns exec implem ip link set implem up",
    # Ensure the veth interfaces are up (redundant but ensures the interfaces are active)
    "ip netns exec ivy    ip link set dev ivy up",
    "ip netns exec implem ip link set dev implem up",
    # Bring up the loopback interfaces within the namespaces
    "ip netns exec ivy    ip link set dev lo up",
    "ip netns exec implem ip link set dev lo up",
    "ip netns exec ivy    ip link show",
    "ip netns exec implem ip link show",
    # Add routing rules within the namespaces
    "ip netns exec ivy    ip route add 10.0.0.3 dev lo",  # Route for ivy to reach 10.0.0.3 via loopback
    "ip netns exec implem ip route add 10.0.0.1 via 10.0.0.2",  # Route for implem to reach 10.0.0.1 via 10.0.0.2
    # Enable the acceptance of locally generated packets by all interfaces within the "ivy" namespace
    "ip netns exec ivy sysctl -w net.ipv4.conf.all.accept_local=1",
    # Test connectivity by pinging from the "ivy" namespace to its own IP addresses
    "ip netns exec ivy ping 10.0.0.1 -c1",
    "ip netns exec ivy ping -I ivy 10.0.0.3 -c1",
]


setup_mim = [
    "ip netns add ivy",
    "ip netns add tested_client",
    "ip netns add tested_server",
    # Create pairs of connected virtual Ethernet (veth) interfaces
    "ip link add ivy_client      type veth peer name client_ivy",
    "ip link add ivy_server      type veth peer name server_ivy",
    "ip link add client_server   type veth peer name server_client",
    # Verify that the veth pairs were created successfully
    "ip link show ivy_client",
    "ip link show client_ivy",
    "ip link show ivy_server",
    "ip link show server_ivy",
    "ip link show client_server",
    "ip link show server_client",
    # Assign one end of the veth pairs to their respective namespaces
    "ip link set ivy_client      netns ivy",
    "ip link set client_ivy      netns tested_client",
    "ip link set ivy_server      netns ivy",
    "ip link set server_ivy      netns tested_server",
    "ip link set client_server   netns tested_client",
    "ip link set server_client   netns tested_server",
    # Verify that the veth pairs were assigned to namespaces successfully
    "ip netns exec ivy                  ip addr",
    "ip netns exec tested_client        ip addr",
    "ip netns exec tested_server        ip addr",
    # Assign IP addresses to the veth interfaces within their respective namespaces
    "ip netns exec ivy                  ip addr add 10.0.0.1/24 dev ivy_client",
    "ip netns exec ivy                  ip addr add 10.0.0.3/24 dev ivy_server",
    "ip netns exec tested_client        ip addr add 10.0.0.2/24 dev client_ivy",
    "ip netns exec tested_client        ip addr add 10.0.0.5/24 dev client_server",
    "ip netns exec tested_server        ip addr add 10.0.0.4/24 dev server_ivy",
    "ip netns exec tested_server        ip addr add 10.0.0.6/24 dev server_client",
    # Verify IP addresses
    "ip netns exec ivy                  ip addr",
    "ip netns exec tested_client        ip addr",
    "ip netns exec tested_server        ip addr",
    # Bring up the veth interfaces in their respective namespaces
    "ip netns exec ivy                  ip link set ivy_client up",
    "ip netns exec ivy                  ip link set ivy_server up",
    "ip netns exec tested_client        ip link set client_ivy up",
    "ip netns exec tested_client        ip link set client_server up",
    "ip netns exec tested_server        ip link set server_ivy up",
    "ip netns exec tested_server        ip link set server_client up",
    # Verify interfaces are up
    "ip netns exec ivy                  ip addr",
    "ip netns exec tested_client        ip addr",
    "ip netns exec tested_server        ip addr",
    # Bring up the loopback interfaces within the namespaces
    "ip netns exec ivy                  ip link set dev lo up",
    "ip netns exec tested_client        ip link set dev lo up",
    "ip netns exec tested_server        ip link set dev lo up",
    # Enable IP forwarding on ivy namespace to facilitate ARP spoofing
    "ip netns exec ivy                  sysctl -w net.ipv4.ip_forward=1",
    "ip netns exec tested_client        sysctl -w net.ipv4.ip_forward=1",
    "ip netns exec tested_server        sysctl -w net.ipv4.ip_forward=1",
    # Verify loopback interfaces
    "ip netns exec ivy                  ip addr",
    "ip netns exec tested_client        ip addr",
    "ip netns exec tested_server        ip addr",
    "ip netns exec ivy                  ip route",
    "ip netns exec tested_client        ip route",
    "ip netns exec tested_server        ip route",
    # Add routes to enable communication between the namespaces
    "ip netns exec tested_client ip route add 10.0.0.6/32 dev client_server",  # client to server
    "ip netns exec tested_server ip route add 10.0.0.1/32 dev server_ivy",  # server to ivy
    "ip netns exec tested_server ip route add 10.0.0.2/32 dev server_client",  # server to client
    "ip netns exec tested_server ip route add 10.0.0.5/32 dev server_client",  # server to client
    # Add routes in ivy to forward packets between client and server
    "ip netns exec ivy ip route add 10.0.0.2/32 via 10.0.0.1 dev ivy_client",  # ivy to client
    "ip netns exec ivy ip route add 10.0.0.4/32 via 10.0.0.3 dev ivy_server",  # ivy to server
    "ip netns exec ivy ip route add 10.0.0.5/32 via 10.0.0.1 dev ivy_client",  # ivy to client
    "ip netns exec ivy ip route add 10.0.0.6/32 via 10.0.0.3 dev ivy_server",  # ivy to server
    # Test connectivity by pinging between namespaces
    "ip netns exec tested_client ping -c 3 10.0.0.6",  # client to server
    "ip netns exec tested_server ping -c 3 10.0.0.3",  # server to ivy
    "ip netns exec tested_server ping -c 3 10.0.0.5",  # server to client
    "ip netns exec ivy ping -c 3 10.0.0.2",  # ivy to client
    "ip netns exec ivy ping -c 3 10.0.0.4"  # ivy to server
    "ip netns exec ivy                  ip route",
    "ip netns exec tested_client        ip route",
    "ip netns exec tested_server        ip route",
    # Test connectivity by pinging from each namespace to its own veth interface
    "ip netns exec ivy                  ping 10.0.0.1 -c1",
    "ip netns exec tested_client        ping 10.0.0.2 -c1",
    "ip netns exec ivy                  ping 10.0.0.3 -c1",
    "ip netns exec tested_server        ping 10.0.0.4 -c1",
    "ip netns exec tested_client        ping 10.0.0.5 -c1",
    "ip netns exec tested_server        ping 10.0.0.6 -c1",
    # Test connectivity between namespaces
    "ip netns exec ivy                  ping -I ivy_client 10.0.0.2 -c1",  # ivy to client
    "ip netns exec ivy                  ping -I ivy_server 10.0.0.4 -c1",  # ivy to server
    "ip netns exec tested_client        ping -I client_ivy 10.0.0.1 -c1",  # client to ivy
    "ip netns exec tested_client        ping -I client_server 10.0.0.6 -c1",  # client to server
    "ip netns exec tested_server        ping -I server_ivy 10.0.0.3 -c1",  # server to ivy
    "ip netns exec tested_server        ping -I server_client 10.0.0.5 -c1",  # server to client
    # Install and run ARP spoofing (requires arpspoof utility from dsniff package)
    # "ip netns exec ivy                  arpspoof -i ivy_client -t 10.0.0.2 10.0.0.4 &",
    # "ip netns exec ivy                  arpspoof -i ivy_server -t 10.0.0.4 10.0.0.2 &"
]

reset_mim = [
    "ip netns del ivy",
    "ip netns del tested_server",
    "ip netns del tested_client",
]


def run_steps(steps, ignore_errors=False):
    for step in steps:
        try:
            logger.info("+ {}".format(step))
            subprocess.check_call(step, shell=True)
        except subprocess.CalledProcessError:
            if ignore_errors:
                pass
            else:
                raise
