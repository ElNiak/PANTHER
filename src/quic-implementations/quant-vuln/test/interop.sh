#! /usr/bin/env bash

# Set up the routing needed for the simulation
/setup.sh

if [ -n "$TESTCASE" ]; then
    case "$TESTCASE" in
    "versionnegotiation"|"handshake"|"transfer"|"retry"|"resumption"|"multiconnect"|"zerortt"|"chacha20")
        ;;
    *)
        exit 127
        ;;
    esac
fi

# The following variables are available for use:
# - ROLE contains the role of this execution context, client or server
# - SERVER_PARAMS contains user-supplied command line parameters
# - CLIENT_PARAMS contains user-supplied command line parameters

# For quant, call client and server with full path, so addr2line can find them

if [ "$ROLE" == "client" ]; then
    CLIENT_ARGS="-i eth0 -w -q $QLOGDIR -l $SSLKEYLOGFILE -t 150 -x 50 \
        -e 0xff00001d $CLIENT_ARGS"

    # Wait for the simulator to start up.
    /wait-for-it.sh sim:57832 -s -t 30
    cd /downloads || exit

    skip=0
    case "$TESTCASE" in
    "versionnegotiation")
        CLIENT_ARGS="-e 12345678 $CLIENT_ARGS"
        ;;
    "chacha20")
        CLIENT_ARGS="-a $CLIENT_ARGS"
        ;;
    "resumption"|"zerortt")
        REQS=($REQUESTS)
        REQUESTS=${REQS[0]}
        /usr/local/bin/client $CLIENT_ARGS $REQUESTS 2>&1 | \
            tee -i -a "/logs/$ROLE.log"
        echo "XXX $ROLE DONE" | tee -i -a "/logs/$ROLE.log"
        REQUESTS=${REQS[@]:1}
        ;;
    "multiconnect")
        for req in $REQUESTS; do
            ((skip++))
            /usr/local/bin/client $CLIENT_ARGS \
                -q "$QLOGDIR" $req 2>&1 | \
                tee -i -a "/logs/$ROLE.log"
            echo "XXX $ROLE DONE" | tee -i -a "/logs/$ROLE.log"
        done
        ;;
    *)
        ;;
    esac

    if [ $skip -eq 0 ]; then
        /usr/local/bin/client $CLIENT_ARGS $REQUESTS 2>&1 | \
            tee -i -a "/logs/$ROLE.log"
        echo "XXX $ROLE DONE" | tee -i -a "/logs/$ROLE.log"
    fi
    sed 's,\x1B\[[0-9;]*[a-zA-Z],,g' "/logs/$ROLE.log" > "/logs/$ROLE.log.txt"

elif [ "$ROLE" == "server" ]; then
    case "$TESTCASE" in
    "retry")
        SERVER_ARGS="-r $SERVER_ARGS"
        ;;
    *)
        ;;
    esac

    /usr/local/bin/server $SERVER_ARGS -i eth0 -d /www -p 443 -p 4434 -t 0 \
        -x 50 -c /tls/dummy.crt -k /tls/dummy.key -q "$QLOGDIR" 2>&1 \
            | tee -i -a "/logs/$ROLE.log" \
            | sed -u 's,\x1B\[[0-9;]*[a-zA-Z],,g' \
            | tee -i -a "/logs/$ROLE.log.txt"
fi
