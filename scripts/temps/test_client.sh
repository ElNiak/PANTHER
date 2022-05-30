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
		 quant # sometimes decryption problem
		 #quant-vuln
	     picoquic
		#  mvfst # Not working: unknown reason (ok now, vn condition problem) (todo 0rtt) -> check why few packet are sent -> +- ok now, somtime 0rtt done, sometime not
		#  lsquic
		#  quic-go # 0rtt (todo -> ok now) + set max cid  (ok now)
		#  aioquic
	    #  quinn # Not working: unknown reason (ok now, check alpn + ignore cert) -> no co_close ? + 0rtt todo +- ok now
		quiche # 0rtt client not implemented in v0.0.7 -> update to 0.9.0  +- ok now, somtime 0rtt done, sometime not (check other version)
		)

alpn=(hq-29 hq-29 hq-29 hq-29 hq-29)

tests_client=(
	      quic_client_test_max
		  #quic_client_test_0rtt
	      #quic_client_test_retry
	      #quic_client_test_version_negociation
		  #quic_client_test_version_negociation_mim
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
export IS_NOT_DOCKER=true

rm $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/test.py
cp $PROOTPATH/ressources/test.py $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/
cp $PROOTPATH/ressources/stats.py $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/
cp $PROOTPATH/ressources/plot.py $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/
cp $PROOTPATH/ressources/show.py $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/
cp $PROOTPATH/ressources/outliers.py $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/

cd $PROOTPATH/QUIC-Ivy/doc/examples/quic/quic_tests

export ZRTT_SSLKEYLOG_FILE=$PROOTPATH/QUIC-Ivy/doc/examples/quic/last_tls_key.key

echo $ZRTT_SSLKEYLOG_FILE
echo $ZRTT_SSLKEYLOG_FILEC
export STFILE=$PROOTPATH/QUIC-Ivy/doc/examples/quic/last_session_ticket.txt
export RTFILE=$PROOTPATH/QUIC-Ivy/doc/examples/quic/last_retry_token.txt
export NEW_TOKEN_FILE=$PROOTPATH/QUIC-Ivy/doc/examples/quic/last_new_token.txt
export ENCRYPT_TICKET_FILE=$PROOTPATH/QUIC-Ivy/doc/examples/quic/last_encrypt_session_ticket.txt
export SESSION_TICKET_FILE=$PROOTPATH/QUIC-Ivy/doc/examples/quic/last_session_ticket_cb.txt

#export SESSION_TICKET_FILE=$PROOTPATH/QUIC-Ivy/doc/examples/quic/last_session_ticket_cb.txt


echo $STFILE
echo $ENCRYPT_TICKET_FILE
echo $RTFILE
echo $NEW_TOKEN_FILE


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
	if [ $j = quic_client_test_0rtt ]; then
		ivyc target=test quic_client_test_0rtt_max.ivy #TODO update g++ add lib
		cp quic_client_test_0rtt_max $PROOTPATH/QUIC-Ivy/doc/examples/quic/build/
		cp quic_client_test_0rtt_max.cpp $PROOTPATH/QUIC-Ivy/doc/examples/quic/build/
		cp quic_client_test_0rtt_max.h $PROOTPATH/QUIC-Ivy/doc/examples/quic/build/
		rm quic_client_test_0rtt_max
		rm quic_client_test_0rtt_max.cpp
		rm quic_client_test_0rtt_max.h
		printf "\n"
	fi
done

sudo sysctl -w net.core.rmem_max=2500000 # for quic-go

printf "Create SSLLOGFILE TEST \n"
for j in "${clients[@]}"; do
    :
    touch $PROOTPATH"/tls-keys/${j}_key.log"
done



cnt=0
ITER=1
printf "\n"
cd $PROOTPATH/QUIC-Ivy/doc/examples/quic/test/
printf "TEST CLIENT \n"
for j in "${tests_client[@]}"; do
    :
    printf "Client => $j  "
	if [ $j = quic_client_test_0rtt ]; then
		echo "test"
		export ZERORTT_TEST=true
	else
		unset ZERORTT_TEST
	fi
	if [ $j = quic_client_test_version_negociation_mim ]; then
		echo "test"
		bash $PROOTPATH/mim-setup.sh
	else
		bash $PROOTPATH/mim-reset.sh
	fi
    for i in "${clients[@]}"; do
        :
	export SSLKEYLOGFILE=$PROOTPATH"/tls-keys/${i}_key.log"
	echo $SSLKEYLOGFILE
	k=1
        until [ $k -gt $ITER ]; do
            printf "\n\Iteration => $k \n"
            printf "\n\nTesting => $i \n"
			export TEST_IMPL=$i
			export TEST_ALPN=hq-29
			export CNT=$cnt
			export RND=$RANDOM # check if usefull -> for seed
			> $PROOTPATH/tickets/ticket.bin
			pcap_i=$((`(find temp/* -maxdepth 0 -type d | wc -l)`))
            touch temp/${pcap_i}_${i}_${j}.pcap
            sudo chmod o=xw temp/${pcap_i}_${i}_${j}.pcap
			# -Y "quic"
            sudo tshark -i lo -w temp/${pcap_i}_${i}_${j}.pcap -f "udp" & 
            if [ $k = 1 ]; then
				python test.py iters=1 stats=false client=$i test=$j run=true gdb=false keep_alive=false > res_client.txt 2>&1
            else
				python test.py iters=1 stats=false client=$i test=$j run=true > res_client.txt 2>&1
			fi
			printf "\n"
	    	((k++))
            cat res_client.txt
            mv res_client.txt temp/${pcap_i}/res_client.txt
	    	cnt=$((cnt + 1))
            kill $(lsof -i udp) >/dev/null 2>&1
            sudo pkill tshark
        done
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

