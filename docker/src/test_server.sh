#!/bin/bash

#
# Launch the server suite test for each implementation
# 

# <!><!><!> restest quant with removing line in quic packet TOREDO <!><!><!><!><!>
# require ~_generating & ~queued_non_ack(scid) -> ack_credit(scid) > 0;  # [5]
 
# lsquic not working lsquic


servers=(quant quinn mvfst picoquic quic-go aioquic quiche)
alpn=(hq-29 hq-29 hq-29 hq-29 hq-29 hq-29 hq-29)

tests_server=(#quic_server_test_stream
              #quic_server_test_unkown
	          #quic_server_test_blocked_streams_maxstream_error
              #quic_server_test_tp_limit_newcoid
	          #quic_server_test_max 
	          #quic_server_test_token_error  
              #quic_server_test_tp_error
              #quic_server_test_tp_acticoid_error
              #quic_server_test_connection_close #toretest
              #quic_server_test_reset_stream
	          #quic_server_test_newcoid_zero_error # not working
	          #quic_server_test_handshake_done_error
	          #quic_server_test_stop_sending # not working
              #quic_server_test_double_tp_error
	          #quic_server_test_tp_limit_acticoid_error
	          #quic_server_test_accept_maxdata
	          #quic_server_test_no_icid #to retest
              #quic_server_test_ext_min_ack_delay

              # No migration to see what happen
              #quic_server_test_stream_limit_error     # ~Good remve one requirement
              quic_server_test_crypto_limit_error     # Good
              #quic_server_test_retirecoid_error       # Good
              #quic_server_test_newcoid_rtp_error      # Good
              #quic_server_test_newcoid_length_error   # Good
              #quic_server_test_new_token_error        # Good
              ##quic_server_test_stop_sending_error     #BAD
              #quic_server_test_unkown_tp              # Good
              #quic_server_test_max_limit_error        # GOOD
              #quic_server_test_max_error              # Good
	        )

cd /

bash install_ivy.sh

rm /QUIC-Ivy/doc/examples/quic/test/test.py
cp /test.py /QUIC-Ivy/doc/examples/quic/test/
cd /QUIC-Ivy/doc/examples/quic/quic_tests

printf "BUILDING TEST \n"
for j in "${tests_server[@]}"; do
    :
    ivyc target=test $j.ivy
    cp $j /QUIC-Ivy/doc/examples/quic/build/
    cp $j.cpp /QUIC-Ivy/doc/examples/quic/build/
    cp $j.h /QUIC-Ivy/doc/examples/quic/build/
    rm $j
    rm $j.cpp
    rm $j.h
    printf "\n"
done

mkdir /results/temp/

printf "Create SSLLOGFILE TEST \n"
for j in "${servers[@]}"; do
    :
    touch /results/temp/${j}_key.log
done

ITER=$1

export TEST_TYPE=server

printf "\n"
cd /QUIC-Ivy/doc/examples/quic/test/
printf "TEST SERVER \n"
count=0
for j in "${tests_server[@]}"; do
    :
    printf "Server => $j  "
    cnt2=0
    for i in "${servers[@]}"; do
        :
        export SSLKEYLOGFILE="/results/temp/${i}_key.log"
        printf "\n\nTesting => $i \n"
        k=1
        until [ $k -gt $ITER ]; do
            printf "\n\Iteration => $k \n"
            printf "\Implementation => $i \n"
            printf "\Test => $j \n"
            export TEST_IMPL=$i
            export CNT=$count
            export RND=$RANDOM
            export TEST_ALPN=hq-29
            touch /QUIC-Ivy/doc/examples/quic/test/temp/${count}_${i}_${j}.pcap
            chmod o=xw /QUIC-Ivy/doc/examples/quic/test/temp/${count}_${i}_${j}.pcap
            tshark -i lo -w /QUIC-Ivy/doc/examples/quic/test/temp/${count}_${i}_${j}.pcap -f "udp" &
            python test.py iters=1 server=$i test=$j > res_server.txt 2>&1
            ((k++))
            printf "\n"
            pkill tshark
            cat res_server.txt
            cp res_server.txt /QUIC-Ivy/doc/examples/quic/test/temp/${count}/res_server.txt
            count=$((count + 1))
        done
        cnt2=$((cnt2 + 1))
	    printf "\n"
    done
done

cd /
bash remove_ivy.sh

cp -R /QUIC-Ivy/doc/examples/quic/test/temp/ /results


cd /results
#python create-csv.py
#python update_key_aioquic.py