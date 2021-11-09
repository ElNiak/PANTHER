#install deps

cd ../..
PROOTPATH=$PWD
export PROOTPATH

printf '%s\n' "-------------> Installing dependencies: <-------------"
sudo apt-get -y install python python-pip libssl-dev python3-dev g++ cmake python-ply python-pygraphviz git python-tk tix gperf pkg-config libssl-dev doxygen libev-dev libhttp-parser-dev libbsd-dev faketime libscope-guard-perl libtest-tcp-perl libbrotli-dev
pip2 install pexpect
pip2 install gperf

sudo apt remove cmake
sudo snap install cmake --classic
cmake --version

printf '%s\n' "-------------> Init submodules: <-------------"

git submodule update --init --recursive

printf '%s\n' "-------------> Installing Ivy: <-------------"

cd QUIC-Ivy/
mkdir doc/examples/quic/build
mkdir doc/examples/quic/test/temp

sudo rm -r /usr/local/lib/python2.7/dist-packages && sudo mkdir /usr/local/lib/python2.7/dist-packages
python build_submodules.py
sudo pip2 install ms-ivy #global install

rm doc/examples/quic/test/test.py
cp $PROOTPATH/ressources/test.py $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/

cd $PROOTPATH/scripts/installers/implementation-installer/

printf '%s\n' "-------------> Installing picoquic: <-------------"

bash install_picoquic.sh

printf '%s\n' "-------------> Installing quant: <-------------"

bash install_quant.sh

printf '%s\n' "-------------> Installing quic-go: <-------------"

bash install_goquic.sh

printf '%s\n' "-------------> Installing aioquic: <-------------"

bash install_aioquic.sh

printf '%s\n' "-------------> Installing lsquic: <-------------"

bash install_lsquic.sh

printf '%s\n' "-------------> Installing quiche: <-------------"

bash install_quiche.sh

printf '%s\n' "-------------> Installing quinn: <-------------"

bash install_quinn.sh

printf '%s\n' "-------------> Installing mvfst: <-------------"

bash install_mvfst.sh