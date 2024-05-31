sudo apt remove --fix-missing -y cmake
sudo snap remove cmake
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
git fetch
git checkout 4bda0917dd5aa535f39214063ee85c2cad00ceb2 #0.7.0 # master # 0.9.0 for quic client ! TODO
git submodule update --init
# cp $PROOTPATH/ressources/quiche/rfc9000/packet_0.9.0.rs src/packet.rs
cargo build --examples
cargo test
