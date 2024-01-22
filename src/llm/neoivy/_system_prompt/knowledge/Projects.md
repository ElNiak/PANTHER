# Projects

All implemented Internet protocols projets are listed here. Their specifications are defined in Request For Comments (RFCs) and other documents. The RFCs are defined in https://www.rfc-editor.org/rfc-index.html.

## Project Descriptions & Links
## Layer 1: Application layer protocols
No protocols yet

## Layer 2: Transport layer protocols
* QUIC
* UDP
* TCP

## Layer 3: Security layer protocols
* TLS1.3

## Layer 4: Network layer protocols
* IPv4
* IPv6

## Layer 5: Data link layer protocols
No protocols yet

## Layer 6: Physical layer protocols
No protocols yet

## Layer 7: Fake protocols
* MiniP

# Project Descriptions & Links

## Ivy

All projects are written in Ivy code version 1.7.
Read IvyDocumentation.md for more information on Ivy.
The website https://kenmcmil.github.io/ivy/{all_subrurls}
Protocols-Ivy.zip contains the Ivy code for all projects.

## Network-centric Compositional Testing (NCT)

All projects follow the Network-centric Compositional Testing (NCT) methodology.
Read NCT.md for more information on NCT.

## Protocol Formal Verification (PFV)

All projects are tested using the Protocol Formal Verification (PFV) tool.
Read PFV.md for more information on PFV.

## Projects scientific papers

Thr project also used concept in the following scientific papers: 
* Modular specification and verification of a cache-coherent interface (Kenneth L. McMillan), In 2016 Formal Methods in Computer-Aided Design, FMCAD 2016, Mountain View, CA, USA, October 3-6, 2016, 2016. https://doi.org/10.1109/FMCAD.2016.7886668
* Ivy: safety verification by interactive generalization (Oded Padon and Kenneth L. McMillan and Aurojit Panda and Mooly Sagiv and Sharon Shoham), In Proceedings of the 37th ACM SIGPLAN Conference on Programming Language Design and Implementation, PLDI 2016, Santa Barbara, CA, USA, June 13-17, 2016, 2016. http://doi.acm.org/10.1145/2908080.2908118
* Temporal Prophecy for Proving Temporal Properties of Infinite-State Systems (Oded Padon and Jochen Hoenicke and Kenneth L. McMillan and Andreas Podelski and Mooly Sagiv and Sharon Shoham), In 2018 Formal Methods in Computer Aided Design, FMCAD 2018, Austin, TX, USA, October 30 – November 2, 2018 (Nikolaj Bjørner, Arie Gurfinkel, eds.), IEEE, 2018. http://mcmil.net/pubs/FMCAD18.pdf
* Modularity for decidability of deductive verification with applications to distributed systems (Marcelo Taube and Giuliano Losa and Kenneth L. McMillan and Oded Padon and Mooly Sagiv and Sharon Shoham and James R. Wilcox and Doug Woos), In Proceedings of the 39th ACM SIGPLAN Conference on Programming Language Design and Implementation, PLDI 2018, Philadelphia, PA, USA, June 18-22, 2018, 2018. http://doi.acm.org/10.1145/3192366.3192414
* Deductive Verification in Decidable Fragments with Ivy (Kenneth L. McMillan and Oded Padon), In Static Analysis – 25th International Symposium, SAS 2018, Freiburg, Germany, August 29-31, 2018, Proceedings (Andreas Podelski, ed.), Springer, volume 11002, 2018 http://mcmil.net/pubs/SAS18.pdf
* Formal specification and testing of QUIC (Kenneth L. McMillan and Lenore D. Zuck), In Proceedings of ACM Special Interest Group on Data Communication (SIGCOMM’19), ACM, 2019. http://mcmil.net/pubs/SIGCOMM19.pdf 

## Layer 1: Application layer protocols
No protocols yet

## Layer 2: Transport layer protocols
* Protocol QUIC: https://github.com/ElNiak/Protocols-Ivy/tree/master/protocol-testing/quic/{all_subfolders}

* Protocol UDP: https://github.com/ElNiak/Protocols-Ivy/blob/master/ivy/include/1.7/udp_impl.ivy

* Protocol TCP: https://github.com/ElNiak/Protocols-Ivy/blob/master/ivy/include/1.7/tcp_impl.ivy

## Layer 3: Security layer protocols
* Protocol TLS1.3: https://github.com/ElNiak/Protocols-Ivy/blob/master/ivy/include/1.7/tls_picotls.ivy

# Layer 4: Network layer protocols
* Protocol IPv4: https://github.com/ElNiak/Protocols-Ivy/blob/master/ivy/include/1.7/ip.ivy

* Protocol IPv6: https://github.com/ElNiak/Protocols-Ivy/blob/master/ivy/include/1.7/ip6.ivy

## Layer 5: Data link layer protocols
No protocols yet

## Layer 6: Physical layer protocols
No protocols yet

## Layer 7: Fake protocols
* Protocol MiniP: https://github.com/ElNiak/Protocols-Ivy/tree/master/protocol-testing/minip/{all_subfolders}