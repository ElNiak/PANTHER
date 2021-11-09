#!/bin/bash
set -e

if [ "$ROLE" == "client" ]; then
    GLOG_minloglevel=3 /mvfst-generic/generic "$@"
elif [ "$ROLE" == "server" ]; then
    echo "## Starting mvfst server..."
    GLOG_minloglevel=3 /mvfst-generic/generic -S "$@"
fi
