#!/bin/bash
set -e
# needs the $ROLE={server,client} environment variable telling if we act as a server or client
# Set up the routing needed for the simulation.

if [ "$ROLE" == "client" ]; then
    # Wait for the simulator to start up.
    echo "Starting QUIC client..."
    echo "Client params: $@"
    /client/client "$@"
else
    echo "Running QUIC server."
    /server/server "$@"
fi
