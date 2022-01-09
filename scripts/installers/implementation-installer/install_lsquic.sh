cd $PROOTPATH/quic-implementations/boringssl
export PATH="/go/bin:${PATH}"
git checkout a2278d4d2cabe73f6663e3299ea7808edfa306b9 
sudo apt-get update && \
sudo apt-get install -y build-essential software-properties-common \
                       zlib1g-dev libevent-dev

cmake . &&  make
export BORINGSSL=$PWD

cd $PROOTPATH/quic-implementations/lsquic
git checkout v2.29.4
cp $PROOTPATH/ressources/lsquic/lsquic_types.h $PROOTPATH/quic-implementations/lsquic/include/lsquic_types.h
cmake -DBORINGSSL_DIR=$BORINGSSL .
make
make test

