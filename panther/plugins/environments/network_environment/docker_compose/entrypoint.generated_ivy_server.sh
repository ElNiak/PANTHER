#!/bin/bash -x
# -x: trace every command (with expansions)

set_environment() {
  log "Setting environment for ivy_server..."
  export ROLE="server"
  export PROTOCOL_TESTED="quic"
  export RUST_LOG="debug"
  export RUST_BACKTRACE="1"
  export SOURCE_DIR="/opt/"
  export IVY_DIR="/opt//panther_ivy"
  export PYTHON_IVY_DIR="/usr/local/lib/python3.10/dist-packages/"
  export IVY_INCLUDE_PATH="$$IVY_INCLUDE_PATH:/usr/local/lib/python3.10/dist-packages/ivy/include/1.7"
  export Z3_LIBRARY_DIRS="/opt//panther_ivy/submodules/z3/build"
  export Z3_LIBRARY_PATH="/opt//panther_ivy/submodules/z3/build"
  export LD_LIBRARY_PATH="$$LD_LIBRARY_PATH:/opt//panther_ivy/submodules/z3/build"
  export PROOTPATH="/opt/"
  export ADDITIONAL_PYTHONPATH="/app/implementations/quic-implementations/aioquic/src/:/opt//panther_ivy/submodules/z3/build/python:/usr/local/lib/python3.10/dist-packages/"
  export ADDITIONAL_PATH="/go/bin:/opt//panther_ivy/submodules/z3/build"
  export TEST_ALPN="hq-interop"
  export ZRTT_SSLKEYLOGFILE="/opt//panther_ivy/protocol-testing/quic/last_tls_key.txt"
  export RETRY_TOKEN_FILE="/opt//panther_ivy/protocol-testing/quic/last_retry_token.txt"
  export NEW_TOKEN_FILE="/opt//panther_ivy/protocol-testing/quic/last_new_token.txt"
  export ENCRYPT_TICKET_FILE="/opt//panther_ivy/protocol-testing/quic/last_encrypt_session_ticket.txt"
  export SESSION_TICKET_FILE="/opt//panther_ivy/protocol-testing/quic/last_session_ticket_cb.txt"
  export SAVED_PACKET="/opt//panther_ivy/protocol-testing/quic/saved_packet.txt"
  export initial_max_stream_id_bidi="/opt//panther_ivy/protocol-testing/quic/initial_max_stream_id_bidi.txt"
  export active_connection_id_limit="/opt//panther_ivy/protocol-testing/quic/active_connection_id_limit.txt"
  export initial_max_stream_data_bidi_local="/opt//panther_ivy/protocol-testing/quic/initial_max_stream_data_bidi_local.txt"
  export initial_max_stream_data_bidi_remote="/opt//panther_ivy/protocol-testing/quic/initial_max_stream_data_bidi_remote.txt"
  export initial_max_stream_data_uni="/opt//panther_ivy/protocol-testing/quic/initial_max_stream_data_uni.txt"
  export initial_max_data="/opt//panther_ivy/protocol-testing/quic/initial_max_data.txt"
  export INITIAL_VERSION="1"
  export TEST_TYPE="client"
}

# Initialize environment variables
log "Setting up environment variables..."
set_environment

set -x;
PS4="+ [${BASH_SOURCE:-sh}:${LINENO}] "; export PS4;
export SHELLOPTS
export PATH=$PATH:$ADDITIONAL_PATH;
export PYTHONPATH=$PYTHONPATH:$ADDITIONAL_PYTHONPATH;
env >> /app/logs/ivy_setup.log;
TARGET_IP=$(getent hosts  | awk "{ print \$1 }");
echo "Resolved  IP - $TARGET_IP" >> /app/logs/ivy_setup.log;
IVY_IP=$(hostname -I | awk "{ print \$1 }");
echo "Resolved  ivy_server IP - $IVY_IP" >> /app/logs/ivy_setup.log;

ip_to_hex() {
PS4="[<ip_to_hex>:${LINENO}] "; export PS4; set -x;
  echo $1 | awk -F"." "{ printf(\"%02X%02X%02X%02X\", \$1, \$2, \$3, \$4) }";
}

ip_to_decimal() {
PS4="[<ip_to_decimal>:${LINENO}] "; export PS4; set -x;
  echo $1 | awk -F"." "{ printf(\"%.0f\", (\$1 * 256 * 256 * 256) + (\$2 * 256 * 256) + (\$3 * 256) + \$4) }";
}

TARGET_IP_HEX=$(ip_to_decimal $TARGET_IP);
IVY_IP_HEX=$(ip_to_decimal $IVY_IP);
echo "Resolved  IP in hex - $TARGET_IP_HEX" >> /app/logs/ivy_setup.log;
echo "Resolved ivy_server IP in hex - $IVY_IP_HEX" >> /app/logs/ivy_setup.log;

rm -rf /opt/panther_ivy/protocol-testing/quic/build/*;
echo "Copying QUIC libraries..." >> /app/logs/ivy_setup.log &&
cp -f -a /opt/picotls/*.a "/usr/local/lib/python3.10/dist-packages/ivy/lib/" &&
cp -f -a /opt/picotls/*.a "/opt/panther_ivy/ivy/lib/" &&
cp -f /opt/picotls/include/picotls.h "/usr/local/lib/python3.10/dist-packages/ivy/include/picotls.h" &&
cp -f /opt/picotls/include/picotls.h "/opt/panther_ivy/ivy/include/picotls.h" &&
cp -r -f /opt/picotls/include/picotls/. "/usr/local/lib/python3.10/dist-packages/ivy/include/picotls" &&
cp -f "/opt/panther_ivy/protocol-testing/quic//quic_utils/quic_ser_deser.h" "/usr/local/lib/python3.10/dist-packages/ivy/include/1.7/" &&

update_ivy_tool() {
PS4="[<update_ivy_tool>:${LINENO}] "; export PS4; set -x;
	echo "Updating Ivy tool..." >> /app/logs/ivy_setup.log;
	cd "/opt/panther_ivy" || exit 1;
	cat setup.py >> /app/logs/ivy_setup.log;
	sudo python3.10 setup.py install >> /app/logs/ivy_setup.log 2>&1 &&
	cp lib/libz3.so submodules/z3/build/python/z3 >> /app/logs/ivy_setup.log 2>&1 &&
	echo "Copying updated Ivy files..." >> /app/logs/ivy_setup.log;
	find /opt/panther_ivy/ivy/include/1.7/ -type f -name "*.ivy" -exec cp {} /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ \; >> /app/logs/ivy_setup.log 2>&1;
	echo "Copying updated Z3 files..." >> /app/logs/ivy_setup.log 2>&1;
	cp -f -a /opt/panther_ivy/ivy/lib/*.a "/usr/local/lib/python3.10/dist-packages/ivy/lib/" >> /app/logs/ivy_setup.log 2>&1;
}

update_ivy_tool &&


remove_debug_events() {
PS4="[<remove_debug_events>:${LINENO}] "; export PS4; set -x;
	echo "Removing debug events..." >> /app/logs/ivy_setup.log;
	printf "%s\n" "$@" | xargs -I {} sh -c "
		if [ -f \"\$1\" ]; then
			sed -i \"s/^\\([^#]*debug_event.*\\)/##\\1/\" \"\$1\";
		else
			echo \"File not found - \$1\" >> /app/logs/ivy_setup.log;
		fi
	" _ {};
}

restore_debug_events() {
PS4="[<restore_debug_events>:${LINENO}] "; export PS4; set -x;
	echo "Restoring debug events..." >> /app/logs/ivy_setup.log;
	printf "%s\n" "$@" | xargs -I {} sh -c "
		if [ -f \"\$1\" ]; then
			sed -i \"s/^##\\(.*debug_event.*\\)/\\1/\" \"\$1\";
		else
			echo \"File not found - \$1\" >> /app/logs/ivy_setup.log;
		fi
	" _ {};
}

setup_ivy_model() {
PS4="[<setup_ivy_model>:${LINENO}] "; export PS4; set -x;
	echo "Setting up Ivy model..." >> /app/logs/ivy_setup.log &&
	echo "Updating include path of Python with updated version of the project from /opt/panther_ivy/protocol-testing/quic/" >> /app/logs/ivy_setup.log &&
	echo "Finding .ivy files..." >> /app/logs/ivy_setup.log &&
	find "/opt/panther_ivy/protocol-testing/quic/" -type f -name "*.ivy" -exec sh -c "
		echo \"Found Ivy file - \$1\" >> /app/logs/ivy_setup.log;
		if [ 10 -gt 10 ]; then
			echo \"Removing debug events from \$1\" >> /app/logs/ivy_setup.log;
			remove_debug_events \"\$1\";
		fi;
		echo \"Copying Ivy file to include path...\" >> /app/logs/ivy_setup.log;
		cp -f \"\$1\" \"/usr/local/lib/python3.10/dist-packages/ivy/include/1.7/\";
	" _ {} \;;
	ls -l /usr/local/lib/python3.10/dist-packages/ivy/include/1.7/ >> /app/logs/ivy_setup.log;
}

setup_ivy_model &&

cd /opt/panther_ivy/protocol-testing/quic/quic_tests/client_tests;
PYTHONPATH=$PYTHON_IVY_DIR ivyc trace=false show_compiled=false target=test test_iters=300 quic_client_test_max.ivy >> /app/logs/ivy_setup.log 2>&1;
(ls >> /app/logs/ivy_setup.log 2>&1 ;

cp /opt/panther_ivy/protocol-testing/quic/quic_tests/client_tests/quic_client_test_max* /opt/panther_ivy/protocol-testing/quic/build/;
ls /opt/panther_ivy/protocol-testing/quic/build/ >> /app/logs/ivy_setup.log 2>&1 ;)
 && \
 (touch /app/sync_logs/ivy_ready.log)
cd /opt/panther_ivy/protocol-testing/quic/;
(touch /app/logs/ivy_server.pcap; tshark -a duration:100 -i any -w /app/logs/ivy_server.pcap;) &
echo "Running timeout 100 build/quic_client_test_max seed=0 the_cid=1 server_port=4443 iversion=1 server_addr=$$IVY_IP_HEX > /app/logs/quic_client_test_max.log 2> /app/logs/quic_client_test_max.err" >> /app/logs/ivy_server_setup.log;
(exec timeout 100 /opt/panther_ivy/protocol-testing/quic//build/quic_client_test_max seed=0 the_cid=1 server_port=4443 iversion=1 server_addr=$$IVY_IP_HEX > /app/logs/quic_client_test_max.log 2> /app/logs/quic_client_test_max.err) ;
( cp /opt/panther_ivy/protocol-testing/quic/build/quic_client_test_max /app/logs/quic_client_test_max && \  rm /opt/panther_ivy/protocol-testing/quic/build/quic_client_test_max*; )'