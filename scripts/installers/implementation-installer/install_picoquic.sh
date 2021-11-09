
#Install picotls
printf '%s\n' "-------------> Installing PicoTLS:"
cd $PROOTPATH/quic-implementations/picotls/
# git checkout 2464adadf28c1b924416831d24ca62380936a209
# git submodule init
# git submodule update
cmake .
make
make check

#Install picoquic
printf '%s\n' "-------------> Installing PicoQUIC:"
cd $PROOTPATH/quic-implementations/picoquic/
# git checkout 639c9e685d37e74d357d3dd8599b9dbff90934af 
cmake .
make
./picoquic_ct
