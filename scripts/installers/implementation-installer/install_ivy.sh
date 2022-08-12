cd QUIC-Ivy/
#git stash
git checkout quic-rfc9000 # rfc9000 # quic_29 
git submodule update --init --recursive
git submodule update --recursive
mkdir doc/examples/quic/build
mkdir doc/examples/quic/test/temp

sudo rm -r /usr/local/lib/python2.7/dist-packages && sudo mkdir /usr/local/lib/python2.7/dist-packages
sudo pip2 install pexpect chardet
sudo pip2 install gperf pandas scandir
sudo pip3 install pexpect chardet
sudo pip3 install gperf pandas scandir
cd $PROOTPATH/QUIC-Ivy/submodules/picotls
git checkout 047c5fe20bb9ea91c1caded8977134f19681ec76

cd $PROOTPATH/QUIC-Ivy/
python2.7 build_submodules.py
sudo pip2 install ms-ivy==1.8.23 #global install


# cd $PROOTPATH/QUIC-Ivy/
# rm doc/examples/quic/test/test.py
# cp $PROOTPATH/ressources/test.py $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/

