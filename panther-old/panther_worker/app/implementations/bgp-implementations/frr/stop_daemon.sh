#!/bin/bash
 

# # Error messages with PIDs
# error_messages=$(/etc/init.d/frr stop 2>&1)

# # Extract PIDs
# zebra_pid=$(echo "$error_messages" | grep -oP 'zebra, pid \K\d+')
# staticd_pid=$(echo "$error_messages" | grep -oP 'staticd, pid \K\d+')
# bgpd_pid=$(echo "$error_messages" | grep -oP 'bgpd, pid \K\d+')
# mgmtd_pid=$(echo "$error_messages" | grep -oP 'mgmtd, pid \K\d+')

# # Function to stop FRR daemon by PID
# stop_frr_daemon() {
#     pid=$1
#     if [ -n "$pid" ]; then
#         echo "Stopping FRR daemon with PID $pid"
#         kill -TERM $pid
#         sleep 2
#         if kill -0 $pid 2>/dev/null; then
#             echo "Forcibly stopping FRR daemon with PID $pid"
#             kill -9 $pid
#         else
#             echo "FRR daemon with PID $pid stopped gracefully"
#         fi
#     fi
# }

# # Stop FRR daemons
# stop_frr_daemon $zebra_pid
# stop_frr_daemon $staticd_pid
# stop_frr_daemon $bgpd_pid
# stop_frr_daemon $mgmtd_pid

# /etc/init.d/frr start

ip netns exec implem /usr/lib/frr/watchfrr.sh restart all