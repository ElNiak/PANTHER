
#Install picotls
printf '%s\n' "-------------> Installing PicoTLS:"
export OPENSSL_INCLUDE_DIR=/usr/include/openssl
cd $PROOTPATH/quic-implementations/picotls/
git checkout 47327f8d032f6bc2093a15c32e666ab6384ecca2 # 2464adadf28c1b924416831d24ca62380936a209
git submodule init
git submodule update
cmake .
make
make check

#Install picoquic
printf '%s\n' "-------------> Installing PicoQUIC:"
cd $PROOTPATH/quic-implementations/picoquic/
git checkout ad23e6c3593bd987dcd8d74fc9f528f2676fedf4 # 639c9e685d37e74d357d3dd8599b9dbff90934af 
cmake .
make
./picoquic_ct
