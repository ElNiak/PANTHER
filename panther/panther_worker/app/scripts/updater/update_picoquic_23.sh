cd quic/
sudo rm -r picotls/
git clone https://github.com/h2o/picotls.git

#Install picotls
printf "\n\n"
printf "###### Installing PicoTLS:\n\n"
cd $HOME/TVOQE_UPGRADE_27/quic/picotls/
git checkout 3fdf6a54c4c0762226afcbabda3b2016af5a8761
git submodule init
git submodule update
cmake .
make
make check


#Install picoquic
printf "\n\n"
printf "###### Installing PicoQUIC:\n\n"
cd $HOME/TVOQE_UPGRADE_27/quic/picoquic/
git checkout 236a754f32860f58af9b129b62f6836c76c8a748 #c8e15c92ae5b76604ae176ba14772c1685ad8aca 
cmake .
make
./picoquic_ct
