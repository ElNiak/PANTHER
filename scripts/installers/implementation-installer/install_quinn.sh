 # install RUST
# curl https://sh.rustup.rs -sSf  | sh -s -- -y

cd $PROOTPATH/quic-implementations/quinn/
cargo build --examples
cargo test
