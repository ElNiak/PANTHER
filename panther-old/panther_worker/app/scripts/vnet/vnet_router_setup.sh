
sudo ip netns del n0;
sudo ip netns del n1;
sudo ip netns del router;

sudo ip link set dev veth-ivy-out down
sudo ip link del dev veth-ivy-out
sudo ip link set dev veth-iut-out down
sudo ip link del dev veth-iut-out
sudo ip link set dev veth-mim-out down
sudo ip link del dev veth-mim-out

sudo ip link set dev veth0-out down
sudo ip link del dev veth0-out
sudo ip link set dev veth1-out down
sudo ip link del dev veth1-out
sudo ip link set dev veth2-out down
sudo ip link del dev veth2-out

sudo ip netns add n0;
sudo ip netns exec n0 ip link set dev lo up  
sudo ip netns add router;
sudo ip netns exec router ip link set dev lo up  
sudo ip netns add n1;
sudo ip netns exec n1 ip link set dev lo up  


# We assume mim already setup routing attack

#########################################################
# Router node
# 
#
#########################################################

sudo ip link add dev veth-ivy-out type veth peer name veth-ivy-in
sudo ip link set dev veth-ivy-in netns router;
sudo ip netns exec router ip addr add 10.0.1.1/32 dev veth-ivy-in;
sudo ip netns exec router ip link set dev veth-ivy-in up
sudo ip addr add 10.0.1.1/32 dev veth-ivy-out
sudo ip link set dev veth-ivy-out up

sudo ip link add dev veth-mim-out type veth peer name veth-mim-in
sudo ip link set dev veth-mim-in netns router;
sudo ip netns exec router ip addr add 10.0.2.1/32 dev veth-mim-in;
sudo ip netns exec router ip link set dev veth-mim-in up
sudo ip addr add 10.0.2.1/32 dev veth-mim-out
sudo ip link set dev veth-mim-out up

sudo ip link add dev veth-iut-out type veth peer name veth-iut-in
sudo ip link set dev veth-iut-in netns router;
sudo ip netns exec router ip addr add 10.0.3.1/32 dev veth-iut-in;
sudo ip netns exec router ip link set dev veth-iut-in up
sudo ip addr add 10.0.3.1/32 dev veth-iut-out
sudo ip link set dev veth-iut-out up

#########################################################
# Ivy node
# 
#
#########################################################

sudo ip link add dev veth0-out type veth peer name veth0-in
sudo ip link set dev veth0-in netns n0;
sudo ip netns exec n0 ip addr add 10.0.1.2/32 dev veth0-in;
sudo ip netns exec n0 ip link set dev veth0-in up
sudo ip addr add 10.0.1.2/32 dev veth0-out
sudo ip link set dev veth0-out up

#########################################################
# Ivy MitM node
# 
#
#########################################################

sudo ip link add dev veth1-out type veth peer name veth1-in
sudo ip link set dev veth1-in netns n0;
sudo ip netns exec n0 ip addr add 10.0.2.2/32 dev veth1-in;
sudo ip netns exec n0 ip link set dev veth1-in up
sudo ip addr add 10.0.2.2/32 dev veth1-out
sudo ip link set dev veth1-out up

#########################################################
# IUT node
# 
#
#########################################################

sudo ip link add dev veth2-out type veth peer name veth2-in
sudo ip link set dev veth2-in netns n1;
sudo ip netns exec n1 ip addr add 10.0.3.2/32 dev veth2-in;
sudo ip netns exec n1 ip link set dev veth2-in up
sudo ip addr add 10.0.3.2/32 dev veth2-out
sudo ip link set dev veth2-out up

#########################################################
# Routing table
# 
#
#########################################################

sudo ip link add dev veth-ivy-out type veth peer name veth0-out
sudo ip link add dev veth-iut-out type veth peer name veth1-out
sudo ip link add dev veth-mim-out type veth peer name veth3-out

sudo ip netns exec n0 ip route add 10.0.1.1 dev veth0-in;
sudo ip route add 10.0.1.1/32 dev veth0-out;
sudo ip netns exec n0 ip route add 10.0.2.1 dev veth1-in;
sudo ip route add 10.0.2.1/32 dev veth1-out;
sudo ip netns exec n1 ip route add 10.0.3.1 dev veth2-in;
sudo ip route add 10.0.3.1/32 dev veth2-out;

sudo ip netns exec router ip route add 10.0.3.2 dev veth-iut-in;
sudo ip route add 10.0.3.2/32 dev veth-iut-out;

sudo ip netns exec router ip route add 10.0.2.2 dev veth-mim-in;
sudo ip route add 10.0.2.2/32 dev veth-mim-out;

sudo ip netns exec router ip route add 10.0.1.2 dev veth-ivy-in;
sudo ip route add 10.0.1.2/32 dev veth-ivy-out;


ifconfig
echo "--------------------------------------------------"
sudo ip netns exec n1 ifconfig
echo "--------------------------------------------------"
sudo ip netns exec n0 ifconfig
echo "--------------------------------------------------"
sudo ip netns exec router ifconfig

echo "--------------------------------------------------"
sudo ip netns exec router ping -4 -c 2 10.0.1.2
sudo ip netns exec router ping -4 -c 2 10.0.2.2
sudo ip netns exec router ping -4 -c 2 10.0.3.2
echo "--------------------------------------------------"
ping  -4 -c 2 10.0.1.2
ping  -4 -c 2 10.0.2.2
ping  -4 -c 2 10.0.3.2

echo "--------------------------------------------------"
sudo ip netns exec n0 ping -4 -c 2 10.0.1.1
sudo ip netns exec n0 ping -4 -c 2 10.0.2.1
sudo ip netns exec n1 ping -4 -c 2 10.0.3.1