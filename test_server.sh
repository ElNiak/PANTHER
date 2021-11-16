#go build -o $HOME/TVOQE_UPGRADE_27/quic/quic-go/server/server $HOME/TVOQE_UPGRADE_27/quic/quic-go/example/echo/echo.go
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


servers=(
		 quant 
		 picoquic
		 # mvfst
		 lsquic
		 quic-go
		 aioquic
		 quinn
		 quiche
		 )

alpn=(hq-29 hq-29 hq-29 hq-29 hq-29)
tests_server=(
	      quic_server_test_stream
	      #quic_server_test_version_negociation_ext
	      #quic_server_test_retry
	      #quic_server_test_version_negociation
          #quic_server_test_unkown
	      #quic_server_test_blocked_streams_maxstream_error
          #quic_server_test_tp_limit_newcoid
	      #quic_server_test_max 
	      #quic_server_test_token_error  
          #quic_server_test_tp_error #quant: corrected in master
          #quic_server_test_tp_acticoid_error
          #quic_server_test_connection_close
          #quic_server_test_reset_stream
	      #quic_server_test_newconnectionid_error
	      #quic_server_test_newcoid_zero_error #not working
	      #quic_server_test_handshake_done_error
	      #quic_server_test_stop_sending
          #quic_server_test_double_tp_error
	      #quic_server_test_tp_limit_acticoid_error #not working
	      #quic_server_test_accept_maxdata
	      #quic_server_test_no_icid 
	      #quic_server_test_ext_min_ack_delay

	      # No migration to see what happen
	      #quic_server_test_stream_limit_error     # ~Good remve one requirement
	      #quic_server_test_crypto_limit_error     # Not Good
	      #quic_server_test_retirecoid_error       # Good
	      #quic_server_test_newcoid_rtp_error      # Good
	      #quic_server_test_newcoid_length_error   # Good
	      #quic_server_test_new_token_error        # Good
	      ##quic_server_test_stop_sending_error     #BAD
	      #quic_server_test_unkown_tp              # Good
	      #quic_server_test_max_limit_error        # GOOD
	      #quic_server_test_max_error              # Good
	      )




# Update Ivy (for included files)
array=()
while IFS=  read -r -d $'\0'; do
    array+=("$REPLY")
done < <(find $PROOTPATH/QUIC-Ivy/doc/examples/quic -type f -name \*.ivy -print0)

echo $array

SUB='test'
for j in "${array[@]}"; do : 
    if [[ ! "$j" == *"$SUB"* ]]; then
	printf "Files => $j  \n" 
    	sudo cp $j $PYTP/lib/python2.7/dist-packages/ivy/include/1.7
    fi
done
sudo cp $PROOTPATH/QUIC-Ivy/doc/examples/quic/quic_utils/quic_ser_deser.h $PYTP/lib/python2.7/dist-packages/ivy/include/1.7
sudo cp $PROOTPATH/QUIC-Ivy/doc/examples/quic/quic_utils/quic_ser_deser.h $PROOTPATH/QUIC-Ivy/doc/examples/quic/build/


export TEST_TYPE=server

rm $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/test.py
cp $PROOTPATH/ressources/test.py $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/
cd $PROOTPATH/QUIC-Ivy/doc/examples/quic/quic_tests

printf "BUILDING TEST \n"
for j in "${tests_server[@]}"; do
    :
    ivyc target=test $j.ivy #TODO update g++ add lib
    cp $j $PROOTPATH/QUIC-Ivy/doc/examples/quic/build/
    cp $j.cpp $PROOTPATH/QUIC-Ivy/doc/examples/quic/build/
    cp $j.h $PROOTPATH/QUIC-Ivy/doc/examples/quic/build/
    rm $j
    rm $j.cpp
    rm $j.h
    printf "\n"
done


printf "Create SSLLOGFILE TEST \n"
for j in "${servers[@]}"; do
    :
    touch $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/temp/${j}_key.log
done

cnt=0
ITER=1
printf "\n"
cd $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/
printf "TEST SERVER \n"
for j in "${tests_server[@]}"; do
    :
    printf "Server => $j  "
    cnt2=0
    for i in "${servers[@]}"; do
        :
	export SSLKEYLOGFILE=$PROOTPATH+"/QUIC-Ivy/doc/examples/quic/test/temp/${i}_key.log"
	echo $SSLKEYLOGFILE
	k=1
        until [ $k -gt $ITER ]; do
            printf "\n\Iteration => $k \n"
            printf "\n\nTesting => $i \n"
			export TEST_IMPL=$i
			export CNT=$cnt
			export RND=$RANDOM
			export TEST_ALPN=hq-29
            touch temp/${cnt}_${i}_${j}.pcap
            sudo chmod o=xw temp/${cnt}_${i}_${j}.pcap
            sudo tshark -i lo -w temp/${cnt}_${i}_${j}.pcap -f "udp" & 
	    	python test.py iters=1 server=$i test=$j > res_server.txt 2>&1
            printf "\n"
	    	((k++))
            sudo pkill tshark
            cat res_server.txt
            cp res_server.txt temp/${cnt}/res_server.txt
	    	cnt=$((cnt + 1))
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
