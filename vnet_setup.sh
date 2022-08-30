#!/bin/sh

sudo core-cleanup > /dev/null 2>&1
sudo ip link set vbridge down > /dev/null 2>&1
sudo brctl delbr vbridge > /dev/null 2>&1
sudo pkill vcmd

sudo ip netns del n0;
sudo ip netns del n1;

sudo ip link set dev rmyveth0-out down
sudo ip link del dev rmyveth0-out
sudo ip link set dev rmyveth1-out down
sudo ip link del dev rmyveth1-out
sudo ip link set dev rmyveth2-out down
sudo ip link del dev rmyveth2-out
sudo ip link set dev rmyveth3-out down
sudo ip link del dev rmyveth3-out

sudo ip link add name vbridge type bridge 
sudo ip link set dev vbridge up
sudo ifconfig vbridge 10.0.0.1 netmask 255.255.255.0 up

#########################################################
# server node
# 
#
#########################################################

sudo ip netns add n0;
# create a virtual Ethernet (veth) pair, installing one end into node 0
sudo ip link add dev rmyveth0-out type veth peer name rmyveth0-in
sudo ip link set dev rmyveth0-in netns n0
sudo ip netns exec n0 ip addr add 10.0.1.1/24 dev rmyveth0-in;
sudo ip netns exec n0 ip link set dev rmyveth0-in up
sudo ip addr add 10.0.1.1/24 dev rmyveth0-out
sudo ip link set dev rmyveth0-out up
sudo ip link set dev rmyveth0-out master vbridge
sudo ip netns exec n0 ip link set dev lo up  

#########################################################
# client node
# 
#
#########################################################

sudo ip netns add n1;
# create a virtual Ethernet (veth) pair, installing one end into node 0
sudo ip link add dev rmyveth1-out type veth peer name rmyveth1-in
sudo ip link set dev rmyveth1-in netns n1
sudo ip netns exec n1 ip addr add 10.0.2.1/24 dev rmyveth1-in;
sudo ip netns exec n1 ip link set dev rmyveth1-in up
sudo ip addr add 10.0.2.1/24 dev rmyveth1-out
sudo ip link set dev rmyveth1-out up
sudo ip link set dev rmyveth1-out master vbridge
sudo ip netns exec n1 ip link set dev lo up  

#########################################################
# mitm node
# 
#
#########################################################

sudo ip link add dev rmyveth2-out type veth peer name rmyveth2-in
sudo ip link set dev rmyveth2-in netns n0
sudo ip netns exec n0 ip addr add 10.0.3.1/24 dev rmyveth2-in;
sudo ip netns exec n0 ip link set dev rmyveth2-in up
sudo ip addr add 10.0.3.1/24 dev rmyveth2-out
sudo ip link set dev rmyveth2-out up

#########################################################
# victim node
# 
#
#########################################################

sudo ip link add dev rmyveth3-out type veth peer name rmyveth3-in
sudo ip link set dev rmyveth3-in netns n0
sudo ip netns exec n0 ip addr add 10.0.4.1/24 dev rmyveth3-in;
sudo ip netns exec n0 ip link set dev rmyveth3-in up
sudo ip addr add 10.0.4.1/24 dev rmyveth3-out
sudo ip link set dev rmyveth3-out up

#########################################################
# Routing table
# 
#
#########################################################

# TODO all the routing table stuff not totally correct

# Add default gateway
ip netns exec red ip route add default via 10.0.2.1 dev rmyveth0-in
ip netns exec blue ip route add default via 10.0.1.1 dev rmyveth1-in

echo "Adding routing table entries for n0 10.0.2.1 NS"
sudo ip netns exec n0 ip route add 10.0.2.1/8 via 192.168.122.1 dev rmyveth0-in;
sudo ip netns exec n0 ip route add 10.0.2.1/24 via 10.0.2.1 dev rmyveth2-in;
sudo ip netns exec n0 ip route add 10.0.2.1/32 dev rmyveth3-in;
echo "Adding routing table entries for n0 10.0.2.1"
sudo ip route add 10.0.2.1/32 dev rmyveth0-out;
sudo ip route add 10.0.2.1/24 via 10.0.3.1 dev rmyveth2-out;
sudo ip route add 10.0.2.1/32 dev rmyveth3-out;
echo "Adding routing table entries for n0 10.0.3.1 NS"
sudo ip netns exec n0 ip route add 10.0.3.1/32 dev rmyveth3-in;
sudo ip netns exec n0 ip route add 10.0.3.1/32 dev rmyveth2-in;
sudo ip netns exec n0 ip route add 10.0.3.1/32 dev rmyveth0-in;
echo "Adding routing table entries for n0 10.0.3.1"
sudo ip route add 10.0.3.1/32 dev rmyveth3-out;
sudo ip route add 10.0.3.1/32 dev rmyveth2-out;
sudo ip route add 10.0.3.1/32 dev rmyveth0-out;
echo "Adding routing table entries for n0 10.0.4.1 NS"
sudo ip netns exec n0 ip route add 10.0.4.1/32 dev rmyveth3-in;
sudo ip netns exec n0 ip route add 10.0.4.1/32 dev rmyveth2-in;
sudo ip netns exec n0 ip route add 10.0.4.1/32 dev rmyveth0-in;
echo "Adding routing table entries for n0 10.0.4.1"
sudo ip route add 10.0.4.1/32 dev rmyveth3-out;
sudo ip route add 10.0.4.1/32 dev rmyveth2-out;
sudo ip route add 10.0.4.1/32 dev rmyveth0-out;

echo "Adding routing table entries for n1 10.0.1.1"
sudo ip netns exec n1 ip route add 10.0.1.1/32 dev rmyveth1-in;
sudo ip route add 10.0.1.1/32 dev rmyveth1-out;
sudo ip netns exec n1 ip route add 10.0.3.1/32 dev rmyveth1-in;
sudo ip route add 10.0.3.1/32 dev rmyveth1-out;
sudo ip netns exec n1 ip route add 10.0.4.1/32 dev rmyveth1-in;
sudo ip route add 10.0.4.1/32 dev rmyveth1-out;

ifconfig
sudo brctl show 
sudo ip route list

sudo ip netns exec n0 ping -I rmyveth0-in -4 -c 2 10.0.1.1
sudo ip netns exec n0 ping -I rmyveth0-in -4 -c 2 10.0.2.1
sudo ip netns exec n0 ping -I rmyveth0-in -4 -c 2 10.0.3.1 #BAD
sudo ip netns exec n0 ping -I rmyveth0-in -4 -c 2 10.0.4.1 #BAD

sudo ip netns exec n0 ping -I rmyveth2-in -4 -c 2 10.0.1.1 #BAD
sudo ip netns exec n0 ping -I rmyveth2-in -4 -c 2 10.0.2.1 #BAD
sudo ip netns exec n0 ping -I rmyveth2-in -4 -c 2 10.0.3.1
sudo ip netns exec n0 ping -I rmyveth2-in -4 -c 2 10.0.4.1 #BAD

sudo ip netns exec n0 ping -I rmyveth3-in -4 -c 2 10.0.1.1 #BAD
sudo ip netns exec n0 ping -I rmyveth3-in -4 -c 2 10.0.2.1 #BAD
sudo ip netns exec n0 ping -I rmyveth3-in -4 -c 2 10.0.3.1 #BAD
sudo ip netns exec n0 ping -I rmyveth3-in -4 -c 2 10.0.4.1


sudo ip netns exec n1 ping -4 -c 2 10.0.1.1
sudo ip netns exec n1 ping -4 -c 2 10.0.2.1
sudo ip netns exec n1 ping -4 -c 2 10.0.3.1
sudo ip netns exec n1 ping -4 -c 2 10.0.4.1


