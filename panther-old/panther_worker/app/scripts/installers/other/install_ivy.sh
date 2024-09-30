array=()
while IFS=  read -r -d $'\0'; do
    array+=("$REPLY")
done < <(find $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/doc/examples/quic -type f -name \*.ivy -print0)

echo $array

SUB='test'
for j in "${array[@]}"; do : 
    if [[ ! "$j" == *"$SUB"* ]]; then
	printf "Files => $j  \n" 
    	sudo cp $j /usr/local/lib/python3.10.10/dist-packages/ivy/include/1.7
    fi
done

sudo cp $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/doc/examples/quic/quic_utils/quic_ser_deser.h /usr/local/lib/python3.10.10/dist-packages/ivy/include/1.7
sudo cp $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/doc/examples/quic/quic_utils/quic_ser_deser.h $HOME/TVOQE_UPGRADE_27/QUIC-Ivy/doc/examples/quic/build/
