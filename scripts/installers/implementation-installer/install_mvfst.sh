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
cp $PROOTPATH/ressources/mvfst/EchoServer.h $PROOTPATH/quic-implementations/mvfst/quic/samples/echo/EchoServer.h
cp $PROOTPATH/ressources/mvfst/build_helper.sh $PROOTPATH/quic-implementations/mvfst/build_helper.sh
cp $PROOTPATH/ressources/mvfst/QuicConstants.h $PROOTPATH/quic-implementations/mvfst/quic/QuicConstants.h
cp $PROOTPATH/ressources/mvfst/main.cpp $PROOTPATH/quic-implementations/mvfst/quic/samples/echo/main.cpp


echo "----> Cloning mvfst build_helper"
bash build_helper.sh

echo "----> Cloning mvfst apply"
git apply samples-build-patch.diff #Should not be here  $PROOTPATH/quic-implementations/mvfst/
cd $PROOTPATH/quic-implementations/mvfst/quic/samples
cp -R $PROOTPATH/ressources/mvfst/generic $PROOTPATH/quic-implementations/mvfst/quic/samples/generic
cp $PROOTPATH/ressources/mvfst/EchoClient.h $PROOTPATH/quic-implementations/mvfst/quic/samples/echo/EchoClient.h
cp $PROOTPATH/ressources/mvfst/EchoServer.h $PROOTPATH/quic-implementations/mvfst/quic/samples/echo/EchoServer.h
cp $PROOTPATH/ressources/mvfst/QuicClientTransport.h $PROOTPATH/quic-implementations/mvfst/quic/client/QuicClientTransport.h
cp $PROOTPATH/ressources/mvfst/QuicConstants.h $PROOTPATH/quic-implementations/mvfst/quic/QuicConstants.h
cp $PROOTPATH/ressources/mvfst/main.cpp $PROOTPATH/quic-implementations/mvfst/quic/samples/echo/main.cpp
cmake .
make
cd $PROOTPATH/quic-implementations/mvfst/_build/build/quic/samples
make #-j 6
