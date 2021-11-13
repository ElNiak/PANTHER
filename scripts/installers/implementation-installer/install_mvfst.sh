cd $PROOTPATH/quic-implementations/mvfst/
git checkout 36111c1
cp -R $PROOTPATH/ressources/mvfst/generic $PROOTPATH/quic-implementations/mvfst/quic/samples/generic
cp $PROOTPATH/ressources/mvfst/tls-keys-patch.diff $PROOTPATH/quic-implementations/mvfst/
cp $PROOTPATH/ressources/mvfst/samples-build-patch.diff $PROOTPATH/quic-implementations/mvfst/
cp $PROOTPATH/ressources/mvfst/EchoClient.h $PROOTPATH/quic-implementations/mvfst/quic/samples/echo/EchoClient.h
git apply tls-keys-patch.diff
bash build_helper.sh
git apply samples-build-patch.diff #Should not be here
cd $PROOTPATH/quic-implementations/mvfst/quic/samples
cmake .
make
cd $PROOTPATH/quic-implementations/mvfst/_build/build/quic/samples
make #-j 6
