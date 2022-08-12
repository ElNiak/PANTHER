PROOTPATH=$PWD
#sysctl -w net.ipv4.conf.all.route_localnet=0
echo "mim reset"
sudo iptables -t nat -F