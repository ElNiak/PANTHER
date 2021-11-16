# TOREDO : ./build/quic_client_test_tp_error good cid
PROOTPATH=$PWD
export PROOTPATH
export PATH="/go/bin:${PATH}"

source $HOME/.cargo/env

PYTP=/usr/local
if [[ ! -v VirtualEnv ]]; then
    echo "VirtualEnv is not set"
elif [[ -z "$VirtualEnv" ]]; then
    echo "VirtualEnv is set to the empty string"
else
    echo "VirtualEnv has the value: $VirtualEnv"
	PYTP=$VirtualEnv
fi

clients=(
		 quant 
		 picoquic
		 mvfst
		 lsquic
		 quic-go
		 aioquic
		 quinn
		 quiche
		 )

alpn=(hq-29 hq-29 hq-29 hq-29 hq-29)

tests_client=(
	      #quic_client_test_max
	      quic_client_test_retry
	      #quic_client_test_version_negociation
	      #quic_client_test_stream #useless here
	      #quic_client_test_ext_min_ack_delay
	      #quic_client_test_tp_error
	      #quic_client_test_double_tp_error
	      #quic_client_test_tp_acticoid_error
	      #quic_client_test_tp_limit_acticoid_error
	      #quic_client_test_blocked_streams_maxstream_error
	      #quic_client_test_retirecoid_error
	      #quic_client_test_newcoid_zero_error
	      #quic_client_test_accept_maxdata
	      #quic_client_test_tp_prefadd_error
	      #quic_client_test_no_odci  # Todo
	      #quic_client_test_handshake_done_error # Todo
	      #quic_client_test_unkown
	      #quic_client_test_tp_unkown
	      #quic_client_test_limit_max_error
	      #quic_client_test_new_token_error

	      #quic_client_test_token_error
	      #quic_client_test_tp_error
	      #quic_client_test_double_tp_error
	      #quic_client_test_tp_acticoid_error
	      #quic_client_test_tp_limit_acticoid_error
	      #quic_client_test_blocked_streams_maxstream_error
	      #quic_client_test_retirecoid_error
	      #quic_client_test_newcoid_zero_error
	      #quic_client_test_accept_maxdata
	      #quic_client_test_tp_prefadd_error
	      #quic_client_test_no_odci quic_client_test_stateless_reset_token
		)

# Update Ivy (for included files)
cd $PROOTPATH
array=()
while IFS=  read -r -d $'\0'; do
    array+=("$REPLY")
done < <(find $PROOTPATH/QUIC-Ivy/doc/examples/quic -type f -name \*.ivy -print0)

echo $array

SUB='test'
for j in "${array[@]}"; do : 
    if [[ ! "$j" == *"$SUB"* ]]; then
	printf "Files => $j  \n" 
    	sudo cp $j $PYTP/lib/python2.7/dist-packages/ivy/include/1.7/
    fi
done
sudo cp $PROOTPATH/QUIC-Ivy/doc/examples/quic/quic_utils/quic_ser_deser.h $PYTP/lib/python2.7/dist-packages/ivy/include/1.7
sudo cp $PROOTPATH/QUIC-Ivy/doc/examples/quic/quic_utils/quic_ser_deser.h $PROOTPATH/QUIC-Ivy/doc/examples/quic/build/


export TEST_TYPE=client

rm $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/test.py
cp $PROOTPATH/ressources/test.py $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/
cd $PROOTPATH/QUIC-Ivy/doc/examples/quic/quic_tests


printf "BUILDING TEST \n"
for j in "${tests_client[@]}"; do
    :
    ivyc target=test $j.ivy
    cp $j $PROOTPATH/QUIC-Ivy/doc/examples/quic/build/
    cp $j.cpp $PROOTPATH/QUIC-Ivy/doc/examples/quic/build/
    cp $j.h $PROOTPATH/QUIC-Ivy/doc/examples/quic/build/
    rm $j
    rm $j.cpp
    rm $j.h
    printf "\n"
done


printf "Create SSLLOGFILE TEST \n"
for j in "${clients[@]}"; do
    :
    touch /home/chris/TVOQE_UPGRADE_27/QUIC-Ivy/doc/examples/quic/test/temp/${j}_key.log
done



cnt=0
ITER=1
printf "\n"
cd $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/
printf "TEST CLIENT \n"
for j in "${tests_client[@]}"; do
    :
    printf "Client => $j  "
    cnt2=0
    for i in "${clients[@]}"; do
        :
	export SSLKEYLOGFILE=$PROOTPATH+"/tls-keys/${i}_key.log"
	k=1
        until [ $k -gt $ITER ]; do
            printf "\n\Iteration => $k \n"
            printf "\n\nTesting => $i \n"
			export TEST_IMPL=$i
			export TEST_ALPN=hq-29
			export CNT=$cnt
			export RND=$RANDOM
            touch temp/${cnt}_${i}_${j}.pcap
            sudo chmod o=xw temp/${cnt}_${i}_${j}.pcap
            sudo tshark -i lo -w temp/${cnt}_${i}_${j}.pcap -f "udp" & 
            python test.py iters=1 client=$i test=$j > res_client.txt 2>&1
            printf "\n"
	    	((k++))
            cat res_client.txt
            cp res_client.txt temp/${cnt}/res_client.txt
	    	cnt=$((cnt + 1))
            kill $(lsof -i udp) >/dev/null 2>&1
            sudo pkill tshark
        done
	cnt2=$((cnt2 + 1))
	printf "\n"
    done
done

cd $PROOTPATH
# Revove Ivy modification (for included files)
array=()
while IFS=  read -r -d $'\0'; do
    array+=("$REPLY")
done < <(find $PROOTPATH/QUIC-Ivy/doc/examples/quic -type f -name \*.ivy -print0 -printf "%f\n")

echo $array

SUB='test'
for j in "${array[@]}"; do : 
    # Set space as the delimiter
    IFS=' '
    #Read the split words into an array based on space delimiter
    read -a strarr <<< "$j"
    if [[ ! "${strarr[0]}" == *"$SUB"* ]]; then
	printf "Files => $PYTP/lib/python2.7/dist-packages/ivy/include/1.7/$strarr  \n" 
    	sudo rm $PYTP/lib/python2.7/dist-packages/ivy/include/1.7/${strarr[0]}
    fi
done

