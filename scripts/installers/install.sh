#install deps

cd ../..
PROOTPATH=$PWD
export PROOTPATH

printf '%s\n' "-------------> Installing dependencies: <-------------"
sudo apt-get --fix-missing  -y install tzdata curl wget tar 
sudo apt-get install  --fix-missing  -y python2.7 python-pip g++ cmake python-ply python-pygraphviz git python-tk tix gperf pkg-config libssl-dev lsof
sudo apt-get install  --fix-missing  -y doxygen pkg-config faketime libscope-guard-perl libtest-tcp-perl libbrotli-dev
sudo apt-get install  --fix-missing  -y libev-dev libhttp-parser-dev libbsd-dev snapd
sudo apt-get install  --fix-missing  -y cmake wireshark tshark rand
sudo apt-get install  --fix-missing  -y binutils autoconf automake autotools-dev libtool pkg-config libev-dev libjemalloc-dev ca-certificates mime-support
sudo apt-get install  --fix-missing  -y libboost-all-dev libevent-dev libdouble-conversion-dev libgoogle-glog-dev libgflags-dev libiberty-dev liblz4-dev liblzma-dev
sudo apt-get install  --fix-missing  -y libsnappy-dev zlib1g-dev binutils-dev libjemalloc-dev libsodium-dev sudo
sudo apt-get install  --fix-missing  -y git python3 python3-dev python3-pip build-essential libffi-dev python-dev cargo
sudo apt-get install  --fix-missing  -y build-essential software-properties-common zlib1g-dev libevent-dev
sudo apt-get install  --fix-missing  -y python python-pip g++ cmake python-ply python-pygraphviz git python-tk tix pkg-config libssl-dev # TODO
sudo apt-get install  --fix-missing  -y libunwind-dev
sudo apt-get install --fix-missing  -y libssl-dev
sudo apt install --fix-missing  -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get install  --fix-missing  -y python3.9 python3.9-dev #python3.9-pip

sudo apt remove cmake -y
sudo snap remove cmake

pip3 uninstall progressbar2
pip3 uninstall progressbar
pip3 install progressbar2

sudo snap install cmake --classic
sudo apt-get install cmake
cmake --version
/usr/bin/cmake --version


# curl -fsSL https://bootstrap.pypa.io/pip/3.5/get-pip.py | python3.5

printf '%s\n' "-------------> Init submodules: <-------------"

git submodule update --init --recursive
git submodule update --recursive

printf '%s\n' "-------------> Installing Ivy: <-------------"

bash $PROOTPATH/scripts/installers/implementation-installer/install_ivy.sh

cd $PROOTPATH/scripts/installers/implementation-installer/

printf '%s\n' "-------------> Installing picoquic: <-------------"

bash install_picoquic.sh

printf '%s\n' "-------------> Installing picoquic vuln: <-------------"

# bash install_picoquic_vulne_retry.sh

printf '%s\n' "-------------> Installing quant: <-------------"
cd $PROOTPATH/scripts/installers/implementation-installer/
bash install_quant.sh

printf '%s\n' "-------------> Installing quant vuln: <-------------"

# bash install_quant_vulne.sh

printf '%s\n' "-------------> Installing quic-go: <-------------"
cd $PROOTPATH/scripts/installers/implementation-installer/
bash install_goquic.sh

printf '%s\n' "-------------> Installing lsquic: <-------------"
cd $PROOTPATH/scripts/installers/implementation-installer/
bash install_lsquic.sh 

printf '%s\n' "-------------> Installing quiche: <-------------"
#cmake 3.12
cd $PROOTPATH/scripts/installers/implementation-installer/
bash install_quiche.sh

printf '%s\n' "-------------> Installing quinn: <-------------"
cd $PROOTPATH/scripts/installers/implementation-installer/
#bash install_quinn.sh

printf '%s\n' "-------------> Installing aioquic: <-------------"
cd $PROOTPATH/scripts/installers/implementation-installer/
bash install_aioquic.sh

printf '%s\n' "-------------> Installing mvfst: <-------------"
cd $PROOTPATH/scripts/installers/implementation-installer/
bash install_mvfst.sh 

