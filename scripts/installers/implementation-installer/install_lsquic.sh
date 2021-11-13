cd $PROOTPATH/quic-implementations/boringssl

sudo apt-get update && \
sudo apt-get install -y build-essential software-properties-common \
                       zlib1g-dev libevent-dev

cmake . &&  make
export BORINGSSL=$PWD
export PATH="/go/bin:${PATH}"

cd $PROOTPATH/quic-implementations/lsquic
cmake -DBORINGSSL_DIR=$BORINGSSL .
make
make test

