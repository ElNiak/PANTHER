 # install RUST
# curl https://sh.rustup.rs -sSf  | sh -s -- -y

cd $PROOTPATH/quic-implementations/quinn/
git checkout 0.7.0
source $HOME/.cargo/env
cargo build --examples
cargo test
