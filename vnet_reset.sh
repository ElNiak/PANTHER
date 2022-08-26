#!/bin/sh

# This scripe uses CORE to set up a virtual network with two nodes n0
# and n1 located respectively at ip addresses 10.0.0.1 and
# 10.0.0.2.

# sudo systemctl reload networking > /dev/null 2>&1
#sudo systemctl restart networking > /dev/null 2>&1

# sudo ip link set vbridge down > /dev/null 2>&1
# sudo ip link del vbridge  > /dev/null 2>&1
# # sudo pkill ip
# sudo ip link set dev rmyveth0 down
# sudo ip link del dev rmyveth0
# sudo ip link set dev rmyveth1 down
# sudo ip link del rmyveth1
# sudo ip link set dev n0.0 down
# sudo ip link del dev n0.0
# sudo ip link set dev n1.0 down
# sudo ip link del dev n1.0
# sudo brctl delbr vbridge > /dev/null 2>&1
# sudo ip netns pids n0 #| sudo xargs kill
# sudo ip netns pids n1 #| sudo xargs kill
# sudo ip -all netns del;

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