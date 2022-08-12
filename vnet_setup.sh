#!/bin/sh

# This scripe uses CORE to set up a virtual network with two nodes n0
# and n1 located respectively at ip addresses 10.0.0.1 and
# 10.0.0.2.

# sudo pkill ip;
# sudo systemctl reload networking > /dev/null 2>&1
# sudo systemctl restart networking > /dev/null 2>&1

function clean_node  {
    sudo ip link set dev rmyveth$1 down
    sudo ip link del dev rmyveth$1
    sudo ip link set dev n$1.0 down
    sudo ip link del dev n$1.0
    sudo ip netns pids n$1
    sudo ip -all netns del;
} 

function clean_bridge {
    sudo ip link set vbridge down > /dev/null 2>&1
    sudo ip link del vbridge  > /dev/null 2>&1
    sudo brctl delbr vbridge > /dev/null 2>&1
}

function create_node {
    echo " --> Create a server node namespace container - node $1"
    sudo ip netns add n$1;
    # create a virtual Ethernet (veth) pair, installing one end into node 0
    sudo ip link add dev rmyveth$1 type veth peer name n$1.0
    sudo ip link set dev n$1.0 netns n$1
    sudo ip netns exec n$1 ip addr add $2 dev n$1.0;
    sudo ip netns exec n$1 ip link set dev n$1.0 up
    sudo ip addr add $2 dev rmyveth$1
    sudo ip link set dev rmyveth$1 up
    sudo ip link set dev rmyveth$1 master vbridge
}

function build_routes {
    echo " --> Build routes for node $1"
    array=("$@")
    for DEST in  "${array[@]}"; do
    :
        echo "  To $DEST"
        sudo ip netns exec n$1 ip route add $DEST/32 dev n$1.0;
        sudo ip route add $DEST/32 dev rmyveth$1;
    done
    sudo ip netns exec n$1 ip route list
    sudo ip route list
}

function test_connectivity {
    echo " --> Test connectivity for node $1"
    array=("$@")
    for DEST in  "${array[@]}"; do
    :
        echo "  To $DEST"
        sudo ip netns exec n$1 ping -4 -c 2 $DEST;
    done
}


clean_bridge
clean_node 0; # server
clean_node 1; # client
clean_node 2; # server
clean_node 3; # client

echo "Set bridge"
# bridge together nodes using the other end of each veth pair
sudo ip link add name vbridge type bridge 
sudo ip link set dev vbridge up

create_node 0 10.0.0.1; # server
create_node 1 10.0.0.2; # client
create_node 2 10.0.0.3; # victim
create_node 3 10.0.0.4; # mim agent

dest=(10.0.0.2 10.0.0.3 10.0.0.4)
build_routes 0 "${dest[@]}"
dest=(10.0.0.1 10.0.0.3 10.0.0.4)
build_routes 1 "${dest[@]}"
dest=(10.0.0.1 10.0.0.2 10.0.0.4)
build_routes 2 "${dest[@]}"
dest=(10.0.0.1 10.0.0.3 10.0.0.2)
build_routes 3 "${dest[@]}"

ifconfig

sudo brctl show 

dest=(10.0.0.2 10.0.0.3 10.0.0.4)
test_connectivity 0 "${dest[@]}"
dest=(10.0.0.1 10.0.0.3 10.0.0.4)
test_connectivity 1 "${dest[@]}"
dest=(10.0.0.1 10.0.0.2 10.0.0.4)
test_connectivity 2 "${dest[@]}"
dest=(10.0.0.1 10.0.0.3 10.0.0.2)
test_connectivity 3 "${dest[@]}"
