PROOTPATH=$PWD
#sysctl -w net.ipv4.conf.all.route_localnet=1
echo "mim setup"
# TODO more dynamic 

# iptables -A INPUT -j LOG
# iptables -A OUTPUT -j LOG

bash mim-reset.sh

sudo iptables -t nat -I OUTPUT -t raw -p udp --sport 4443 -j CT --notrack
sudo iptables -t nat -I PREROUTING -t raw -p udp --dport 4443 -j CT --notrack

sudo iptables -t nat -P PREROUTING ACCEPT
sudo iptables -t nat -P POSTROUTING ACCEPT
sudo iptables -t nat -P OUTPUT ACCEPT

# Incoming traffic to 4443 is redirect to 4440 exept if it is from 4440
# "If you want to access the port 4443 from the same machine as well, you'll need to add an OUTPUT"
#sudo iptables -t nat -A POSTROUTING -o lo -d 127.0.0.1 -p udp --sport 4439 -j REDIRECT --to-port 4443
# sudo iptables -t nat -A INPUT -d 127.0.0.1 -p udp --sport 4439:4439 -j SNAT --to-source 127.0.0.1:4443
sudo iptables -t nat -A POSTROUTING -o lo -d 127.0.0.1 -p udp --sport 4439:4439 -j SNAT --to-source 127.0.0.1:4443 # error in localhost
#sudo iptables -t nat -A PREROUTING -i lo -d 127.0.0.1 -p udp --dport 4439:4439 -j REDIRECT --to-port 4443
#sudo iptables -t nat -A OUTPUT -o lo -d 127.0.0.1 -p udp --sport  4439:4439 -j DNAT --to-destination 127.0.0.1:4443
sudo iptables -t nat -A OUTPUT -o lo -d 127.0.0.1 -p udp --dport 4443:4443 ! --sport 4440:4440 -j DNAT --to-destination 127.0.0.1:4440


# sudo iptables -t nat -A PREROUTING -d 127.0.0.1 -p udp --dport 4443 ! --sport 4440 -j DNAT --to-destination 127.0.0.1:4440
# sudo iptables -t nat -A POSTROUTING -o lo -d 127.0.0.1 -p udp --sport 4440 -j SNAT --to-source 127.0.0.1:4443


#sudo iptables -t nat -A OUTPUT -o lo -d 127.0.0.1 -p udp --sport 4443 ! --dport 4444 -j DNAT --to-destination 127.0.0.1:4444
#sudo iptables -t nat -A OUTPUT -o lo -d 127.0.0.1 -p udp --dport 4444 -j DNAT --to-destination 127.0.0.1:4443



