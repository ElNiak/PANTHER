# New protocol integration to PFV

## Introduction

Before starting the protocol integration to PFV, you and the experts MUST read the documentations provided in Documentation.md

## Steps to implement a new protocol

### Step 1: RFC Analysis & project initialization

Read the RFCs and other documents that define the protocol. 
You must understand the protocol's behavior and the protocol's components.
You must identify the protocol layer.

You should have a good base for your project. You can inspire yourself from the existing projects in Protocols-Ivy/protocol-testing/ to create your project. You can now create your project in src/pfv/*

### Step 2: Add protocols implementation to be tested

Find some implementations of the protocol and add them to the PFV tool.
You must defined containers for the implementations.

#### Example: QUIC

Example for QUIC can be found at: https://github.com/ElNiak/PFV/tree/production/src/containers

### Step 3: Automating the protocol's tests in PFV tool

Update the PFV tool to automatically run the protocol's tests.

#### Example: QUIC

Example for QUIC can be found at: https://github.com/ElNiak/PFV/blob/production/src/pfv/pfv_runner/pfv_quic_runner.py, https://github.com/ElNiak/PFV/tree/production/src/pfv/pfv_tester/pfv_quic_tester.py, https://github.com/ElNiak/PFV/blob/production/src/pfv/pfv_stats/pfv_quic_stats.py and https://github.com/ElNiak/PFV/blob/production/src/pfv/pfv.py

### Step 4: Create configuration files for the protocol's tests

Update the global configuration file to include:
* The protocol's implementation containers
* The protocol's related tools containers


Update the default configuration file to include:
* The protocol name at [verified_protocol]


Create configuration files for the protocol's tests. It contains the Ivy tests, the global parameters related to the protocol.

Create configuration files for the protocol implementations to automatize the commands to run the protocol's implementations for each endpoint type.

#### Example: QUIC
Example can be found at: https://github.com/ElNiak/PFV/blob/production/src/pfv/configs/global-conf.ini

Example can be found at: https://github.com/ElNiak/PFV/blob/production/src/pfv/configs/default_config.ini

Example can be found at: https://github.com/ElNiak/PFV/blob/production/src/pfv/configs/quic/quic_config.ini

Example can be found at: https://github.com/ElNiak/PFV/blob/production/src/pfv/configs/quic/default_quic_implem_config.ini with a concretization for picoquic implementation at https://github.com/ElNiak/PFV/blob/production/src/pfv/configs/quic/implem-client/picoquic.ini for the client and https://github.com/ElNiak/PFV/blob/production/src/pfv/configs/quic/implem-server/picoquic.ini for the server.

