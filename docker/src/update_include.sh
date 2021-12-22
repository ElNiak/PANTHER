array=()
while IFS=  read -r -d $'\0'; do
    array+=("$REPLY")
done < <(find /QUIC-Ivy/ivy/include/1.7/ -type f -name \*.ivy -print0)

echo $array

SUB='test'
for j in "${array[@]}"; do : 
    if [[ ! "$j" == *"$SUB"* ]]; then
	printf "Files => $j  \n" 
    	cp $j /usr/local/lib/python2.7/dist-packages/ivy/include/1.7
    fi
done

cp -f $PROOTPATH/QUIC-Ivy/ivy/ivy_to_cpp.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_to_cpp.py
cp -f $PROOTPATH/QUIC-Ivy/ivy/ivy_solver.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_solver.py
cp -f $PROOTPATH/QUIC-Ivy/ivy/ivy_cpp_types.py /usr/local/lib/python2.7/dist-packages/ivy/ivy_cpp_types.py

cd /usr/local/lib/python2.7/dist-packages/ivy/
python -m compileall ivy_to_cpp.py
python -m compileall ivy_cpp_types.py
python -m compileall ivy_solver.py

echo "CP picotls lib"
cp -f /quic/picotls/libpicotls-core.a /usr/local/lib/python2.7/dist-packages/ivy/lib
cp -f /quic/picotls/libpicotls-core.a /QUIC-Ivy/ivy/lib
cp -f /quic/picotls/libpicotls-minicrypto.a /usr/local/lib/python2.7/dist-packages/ivy/lib
cp -f /quic/picotls/libpicotls-minicrypto.a /QUIC-Ivy/ivy/lib
cp -f /quic/picotls/libpicotls-openssl.a /usr/local/lib/python2.7/dist-packages/ivy/lib
cp -f /quic/picotls/libpicotls-openssl.a /QUIC-Ivy/ivy/lib

cp -f /quic/picotls/include/picotls.h /usr/local/lib/python2.7/dist-packages/ivy/include
cp -f /quic/picotls/include/picotls.h /QUIC-Ivy/ivy/include
cp -r -f /quic/picotls/include/picotls/. /usr/local/lib/python2.7/dist-packages/ivy/include/picotls
cp -r -f /quic/picotls/include/picotls/. /QUIC-Ivy/ivy/include/picotls
