#!/bin/bash
set -e

if [ "$ROLE" == "client" ]; then
    /ngtcp2-generic/generic-http3-client $@
elif [ "$ROLE" == "server" ]; then
    echo "## Starting ngtcp2 server..."
    /ngtcp2-generic/generic-http3-server $@
fi