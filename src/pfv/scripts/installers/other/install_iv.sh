cd $HOME/TVOQE_UPGRADE_27/
#Install ivy
printf "\n\n"
printf "###### Installing Ivy:\n\n"
git clone --recurse-submodules https://github.com/ElNiak/QUIC-Ivy.git
cd QUIC-Ivy/
git checkout quic_29 #Jan 28 2020
mkdir $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/doc/examples/quic/build
mkdir $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/doc/examples/quic/test/temp
cd ..
bash modif.sh
rm $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/doc/examples/quic/test/test.py
cp $HOME/TVOQE_UPGRADE_27/test.py $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/doc/examples/quic/test/
