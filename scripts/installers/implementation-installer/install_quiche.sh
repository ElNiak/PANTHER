 
cd $PROOTPATH/quic-implementations/
# install RUST
curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env
cd quiche/
git stash
git checkout   0.7.0 # master #
cp $PROOTPATH/ressources/quiche/packet.rs src/packet.rs
#cp $PROOTPATH/ressources/quiche/master/packet.rs src/packet.rs
cargo build --examples
cargo test
