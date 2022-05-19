 # install RUST
# curl https://sh.rustup.rs -sSf  | sh -s -- -y

cd $PROOTPATH/quic-implementations/quinn/
git stash
git checkout 0.7.0
git submodule update --init --recursive
git submodule update --recursive
cp $PROOTPATH/ressources/quinn/lib.rs quinn-proto/src/lib.rs
cp $PROOTPATH/ressources/quinn/client.rs quinn/examples/client.rs
source $HOME/.cargo/env
cargo build --examples
cargo test
