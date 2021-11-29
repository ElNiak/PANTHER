 # install RUST
# curl https://sh.rustup.rs -sSf  | sh -s -- -y

cd $PROOTPATH/quic-implementations/quinn/
git stash
git checkout 0.7.0
cp $PROOTPATH/ressources/quinn/lib.rs quinn-proto/src/lib.rs
source $HOME/.cargo/env
cargo build --examples
cargo test
