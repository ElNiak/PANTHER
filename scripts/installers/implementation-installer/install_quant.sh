cd $PROOTPATH/quic-implementations/quant/
git submodule update --init --recursive
mkdir Debug 
cd Debug
cmake ..
make

