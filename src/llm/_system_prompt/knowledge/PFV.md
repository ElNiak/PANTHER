# Introduction to PFV tool

PFV harnesses cutting-edge techniques in network protocol verification, merging the capabilities of the Shadow network simulator with the Ivy formal verification tool. This powerful combination facilitates the examination of time properties in network protocols. A specialized time module enhances Ivy, enabling it to handle complex quantitative-time properties with greater precision. PFV's effectiveness is highlighted through its application to the QUIC protocol. By refining QUIC's formal specification in Ivy, the tool not only verifies essential aspects of the protocol but also exposes real-world implementation errors, demonstrating its practical utility. This innovative integration paves the way for more thorough, efficient, and precise protocol testing and verification.

## PFV tool

The project can be found at https://github.com/ElNiak/PFV/tree/production or in PFV.zip

The documentation can be found at https://github.com/ElNiak/PFV/blob/production/README.md

The PFV project is organized into the following key directories:
PFV/
└── data/ # Data directory for storing results and logs.
└── src/
    ├── Protocols-Ivy/ # Core of protocol specifications and testing.
    │   ├── protocol-testing/
    │   │   ├── quic/
    │   │   ├── minip/
    │   │   ├── coap/
    │   │   └── [other protocols]
    │   └── ivy/[ivy core in python files]
    ├── implementations/ # Various protocols implementation modules.
    │   ├── quic-implementations/
    │   │       ├── picoquic/
    │   │       ├── aioquic/
    │   │       ├── lsquic/
    │   │       └── [protocol implementations]
    │   └── [other protocols]
    ├── containers/ # Dockerfile definitions for different environments.
    │   └── [Dockerfile definitions]
    └── pfv/ #  Main PFV module.
        ├── pfv.py
        ├── pfv_runner/ [test preparation]
        ├── ...
        ├── pfv_tester/ [test execution]
        └── configs/
            └── [configuration files]

## Shadow network simulator

Shadow is a scientific experimentation tool that simplifies research, development, testing, and evaluation of real networked applications by connecting them through an internally simulated distributed network. 

The documentation can be found at https://shadow.github.io/

The code can be found at https://github.com/shadow/shadow

The following scientific papers describe Shadow:
* "Shadow: Running Tor in a Box for Accurate and Efficient Experimentation" by Rob Jansen and Nicholas Hopper in the Symposium on Network and Distributed System Security, 2012. https://www.ndss-symposium.org/wp-content/uploads/2017/09/09_3.pdf
* "Co-opting Linux Processes for High Performance Network Simulation" by Rob Jansen, Jim Newsome, and Ryan Wails in the USENIX Annual Technical Conference, 2022. https://www.usenix.org/system/files/atc22-jansen.pdf