cp $PROOTPATH/ressources/tls-keys-patch.diff $PROOTPATH/quic-implementations/mvfst/
cp $PROOTPATH/ressources/samples-build-patch.diff $PROOTPATH/quic-implementations/mvfst/
cd mvfst
git checkout 36111c1
git apply tls-keys-patch.diff
bash build_helper.sh
git apply samples-build-patch.diff #Should not be here
cd $PROOTPATH/quic-implementations/mvfst/quic/samples
cmake .
make
cd $PROOTPATH/quic-implementations/mvfst/_build/build/quic/samples
make -j 6
