cd $PROOTPATH/quic-implementations/
sudo apt remove --fix-missing -y cmake
wget https://github.com/Kitware/CMake/releases/download/v3.12.4/cmake-3.12.4-Linux-x86_64.sh  &> /dev/null
chmod +x cmake-3.12.4-Linux-x86_64.sh
mkdir /opt/cmake
bash cmake-3.12.4-Linux-x86_64.sh --skip-license --prefix=/opt/cmake
ln -s /opt/cmake/bin/cmake /usr/local/bin/cmake
cmake --version

cd $PROOTPATH/quic-implementations/quant/
git submodule update --init --recursive
mkdir Debug 
cd Debug
cmake ..
make

