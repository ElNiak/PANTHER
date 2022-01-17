sudo apt remove --fix-missing -y cmake
wget https://github.com/Kitware/CMake/releases/download/v3.12.4/cmake-3.12.4-Linux-x86_64.sh  &> /dev/null
chmod +x cmake-3.12.4-Linux-x86_64.sh
mkdir /opt/cmake
bash cmake-3.12.4-Linux-x86_64.sh --skip-license --prefix=/opt/cmake
ln -s /opt/cmake/bin/cmake /usr/local/bin/cmake
cmake --version

cd $PROOTPATH/quic-implementations/
# install RUST
curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env
cd quiche/
git stash
git checkout 0.7.0 # master #
git submodule update --init
cp $PROOTPATH/ressources/quiche/packet.rs src/packet.rs
#cp $PROOTPATH/ressources/quiche/master/packet.rs src/packet.rs
cargo build --examples
cargo test
