#!/bin/bash

# #Install picotls
printf "\n\n"
printf "###### Installing PicoTLS:\n\n"
cd /quic/picotls/
git submodule init
git submodule update
cmake .
make
make check


# #Install picoquic
printf "\n\n"
printf "###### Installing PicoQUIC:\n\n"
cd /quic/picoquic/
cmake .
make
./picoquic_ct


#Install go
cd /
mkdir /logs
wget https://dl.google.com/go/go1.15.linux-amd64.tar.gz  &> /dev/null
tar xfz go1.15.linux-amd64.tar.gz &> /dev/null
rm go1.15.linux-amd64.tar.gz
export PATH="/go/bin:${PATH}"

cd /quic/quic-go/
echo "Build go 1"
#export GOPATH=$PWD
go mod init github.com/lucas-clemente/quic-go
echo "Build go 2"
go get ./...
echo "Build client go"
go build -o /client/client /quic/quic-go/custom/client.go
echo "Build server go"
go build -o /server/server /quic/quic-go/custom/server.go

# Install aioquic
cd /
cd /quic/aioquic
curl https://sh.rustup.rs -sSf | sh -s -- -y
export PYTHONPATH=$PWD
#pip3 install pyopenssl==19.0.0

python3 -m pip install --upgrade setuptools
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade cryptography
python3 -m pip install --upgrade cffi
pip3 install -e .
pip3 install aiofiles asgiref dnslib httpbin starlette wsproto
rm /quic/aioquic/examples/http3_client.py
cp /http3_client.py /quic/aioquic/examples/http3_client.py


#Install Quant
cd /
sudo apt remove --fix-missing -y cmake
wget https://github.com/Kitware/CMake/releases/download/v3.12.4/cmake-3.12.4-Linux-x86_64.sh  &> /dev/null
# tar xfz cmake-3.19.6-Linux-x86_64.tar.gz  &> /dev/null
# cd cmake-3.19.6-Linux-x86_64
# ./configure
# make
chmod +x cmake-3.12.4-Linux-x86_64.sh
mkdir /opt/cmake
bash cmake-3.12.4-Linux-x86_64.sh --skip-license --prefix=/opt/cmake
ln -s /opt/cmake/bin/cmake /usr/local/bin/cmake
cmake --version
# ls
# ln -s /opt/cmake-3.12.4-Linux-x86_64/bin/* /usr/local/bin
cd /quic/quant/
cmake --version
mkdir Debug 
cd Debug
cmake ..
make

# #Install mvfst
cd /
cd /quic/mvfst
bash build_helper.sh
git apply samples-build-patch.diff #Should not be here
cd /quic/mvfst/quic/samples
cmake .
make
cd /quic/mvfst/_build/build/quic/samples
make # -j 4 # Slower but dont crash the VM

# #Install boringssl
cd /
cd /quic/boringssl
cmake . &&  make
export BORINGSSL=$PWD

# #Install lsquic
cd /
cd /quic/lsquic
cmake -DBORINGSSL_DIR=$BORINGSSL .
make
make test


#Install Quinn
cd /quic/quinn
echo "Build quinn"
cargo clean
cargo build --examples
cargo test

#Install Quiche
cd /quic/quiche/
cargo clean
cargo build --examples
cargo test

#Update includes of python lib
cd /
echo "Update Includes"
bash update_include.sh


