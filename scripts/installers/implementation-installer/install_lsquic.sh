cd $PROOTPATH/quic-implementations/boringssl
git checkout a2278d4d2cabe73f6663e3299ea7808edfa306b9 
sudo apt-get update && \
sudo apt-get install -y build-essential software-properties-common \
                       zlib1g-dev libevent-dev

cmake . &&  make
export BORINGSSL=$PWD
export PATH="/go/bin:${PATH}"

cd $PROOTPATH/quic-implementations/lsquic
git checkout v2.29.4
cmake -DBORINGSSL_DIR=$BORINGSSL .
make
make test

