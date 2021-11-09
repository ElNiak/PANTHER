#!/bin/bash

# Remove previously added .ivy file of the quic project directly 
# in "include" folder of the ivy python library 

array=()
while IFS=  read -r -d $'\0'; do
    array+=("$REPLY")
done < <(find /QUIC-Ivy/doc/examples/quic -type f -name \*.ivy -print0 -printf "%f\n")

echo $array

SUB='test'
for j in "${array[@]}"; do : 
    # Set space as the delimiter
    IFS=' '
    #Read the split words into an array based on space delimiter
    read -a strarr <<< "$j"
    if [[ ! "${strarr[0]}" == *"$SUB"* ]]; then
	printf "Files => /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/$strarr  \n" 
    	rm /usr/local/lib/python2.7/dist-packages/ivy/include/1.7/${strarr[0]}
    fi
done

