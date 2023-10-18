graph [
  directed 0
  node [
    id 0
    label "client"
    host_bandwidth_down "100 Gbit"
    host_bandwidth_up "100 Gbit"
  ]
  node [
    id 0
    label "server"
    host_bandwidth_down "100 Gbit"
    host_bandwidth_up "100 Gbit"
  ]
  edge [
    source 0
    target 0
    label "lo 0"
    latency "100 ms"
    jitter "0 ms"
    packet_loss 0.0
  ]
]