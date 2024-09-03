cd QUIC-Ivy/
git checkout quic-rfc9000 # rfc9000 # quic_29 
git submodule update --init --recursive
git submodule update --recursive
git config --global --add safe.directory $PROOTPATH/QUIC-Ivy/submodules/picotls

mkdir doc/examples/quic/build
mkdir doc/examples/quic/test/temp

sudo rm -r /usr/local/lib/python3.10.10/dist-packages && sudo mkdir /usr/local/lib/python3.10.10/dist-packages
sudo pip2 install pexpect chardet
sudo pip2 install gperf pandas scandir
sudo pip2 install ply
sudo python3.10 -m pip install pexpect chardet
sudo python3.10 -m pip install gperf pandas scandir
sudo python3.10 -m pip install ply
sudo pip install pexpect chardet
sudo pip install gperf pandas scandir
sudo pip install ply
sudo pip3 install pexpect chardet
sudo pip3 install gperf pandas scandir

cd $PROOTPATH/QUIC-Ivy/submodules/picotls
git checkout 047c5fe20bb9ea91c1caded8977134f19681ec76

cd $PROOTPATH/QUIC-Ivy/

sudo pip3 install ply


echo "building submodules"

python2.7 build_submodules.py
sudo pip2 install ms-ivy==1.8.23 #global install


# cd $PROOTPATH/QUIC-Ivy/
# rm doc/examples/quic/test/test.py
# cp $PROOTPATH/ressources/test.py $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/

