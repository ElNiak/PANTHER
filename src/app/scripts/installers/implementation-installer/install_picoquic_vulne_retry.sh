
#Install picotls

cd $PROOTPATH/quic-implementations/
git clone https://github.com/h2o/picotls.git picotls-vuln

printf '%s\n' "-------------> Installing PicoTLS:"
export OPENSSL_INCLUDE_DIR=/usr/include/openssl
cd $PROOTPATH/quic-implementations/picotls-vuln/
git checkout 5e0f82e184f1ae79de58837819b13ea7ef89b6f1 # 47327f8d032f6bc2093a15c32e666ab6384ecca2
git submodule init
git submodule update
cmake .
make
make check

cd $PROOTPATH/quic-implementations/
git clone https://github.com/private-octopus/picoquic.git picoquic-vuln

#Install picoquic
printf '%s\n' "-------------> Installing PicoQUIC:"
cd $PROOTPATH/quic-implementations/picoquic-vuln/
git stash
git checkout 97687415c78f5cae4ea3ac6a7373e369415480ce # 639c9e685d37e74d357d3dd8599b9dbff90934af
cp $PROOTPATH/ressources/picoquic-vuln/CMakeLists.txt  $PROOTPATH/quic-implementations/picoquic-vuln/CMakeLists.txt
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
