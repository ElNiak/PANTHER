# QUIC-FormalVerification

## Installation

Currently, only work under Ubuntu 18

With Python Virtual Environment (todo)
```
export VirtualEnv="env"
sudo apt install virtualenv
virtualenv -p /usr/bin/python2.7 env
source env/bin/activate
cd scripts/installers/
bash install.sh
```

Without Python Virtual Environment
```
cd scripts/installers/
bash install.sh
```


## TODO

- reput the adversarial env for tested (!= port, adress, cid) -> long run (40 min same server)

- Why sometimes the deserializer do not take the full packet ?

- NS3

- Why removing the dcil and scil field ?

- VN: when the list no contain "Supported Version: Unknown (0x0a1a2a3a) (GREASE)"
    => never run read() from udp_impl.ivy TODO

- TODO 0rtt same keys + tps

- How to activate the generation of 2 packets at the same time ?
