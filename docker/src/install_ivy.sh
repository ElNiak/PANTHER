#!/bin/bash

# Add .ivy file of the quic project directly in "include" folder of the ivy python
# library 

array=()
while IFS=  read -r -d $'\0'; do
    array+=("$REPLY")
done < <(find /QUIC-Ivy/doc/examples/quic -type f -name \*.ivy -print0)

echo $array

SUB='test'
for j in "${array[@]}"; do : 
    if [[ ! "$j" == *"$SUB"* ]]; then
	printf "Files => $j  \n" 
    	cp $j /usr/local/lib/python2.7/dist-packages/ivy/include/1.7
    fi
done

