#!/bin/sh

ip netns del implem        
ip netns del ivy 


ip netns add ivy
ip netns add implem


ip link add ivy type veth peer name implem


ip link set ivy    netns ivy
ip link set implem netns implem


# ip netns exec ivy    ip addr add 10.0.0.1/24 dev lo
ip netns exec ivy    ip addr add 10.0.0.1/24 dev ivy
# ip netns exec ivy    ip addr add 10.0.0.3/24 dev lo
ip netns exec implem ip addr add 10.0.0.3/24 dev implem

ip netns exec ivy    ip link set ivy    up
ip netns exec implem ip link set implem up


ip netns exec ivy    ip link set dev ivy    up
ip netns exec implem ip link set dev implem up


ip netns exec ivy    ip link   set dev lo   up
ip netns exec implem ip link   set dev lo   up


# ip netns exec ivy    ip route add 10.0.0.3 dev lo
# ip netns exec implem ip route add 10.0.0.1 via 10.0.0.2


# ip netns exec ivy    sysctl -w net.ipv4.conf.all.accept_local=1


ip netns exec ivy    ping   10.0.0.1 -c1
ip netns exec ivy    ping -I ivy 10.0.0.3 -c1
ip netns exec implem ping -I implem  10.0.0.1 -c1.
ip netns exec implem ping   10.0.0.1 -c1