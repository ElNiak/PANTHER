#!/bin/bash

cd /
# Clone Ivy project 
echo "----> Cloning Ivy"
git clone --recurse-submodules https://ElNiak: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@github.com/ElNiak/QUIC-Ivy.git --branch quic_29
mkdir /QUIC-Ivy/doc/examples/quic/build
mkdir /QUIC-Ivy/doc/examples/quic/test/temp
cd /
echo "----> Cloning Picotls"
# Clone picotls project 
git clone https://github.com/h2o/picotls.git 
cd /picotls
git checkout 47327f8d032f6bc2093a15c32e666ab6384ecca2 # 2464adadf28c1b924416831d24ca62380936a209 
git submodule init
git submodule update
echo "----> Cloning Picoquic"
# # Clone picoquic project 
cd /
git clone https://github.com/private-octopus/picoquic.git 
cd /picoquic 
git checkout ad23e6c3593bd987dcd8d74fc9f528f2676fedf4 
echo "----> Cloning quic-go"
#Clone quic-go project
cd /
# Install go
echo "----> Cloning go"
wget https://dl.google.com/go/go1.15.linux-amd64.tar.gz  &> /dev/null
tar xfz go1.15.linux-amd64.tar.gz &> /dev/null
rm go1.15.linux-amd64.tar.gz
#Install project
git clone https://github.com/lucas-clemente/quic-go
cd /quic-go
git checkout v0.20.0
export PATH="/go/bin:${PATH}"
mkdir client server
echo "----> Cloning aioquic"
# #Clone AIOQuic
cd /
git clone https://github.com/aiortc/aioquic.git
cd /aioquic
git checkout 0.9.3
echo "----> Cloning quant"
# #Clone Quant
cd /
git clone https://github.com/NTAP/quant.git --branch 29
cd /quant
git submodule update --init --recursive
echo "----> Cloning mvfst"
# #Clone mvfst
cd /
git clone https://github.com/facebookincubator/mvfst
mv tls-keys-patch.diff /mvfst
cd /mvfst
git checkout 36111c1
git apply tls-keys-patch.diff
echo "----> Cloning boring ssl"
# Clone boringssl project 
cd /
git clone https://boringssl.googlesource.com/boringssl
cd /boringssl 
git checkout a2278d4d2cabe73f6663e3299ea7808edfa306b9 
echo "----> Cloning lsquic"
#Clone LSQuic
cd /
git clone https://github.com/litespeedtech/lsquic.git
cd /lsquic
git checkout v2.29.4
git submodule init
git submodule update
echo "----> Cloning quinn"
#Clone Quinn
cd /
git clone --recursive https://github.com/quinn-rs/quinn.git 
cd /quinn
git checkout 0.7.0
echo "----> Cloning quiche"
#Clone Quiche
cd /
git clone --recursive https://github.com/cloudflare/quiche
cd /quiche
git checkout 0.7.0
