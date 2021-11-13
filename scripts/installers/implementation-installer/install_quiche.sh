 
cd $PROOTPATH/quic-implementations/
# install RUST
curl https://sh.rustup.rs -sSf | sh
source $HOME/.cargo/env
cd quiche/
cargo build --examples
cargo test
