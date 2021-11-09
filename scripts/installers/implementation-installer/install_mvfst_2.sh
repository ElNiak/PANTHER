cd $HOME/TVOQE_UPGRADE_27/quic


#cd $HOME/TVOQE_UPGRADE_27/quic/mvfst/quic/client
#cmake .
#make
cd $HOME/TVOQE_UPGRADE_27/quic/mvfst/_build/build/quic/client
make -j 8


#cd $HOME/TVOQE_UPGRADE_27/quic/mvfst/quic/server
#cmake .
#make
cd $HOME/TVOQE_UPGRADE_27/quic/mvfst/_build/build/quic/server
make -j 8

cd $HOME/TVOQE_UPGRADE_27/quic/mvfst/quic/samples
cmake .
make
cd $HOME/TVOQE_UPGRADE_27/quic/mvfst/_build/build/quic/samples
make -j 6
