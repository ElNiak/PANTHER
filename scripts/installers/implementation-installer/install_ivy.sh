cd QUIC-Ivy/
git stash
git checkout rfc9000 # rfc9000 # quic_29 
git submodule update --init --recursive
git submodule update --recursive
mkdir doc/examples/quic/build
mkdir doc/examples/quic/test/temp

sudo rm -r /usr/local/lib/python2.7/dist-packages && sudo mkdir /usr/local/lib/python2.7/dist-packages
sudo pip2 install pexpect chardet
sudo pip2 install gperf pandas scandir
python2.7 build_submodules.py
sudo pip2 install ms-ivy #global install

rm doc/examples/quic/test/test.py
cp $PROOTPATH/ressources/test.py $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/

