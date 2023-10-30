cd quic/
[ ! -f pquic/ ] && git clone https://github.com/p-quic/pquic.git 

sudo rm -r picotls/
git clone https://github.com/p-quic/picotls.git

sudo apt-get install libarchive-dev gperf
sudo apt-get install libgoogle-perftools-dev 

#Install picotls
printf "\n\n"
printf "###### Installing PicoTLS:\n\n"
cd $HOME/TVOQE_UPGRADE_27/quic/picotls/
git checkout adf6fa1befb73769f5de590609fd1d82e2ab326f
git submodule init
git submodule update
cmake .
make
make check


printf "\n\n"
printf "###### Installing PQUIC \n\n"
cd $HOME/TVOQE_UPGRADE_27/quic/pquic/
git checkout master #99eede2016caf86016e7d75f5502b89217f52d3b
git submodule update --init
cd ubpf/vm
make
cd ../..
cd picoquic/michelfralloc
make
cd ../..
cmake .
make


