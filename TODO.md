# :memo: TODO List

- [ ] Rename gits

##  :memo: PFV

- [ ] refactor

- [ ] change os.system with subprocess or with python funct

- [ ] add barplot progression

- [ ] Complete config file

- [ ] Add template to automatise the addition of new protocols without modifying the code

    - [ ] should remove the <protocol>_runner/tester/stats.py

    - [ ] Add envariable to config file and automatise


- [ ] Reinstate adversarial environment testing (different ports, addresses, connection IDs) for extended runs (approx. 40 minutes on the same server).
- [ ] Investigate occasional incomplete packet deserialization.
- [ ] Implement integration with NS3.
- [ ] Clarify the removal of dcil and scil fields.
- [ ] Address the VN issue where the list does not contain "Supported Version: Unknown (0x0a1a2a3a) (GREASE)" - [ ] leads to failure in read() execution in udp_impl.ivy.
- [ ] Resolve the 0rtt issue with the same keys and transport parameters.
- [ ] Explore methods to trigger simultaneous generation of multiple packets.

##  :memo: PFV webapp

- [ ] refactor /creator with accordingly -> to allow and adapt multiple protocol

- [ ] refactor /result with accordingly -> to allow and adapt multiple protocol

- [ ] Allow to add new implementation configuration

##  :memo: PVF architecture

- [ ] Make docker internal system match to current system

- [ ] build.py to replace makefile

- [ ] update docker compose file

##  :memo: PVF LLM

- [ ] Add LLM to the webapp