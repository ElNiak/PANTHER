# Contributing

## :open_file_folder: Project Structure



### :open_file_folder: Directory Structure



The PANTHER project is organized into the following key directories:

```
PANTHER/
└── data/
└── src/
    ├── Protocols-Ivy/
    │   ├── protocol-testing/
    │   │   ├── quic/
    │   │   ├── minip/
    │   │   ├── coap/
    │   │   └── [other protocols]
    │   └── ivy/[ivy-core]
    ├── implementations/
    │   ├── quic-implementations/
    │   │       ├── picoquic/
    │   │       ├── aioquic/
    │   │       ├── lsquic/
    │   │       └── [protocol implementations]
    │   └── [other protocols]
    ├── containers/
    │   └── [Dockerfile definitions]
    └── panther/
        ├── panther.py
        ├── panther_runner/ [test preparation]
        ├── ...
        ├── panther_tester/ [test execution]
        └── configs/
            └── [configuration files]
```
- `data/`: Data directory for storing results and logs.
- `panther/`: Main PANTHER module.
- `Protocols-Ivy/`: Core of protocol specifications and testing.
- `implementations/`: Various QUIC implementation modules.
- `containers/`: Dockerfile definitions for different environments.




### :framed_picture: Architecture Diagrams



| Docker Compose Architecture | Docker Container Internal Architecture |
|:---------------------------:|:--------------------------------------:|
| ![Docker Compose Architecture](readme-res/DALL·E%202024-01-05%2006.59.32%20-%20A%20diagram%20illustrating%20the%20architecture%20of%20a%20Docker%20Compose%20setup%20for%20the%20PFV%20(Protocols%20Formal%20Verification)%20project.%20It%20shows%20various%20Docker%20contain.png) | ![Docker Container Internal Architecture](readme-res/DALL·E%202024-01-05%2007.00.02%20-%20An%20internal%20architecture%20diagram%20of%20a%20Docker%20container%20for%20the%20PFV%20(Protocols%20Formal%20Verification)%20project.%20The%20diagram%20should%20show%20the%20layering%20of%20co.png) |






---
