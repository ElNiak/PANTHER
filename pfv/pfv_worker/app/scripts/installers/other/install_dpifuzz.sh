#!/bin/sh
sudo apt-get install -y tcpdump
sudo apt-get install -y libpcap-dev
sudo apt-get install faketime libscope-guard-perl libtest-tcp-perl
sudo apt-get install make
sudo apt-get install cmake
sudo apt-get install build-essential
sudo apt-get install pkg-config
sudo apt-get install libssl-dev


export GOPATH=`pwd`
echo export GOPATH=`pwd` >> ~/.profile 
export GOROOT=/usr/local/go
export GOPATH=$HOME/TVOQE_UPGRADE_27/quic/go
export PATH=$PATH:$GOROOT/bin:$GOPATH/bin

go get -u github.com/QUIC-Tracker/quic-tracker  # This will fail because of the missing dependencies that should be build using the 4 lines below
cd $GOPATH/src/github.com/mpiraux/pigotls
make
cd $GOPATH/src/github.com/mpiraux/ls-qpack-go
make
cd $GOPATH/src/github.com/QUIC-Tracker
rm -rf quic-tracker
git clone https://github.com/piano-man/DPIFuzz.git
mv ./DPIFuzz ./quic-tracker
cd $GOPATH/src/github.com/QUIC-Tracker/quic-tracker
