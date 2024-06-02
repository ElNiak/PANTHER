cd $PROOTPATH/quic-implementations/boringssl
export PATH="/go/bin:${PATH}"
git stash
git fetch
git checkout a9670a8b476470e6f874fef3554e8059683e1413 
sudo apt-get update && \
sudo apt-get install -y build-essential software-properties-common \
                       zlib1g-dev libevent-dev

cmake . &&  make
export BORINGSSL=$PWD

cd $PROOTPATH/quic-implementations/lsquic
git stash
git fetch
git checkout 0a4f8953dc92dd3085e48ed90f293f052cff8427
cp $PROOTPATH/ressources/lsquic/rfc9000/lsquic_types.h $PROOTPATH/quic-implementations/lsquic/include/lsquic_types.h
cmake -DBORINGSSL_DIR=$BORINGSSL .
make
make test

