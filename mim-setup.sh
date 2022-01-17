PROOTPATH=$PWD
#sysctl -w net.ipv4.conf.all.route_localnet=1
sudo iptables -t nat -A OUTPUT -o lo -d 127.0.0.1 -p udp --dport 4443 ! --sport 4444 -j DNAT --to-destination 127.0.0.1:4444
#sudo iptables -t nat -A OUTPUT -o lo -d 127.0.0.1 -p udp --sport 4443 ! --dport 4444 -j DNAT --to-destination 127.0.0.1:4444

#sudo iptables -t nat -A OUTPUT -o lo -d 127.0.0.1 -p udp --dport 4444 -j DNAT --to-destination 127.0.0.1:4443



