#sudo rm -r /usr/local/lib/python2.7/dist-packages && sudo mkdir /usr/local/lib/python2.7/dist-packages
#sudo pip install ms-ivy

array=()
while IFS=  read -r -d $'\0'; do
    array+=("$REPLY")
done < <(find $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/ivy/include/1.7/ -type f -name \*.ivy -print0)

echo $array

#sudo rm -r /usr/local/lib/python2.7/dist-packages/ivy/include/1.7

SUB='test'
for j in "${array[@]}"; do : 
    if [[ ! "$j" == *"$SUB"* ]]; then
	printf "Files => $j  \n" 
    	sudo cp $j /usr/local/lib/python2.7/dist-packages/ivy/include/1.7
    fi
done

cd $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/ivy/ #TODO add manually lines in ivy to cpp
#python -m compileall ivy_to_cpp.py
sudo cp ivy_cpp_types.py /usr/local/lib/python2.7/dist-packages/ivy/
sudo cp ivy_solver.py /usr/local/lib/python2.7/dist-packages/ivy/
sudo cp ivy_to_cpp.py /usr/local/lib/python2.7/dist-packages/ivy/
#sudo cp -R include/bignum/ /usr/local/lib/python2.7/dist-packages/ivy/include/bignum
#sudo cp -R include/wide-integer/ /usr/local/lib/python2.7/dist-packages/ivy/include/wide-integer
#sudo cp include/BigInt.cpp /usr/local/lib/python2.7/dist-packages/ivy/include/BigInt.cpp #not working
cd /usr/local/lib/python2.7/dist-packages/ivy/
sudo python -m compileall ivy_to_cpp.py
sudo python -m compileall ivy_cpp_types.py
sudo python -m compileall ivy_solver.py

echo "CP picotls lib"
sudo cp -f $HOME/TVOQE_UPGRADE_27/quic/picotls/libpicotls-core.a /usr/local/lib/python2.7/dist-packages/ivy/lib
sudo cp -f $HOME/TVOQE_UPGRADE_27/quic/picotls/libpicotls-core.a $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/ivy/lib
sudo cp -f $HOME/TVOQE_UPGRADE_27/quic/picotls/libpicotls-minicrypto.a /usr/local/lib/python2.7/dist-packages/ivy/lib
sudo cp -f $HOME/TVOQE_UPGRADE_27/quic/picotls/libpicotls-minicrypto.a $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/ivy/lib
sudo cp -f $HOME/TVOQE_UPGRADE_27/quic/picotls/libpicotls-openssl.a /usr/local/lib/python2.7/dist-packages/ivy/lib
sudo cp -f $HOME/TVOQE_UPGRADE_27/quic/picotls/libpicotls-openssl.a $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/ivy/lib

sudo cp -f $HOME/TVOQE_UPGRADE_27/quic/picotls/include/picotls.h /usr/local/lib/python2.7/dist-packages/ivy/include
sudo cp -f $HOME/TVOQE_UPGRADE_27/quic/picotls/include/picotls.h $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/ivy/include
sudo cp -r -f $HOME/TVOQE_UPGRADE_27/quic/picotls/include/picotls/. /usr/local/lib/python2.7/dist-packages/ivy/include/picotls
sudo cp -r -f $HOME/TVOQE_UPGRADE_27/quic/picotls/include/picotls/. $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/ivy/include/picotls
