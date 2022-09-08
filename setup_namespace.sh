#!/bin/bash

#set -x

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

ip netns del implem        
ip netns del ivy 


ip netns add ivy
ip netns add implem


ip link add ivy type veth peer name implem


ip link set ivy    netns ivy
ip link set implem netns implem


ip netns exec ivy    ip addr add 10.0.0.1/24 dev lo
ip netns exec ivy    ip addr add 10.0.0.2/24 dev ivy
ip netns exec ivy    ip addr add 10.0.0.3/24 dev lo
ip netns exec implem ip addr add 10.0.0.3/24 dev implem

ip netns exec ivy    ip link set ivy    up
ip netns exec implem ip link set implem up


ip netns exec ivy    ip link set dev ivy    up
ip netns exec implem ip link set dev implem up


ip netns exec ivy    ip link   set dev lo   up
ip netns exec implem ip link   set dev lo   up


ip netns exec ivy    ip route add 10.0.0.3 dev lo
ip netns exec implem ip route add 10.0.0.1 via 10.0.0.2


ip netns exec ivy    sysctl -w net.ipv4.conf.all.accept_local=1


ip netns exec ivy    ping        10.0.0.1 -c1
ip netns exec ivy    ping -I ivy 10.0.0.3 -c1

mitm() { #ns, src_ip, src_p, dst_ip, dst_p, l_dev, s_dev
  echo mitm
  msg=$(ip netns exec $1 ./listener -i "$4" -d $6 -p $5 -f)
  ip netns exec $1 ./sender -i "$4" -d $7 -p $5 -s "$2" -z $3 -m "mitmed($msg)"
}

server() {
  echo server
  msg=$(ip netns exec implem ./listener -i "10.0.0.3" -d "implem" -p 60443)
  ip netns exec implem ./sender -i "10.0.0.1" -d implem -p 60444 -s "10.0.0.3" -z 60443 -m "recv($msg)"
}

final() {
  ret=$(ip netns exec ivy ./listener -i "10.0.0.1" -d lo -p 60444)
  waited_ret="lo: mitmed(ivy: recv(implem: mitmed(lo: init)))"
  if [[ "$ret" == "$waited_ret" ]]
  then
    echo ok
  else
    echo ERROR
  fi
}

pkill listener
gcc sender.c -o sender -Werror -Wall
gcc listener.c -o listener -Werror -Wall

ifconfig
echo "--------------------------------------------------"
sudo ip netns exec ivy ifconfig
echo "--------------------------------------------------"
sudo ip netns exec implem ifconfig
echo "----"

#pkill wireshark
#ip netns exec ivy    wireshark -i any -Y udp 2>/dev/null &
#ip netns exec implem wireshark -i any -Y udp 2>/dev/null &
#read -p "Press [Enter] to continue..."

mitm ivy 10.0.0.1 60444 10.0.0.3 60443 lo ivy &
mitm ivy 10.0.0.3 60443 10.0.0.1 60444 ivy lo &
server &
final &
pid=$!

read -p "Press [Enter] to continue..."
ip netns exec ivy ./sender -i "10.0.0.3" -d lo -p 60443 -s "10.0.0.1" -z 60444 -m "init"

wait $pid





