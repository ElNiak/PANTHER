
#Install picotls
printf '%s\n' "-------------> Installing PicoTLS:"
export OPENSSL_INCLUDE_DIR=/usr/include/openssl
cd $PROOTPATH/quic-implementations/picotls/
git stash
git fetch
git checkout 047c5fe20bb9ea91c1caded8977134f19681ec76 # 47327f8d032f6bc2093a15c32e666ab6384ecca2
git submodule init
git submodule update
cmake .
make
make check


#Install picoquic
printf '%s\n' "-------------> Installing PicoQUIC:"
cd $PROOTPATH/quic-implementations/picoquic/
git stash
git fetch
git checkout bb67995f2d7c0e577c2c8788313c3b580d3df9a7 # 639c9e685d37e74d357d3dd8599b9dbff90934af
cp $PROOTPATH/ressources/picoquic/rfc9000/picoquic_internal.h  $PROOTPATH/quic-implementations/picoquic/picoquic/picoquic_internal.h

# sudo snap remove cmake
# sudo apt remove cmake
# sudo apt-get install cmake
/usr/bin/cmake --version
#sudo snap install cmake --classic 


/usr/bin/cmake .
make
./picoquic_ct

# sudo apt remove cmake
# sudo snap remove cmake
# sudo apt install cmake
