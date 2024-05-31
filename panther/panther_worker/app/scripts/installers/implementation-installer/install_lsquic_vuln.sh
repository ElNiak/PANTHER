cd $PROOTPATH/quic-implementations/boringssl-vuln
export PATH="/go/bin:${PATH}"
git --work-tree=. stash
git fetch
git checkout a2278d4d2cabe73f6663e3299ea7808edfa306b9 
git submodule update --init --recursive
git submodule update --recursive
sudo apt-get update && \
sudo apt-get install -y build-essential software-properties-common \
                       zlib1g-dev libevent-dev

cmake . &&  make
export BORINGSS2L=$PWD

cd $PROOTPATH/quic-implementations/lsquic-vuln
git --work-tree=. stash
git fetch
git checkout v2.29.4
git submodule update --init --recursive
git submodule update --recursive
cp $PROOTPATH/ressources/lsquic/lsquic_types.h $PROOTPATH/quic-implementations/lsquic-vuln/include/lsquic_types.h
cmake -DBORINGSSL_DIR=$BORINGSS2L .
make
make test

