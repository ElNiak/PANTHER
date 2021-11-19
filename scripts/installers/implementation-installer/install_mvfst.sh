# Possible error: c++: internal compiler error: Killed (program cc1plus)

cd $PROOTPATH/quic-implementations/mvfst/
git stash
git checkout 36111c1
cp $PROOTPATH/ressources/mvfst/tls-keys-patch.diff $PROOTPATH/quic-implementations/mvfst/
echo "----> Cloning mvfst apply1"
git apply tls-keys-patch.diff

cp -R $PROOTPATH/ressources/mvfst/generic $PROOTPATH/quic-implementations/mvfst/quic/samples/generic
cp $PROOTPATH/ressources/mvfst/samples-build-patch.diff $PROOTPATH/quic-implementations/mvfst/
cp $PROOTPATH/ressources/mvfst/EchoClient.h $PROOTPATH/quic-implementations/mvfst/quic/samples/echo/EchoClient.h

ls $PROOTPATH/quic-implementations/mvfst/quic/samples/
echo "----> Cloning mvfst build_helper"
bash build_helper.sh

echo "----> Cloning mvfst apply2"
git apply samples-build-patch.diff #Should not be here
cd $PROOTPATH/quic-implementations/mvfst/quic/samples
cmake .
make
cd $PROOTPATH/quic-implementations/mvfst/_build/build/quic/samples
make #-j 6
