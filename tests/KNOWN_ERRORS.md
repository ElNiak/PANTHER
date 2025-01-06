1. 

```
2024-12-19 15:40:50,417 [ERROR] - docker_compose - Failed to launch Docker Compose environment: time="2024-12-19T15:40:50+01:00" level=warning msg="The \"UID\" variable is not set. Defaulting to a blank string."
time="2024-12-19T15:40:50+01:00" level=warning msg="The \"GID\" variable is not set. Defaulting to a blank string."
time="2024-12-19T15:40:50+01:00" level=warning msg="The \"UID\" variable is not set. Defaulting to a blank string."
time="2024-12-19T15:40:50+01:00" level=warning msg="The \"GID\" variable is not set. Defaulting to a blank string."
time="2024-12-19T15:40:50+01:00" level=warning msg="The \"UID\" variable is not set. Defaulting to a blank string."
time="2024-12-19T15:40:50+01:00" level=warning msg="The \"GID\" variable is not set. Defaulting to a blank string."
validating /home/crochetch/Documents/Projects/VerificationQUIC/SCP-TEST/PANTHER/outputs/2024-12-19_15-40-33_unnamed_experiment/Fuzz_QUIC_IyvClient_Server_Communication_Test/docker_compose.yml: services.picoquic_client.ports must be a list
```

2. 

```
2024-12-19 15:43:16,075 [ERROR] - docker_compose - Failed to launch Docker Compose environment: time="2024-12-19T15:43:15+01:00" level=warning msg="The \"UID\" variable is not set. Defaulting to a blank string."
time="2024-12-19T15:43:15+01:00" level=warning msg="The \"GID\" variable is not set. Defaulting to a blank string."
time="2024-12-19T15:43:15+01:00" level=warning msg="The \"UID\" variable is not set. Defaulting to a blank string."
time="2024-12-19T15:43:15+01:00" level=warning msg="The \"GID\" variable is not set. Defaulting to a blank string."
time="2024-12-19T15:43:15+01:00" level=warning msg="The \"UID\" variable is not set. Defaulting to a blank string."
time="2024-12-19T15:43:15+01:00" level=warning msg="The \"GID\" variable is not set. Defaulting to a blank string."
 Network fuzz_quic_iyvclient_server_communication_test_panther_network  Creating
 Network fuzz_quic_iyvclient_server_communication_test_panther_network  Created
 Volume "fuzz_quic_iyvclient_server_communication_test_shared_logs"  Creating
 Volume "fuzz_quic_iyvclient_server_communication_test_shared_logs"  Created
 Container picoquic_client  Creating
 Container picoquic_server  Creating
 Container fuzz_in_the_middle  Creating
 Container fuzz_in_the_middle  Created
 Container picoquic_server  Created
 Container picoquic_client  Created
 Container picoquic_client  Starting
 Container fuzz_in_the_middle  Starting
 Container picoquic_server  Starting
 Container picoquic_server  Started
 Container fuzz_in_the_middle  Started
Error response from daemon: driver failed programming external connectivity on endpoint picoquic_client (de27fff1f2e76eed84a17e6dc935d5d0c63d1a346b69c38750f34260589f2b4d): Bind for 0.0.0.0:8080 failed: port is already allocated
```