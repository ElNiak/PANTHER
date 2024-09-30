 #Install picotls
printf "\n\n"
printf "###### Installing PicoTLS:\n\n"
cd $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/submodules/picotls/
git checkout 3fdf6a54c4c0762226afcbabda3b2016af5a8761
git submodule init
git submodule update
cmake .
make
make check

cd $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/submodules/picotls/include/
sudo rm -r /usr/local/lib/python3.10.10/dist-packages/ivy/include/picotls/
sudo rm /usr/local/lib/python3.10.10/dist-packages/ivy/include/picotls.h

sudo cp -r $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/submodules/picotls/include/picotls/ /usr/local/lib/python3.10.10/dist-packages/ivy/include/
sudo cp $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/submodules/picotls/include/picotls.h /usr/local/lib/python3.10.10/dist-packages/ivy/include/
