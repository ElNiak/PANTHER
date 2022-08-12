 # install RUST
# curl https://sh.rustup.rs -sSf  | sh -s -- -y

cd $PROOTPATH/quic-implementations/quinn/
git stash
git fetch
git checkout 4395b969a69b9e39bef1333e44312bf2548d4e1c
git submodule update --init --recursive
git submodule update --recursive
cp $PROOTPATH/ressources/quinn/rfc9000/lib.rs quinn-proto/src/lib.rs
#cp $PROOTPATH/ressources/quinn/rfc9000/client.rs quinn/examples/client.rs #TODO
source $HOME/.cargo/env
cargo build --examples
cargo test
