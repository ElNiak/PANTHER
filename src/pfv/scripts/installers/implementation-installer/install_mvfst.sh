# Possible error: c++: internal compiler error: Killed (program cc1plus)

cd $PROOTPATH/quic-implementations/
sudo apt remove --fix-missing -y cmake
wget https://github.com/Kitware/CMake/releases/download/v3.12.4/cmake-3.12.4-Linux-x86_64.sh  &> /dev/null
chmod +x cmake-3.12.4-Linux-x86_64.sh
mkdir /opt/cmake
bash cmake-3.12.4-Linux-x86_64.sh --skip-license --prefix=/opt/cmake
ln -s /opt/cmake/bin/cmake /usr/local/bin/cmake
cmake --version


cd $PROOTPATH/quic-implementations/mvfst/
git stash 
git fetch
git checkout a34dc237104c6df3daca48afac51ca5777c5490e

echo "----> Cloning mvfst build_helper"
bash build_helper.sh

echo "----> Cloning mvfst apply"
cd $PROOTPATH/quic-implementations/mvfst/quic/samples

# rm -r $PROOTPATH/quic-implementations/mvfst/quic/samples/echo 
# cp -r $PROOTPATH/ressources/mvfst/rfc9000/echo/ $PROOTPATH/quic-implementations/mvfst/quic/samples/
# cp $PROOTPATH/ressources/mvfst/rfc9000/QuicClientTransport.h $PROOTPATH/quic-implementations/mvfst/quic/client/QuicClientTransport.h
# cp $PROOTPATH/ressources/mvfst/rfc9000/QuicConstants.h $PROOTPATH/quic-implementations/mvfst/quic/QuicConstants.h

cmake .
make
cd $PROOTPATH/quic-implementations/mvfst/_build/build/quic/samples
make #-j 6
