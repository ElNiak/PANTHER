
#Install picotls
printf '%s\n' "-------------> Installing PicoTLS:"
export OPENSSL_INCLUDE_DIR=/usr/include/openssl
cd $PROOTPATH/quic-implementations/picotls/
git checkout 2464adadf28c1b924416831d24ca62380936a209 # 47327f8d032f6bc2093a15c32e666ab6384ecca2
git submodule init
git submodule update
cmake .
make
make check



#Install picoquic
printf '%s\n' "-------------> Installing PicoQUIC:"
cd $PROOTPATH/quic-implementations/picoquic/
git stash
git checkout 639c9e685d37e74d357d3dd8599b9dbff90934af # 639c9e685d37e74d357d3dd8599b9dbff90934af
sudo snap remove cmake
sudo apt remove cmake
sudo apt-get install cmake
#sudo snap install cmake --classic 
cmake --version

cmake .
make
./picoquic_ct

# sudo apt remove cmake
# sudo snap remove cmake
# sudo apt install cmake
