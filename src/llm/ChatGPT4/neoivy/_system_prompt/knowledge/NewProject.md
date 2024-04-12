# New protocol formal specification

Before starting the protocol formal specification, you and the experts MUST read the documentations provided in Documentation.md

## Steps to implement a new protocol

### Step 1: RFC Analysis & project initialization

#### Description of the step

Read the RFCs and other documents that define the protocol. 
You must understand the protocol's behavior and the protocol's components.
You must identify the protocol layers, usually these layers are the formal components.

Determine if the protocol is on top of UDP or TCP to instanciate in your project the network layer protocol.
If the protocol is on top of UDP, you know that you need to include udp_impl.ivy file in your project.
If the protocol is on top of TCP, you know that you need to include tcp_impl.ivy file in your project.

You need to:

Determine if the protocol is a secure protocol or not. 
If the protocol is a secure protocol on top of TLS1.3, you know that you need to include tls_msg.ivy (which itself include tls_picotls.ivy, the picotls interface with Ivy) file in your project. You also need to have a security component in your project. 
If it is secure and not on top of TLS1.3, you need to create the protocol's security component and include it in your project.
Determine if the protocol is a client-server protocol or a peer-to-peer protocol.

You can now have a shim component that instanciate the network and the security layer protocol if needed. You can also have sub-shim components for the different protocol endpoints.

You should have a good base for your project. You can inspire yourself from the existing projects in Protocols-Ivy/protocol-testing/ to create your project. You can now create your project in Protocols-Ivy/protocol-testing/<protocol_name>/

#### Example: QUIC

QUIC is defined in the following RFCs: RFC9000, RFC9001, RFC9002

QUIC is a transport layer protocol on top of UDP. So you need to include udp_impl.ivy file in your project, in this case in src/Protocols-Ivy/protocol-testing/quic/quic_utils/quic_locale.ivy. This allows to instanciate the network layer protocol as presented:
```ivy
include udp_impl
instance net : udp_impl(endpoint_id,prot.arr,quic_prot_ser,quic_prot_deser)

```
quic_prot_ser and quic_prot_deser are the serialization and deserialization (at bytes level) functions of the protocol. They allow to get the QUIC data as byte array that will then be used to be encrypted or decrypted before being sent on the wire. They are defined in src/Protocols-Ivy/protocol-testing/quic/quic_stack/quic_protection.ivy
Here is the content of quic_protection.ivy focus on the serialization and deserialization functions:
```ivy
# Because of packet coalescing, we need a custom serializer and
# deserializer for protected packets. In particular, we need to look
# at the length field of the long form packets to find the packet
# boundaries within a datagram.

# The serializer just concatenates the packets

object quic_prot_ser = {}

<<< member

    class `quic_prot_ser`;

>>>

<<< impl

    class `quic_prot_ser` : public ivy_binary_ser_128 {
    public:

        void open_list(int) {
        }

        virtual void  set(int128_t res) {
            setn(res,1);
        }    
    };

>>>

# The deserializer is tricker. It looks at the first byte of the packet
# to determine if it is a long or short packet. For long packets, it computes
# the total length based on the header bytes and the payload length field.
# This is a bit redundant with the above code, however this can't be helped as
# there is no way for the deserializer to have access to the ivy object.

object quic_prot_deser = {}

<<< member

    class `quic_prot_deser`;

>>>

<<< impl

    class `quic_prot_deser` : public ivy_binary_deser_128 {
        int data_remaining;
        int level;
    public:
        quic_prot_deser(const std::vector<char> &inp) : ivy_binary_deser_128(inp),level(0) {}

        void  get(int128_t &res) {
            getn(res,1);
        }    

        unsigned char peek(unsigned p) {
            return more(p-pos+1) ? inp[p] : 0;
        }

        unsigned get_var_int_len(unsigned p) {
            unsigned code = peek(p) & 0xc0;
            return (code == 0x00) ? 1 : (code == 0x40) ? 2 : (code == 0x80) ? 4 : 8;
        }

        unsigned get_var_int(unsigned p, unsigned len) {
            unsigned res = peek(p) & 0x3f;
            for (unsigned i = 1; i < len; i++)
                res = (res << 8) + peek(p+i);
            return res;
        }
            
        void open_list() {
            if (level != 1)
                return;
            if (peek(pos) & 0x80) { // a long packet
                unsigned dcil = peek(pos+5);
                unsigned scil = peek(pos+6+dcil);
                unsigned pnum_pos = pos + 7 + dcil + scil;
                unsigned ptype = peek(pos) & 0x30;
                if (ptype == 0x00) { // initial packets have tokens
                    unsigned len = get_var_int_len(pnum_pos);
                    unsigned retry_token_len = get_var_int(pnum_pos,len);
                    pnum_pos = pnum_pos + len + retry_token_len;
                } else if (ptype == 0x30) { // Retry packets have tokens
                    unsigned packet_size = inp.size();
                    unsigned len = packet_size - 16 - 1 - dcil - 1 - scil - 1 - 4;
                    pnum_pos = pnum_pos + len + 16;
                    data_remaining = pnum_pos-pos;
                }
                if (inp[1]+inp[2]+inp[3]+inp[4] == 0) {
                    // Version negociation
                    std::cerr << "Version n (prot) \n";
                    unsigned remain = inp.size() - pnum_pos;
                    data_remaining = (pnum_pos-pos) + remain;
                }
                else if ((ptype == 0x00 || ptype == 0x20 || ptype == 0x10)) { 
                    // Only for Handshake and initial
                    unsigned len = get_var_int_len(pnum_pos);
                    unsigned pyld_len = get_var_int(pnum_pos,len);
                    data_remaining = (pnum_pos-pos) + len + pyld_len;
                }  
            }
            else {
                data_remaining = 0x7fffffff;
            }
        }

        bool open_list_elem() {
            if (!more(1)) {
                return false;
            }
            bool res = true;
            if (level == 1) {
                res = data_remaining-- > 0;
            }
            if (res) level++;
            return res;
        }
        void close_list_elem() {
            level--;
        }
    };

>>>
```

QUIC is a secure protocol on top of TLS1.3. This means that you need to include tls_msg.ivy file in your project, in this case in src/Protocols-Ivy/protocol-testing/quic/quic_utils/quic_locale.ivy. This allows to instanciate the security layer protocol as presented:
```ivy
include tls_msg
object tls_api = {
    instance id : long_unbounded_sequence # unbounded_sequence #cid #
    instance lower : tls_lower_intf(id,stream_data)
    instance upper : tls_intf(id,stream_pos,stream_data,lower,tls_extensions,tls_hand_extensions,tls_ser,pkt_num)
}  
```
tls_ser is the serialization function of the protocol. It allows to get the TLS1.3 data message types as byte array that will then be used to be encrypted or decrypted before being sent on the wire. It is defined in src/Protocols-Ivy/protocol-testing/quic/quic_stack/quic_tls.ivysrc/Protocols-Ivy/protocol-testing/quic/tls_stack/tls_deser_ser.ivy

The security component is defined in src/Protocols-Ivy/protocol-testing/quic/quic_stack/quic_protection.ivy.

QUIC is a client-server protocol. This means that you need to define the client and server endpoints in your project. They are defined in src/Protocols-Ivy/protocol-testing/quic/quic_entities/<filename>.ivy and their behavior is defined in src/Protocols-Ivy/protocol-testing/quic/quic_entities_behavior/<filename>.ivy

QUIC shims are defined in src/Protocols-Ivy/protocol-testing/quic/quic_shims/<filename>.ivy

### Step 2: Protocol components identification

#### Description of the step

Carefully read the RFC to identify the protocol main components. 

For each component, identify the following:
* The component's name
* The component's type (e.g. packet, header, field, etc.)
* The component's fields
* The component's invariants
* The component's transitions
* The component's transitions' invariants
* The component's transitions' actions
* The component's transitions' actions' invariants
* The component's transitions' actions' effects
* The component's transitions' actions' effects' invariants
* The component's relations to other components
* The component's requirements from the RFC (statement with MUST). Explicit where in the RFC the requirement is found. Note that some requirement are implicit and must be identified by the expert. Note that some requirement are not explicitly stated in the RFC but are implicitly stated in the RFC. Note that some requirement are not explicitly stated in the RFC but are implicitly stated in other documents. 
* If the component need a serialization and deserialization function in C++

List for each component the requirements and invariants defined in the RFCs and other documents.


#### Example: QUIC

The some of the main components of QUIC are :
- the different QUIC packets. QUIC define long header packets and short header packets. Long header packets are used for the initial handshake, retry and stateless reset, version negociation and short header packets are used for the data exchange. As example, the Initial packet is defined in the RFC9000:
```
 17.2.2. Initial Packet

An Initial packet uses long headers with a type value of 0x00. It carries the first CRYPTO frames sent by the client and server to perform key exchange, and it carries ACK frames in either direction.

Initial Packet {
  Header Form (1) = 1,
  Fixed Bit (1) = 1,
  Long Packet Type (2) = 0,
  Reserved Bits (2),
  Packet Number Length (2),
  Version (32),
  Destination Connection ID Length (8),
  Destination Connection ID (0..160),
  Source Connection ID Length (8),
  Source Connection ID (0..160),
  Token Length (i),
  Token (..),
  Length (i),
  Packet Number (8..32),
  Packet Payload (8..),
}

Figure 15: Initial Packet

The Initial packet contains a long header as well as the Length and Packet Number fields; see Section 17.2. The first byte contains the Reserved and Packet Number Length bits; see also Section 17.2. Between the Source Connection ID and Length fields, there are two additional fields specific to the Initial packet.

Token Length:

    A variable-length integer specifying the length of the Token field, in bytes. This value is 0 if no token is present. Initial packets sent by the server MUST set the Token Length field to 0; clients that receive an Initial packet with a non-zero Token Length field MUST either discard the packet or generate a connection error of type PROTOCOL_VIOLATION.

Token:

    The value of the token that was previously provided in a Retry packet or NEW_TOKEN frame; see Section 8.1.

In order to prevent tampering by version-unaware middleboxes, Initial packets are protected with connection- and version-specific keys (Initial keys) as described in [QUIC-TLS]. This protection does not provide confidentiality or integrity against attackers that can observe packets, but it does prevent attackers that cannot observe packets from spoofing Initial packets.
The client and server use the Initial packet type for any packet that contains an initial cryptographic handshake message. This includes all cases where a new packet containing the initial cryptographic message needs to be created, such as the packets sent after receiving a Retry packet; see Section 17.2.5.A server sends its first Initial packet in response to a client Initial. A server MAY send multiple Initial packets. The cryptographic key exchange could require multiple round trips or retransmissions of this data.The payload of an Initial packet includes a CRYPTO frame (or frames) containing a cryptographic handshake message, ACK frames, or both. PING, PADDING, and CONNECTION_CLOSE frames of type 0x1c are also permitted. An endpoint that receives an Initial packet containing other frames can either discard the packet as spurious or treat it as a connection error.The first packet sent by a client always includes a CRYPTO frame that contains the start or all of the first cryptographic handshake message. The first CRYPTO frame sent always begins at an offset of 0; see Section 7.Note that if the server sends a TLS HelloRetryRequest (see Section 4.7 of [QUIC-TLS]), the client will send another series of Initial packets. These Initial packets will continue the cryptographic handshake and will contain CRYPTO frames starting at an offset matching the size of the CRYPTO frames sent in the first flight of Initial packets.
```
This component need a serialization and deserialization function in C++ to be able to be sent on the wire.

- the different QUIC frame types. QUIC define different frame types. As example, the STREAM frame is defined in the RFC9000:
```
 19.8. STREAM Frames

STREAM frames implicitly create a stream and carry stream data. The Type field in the STREAM frame takes the form 0b00001XXX (or the set of values from 0x08 to 0x0f). The three low-order bits of the frame type determine the fields that are present in the frame:
The OFF bit (0x04) in the frame type is set to indicate that there is an Offset field present. When set to 1, the Offset field is present. When set to 0, the Offset field is absent and the Stream Data starts at an offset of 0 (that is, the frame contains the first bytes of the stream, or the end of a stream that includes no data).
The LEN bit (0x02) in the frame type is set to indicate that there is a Length field present. If this bit is set to 0, the Length field is absent and the Stream Data field extends to the end of the packet. If this bit is set to 1, the Length field is present.
The FIN bit (0x01) indicates that the frame marks the end of the stream. The final size of the stream is the sum of the offset and the length of this frame.

An endpoint MUST terminate the connection with error STREAM_STATE_ERROR if it receives a STREAM frame for a locally initiated stream that has not yet been created, or for a send-only stream.
STREAM frames are formatted as shown in Figure 32.

STREAM Frame {
  Type (i) = 0x08..0x0f,
  Stream ID (i),
  [Offset (i)],
  [Length (i)],
  Stream Data (..),
}

Figure 32: STREAM Frame Format

STREAM frames contain the following fields:

Stream ID:

    A variable-length integer indicating the stream ID of the stream; see Section 2.1.

Offset:

    A variable-length integer specifying the byte offset in the stream for the data in this STREAM frame. This field is present when the OFF bit is set to 1. When the Offset field is absent, the offset is 0.
Length:

    A variable-length integer specifying the length of the Stream Data field in this STREAM frame. This field is present when the LEN bit is set to 1. When the LEN bit is set to 0, the Stream Data field consumes all the remaining bytes in the packet.
Stream Data:

    The bytes from the designated stream to be delivered.

When a Stream Data field has a length of 0, the offset in the STREAM frame is the offset of the next byte that would be sent.
The first byte in the stream has an offset of 0. The largest offset delivered on a stream -- the sum of the offset and data length -- cannot exceed 262-1, as it is not possible to provide flow control credit for that data. Receipt of a frame that exceeds this limit MUST be treated as a connection error of type FRAME_ENCODING_ERROR or FLOW_CONTROL_ERROR.
```
This component need a serialization and deserialization function in C++ to be able to be sent on the wire.

Another component less explicit is the application. It is defined in various place in the RFC. This component is about transfers of authenticated, secure, reliable ordered streams between clients and servers. It manage data send in each connection. Connection are also defined in the RFC with connection ID.

### Step 3: Create the protocol's Ivy files

#### Description of the step


For each identified component, create an Ivy file that defines and implement the component.
The component should contains the requirements and invariants defined in the RFCs and other documents.

#### Example: QUIC

- the different QUIC packets. They are defined in src/Protocols-Ivy/protocol-testing/quic/quic_stack/quic_packet[_<subtype>].ivy. For the Initial packet, we have the following:
```ivy
#lang ivy1.7

# include collections
# include order
include quic_types
include quic_transport_error_code
include quic_frame
include quic_transport_parameters
include ip
include quic_fsm_sending
include quic_fsm_receiving

# The packet protocol
#
# The packet protocol has several funcitons including establishing
# connections and loss detection. Packets carry frames whihc implement
# many other funcition of QUIC.
#
# QUIC Packets
# ------------

# This section defines the QUIC packet datatype. Packets are the basic
# unit of communication between endpoints. A packet may be encoded in
# either the long or the short format. There are packet types:
# `initial`, `handshake`, `zero_rtt` and `one_rtt`. The `zero_rtt`
# type is encoded in the short format, while others are encoded in the
# long format.  Packets have associated source cid (long format only)
# and destination cid, protocol version (long format only), and a
# packet sequence number. An initial packet also has a *retry token*, which
# is a (possibly empty) sequence of bytes.  The *payload* of the
# packet consists of a sequence of *frames* (see frame.ivy).

# TODO: retry and one_rtt packet types

# ### Packet

# The type `quic_packet` represents packet. 

# The fields are:
#
# - *ptype*: the packet type [2]
# - *pversion*: the protocol version, if long format, else 0 [3]
# - *dst_cid*: the destination cid [4]
# - *src_cid*: the source cid, if long format, else 0  [5]
# - *token*: the retry token (see section 4.4.1)  [6]
# - *seq_num*: the packet sequence number  [7]
# - *payload*: the payload, a sequence of frames  [8]

object quic_packet = {
    # type this 
    # instance idx : unbounded_sequence
    # instance arr : array(idx,this)

    # object quic_packet_initial = {
    #     variant this of quic_packet = struct {
    #         ptype : quic_packet_type, # [2]
    #         dst_cid : cid, # [4]
    #         src_cid : cid, # [5]
    #         seq_num : pkt_num, # [7]
    #         payload : frame.arr # [8]
    #     }
    # }

    # object quic_packet_handshake = {
    #     variant this of quic_packet = struct {
    #         ptype : quic_packet_type, # [2]
    #         dst_cid : cid, # [4]
    #         src_cid : cid, # [5]
    #         seq_num : pkt_num, # [7]
    #         payload : frame.arr # [8]
    #     }
    # }

    # object quic_packet_one_rtt = {
    #     variant this of quic_packet = struct {
    #         ptype : quic_packet_type, # [2]
    #         dst_cid : cid, # [4]
    #         src_cid : cid, # [5]
    #         seq_num : pkt_num, # [7]
    #         payload : frame.arr # [8]
    #     }
    # }

    # object quic_packet_zero_rtt = {
    #     variant this of quic_packet = struct {
    #         ptype : quic_packet_type, # [2]
    #         dst_cid : cid, # [4]
    #         src_cid : cid, # [5]
    #         seq_num : pkt_num, # [7]
    #         payload : frame.arr # [8]
    #     }
    # }

    type this = struct {
        ptype : quic_packet_type, # [2]
        pversion : version, # [3]
        dst_cid : cid, # [4]
        src_cid : cid, # [5]
        token : stream_data, # [6]
        seq_num : pkt_num, # [7]
        payload : frame.arr # [8]
    }

    #Hamid
    #instance retired_cids : array(idx, cid_seq)
    #Hamid

    instance idx : unbounded_sequence
    instance arr : array(idx,this) 
}


object quic_packet = { 
    ... 
    action long(pkt:this) returns(res:bool) = {
        res := pkt.ptype ~= quic_packet_type.one_rtt;
    }
}

# Note: Short header are considered to have scid of 0 so it is quite important to use this value

# Packet protocol events
# -----------------------

# The packet event
# ================
#
# This event corresponds to transmission of a QUIC packet.
#
# Parameters
# ----------
#
# - `src`: the source endpoint
# - `dst`: the destination endpoint
# - `pkt` : the packet contents
action packet_event(src:ip.endpoint,dst:ip.endpoint,pkt:quic_packet) = {}

action send_ack_eliciting_handshake_packet(src:ip.endpoint,dst:ip.endpoint,pkt:quic_packet) = {}

action send_ack_eliciting_initial_packet(src:ip.endpoint,dst:ip.endpoint,pkt:quic_packet) = {}

action send_ack_eliciting_application_packet(src:ip.endpoint,dst:ip.endpoint,pkt:quic_packet) = {}


#action packet_event_multiple_src(src1:ip.endpoint,src2:ip.endpoint,dst:ip.endpoint,pkt:quic_packet) = {}

# Packet protocol state
# ---------------------

# This section defines the history variables that track the state of
# the packet protocol. Some of these variables are shared between
# protocol layers, so that the allowed interleavings of events at
# different layers can be specified.
#

# Packet protocol state
# ---------------------

# - For each cid C, `conn_seen(C)` is true if a packet with
#   source cid C has been transmitted.
#
# - For each aid C, `conn_closed(C)` is true if C is in the closed state.
#
# - For each aid C, `conn_draining(C)` is true if C is in the draining state.
#
# - For each aid C, `draining_pkt_sent(C)` is true if the single
#   packet allowed to be sent in transition to the draining state has been sent.
#   This one packet must contain a connection_close frame with error code 0.
#   TODO: we don't check the error code.
#
# - For each endpoint aid C, last_pkt_num(C,L) represents the
#   number of the latest packet sent by C in encryption level L.
#
# - For each aid C, sent_pkt(C,L,N) is true if
#   a packet numbered N has been sent by C in encryption level L.
#
# - For each aid C, acked_pkt(C,L,N) is true if
#   a packet numbered N sent by C in encryption level L has been
#   acknowledged. 
#
# - For each aid C, max_acked(C,L) is the greatest
#   packet number N such that acked_pkt(C,L,N), or zero if
#   forall N. ~acked(C,L,N).
#
# - For each aid C, ack_credit(E,C) is the number
#   of non-ack-only packets sent to C, less the number of
#   ack-only packets sent from C.
#
# - For each aid C, `trans_params_set(C)`
#   is true if C has declared transport parameters.
#
# - For each aid C, function `trans_params(C)`
#   gives the transport parameters declared by C.
#
# - The predicate `connected(C)` indicates that the peer of
#   aid `C` has been determined.  This occurs conceptually when a
#   server produces a server hello frame.
#
# - The function `connected_to(C)` maps the aid `C` to its peer, if
#   the peer has been determined.
#
# - The function `nonce_cid(C)` maps the client aid `C` to the nonce
#   cid it has chosen for its initial packet.
#
# - The predicate `is_client(C)` indicates that aid 'C' is taking
#   the client role.
#
# - The predicate `conn_requested(S,D,C)` indicates that a client
#   and endpoint S has requested to open a connection with a server
#   at endpoint D, using cid C. 
#
# - The function `hi_non_probing(C)` indicates the highest packet number
#   of a non-probing packet sent by aid `C`. 
# 
# - The relation `hi_non_probing_endpoint(C,E)` that the highest-numbered
#   non-probing packet of aid `C` was at some time sent from endpopint `E`.
#
# - The relation `pkt_has_close(C,L,N)` is true if packet number `N` sent 
#   by aid `C` contained a CONNECTION_CLOSE frame.
#
# - The relation cid_mapped(C) is true when connection ID C has been provided as new connection ID for a connection
#   and becomes false when the C is retired
#
# - If cid_mapped(C) is true, then the function cid_to_aid(C) gives the aid for which C is a new connection ID
#
# - If aid D created a new connection ID with sequence number S, then seqnum_to_cid(D, S) yield the new connection id.

relation conn_seen(C:cid)
relation conn_closed(C:cid)
relation conn_draining(C:cid)
relation draining_pkt_sent(C:cid)
function last_pkt_num(C:cid,L:quic_packet_type) : pkt_num
relation sent_pkt(C:cid,L:quic_packet_type,N:pkt_num)
relation acked_pkt(C:cid,L:quic_packet_type,N:pkt_num)
function max_acked(C:cid,L:quic_packet_type) : pkt_num
function ack_credit(C:cid) : pkt_num
relation trans_params_set(C:cid)
function trans_params(C:cid) : trans_params_struct
relation connected(C:cid)
function cid_to_aid(C:cid) : cid 
relation cid_mapped(C:cid)

#chris
function cid_to_token(C:cid) : stream_data 
function initial_token : stream_data 
relation cid_mapped_token(C:cid)
#chris

function seqnum_to_cid (D : cid,S : cid_seq) : cid
#Hamid
function max_seq_num(C:cid) : cid_seq
#Hamid
function connected_to(C:cid) : cid
function nonce_cid(C:cid) : cid
relation is_client(C:cid)
relation conn_requested(S:ip.endpoint,D:ip.endpoint,C:cid)
relation issued_zero_length_cid #(S:ip.endpoint,D:ip.endpoint) TODO pass that to handle function of frames
function hi_non_probing(C:cid) : pkt_num
relation hi_non_probing_endpoint(C:cid,E:ip.endpoint)
relation pkt_has_close(C:cid,L:quic_packet_type,N:pkt_num)
#chris
# We start with the initial cid
function num_conn(C:cid) : stream_pos
relation tls_handshake_finished
relation migration_done

relation first_initial_send
function initial_scid : cid 
function initial_dcid : cid 


relation is_lost(C:cid,L:quic_packet_type,N:pkt_num)
function is_retransmitted(P:frame.arr) : pkt_num

#function cid_ip_mapped(D:ip.endpoint) :cid
#relation cid_ip_mapped(D:ip.endpoint)
#chris

function dst_endpoint : ip.endpoint


relation address_validated

relation path_validated
function path_validated_pkt_num: pkt_num

function anti_amplification_limit : stream_pos

relation is_not_sleeping


# Initial state
# -------------

# The history variables are initialized as follows.  Initially, no
# connections have been seen and no packets have been sent or
# acknowledged.

after init {
    conn_seen(C) := false;
    last_pkt_num(C,L) := 0;
    conn_closed(C) := false;
    conn_draining(C) := false;
    draining_pkt_sent(C) := false;
    sent_pkt(C,L,N) := false;
    acked_pkt(C,L,N) := false;
    pkt_has_close(C,L,N) := false;
    max_acked(C,L) := 0;
    ack_credit(C) := 0;
    trans_params_set(C:cid) := false;
    is_client(C) := false;
    conn_requested(S,D,C) := false;
    hi_non_probing(C) := 0;
    hi_non_probing_endpoint(C,E) := false;
    cid_mapped(C) := false;
    #Hamid
    max_seq_num(C) := 0;
    #Hamid
    #chris
    num_conn(C) := 1; 
    migration_done := false;
    tls_handshake_finished := false;
    first_initial_send := false;
    issued_zero_length_cid := false;
    is_retransmitted(P) := 0;
    is_not_sleeping := true;
    #chris
}

# Packet event specification
# --------------------------

# A packet event represents the transmision of a QUIC packet `pkt`
# from source endpoint `src` to a QUIC destination endpoint `dst`
# containing a sequence of queued frames.
#
# ### Requirements
#
# - The packet payload may not be empty [7].
#
# - A sender may not re-use a packet number on a given connection [4].
#
# - A packet containing only ack frames and padding is *ack-only*.
#   For a given cid, the number of ack-only packets sent from src to dst
#   must not be greater than the number of non-ack-only packets sent
#   from dst to src [5].
#
# - For a given connection, a server must only send packets to an
#   address that at one time in the past sent the as packet with
#   the highest packet numer thus far received. See notes below on
#   migration and path challenge. [10]

#   - Token Length:  A variable-length integer specifying the length of the
#      Token field, in bytes.  This value is zero if no token is present.
#      Initial packets sent by the server MUST set the Token Length field
#      to zero; clients that receive an Initial packet with a non-zero
#      Token Length field MUST either discard the packet or generate a
#      connection error of type PROTOCOL_VIOLATION. [11]

# Upon receiving the client's Initial packet, the server can request address validation 
# by sending a Retry packet (Section 17.2.5) containing a token. This token MUST be 
# repeated by the client in all Initial packets it sends for that connection after it 
# receives the Retry packet.

# ### Effects
#
# - The `conn_seen` and `sent_pkt` relations are updated to reflect
#   the observed packet [1].
# - The `last_pkt_num` function is updated to indicate the observed
#   packets as most recent for the packet's source and cid.
#   
#
# ### Notes
#
# - In the low-level packet encoding, the packet number may be encoded using
#   a small number of bytes, in a way that loses information.
#   At this layer of the protocol, however, the packets contain the original full
#   packet number.
#
# - On seeing a packet form a new address with the highest packect
#   number see thus far, the server detects migration of the
#   client. It begins sending packets to this address and initiates
#   path validation for this address. Until path validation succeeds,
#   the server limits data sent to the new address. Currently we
#   cannot specify this limit because we don't know the byte size of
#   packets or the timings of packets. 

#   An endpoint MUST treat the following as a connection error of type
#   TRANSPORT_PARAMETER_ERROR or PROTOCOL_VIOLATION:
#   *  absence of the retry_source_connection_id transport parameter from
#      the server after receiving a Retry packet, [1]
#   *  presence of the retry_source_connection_id transport parameter
#      when no Retry packet was received, or [3]
#   *  a mismatch between values received from a peer in these transport
#      parameters and the value sent in the corresponding Destination or
#      Source Connection ID fields of Initial packets. [2]
#   If a zero-length connection ID is selected, the corresponding
#   transport parameter is included with a zero-length value.

import action show_is_sleep_fake_timeon_dataout(is_sleep_fake_timeout:bool)
import action show_queued_frames(scid:cid,queued_frames:frame.arr)
import action show_current_time(t:milliseconds)

around packet_event(src:ip.endpoint,dst:ip.endpoint,pkt:quic_packet) {
    # is_not_sleeping := time_api.c_timer.is_sleep_fake_timeout;
    call show_current_time(time_api.c_timer.now_millis_last_bp);
    # call show_is_sleep_fake_timeout(is_not_sleeping);
    # require _generating -> is_not_sleeping;
    # require (_generating  -> is_not_sleeping);
    # require (~is_not_sleeping -> ~_generating);
    if _generating {
       # require ~is_not_sleeping;
    };
    if ~_generating {
        dst_endpoint := dst;
    } else {
        # var local_ack_delay := on_ack_sent(max_acked(dcid,e) ,e);
                # require local_ack_delay <= local_max_ack_delay_tp;
        
    }
   
    # if _generating  {
    #     require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
    # };
    require pkt.ptype ~= quic_packet_type.zero_rtt & pkt.ptype ~= quic_packet_type.version_negociation & pkt.ptype ~= quic_packet_type.retry;
    
    # Extract the source and destination cid's and packet number from the packet.

    var dcid := pkt.dst_cid;
    var scid := pkt.src_cid;

    call show_num_ack_eliciting_pkt(num_ack_eliciting_pkt);
    call show_num_ack_pkt(num_ack_pkt);

    # call show_num_ack_eliciting_pkt(num_ack_eliciting_pkt(scid));
    # call show_num_ack_pkt(num_ack_pkt(scid));
    
    if cid_mapped(dcid) {
	    dcid := cid_to_aid(dcid);
    };
    #require (~is_not_sleeping -> (num_queued_frames(scid) = 0)); # & ~_generating));
    idle_timeout(dcid) := time_api.c_timer.now_micros_last_bp;
    
    call show_current_idle_timeout(idle_timeout(dcid));
    call show_current_idle_timeout(idle_timeout(scid));

    is_retransmitted(pkt.payload) := is_retransmitted(pkt.payload) + 1;
    call show_is_retransmitted(seqnum_to_streampos(pkt.seq_num),is_retransmitted(pkt.payload));
    
    if max_idle_timeout_used > 0 {
        if idle_timeout(dcid) > max_idle_timeout_used  {
            call show_connection_timeout(idle_timeout(dcid), max_idle_timeout_used, pto_timeout*3);
            connection_timeout := true;
        }
    }


    # & idle_timeout > pto_timeout*3
    call show_probe_idle_timeout(pto_timeout*3);
    # To avoid excessively small idle timeout periods, endpoints MUST increase the idle timeout
    # period to be at least three times the current Probe Timeout (PTO). This allows for multiple 
    # PTOs to expire, and therefore multiple probes to be sent and lost, prior to idle timeout.
    if ~_generating & connection_timeout & is_retransmitted(pkt.payload) < 2 & idle_timeout(dcid) > pto_timeout*3 {
        respect_idle_timeout := false;
        call show_connection_timeout(idle_timeout(dcid), max_idle_timeout_used, pto_timeout*3);
        call respect_idle_timeout_none;
    }
    
    require pkt.token.end ~= 0 -> (retry_sent(client_initial_rcid) | retry_recv(scid) | pkt.token = tls_api.upper.get_old_new_token);

    if pkt.token.end ~= 0 { # 
        address_validated := true;
        anti_amplification_limit_reached := true;
    };

    if (src = client_alt | dst = client_alt) & nclients = 1 {
	    migration_done := true;
	    #call net.close(endpoint_id.client,sock);	# destroy connection ?
    };

    # Similarly, an endpoint MUST NOT reuse a connection ID when sending to
    # more than one destination address.  
    
    #if ~_generating  {
    #    if ~migration_done {
    #        cid_ip_mapped(dst) := pkt.dst_cid;
    #    } else {
    #        cid_ip_mapped(dst) := pkt.dst_cid;
    #    };
    #};

    # The destination cid must represent an existing connection,
    # except in the case of a client initial packet, when the
    # destination cid may be the nonce cid chosen by the client for
    # the given source cid. TODO: The standard says that on receiving
    # the the server's cid, the clint must switch to it. However, we
    # can't know when that server's cid has actually been received by
    # the client. As an example, after the server sends its first
    # initial packet, the client might still retransmit its initial
    # packet using the nonce cid. In some cases, we can infer that the
    # client has in fact seen the server's cid (for example, if it
    # packet contains an ACK frame, or a CRYPTO frame that is
    # reponsive to a server FRAME. This is trick to check, however,
    # and the actual servers do not seem to check it.

    require connected(dcid) |
        pkt.ptype = quic_packet_type.initial
        & is_client(scid)
        & dcid = nonce_cid(scid);
    

    # On long headers, both cids are given. If the destination cid is
    # connected, it must be connected to the source cid (otherwise it
    # must be a nonce generated by a client). 
    # On short headers (meaning one_rtt) the scid is not given, so we
    # use the recorded value.

    if pkt.long {
        require connected(dcid) -> connected_to(dcid) = scid;
    } else {
        scid := connected_to(dcid);
    };

    if retry_sent(dcid) & ~_generating & ~zero_length_token & pkt.ptype = quic_packet_type.initial {
        require dcid = client_initial_rcid;
    };

    # The packet type must match the encryption level of the queued
    # frames at the source. 

    require pkt.ptype = queued_level(scid);

   
    # TEMPORARY: prevent big packet number jumps (work around minquic bug)
    # Removed for MVFST that start with big PKT_NUM -> OK now
    if  _generating {
        # if ~is_client(scid) {
        #     #client
        #     require pkt.seq_num > last_pkt_num(scid,pkt.ptype);
        #     require pkt.seq_num <= last_pkt_num(scid,pkt.ptype) + 0x15;
        # } else {
        #server
        require pkt.seq_num = last_pkt_num(scid,pkt.ptype) + 0x1; # OK
        # };
        #require pkt.seq_num < last_pkt_num(scid,pkt.ptype) + 0x1 & pkt.seq_num > last_pkt_num(scid,pkt.ptype);
    };
    # else {
    #     # An endpoint generates an RTT sample on receiving an ACK frame that meets the following two conditions:
    #     # 1. the largest acknowledged packet number is newly acknowledged, and
    #     # 2. at least one of the newly acknowledged packets was ack-eliciting.

    #     if queued_ack_eliciting(scid) {

    #     }
    # };
    last_pkt_num(scid,pkt.ptype) := pkt.seq_num;
    require ~sent_pkt(scid,pkt.ptype,pkt.seq_num);  # [4]
    sent_pkt(scid,pkt.ptype,pkt.seq_num) := true;  # [1]

    # The payload may not be empty
    require num_queued_frames(scid) > 0; # [7]


    # The payload must exactly match the queued frames.
    if _generating {
        if packets_to_retransmit_end(pkt.ptype) > 0 {
            var paylo := packets_to_retransmit(pkt.ptype,packets_to_retransmit_end(pkt.ptype));# TODO change and put that at frame level
            require pkt.payload = paylo;
            packets_to_retransmit_end(pkt.ptype) := packets_to_retransmit_end(pkt.ptype) - 1;
            call show_retransmit_lost_packet(paylo);
        } 
        else {
            require pkt.payload = queued_frames(scid);
        };
    } 
    else {
        call show_queued_frames(scid,queued_frames(scid));
        call is_generating(_generating);
        call show_pkt_num(pkt.seq_num);
        require pkt.payload = queued_frames(scid);
    };
    

    # TEMPORARY: don't allow client migration during handshake

    require conn_seen(scid) & pkt.long & is_client(scid) -> conn_requested(src,dst,scid);

    # Packet must be sent to the endpoint from which the highest numbered
    # packet has been received. ~queued_challenge(dcid) & 
    #call show_probing(dcid ,hi_non_probing(dcid));
    require  conn_seen(dcid) -> hi_non_probing_endpoint(dcid,dst);  # [10]

    # TEMPORARY: do not apply ack-only rule to generated packets
    # This can be removed when we have a frame queue per encryption level

    call show_ack_credit(scid, ack_credit(scid), queued_ack_eliciting(scid), queued_non_ack(scid), pkt.seq_num);
    require ~_generating & ~queued_non_ack(scid) -> ack_credit(scid) > 0;  # [5]

    #Hamid - This is wrong, because if there is no ack credits, it prevents from sending a packet 
    #        containing only a CONNECTION_CLOSE frame but we want to stop packets that contain only ACKs 
    #    require ~_generating & ~queued_ack_eliciting(scid) -> ack_credit(scid) > 0;
    #Hamid

    # QUESTION: THis sentence is from draft-18 section 13.1: "An
    #   endpoint MUST NOT send a packet containing only an ACK frame
    #   in response to a packet containing only ACK or PADDING frames,
    #   even if there are packet gaps which precede the received
    #   packet." Do we interpret this to mean that an ack-only packet
    #   cannot ack *only* ack-only packets?  Or that an ack-only
    #   packet cannot ack *any* ack-only packets?
    
    # If the sender is in the draining state, this is the draining packet.
    # Make sure that a draining packet has not previously been sent and
    # that the packet contains a connection_close frame;

    if conn_draining(scid) {
        require ~draining_pkt_sent(scid) & queued_close(scid);
    };

    ...

    # Here, we have the updates to the packet protocol state.

    # TEMPORARY: The following are repeated because currently locals defined in
    # the "before" section cannot be accessed in the "after" section.

    var dcid := pkt.dst_cid;
    var scid := pkt.src_cid if pkt.long else connected_to(dcid);

    if cid_mapped(dcid) {
	    dcid := cid_to_aid(dcid);
    };
    

    # TODO: the following should not be here

    if pkt.ptype = quic_packet_type.initial {
        initial_token := pkt.token;
        # An initial packet with an unseen destination cid is a connection request.
        if ~conn_seen(dcid)  {
            if ~zero_rtt_sent {
                call show_initial_request_initial;
                call tls_client_initial_request(src,dst,dcid,pkt.pversion,src_tls_id(src));
            };
            conn_requested(src,dst,scid) := true;
        };
        cid_to_token(dcid) := pkt.token;
    };

    conn_seen(scid) := true;  # [1]

    # Update the ack credits. A non-ack packet sent to a destination
    # increases the destination's ack credit. An ack packet decreases
    # the sender's ack credit.

#Hamid

#    if queued_non_ack(scid) {
#	ack_credit(dcid) := ack_credit(dcid) + 1;
#    } else {
#	ack_credit(scid) := ack_credit(scid) - 1;
#    };

    if queued_ack_eliciting(scid) {
        if _generating {
            num_ack_eliciting_pkt := num_ack_eliciting_pkt + 1;
        }
        ack_eliciting_threshold_current_val(dcid) := ack_eliciting_threshold_current_val(dcid) + 1;
        ack_credit(dcid) := ack_credit(dcid) + 1;
    } else {
        if ~_generating {
            num_ack_pkt:= num_ack_pkt + 1;
        }
    };
    if ~queued_non_ack(scid) {
       ack_credit(scid) := ack_credit(scid) - 1;
    };

#Hamid

    # If this is a non-probing packet, update the highest non-probing
    # packet number seen on from this aid.
    # QUESTION: what if two different paths send the same packet number?
    # QUESTION: how do you compare packet numbers with different encryption levels?

    if queued_non_probing(scid) {
        if pkt.ptype = quic_packet_type.one_rtt {
            if pkt.seq_num >= hi_non_probing(scid) {
                hi_non_probing(scid) := pkt.seq_num;
                hi_non_probing_endpoint(scid,src) := true;
            }
        } else {
            hi_non_probing_endpoint(scid,src) := true;
        }
    };

    # If the packet contains a close frame, then set `pkt_has_close`

    if queued_close(scid) {
        pkt_has_close(scid,pkt.ptype,pkt.seq_num) := true;
    };

    # If the sender is in the draining state, this is the draining packet.

    if conn_draining(scid) {
        draining_pkt_sent(scid) := true
    };

    if pkt.ptype = quic_packet_type.initial & ~first_initial_send & zero_rtt_allowed {
        first_initial_send := true;
        initial_scid := scid;
        initial_dcid := dcid;
        queued_level(the_cid) := quic_packet_type.zero_rtt; # todo multiple client
    } else {
        first_initial_send := false;
    };

    # The queued frames are deleted
    
    queued_frames(scid) := frame.arr.empty;
    queued_non_probing(scid) := false;
    queued_non_ack(scid) := false;
    queued_close(scid) := false;
    num_queued_frames(scid) := 0;
#Hamid
    queued_ack_eliciting(scid) := false;
#Hamid
}

import action show_retransmit_lost_packet(paylo:frame.arr) 

import action show_connection_timeout(idle_timeout:microseconds, max_idle_timeout_used:microseconds, pto_timeout:microseconds)

around send_ack_eliciting_handshake_packet(src:ip.endpoint,dst:ip.endpoint,pkt:quic_packet) {
    # is_not_sleeping := time_api.c_timer.is_sleep_fake_timeout;
    # require _generating -> is_not_sleeping;
    # require (_generating  -> is_not_sleeping);
    # require (~is_not_sleeping -> ~_generating);
    require pkt.ptype = quic_packet_type.handshake;
    require need_sent_ack_eliciting_handshake_packet;

   
    
    # Extract the source and destination cid's and packet number from the packet.

    var dcid := pkt.dst_cid;
    var scid := pkt.src_cid;
    if cid_mapped(dcid) {
	    dcid := cid_to_aid(dcid);
    };

    require pkt.ptype = queued_level(scid);
    
    require pkt.token.end ~= 0 -> (retry_sent(client_initial_rcid) | retry_recv(scid) | pkt.token = tls_api.upper.get_old_new_token);

    if (src = client_alt | dst = client_alt) & nclients = 1 {
	    migration_done := true;
    };

    # Similarly, an endpoint MUST NOT reuse a connection ID when sending to
    # more than one destination address.  

    # The destination cid must represent an existing connection,
    # except in the case of a client initial packet, when the
    # destination cid may be the nonce cid chosen by the client for
    # the given source cid. TODO: The standard says that on receiving
    # the the server's cid, the clint must switch to it. However, we
    # can't know when that server's cid has actually been received by
    # the client. As an example, after the server sends its first
    # initial packet, the client might still retransmit its initial
    # packet using the nonce cid. In some cases, we can infer that the
    # client has in fact seen the server's cid (for example, if it
    # packet contains an ACK frame, or a CRYPTO frame that is
    # reponsive to a server FRAME. This is trick to check, however,
    # and the actual servers do not seem to check it.

    require connected(dcid) |
        pkt.ptype = quic_packet_type.initial
        & is_client(scid)
        & dcid = nonce_cid(scid);
    

    # On long headers, both cids are given. If the destination cid is
    # connected, it must be connected to the source cid (otherwise it
    # must be a nonce generated by a client). 
    # On short headers (meaning one_rtt) the scid is not given, so we
    # use the recorded value.

    if pkt.long {
        require connected(dcid) -> connected_to(dcid) = scid;
    } else {
        scid := connected_to(dcid);
    };

    if retry_sent(dcid) & ~_generating & ~zero_length_token & pkt.ptype = quic_packet_type.initial {
        require dcid = client_initial_rcid;
    };

    # TEMPORARY: prevent big packet number jumps (work around minquic bug)
    # Removed for MVFST that start with big PKT_NUM -> OK now
    if  _generating {
        # if ~is_client(scid) {
        #     #client
        #     require pkt.seq_num > last_pkt_num(scid,pkt.ptype);
        #     require pkt.seq_num <= last_pkt_num(scid,pkt.ptype) + 0x15;
        # } else {
        #server
        require pkt.seq_num = last_pkt_num(scid,pkt.ptype) + 0x1; # OK
        # };
        #require pkt.seq_num < last_pkt_num(scid,pkt.ptype) + 0x1 & pkt.seq_num > last_pkt_num(scid,pkt.ptype);
    };
    # else {
    #     # An endpoint generates an RTT sample on receiving an ACK frame that meets the following two conditions:
    #     # 1. the largest acknowledged packet number is newly acknowledged, and
    #     # 2. at least one of the newly acknowledged packets was ack-eliciting.

    #     if queued_ack_eliciting(scid) {

    #     }
    # };
    last_pkt_num(scid,pkt.ptype) := pkt.seq_num;
    require ~sent_pkt(scid,pkt.ptype,pkt.seq_num);  # [4]
    sent_pkt(scid,pkt.ptype,pkt.seq_num) := true;  # [1]

    # The payload may not be empty

    require num_queued_frames(scid) > 0;  # [7]

    # The payload must exactly match the queued frames.

    require pkt.payload = queued_frames(scid);

    # TEMPORARY: don't allow client migration during handshake

    require conn_seen(scid) & pkt.long & is_client(scid) -> conn_requested(src,dst,scid);

    # Packet must be sent to the endpoint from which the highest numbered
    # packet has been received. ~queued_challenge(dcid) & 
    #call show_probing(dcid ,hi_non_probing(dcid));
    require  conn_seen(dcid) -> hi_non_probing_endpoint(dcid,dst);  # [10]

    # TEMPORARY: do not apply ack-only rule to generated packets
    # This can be removed when we have a frame queue per encryption level

    #call show_ack_credit(scid, ack_credit(scid), queued_ack_eliciting(scid), queued_non_ack(scid), pkt.seq_num);
    require ~_generating & ~queued_non_ack(scid) -> ack_credit(scid) > 0;  # [5]

    #Hamid - This is wrong, because if there is no ack credits, it prevents from sending a packet 
    #        containing only a CONNECTION_CLOSE frame but we want to stop packets that contain only ACKs 
    #    require ~_generating & ~queued_ack_eliciting(scid) -> ack_credit(scid) > 0;
    #Hamid

    # QUESTION: THis sentence is from draft-18 section 13.1: "An
    #   endpoint MUST NOT send a packet containing only an ACK frame
    #   in response to a packet containing only ACK or PADDING frames,
    #   even if there are packet gaps which precede the received
    #   packet." Do we interpret this to mean that an ack-only packet
    #   cannot ack *only* ack-only packets?  Or that an ack-only
    #   packet cannot ack *any* ack-only packets?
    
    # If the sender is in the draining state, this is the draining packet.
    # Make sure that a draining packet has not previously been sent and
    # that the packet contains a connection_close frame;

    if conn_draining(scid) {
        require ~draining_pkt_sent(scid) & queued_close(scid);
    };

    ...

    # Here, we have the updates to the packet protocol state.

    # TEMPORARY: The following are repeated because currently locals defined in
    # the "before" section cannot be accessed in the "after" section.

    var dcid := pkt.dst_cid;
    var scid := pkt.src_cid if pkt.long else connected_to(dcid);

    if cid_mapped(dcid) {
	    dcid := cid_to_aid(dcid);
    };
    
    # if is

    # TODO: the following should not be here

    if pkt.ptype = quic_packet_type.initial {
        initial_token := pkt.token;
        # An initial packet with an unseen destination cid is a connection request.
        if ~conn_seen(dcid)  {
            if ~zero_rtt_sent {
                call show_initial_request_initial;
                call tls_client_initial_request(src,dst,dcid,pkt.pversion,src_tls_id(src));
            };
            conn_requested(src,dst,scid) := true;
        };
        cid_to_token(dcid) := pkt.token;
    };

    conn_seen(scid) := true;  # [1]

    # Update the ack credits. A non-ack packet sent to a destination
    # increases the destination's ack credit. An ack packet decreases
    # the sender's ack credit.

#Hamid

#    if queued_non_ack(scid) {
#	ack_credit(dcid) := ack_credit(dcid) + 1;
#    } else {
#	ack_credit(scid) := ack_credit(scid) - 1;
#    };

    if queued_ack_eliciting(scid) {
       ack_credit(dcid) := ack_credit(dcid) + 1;
    };
    if ~queued_non_ack(scid) {
       ack_credit(scid) := ack_credit(scid) - 1;
    };

#Hamid

    # If this is a non-probing packet, update the highest non-probing
    # packet number seen on from this aid.
    # QUESTION: what if two different paths send the same packet number?
    # QUESTION: how do you compare packet numbers with different encryption levels?

    if queued_non_probing(scid) {
        if pkt.ptype = quic_packet_type.one_rtt {
            if pkt.seq_num >= hi_non_probing(scid) {
                hi_non_probing(scid) := pkt.seq_num;
                hi_non_probing_endpoint(scid,src) := true;
            }
        } else {
            hi_non_probing_endpoint(scid,src) := true;
        }
    };

    # If the packet contains a close frame, then set `pkt_has_close`

    if queued_close(scid) {
        pkt_has_close(scid,pkt.ptype,pkt.seq_num) := true;
    };

    # If the sender is in the draining state, this is the draining packet.

    if conn_draining(scid) {
        draining_pkt_sent(scid) := true
    };

    if pkt.ptype = quic_packet_type.initial & ~first_initial_send & zero_rtt_allowed {
        first_initial_send := true;
        initial_scid := scid;
        initial_dcid := dcid;
        queued_level(the_cid) := quic_packet_type.zero_rtt; # todo multiple client
    } else {
        first_initial_send := false;
    };

    # The queued frames are deleted
    
    queued_frames(scid) := frame.arr.empty;
    queued_non_probing(scid) := false;
    queued_non_ack(scid) := false;
    queued_close(scid) := false;
    num_queued_frames(scid) := 0;
#Hamid
    queued_ack_eliciting(scid) := false;
#Hamid
    need_sent_ack_eliciting_handshake_packet := false
}

around send_ack_eliciting_application_packet(src:ip.endpoint,dst:ip.endpoint,pkt:quic_packet) {
    # is_not_sleeping := time_api.c_timer.is_sleep_fake_timeout;
    # require _generating -> is_not_sleeping;
    # require (_generating  -> is_not_sleeping);
    # require (~is_not_sleeping -> ~_generating);
    if _generating {
        
    };
    require pkt.ptype = quic_packet_type.one_rtt;
    require need_sent_ack_eliciting_application_packet;
    
    # Extract the source and destination cid's and packet number from the packet.

    var dcid := pkt.dst_cid;
    var scid := pkt.src_cid;
    if cid_mapped(dcid) {
	    dcid := cid_to_aid(dcid);
    };

    require pkt.ptype = queued_level(scid);
    
    #require pkt.token.end ~= 0 -> (retry_sent(client_initial_rcid) | retry_recv(scid) | pkt.token = tls_api.upper.get_old_new_token);
    require pkt.token.end = 0;
    if (src = client_alt | dst = client_alt) & nclients = 1 {
	    migration_done := true;
    };

    # Similarly, an endpoint MUST NOT reuse a connection ID when sending to
    # more than one destination address.  

    # The destination cid must represent an existing connection,
    # except in the case of a client initial packet, when the
    # destination cid may be the nonce cid chosen by the client for
    # the given source cid. TODO: The standard says that on receiving
    # the the server's cid, the clint must switch to it. However, we
    # can't know when that server's cid has actually been received by
    # the client. As an example, after the server sends its first
    # initial packet, the client might still retransmit its initial
    # packet using the nonce cid. In some cases, we can infer that the
    # client has in fact seen the server's cid (for example, if it
    # packet contains an ACK frame, or a CRYPTO frame that is
    # reponsive to a server FRAME. This is trick to check, however,
    # and the actual servers do not seem to check it.

    require connected(dcid) |
        pkt.ptype = quic_packet_type.initial
        & is_client(scid)
        & dcid = nonce_cid(scid);
    

    # On long headers, both cids are given. If the destination cid is
    # connected, it must be connected to the source cid (otherwise it
    # must be a nonce generated by a client). 
    # On short headers (meaning one_rtt) the scid is not given, so we
    # use the recorded value.

    if pkt.long {
        require connected(dcid) -> connected_to(dcid) = scid;
    } else {
        scid := connected_to(dcid);
    };

    if retry_sent(dcid) & ~_generating & ~zero_length_token & pkt.ptype = quic_packet_type.initial {
        require dcid = client_initial_rcid;
    };

    # TEMPORARY: prevent big packet number jumps (work around minquic bug)
    # Removed for MVFST that start with big PKT_NUM -> OK now
    if  _generating {
        # if ~is_client(scid) {
        #     #client
        #     require pkt.seq_num > last_pkt_num(scid,pkt.ptype);
        #     require pkt.seq_num <= last_pkt_num(scid,pkt.ptype) + 0x15;
        # } else {
        #server
        require pkt.seq_num = last_pkt_num(scid,pkt.ptype) + 0x1; # OK
        # };
        #require pkt.seq_num < last_pkt_num(scid,pkt.ptype) + 0x1 & pkt.seq_num > last_pkt_num(scid,pkt.ptype);
    };
    # else {
    #     # An endpoint generates an RTT sample on receiving an ACK frame that meets the following two conditions:
    #     # 1. the largest acknowledged packet number is newly acknowledged, and
    #     # 2. at least one of the newly acknowledged packets was ack-eliciting.

    #     if queued_ack_eliciting(scid) {

    #     }
    # };
    last_pkt_num(scid,pkt.ptype) := pkt.seq_num;
    require ~sent_pkt(scid,pkt.ptype,pkt.seq_num);  # [4]
    sent_pkt(scid,pkt.ptype,pkt.seq_num) := true;  # [1]

    # The payload may not be empty

    require num_queued_frames(scid) > 0;  # [7]

    # The payload must exactly match the queued frames.

    require pkt.payload = queued_frames(scid);

    # TEMPORARY: don't allow client migration during handshake

    require conn_seen(scid) & pkt.long & is_client(scid) -> conn_requested(src,dst,scid);

    # Packet must be sent to the endpoint from which the highest numbered
    # packet has been received. ~queued_challenge(dcid) & 
    #call show_probing(dcid ,hi_non_probing(dcid));
    require  conn_seen(dcid) -> hi_non_probing_endpoint(dcid,dst);  # [10]

    # TEMPORARY: do not apply ack-only rule to generated packets
    # This can be removed when we have a frame queue per encryption level

    #call show_ack_credit(scid, ack_credit(scid), queued_ack_eliciting(scid), queued_non_ack(scid), pkt.seq_num);
    require ~_generating & ~queued_non_ack(scid) -> ack_credit(scid) > 0;  # [5]

    #Hamid - This is wrong, because if there is no ack credits, it prevents from sending a packet 
    #        containing only a CONNECTION_CLOSE frame but we want to stop packets that contain only ACKs 
    #    require ~_generating & ~queued_ack_eliciting(scid) -> ack_credit(scid) > 0;
    #Hamid

    # QUESTION: THis sentence is from draft-18 section 13.1: "An
    #   endpoint MUST NOT send a packet containing only an ACK frame
    #   in response to a packet containing only ACK or PADDING frames,
    #   even if there are packet gaps which precede the received
    #   packet." Do we interpret this to mean that an ack-only packet
    #   cannot ack *only* ack-only packets?  Or that an ack-only
    #   packet cannot ack *any* ack-only packets?
    
    # If the sender is in the draining state, this is the draining packet.
    # Make sure that a draining packet has not previously been sent and
    # that the packet contains a connection_close frame;

    if conn_draining(scid) {
        require ~draining_pkt_sent(scid) & queued_close(scid);
    };

    ...

    # Here, we have the updates to the packet protocol state.

    # TEMPORARY: The following are repeated because currently locals defined in
    # the "before" section cannot be accessed in the "after" section.

    var dcid := pkt.dst_cid;
    var scid := pkt.src_cid if pkt.long else connected_to(dcid);

    if cid_mapped(dcid) {
	    dcid := cid_to_aid(dcid);
    };
    
    # if is

    # TODO: the following should not be here

    if pkt.ptype = quic_packet_type.initial {
        initial_token := pkt.token;
        # An initial packet with an unseen destination cid is a connection request.
        if ~conn_seen(dcid)  {
            if ~zero_rtt_sent {
                call show_initial_request_initial;
                call tls_client_initial_request(src,dst,dcid,pkt.pversion,src_tls_id(src));
            };
            conn_requested(src,dst,scid) := true;
        };
        cid_to_token(dcid) := pkt.token;
    };

    conn_seen(scid) := true;  # [1]

    # Update the ack credits. A non-ack packet sent to a destination
    # increases the destination's ack credit. An ack packet decreases
    # the sender's ack credit.

#Hamid

#    if queued_non_ack(scid) {
#	ack_credit(dcid) := ack_credit(dcid) + 1;
#    } else {
#	ack_credit(scid) := ack_credit(scid) - 1;
#    };

    if queued_ack_eliciting(scid) {
        # num_ack_eliciting_pkt(scid) := num_ack_eliciting_pkt(scid) + 1;
        ack_credit(dcid) := ack_credit(dcid) + 1;
    } else {
        # num_ack_pkt(scid) := num_ack_pkt(scid) + 1;
    };
    if ~queued_non_ack(scid) {
       ack_credit(scid) := ack_credit(scid) - 1;
    };

#Hamid

    # If this is a non-probing packet, update the highest non-probing
    # packet number seen on from this aid.
    # QUESTION: what if two different paths send the same packet number?
    # QUESTION: how do you compare packet numbers with different encryption levels?

    if queued_non_probing(scid) {
        if pkt.ptype = quic_packet_type.one_rtt {
            if pkt.seq_num >= hi_non_probing(scid) {
                hi_non_probing(scid) := pkt.seq_num;
                hi_non_probing_endpoint(scid,src) := true;
            }
        } else {
            hi_non_probing_endpoint(scid,src) := true;
        }
    };

    # If the packet contains a close frame, then set `pkt_has_close`

    if queued_close(scid) {
        pkt_has_close(scid,pkt.ptype,pkt.seq_num) := true;
    };

    # If the sender is in the draining state, this is the draining packet.

    if conn_draining(scid) {
        draining_pkt_sent(scid) := true
    };

    if pkt.ptype = quic_packet_type.initial & ~first_initial_send & zero_rtt_allowed {
        first_initial_send := true;
        initial_scid := scid;
        initial_dcid := dcid;
        queued_level(the_cid) := quic_packet_type.zero_rtt; # todo multiple client
    } else {
        first_initial_send := false;
    };

    # The queued frames are deleted
    
    queued_frames(scid) := frame.arr.empty;
    queued_non_probing(scid) := false;
    queued_non_ack(scid) := false;
    queued_close(scid) := false;
    num_queued_frames(scid) := 0;
#Hamid
    queued_ack_eliciting(scid) := false;
#Hamid
    need_sent_ack_eliciting_application_packet := false
}


around send_ack_eliciting_initial_packet(src:ip.endpoint,dst:ip.endpoint,pkt:quic_packet) {
    # is_not_sleeping := time_api.c_timer.is_sleep_fake_timeout;
    # require _generating -> is_not_sleeping;
    #require (_generating  -> is_not_sleeping);
    # if _generating {
        
    # };
    # require (~is_not_sleeping -> ~_generating);
    require pkt.ptype = quic_packet_type.initial;

    require need_sent_ack_eliciting_initial_packet;
    # Extract the source and destination cid's and packet number from the packet.

    var dcid := pkt.dst_cid;
    var scid := pkt.src_cid;
    if cid_mapped(dcid) {
	    dcid := cid_to_aid(dcid);
    };


    require pkt.ptype = queued_level(scid);

    
    require pkt.token.end ~= 0 -> (retry_sent(client_initial_rcid) | retry_recv(scid) | pkt.token = tls_api.upper.get_old_new_token);

    if (src = client_alt | dst = client_alt) & nclients = 1 {
	    migration_done := true;
    };

    # Similarly, an endpoint MUST NOT reuse a connection ID when sending to
    # more than one destination address.  

    # The destination cid must represent an existing connection,
    # except in the case of a client initial packet, when the
    # destination cid may be the nonce cid chosen by the client for
    # the given source cid. TODO: The standard says that on receiving
    # the the server's cid, the clint must switch to it. However, we
    # can't know when that server's cid has actually been received by
    # the client. As an example, after the server sends its first
    # initial packet, the client might still retransmit its initial
    # packet using the nonce cid. In some cases, we can infer that the
    # client has in fact seen the server's cid (for example, if it
    # packet contains an ACK frame, or a CRYPTO frame that is
    # reponsive to a server FRAME. This is trick to check, however,
    # and the actual servers do not seem to check it.

    require connected(dcid) |
        pkt.ptype = quic_packet_type.initial
        & is_client(scid)
        & dcid = nonce_cid(scid);
    

    # On long headers, both cids are given. If the destination cid is
    # connected, it must be connected to the source cid (otherwise it
    # must be a nonce generated by a client). 
    # On short headers (meaning one_rtt) the scid is not given, so we
    # use the recorded value.

    if pkt.long {
        require connected(dcid) -> connected_to(dcid) = scid;
    } else {
        scid := connected_to(dcid);
    };

    if retry_sent(dcid) & ~_generating & ~zero_length_token & pkt.ptype = quic_packet_type.initial {
        require dcid = client_initial_rcid;
    };

    # TEMPORARY: prevent big packet number jumps (work around minquic bug)
    # Removed for MVFST that start with big PKT_NUM -> OK now
    # if  _generating {
        # if ~is_client(scid) {
        #     #client
        #     require pkt.seq_num > last_pkt_num(scid,pkt.ptype);
        #     require pkt.seq_num <= last_pkt_num(scid,pkt.ptype) + 0x15;
        # } else {
        #server
        require pkt.seq_num = last_pkt_num(scid,pkt.ptype) + 0x15; # OK
        # };
        #require pkt.seq_num < last_pkt_num(scid,pkt.ptype) + 0x1 & pkt.seq_num > last_pkt_num(scid,pkt.ptype);
    # };
    # else {
    #     # An endpoint generates an RTT sample on receiving an ACK frame that meets the following two conditions:
    #     # 1. the largest acknowledged packet number is newly acknowledged, and
    #     # 2. at least one of the newly acknowledged packets was ack-eliciting.

    #     if queued_ack_eliciting(scid) {

    #     }
    # };
    last_pkt_num(scid,pkt.ptype) := pkt.seq_num;
    require ~sent_pkt(scid,pkt.ptype,pkt.seq_num);  # [4]
    sent_pkt(scid,pkt.ptype,pkt.seq_num) := true;  # [1]

    # The payload may not be empty

    require num_queued_frames(scid) > 0;  # [7]

    # The payload must exactly match the queued frames.

    require pkt.payload = queued_frames(scid);

    # TEMPORARY: don't allow client migration during handshake

    require conn_seen(scid) & pkt.long & is_client(scid) -> conn_requested(src,dst,scid);

    # Packet must be sent to the endpoint from which the highest numbered
    # packet has been received. ~queued_challenge(dcid) & 
    #call show_probing(dcid ,hi_non_probing(dcid));
    require  conn_seen(dcid) -> hi_non_probing_endpoint(dcid,dst);  # [10]

    # TEMPORARY: do not apply ack-only rule to generated packets
    # This can be removed when we have a frame queue per encryption level

    #call show_ack_credit(scid, ack_credit(scid), queued_ack_eliciting(scid), queued_non_ack(scid), pkt.seq_num);
    require ~_generating & ~queued_non_ack(scid) -> ack_credit(scid) > 0;  # [5]

    #Hamid - This is wrong, because if there is no ack credits, it prevents from sending a packet 
    #        containing only a CONNECTION_CLOSE frame but we want to stop packets that contain only ACKs 
    #    require ~_generating & ~queued_ack_eliciting(scid) -> ack_credit(scid) > 0;
    #Hamid

    # QUESTION: THis sentence is from draft-18 section 13.1: "An
    #   endpoint MUST NOT send a packet containing only an ACK frame
    #   in response to a packet containing only ACK or PADDING frames,
    #   even if there are packet gaps which precede the received
    #   packet." Do we interpret this to mean that an ack-only packet
    #   cannot ack *only* ack-only packets?  Or that an ack-only
    #   packet cannot ack *any* ack-only packets?
    
    # If the sender is in the draining state, this is the draining packet.
    # Make sure that a draining packet has not previously been sent and
    # that the packet contains a connection_close frame;

    if conn_draining(scid) {
        require ~draining_pkt_sent(scid) & queued_close(scid);
    };

    ...

    # Here, we have the updates to the packet protocol state.

    # TEMPORARY: The following are repeated because currently locals defined in
    # the "before" section cannot be accessed in the "after" section.

    var dcid := pkt.dst_cid;
    var scid := pkt.src_cid if pkt.long else connected_to(dcid);

    if cid_mapped(dcid) {
	    dcid := cid_to_aid(dcid);
    };
    
    # if is

    # TODO: the following should not be here

    if pkt.ptype = quic_packet_type.initial {
        initial_token := pkt.token;
        # An initial packet with an unseen destination cid is a connection request.
        if ~conn_seen(dcid)  {
            if ~zero_rtt_sent {
                call show_initial_request_initial;
                call tls_client_initial_request(src,dst,dcid,pkt.pversion,src_tls_id(src));
            };
            conn_requested(src,dst,scid) := true;
        };
        cid_to_token(dcid) := pkt.token;
    };

    conn_seen(scid) := true;  # [1]

    # Update the ack credits. A non-ack packet sent to a destination
    # increases the destination's ack credit. An ack packet decreases
    # the sender's ack credit.

#Hamid

#    if queued_non_ack(scid) {
#	ack_credit(dcid) := ack_credit(dcid) + 1;
#    } else {
#	ack_credit(scid) := ack_credit(scid) - 1;
#    };

    if queued_ack_eliciting(scid) {
       ack_credit(dcid) := ack_credit(dcid) + 1;
    };
    if ~queued_non_ack(scid) {
       ack_credit(scid) := ack_credit(scid) - 1;
    };

#Hamid

    # If this is a non-probing packet, update the highest non-probing
    # packet number seen on from this aid.
    # QUESTION: what if two different paths send the same packet number?
    # QUESTION: how do you compare packet numbers with different encryption levels?

    if queued_non_probing(scid) {
        if pkt.ptype = quic_packet_type.one_rtt {
            if pkt.seq_num >= hi_non_probing(scid) {
                hi_non_probing(scid) := pkt.seq_num;
                hi_non_probing_endpoint(scid,src) := true;
            }
        } else {
            hi_non_probing_endpoint(scid,src) := true;
        }
    };

    # If the packet contains a close frame, then set `pkt_has_close`

    if queued_close(scid) {
        pkt_has_close(scid,pkt.ptype,pkt.seq_num) := true;
    };

    # If the sender is in the draining state, this is the draining packet.

    if conn_draining(scid) {
        draining_pkt_sent(scid) := true
    };

    if pkt.ptype = quic_packet_type.initial & ~first_initial_send & zero_rtt_allowed {
        first_initial_send := true;
        initial_scid := scid;
        initial_dcid := dcid;
        queued_level(the_cid) := quic_packet_type.zero_rtt; # todo multiple client
    } else {
        first_initial_send := false;
    };

    # The queued frames are deleted
    
    queued_frames(scid) := frame.arr.empty;
    queued_non_probing(scid) := false;
    queued_non_ack(scid) := false;
    queued_close(scid) := false;
    num_queued_frames(scid) := 0;
#Hamid
    queued_ack_eliciting(scid) := false;
#Hamid
    need_sent_ack_eliciting_initial_packet := false;
}


import action show_initial_request_initial
import action show_is_retransmitted(p:stream_pos, c_time:pkt_num)
import action respect_idle_timeout_none

# Procedures
# ==========    

# TLS extensions are used in the client hello and server hello
# messages to carry the QUIC transport parameters, via special TLS
# extension type `quic_transport_parameters`. This type is defined in
# the reference `quic_transport_parameters`. Here we have procedures
# that infer the transport parameters events from the TLS handshake
# messages that transmit the parameters.
#
# TODO: This inference is not really needed. It should be possible
# to obtain the parameters directly from the TLS API. We infer the
# parameters here only for historical reasons. 
#
# The `handle_tls_handshake` rules apply to each `client_hello`,
# `server_hello` or `encrypted extensions` message, in order of
# occurrence in the crypto data.  The last parameter,
# `is_client_hello`, is true for a `client_hello` message (see below).
#

action handle_tls_handshake(src:ip.endpoint, dst:ip.endpoint, scid:cid, dcid:cid,hs:tls.handshake) = {
    if some(ch:tls.client_hello) hs *> ch {
        is_client(scid) := true;
        call handle_tls_extensions(src,dst,scid,ch.extensions,true);
    }
    else if some(sh:tls.server_hello) hs *> sh {
#        call map_cids(src,scid,dcid);    # [1]
#        call map_cids(dst,dcid,scid);
        call handle_tls_extensions(src,dst,scid,sh.extensions,false);
    }
    else if some(ee:tls.encrypted_extensions) hs *> ee {
        call handle_tls_extensions(src,dst,scid,ee.extensions,false);
    }
    if some(fh:tls.finished) hs *> fh {
        tls_handshake_finished := true;
    }
}

#
# The rules in `handle_client_transport_parameters` apply to each
# `quic_transport_parameters` extension instance in order of
# occurrence.
#

action handle_tls_extensions(src:ip.endpoint,dst:ip.endpoint, scid:cid, exts:vector[tls.extension], is_client_hello:bool) = {

    # We process the extensions in a message in order.

    var idx := exts.begin;
    while idx < exts.end {
        var ext := exts.value(idx);
            
        # For every `quic_transport_parameters` extension...
        if some (tps:quic_transport_parameters) ext *> tps {
            call handle_client_transport_parameters(src,dst,scid,tps,is_client_hello);
            trans_params_set(scid) := true;
        };
        idx := idx.next
    };
}

# The rules in `handle_transport_parameter` apply to each
# `transport_parameter` instance a `quic_transport_parameters`
# extension, in order of occurrence.

# Requirements:
#
# - The endpoint must issue an `initial_max_stream_data` value [1]. [not anymore]
# - The endpoint must issue an `initial_max_data` value [2].
# - The endpoint must issue an `max_idle_timeout` value [3]. [not anymore chris]
# - A client must not issue an `stateless_reset_token` value [4].
# - The endpoint must issue an `initial_source_connection_id` value [5]. [chris]
# - A server must issue an `original_destination_connection_id ` value [6].

# An endpoint's min_ack_delay MUST NOT be greater than the its
#   max_ack_delay.  Endpoints that support this extension MUST treat
#   receipt of a min_ack_delay that is greater than the received
#   max_ack_delay as a connection error of type
#   TRANSPORT_PARAMETER_ERROR. [7] 
#Note that while the endpoint's
#   max_ack_delay transport parameter is in milliseconds (Section 18.2 of
#   [QUIC-TRANSPORT]), min_ack_delay is specified in microseconds.
#   An endpoint MUST treat the following as a connection error of type
#   TRANSPORT_PARAMETER_ERROR or PROTOCOL_VIOLATION:
#   *  absence of the retry_source_connection_id transport parameter from
#      the server after receiving a Retry packet,
# Note:
#
# - Setting a transport parameter requires that the parameter is not
#   previously set.


action handle_client_transport_parameters(src:ip.endpoint,dst:ip.endpoint,scid:cid, tps:quic_transport_parameters, is_client_hello : bool) = {
#    call client_transport_parameters_event(src,dst,scid,tps);
    var idx := tps.transport_parameters.begin;
    while idx < tps.transport_parameters.end {
        trans_params(scid) := tps.transport_parameters.value(idx).set(trans_params(scid));
        idx := idx.next
    };
    #require initial_max_stream_data_bidi_local.is_set(trans_params(scid));  # [1]
    #require initial_max_data.is_set(trans_params(scid));  # [2]
    #require max_idle_timeout.is_set(trans_params(scid));  # [3] TODO
    #require initial_max_stream_data_bidi_remote.is_set(trans_params(scid));  # [1]
    #require initial_max_stream_data_uni.is_set(trans_params(scid));  # [1]
    if ~ _generating  { 
        # for tests where we check that the implementation behave well if not present 
        if client_non_zero_scil & ~(scid = 1) & (client_initial_version = 0x00000001 | client_initial_version = 0x00000001){ # TODO 
            require initial_source_connection_id.is_set(trans_params(scid));  # [5]
        };
    };
    if is_client_hello {
        require ~stateless_reset_token.is_set(trans_params(scid));  # [4]
    } else {
        if ~ _generating & ~(scid = 1) {  # TODO
            require original_destination_connection_id.is_set(trans_params(scid));  # [6]
        };
    };

    if ~is_client_hello & (retry_recv(client_initial_rcid) | retry_sent(client_initial_rcid)) & ~zero_length_token {
        require retry_source_connection_id.is_set(trans_params(scid));
        require retry_source_connection_id.value(trans_params(scid)).rcid = client_initial_rcid; # todo generalize
    };

    if max_ack_delay.is_set(trans_params(scid)) {
        max_ack_delay_tp := milliseconds_to_microseconds(max_ack_delay.value(trans_params(scid)).exponent_8);
        call show_max_ack_delay(max_ack_delay_tp);
    }

    if ack_delay_exponent.is_set(trans_params(scid)) {
        require ack_delay_exponent.value(trans_params(scid)).exponent_8 <= 20;
        ack_delay_exponent_tp := ack_delay_exponent.value(trans_params(scid)).exponent_8;
        call show_ack_delay_exponent(ack_delay_exponent_tp);
    }
    
    # [7]
    if min_ack_delay.is_set(trans_params(scid)) & max_ack_delay.is_set(trans_params(scid)) {
        var min_ack_milli := min_ack_delay.value(trans_params(scid)).exponent_8; #  * 1000;
        require  min_ack_milli < milliseconds_to_microseconds(max_ack_delay.value(trans_params(scid)).exponent_8);  # [1]
    };

    # Chris
    # If a max_idle_timeout is specified by either endpoint in its transport parameters (Section 18.2), the connection is silently closed 
    # and its state is discarded when it remains idle for longer than the minimum of the max_idle_timeout value advertised by both endpoints.
    # -> An endpoint that sends packets close to the effective timeout risks having them be discarded at the peer, since the idle timeout 
    # period might have expired at the peer before these packets arrive.
    if max_idle_timeout.is_set(trans_params(scid)) {
        if is_client_hello {
            max_idle_timeout_client := milliseconds_to_microseconds(max_idle_timeout.value(trans_params(scid)).seconds_16)
        } else {
            max_idle_timeout_server := milliseconds_to_microseconds(max_idle_timeout.value(trans_params(scid)).seconds_16)
        }
        if max_idle_timeout_client = 0 {
            max_idle_timeout_used := max_idle_timeout_server;
        } else if max_idle_timeout_server = 0 {
            max_idle_timeout_used := max_idle_timeout_client;
        } else if max_idle_timeout_server < max_idle_timeout_client {
            max_idle_timeout_used := max_idle_timeout_server;
        } else {
            max_idle_timeout_used := max_idle_timeout_client;
        }
        call max_idle_timeout_update(max_idle_timeout_used);
    }
    # var initial_max_stream_data_uni_server_0rtt : stream_pos_32;
    # var initial_max_stream_data_bidi_remote_server_0rtt : stream_pos_32;
    # var initial_max_data_server_0rtt : stream_pos_32;
    # var initial_max_stream_data_bidi_local_server_0rtt : stream_pos_32;
    # var initial_max_stream_id_bidi_server_0rtt : stream_pos_32;
    # var active_connection_id_limit_server_0rtt : stream_pos_32;
    # [6-0rtt]
    
    if zero_rtt_server_test & ~is_client_hello {
        if initial_max_stream_data_uni.is_set(trans_params(scid)) {
            require initial_max_stream_data_uni.value(trans_params(scid)).stream_pos_32 >= initial_max_stream_data_uni_server_0rtt; # todo generalize
        };
        if initial_max_stream_data_bidi_remote.is_set(trans_params(scid)) {
            require initial_max_stream_data_bidi_remote.value(trans_params(scid)).stream_pos_32 >= initial_max_stream_data_bidi_remote_server_0rtt; # todo generalize
        };
        if initial_max_data.is_set(trans_params(scid)) {
            require initial_max_data.value(trans_params(scid)).stream_pos_32 >= initial_max_data_server_0rtt; # todo generalize
        };
        if initial_max_stream_data_bidi_local.is_set(trans_params(scid)) {
            require initial_max_stream_data_bidi_local.value(trans_params(scid)).stream_pos_32 >= initial_max_stream_data_bidi_local_server_0rtt; # todo generalize
        };
        if initial_max_stream_id_bidi.is_set(trans_params(scid)) {
            require initial_max_stream_id_bidi.value(trans_params(scid)).stream_id_16 >= initial_max_stream_id_bidi_server_0rtt; # todo generalize
        };
        if active_connection_id_limit.is_set(trans_params(scid)) {
            require active_connection_id_limit.value(trans_params(scid)).stream_pos_32 >= active_connection_id_limit_server_0rtt; # todo generalize
        };
    };

    # save server TPs
    if ~is_client_hello {
        if initial_max_stream_data_uni.is_set(trans_params(scid)) {
            call tls_api.upper.save_initial_max_stream_data_uni(initial_max_stream_data_uni.value(trans_params(scid)).stream_pos_32);
        };
        if initial_max_stream_data_bidi_remote.is_set(trans_params(scid)) {
            call tls_api.upper.save_initial_max_stream_data_bidi_remote(initial_max_stream_data_bidi_remote.value(trans_params(scid)).stream_pos_32);
        };
        if initial_max_data.is_set(trans_params(scid)) {
            call tls_api.upper.save_initial_max_data(initial_max_data.value(trans_params(scid)).stream_pos_32);
        };
        if initial_max_stream_data_bidi_local.is_set(trans_params(scid)) {
            call tls_api.upper.save_initial_max_stream_data_bidi_local(initial_max_stream_data_bidi_local.value(trans_params(scid)).stream_pos_32);
        };
        if initial_max_stream_id_bidi.is_set(trans_params(scid)) {
            call tls_api.upper.save_initial_max_stream_id_bidi(initial_max_stream_id_bidi.value(trans_params(scid)).stream_id_16);
        };
        if active_connection_id_limit.is_set(trans_params(scid)) {
            call tls_api.upper.save_active_connection_id_limit(active_connection_id_limit.value(trans_params(scid)).stream_pos_32);
        };
    }
}

import action show_enc_level(e:quic_packet_type)
import action max_idle_timeout_update(e:microseconds)
import action show_current_idle_timeout(e:microseconds)
import action show_probe_idle_timeout(e:microseconds)
import action show_probing_time(e:microseconds)
import action show_max_ack_delay(e:microseconds)
import action show_ack_delay_exponent(e:microseconds)
import action sleep_event(e:microseconds)
import action show_cond(e:bool)

import action show_cid(e:cid)

import action show_pstats(scid:cid,e:quic_packet_type,pnum:pkt_num)

import action show_ack_credit(c:cid , p: pkt_num, eli: bool, non_ack: bool, pp: pkt_num)

import action show_probing(c:cid , pp: pkt_num)
```

- the different QUIC frame. They are defined in src/Protocols-Ivy/protocol-testing/quic/quic_stack/quic_frame.ivy. Since QUIC frame can be derived from each other, we use the following hierarchy:
```ivy 
#lang ivy1.7

include collections
include order
include quic_stream
#include quic_fsm_sending
#include quic_fsm_receiving
include quic_transport_error_code
# include quic_loss_recovery
# include quic_congestion_control

# The frame protocol
# ==================
#
# The frame protocol is defined by a sequence of frame events.
# This protocol is layered on the packet protocol, such that
# each packet event contains a sub-sequence of the frame events.
#
# The frame events are subdivided into variants called frame types.
# For each frame type, we define an event `handle` corresponding
# to the generation of a frame and its transfer to the packet protocol
# for transmission. Frame events effect the protocol state by
# enqueueing frames to be encapsulated into packets. The effect of
# this is that frame and packet events are interleaved, such that the
# frames in each packet occur immediately before the packet event in
# the same order in which they occur in the packet payload. TODO:
# While this ordering seems sensible from a semantic point of view,
# implementations might transmit frames out of order. Requiring
# frame events to be in order might complicate a modular proof of the
# implementation.
#
# Each frame has an encryption level (which is the same as the packet
# type it will be encapsulated in). The enryption level determines
# the keys used to protect to protect that packet payload. Only frames
# of the same encryption level may be encapsulated in the same packet
# (however, multiple packets may be concatenated in a single UDP
# datagram). This requirement is enforced by requiring that every
# frame queue contains only frames of the same encryption level. The
# frame handler for each type enforces this condition.

# Data structures
# ===============

# WARNING Order define tag used in quic_ser & quic_deser

object frame = {

    # The base type for frames

    type this


    # (0x01)
    object ping = {
        # Ping frames contain no data, check peers still alive
        variant this of frame = struct {

        }
    }


    # (0x02) 
    object ack = {

        object range = {
            type this = struct {
                gap : pkt_num,       # gap, or zero for first range
                ranges : pkt_num     # number of packets in range - 1
            }
            instance idx : unbounded_sequence
            instance arr : array(idx,this)
        }
		
        # Ack frames are a variant of frame

        variant this of frame = struct {
        
            largest_acked   : pkt_num,    # largest acknowledged packet number
            ack_delay       : microseconds,  # delay of largest acked packet
            ack_ranges      : range.arr   # ack ranges
			# ecnp            : bool,     # is this the final offset
			# ecn_counts      : ecn.arr
        }
    }

    # (0x03)
    object ack_ecn = {

        object range = {
            type this = struct {
                gap : pkt_num,       # gap, or zero for first range
                ranges : pkt_num     # number of packets in range - 1
            }
            instance idx : unbounded_sequence
            instance arr : array(idx,this)
        }

		# TODO: module counter ? variable ecn ?
		
        # object ecn = {
        #     type this = struct {
        #         ect0            : pkt_num,       # total number of packets received with the ECT(0)
		# 		  ect1 : pkt_num,       # total number of packets received with the ECT(1)
        #         ecn_ce : pkt_num      # total number of packets received with the CE codepoint
        #     }
        #     instance idx : unbounded_sequence
        #     instance arr : array(idx,this)
        # }
		
        # Ack frames are a variant of frame

        variant this of frame = struct {
        
            largest_acked   : pkt_num,       # largest acknowledged packet number
            ack_delay       : microseconds,  # delay of largest acked packet
            ack_ranges      : range.arr,      # ack ranges
			ecnp            : bool,          # is this the final offset
			#ecn_counts     : ecn
            ect0            : pkt_num,       # total number of packets received with the ECT(0)
            ect1            : pkt_num,       # total number of packets received with the ECT(1)
            ecn_ce          : pkt_num        # total number of packets received with the CE codepoint
        }
    }


    # (0x04) RESET_STREAM Frame
    object rst_stream = {
        # RESET_STREAM frames are a variant of frame
        variant this of frame = struct {
        
            id              : stream_id,  # id of stream being reset
            err_code        : error_code, # the error code
            final_offset    : stream_pos  # position of the end of the stream
            
        }
    }

    # (0x05)
    object stop_sending = {
        # Stop sending frames are a variant of frame.
        variant this of frame = struct {
            id                : stream_id,  # the stream id
            err_code          : error_code  # the error code
        }
    }

    # (0x06)
	object crypto = {
        # Crypto frames are a variant of frame
        variant this of frame = struct {
            offset : stream_pos,       # the stream offset (zero if ~off)
            length : stream_pos,       # length of the data
            data : stream_data         # the stream data
        }
    }


    # (0x07)    
	object new_token = {
        # New token frames are a variant of frame.
        variant this of frame = struct {
            length : stream_pos,                  # length of the token
            data : stream_data                    # the token
        }
    }

    # (0x08 -> 0x0f)
    object stream = {

        # Stream frames are a variant of frame

        variant this of frame = struct {
            off : bool,        # is there an offset field
            len : bool,        # is there a length field
            fin : bool,        # is this the final offset

            id : stream_id,            # the stream ID
            offset : stream_pos,       # the stream offset (zero if ~off)
            length : stream_pos,       # length of the data
            data : stream_data         # the stream data
        }
    }

    # (0x10) The MAX_DATA frame is used in flow control to inform the
    # peer of the maximum amount of data that can be sent on the connection
    # as a whole.
    object max_data = {
        # Max data frames are a variant of frame.
        variant this of frame = struct {
            pos               : stream_pos  # max number of bytes
        }
    }


    # (0x11) The MAX_STREAM_DATA frame is used in flow control to
    # inform a peer of the maximum amount of data that can be sent on a
    # stream
	object max_stream_data = {
        # Max stream data frames are a variant of frame.
        variant this of frame = struct {
            id                : stream_id,  # the stream id
            pos               : stream_pos  # max number of bytes
        }
    }

    # (0x12) 
    object max_streams = {  # TODO: handle cases of MAX_STREAMS for bidi and uni
        # max_streams frames are a variant of frame.
        variant this of frame = struct {
            id              : stream_id  # maximum stream id 
        }
    }

    # (0x13) 
    object max_streams_bidi = {  # TODO: handle cases of MAX_STREAMS for bidi and uni
        # max_streams frames are a variant of frame.
        variant this of frame = struct {
            id              : stream_id  # maximum stream id 
        }
    }


    # (0x14) DATA_BLOCKED FRAME 
    object data_blocked = {
        # data_blocked frames are a variant of frame.
        variant this of frame = struct {
            pos               : stream_pos  # max number of bytes
        }
    }  

    # (0x15) STREAM_DATA_BLOCKED 
    object stream_data_blocked = {
        # Stream blocked frames are a variant of frame.
        variant this of frame = struct {
            id                : stream_id,  # the stream id
            pos               : stream_pos  # max number of bytes
        }
    }

    # (0x16)
    object streams_blocked = { # TODO: handle bidi and uni cases => create streams_blocked_uni and streams_blocked_bidi + serializer
        # Stream id blocked frames are a variant of frame.
        variant this of frame = struct {
            id                : cid  # the stream id (we use cid for the 16 bytes)
        }
    }

    # (0x17)
    object streams_blocked_bidi = { # TODO: handle bidi and uni cases => create streams_blocked_uni and streams_blocked_bidi + serializer
        # Stream id blocked frames are a variant of frame.
        variant this of frame = struct {
            id                : cid  # the stream id (we use cid for the 16 bytes)
        }
    }

    # (0x18) 
    object new_connection_id = {
        
        # New connection id frames are a variant of frame.

        variant this of frame = struct {
            seq_num                : cid_seq,     # the sequence number of the new cid
            retire_prior_to        : cid_seq,     # retire seq nums prior to this
            length                 : cid_length,  # the length of the new cid in bytes
            scid                   : cid,         # the new cid
            token                  : reset_token  # the stateless reset token
        }
        
    }

    # (0x19)
    object retire_connection_id = {
        
        # Retire connection id frames are a variant of frame.

        variant this of frame = struct {
            seq_num                : cid_seq     # the sequence number of the new cid
        }
        
    }

    # (0x1a)
    object path_challenge = {
        # Path challenge frames are a variant of frame.
        variant this of frame = struct {
            data : stream_data                    # 8-byte payload
        }
    }

    # (0x1b)
    object path_response = {
        # Path response frames are a variant of frame.
        variant this of frame = struct {
            data : stream_data                    # 8-byte payload
        }
    }
    
    # (0x1c or 0x1d) 
    object connection_close = {
        # Connection close frames are a variant of frame.
        variant this of frame = struct {
            err_code               : error_code, # the error code
            frame_type             : error_code, # TODO: not the real type
            reason_phrase_length   : stream_pos, # number of bytes in reason phrase
            reason_phrase          : stream_data # bytes of reason phrase
        }
    }
	


    # (0x1d) NOT PRESENT ANYMORE TOCHECK IF CAN BE REMOVED TODO
    object application_close = {
        # Application close frames are a variant of frame.
        variant this of frame = struct {
            err_code               : error_code, # the error code
            reason_phrase_length   : stream_pos, # number of bytes in reason phrase
            reason_phrase          : stream_data # bytes of reason phrase
        }
    }
    
    	
    #(0x1e) HANDSHAKE_DONE 
    object handshake_done = {
        # HANDSHAKE_DONE frames are a variant of frame.
        variant this of frame = struct {

        }
    }

    #TODO EXTENSION Frames

    # (0xaf) 
    # https://tools.ietf.org/html/draft-iyengar-quic-delayed-ack-02
    object ack_frequency = { # TODO could be moved BUT need to refactor the deser/ser in csq 
        # ACK_FREQUENCY  frame frames are a variant of frame and contains nothing
		# 1 byte frame to increase the size of a packet
         variant this of frame = struct {
			seq_num                     : pkt_num,     # the sequence number 
            ack_eliciting_threshold     : stream_pos,  #maximum number of ack-eliciting packets after which the receiver sends an acknowledgement.
            request_max_ack_delay       : microseconds,
            reordering_threshold        : stream_pos
         }
    } 

    # (0xac) 
    object immediate_ack = {
        # IMMEDIATE_ACK  frame frames are a variant of frame and contains nothing
		# 1 byte frame to increase the size of a packet
         variant this of frame = struct {
         }
    } 

    # (0x42) 
    object unknown_frame = {
        # unknown_frame  frame frames are a variant of frame and contains nothing
        variant this of frame = struct {
        }
    } 

    # (0xtbd) 
    object malicious_frame = {
        # unknown_frame  frame frames are a variant of frame and contains nothing
        variant this of frame = struct {
            data: stream_data
        }
    } 


	# (0x00) implicit in parsing
    #object padding = {
        # PADDING frame frames are a variant of frame and contains nothing
		# 1 byte frame to increase the size of a packet
    #    variant this of frame = struct {
			
    #    }
    #}    


    instance idx : unbounded_sequence
    instance arr : array(idx,this)
}        

# Generic event
# =============

#
# The generic event for frames is specialized for each
# frame type.  Its arguments are:
#
# - `f`: the frame contents
# - `scid`: the source aid
# - `dcid`: the destination aid
# - `e`: the encryption level
# - `seq_num`: the packet number where the frame is


object frame = {
    ...
    action handle(f:this,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num) = {
        # is_not_sleeping := time_api.c_timer.is_sleep_fake_timeout;
        # require (~is_not_sleeping -> ~_generating);
        # require (_generating -> is_not_sleeping);
        
        require false; # this generic action should never be called
    }
}

# TODO: we assume here that a frame can only be sent at a given
# encryption level if the keys for that level have already been
# established.  For 1rtt frames this means that a TLS finish message
# must have bee sent in some prior frame. This is helpful to prevent
# the peer from dropping packets in tests, but not realistic, since
# packet re-ordering could cause the 1rtt frame to be received before
# the required handshake message.  In principle, we should allow this
# case, but reduce its probability in testing.



# Specification state
# ===================
#
# - For each aid C,and stream id S, `stream_seen(C,S)`
#   indicates that a stream has been opened by aid C.
#   
#
# - For each aid C,and stream id S, `max_stream_data_val(C,S)`
#   indicates the maximum number of bytes that may be sent on stream
#   id S to C.
#
# - For each aid C,and stream id S, `max_stream_data_set(C,S)`
#   indicates the maximum number of bytes that may be sent on stream
#   id S to C has been set.
#
# - For each aid C, `max_data_val(C,S)` indicates the maximum total
#   number of bytes that may be sent on all streams to C.
#
# - For each aid C, `max_data_set(C,S)` indicates the maximum total
#   number of bytes that may be sent on all streams to C has been set.
#
# - For each aid C,and stream id S, `stream_length(C,S)`
#   indicates the length of the stream data transmitted in QUIC
#   packets on stream id S to cid C. The length is the
#   least stream position greater than the position of all bytes
#   transmitted. Note this may be less than the length of the application
#   data, but may not be greater.
#
# - For aid C,and stream id S, `stream_finished(C,S)` indicates that
#   the stream transmitted to C on stream id S is finished (that is, a
#   FIN frame has been sent).
#
# - For each aid C,and stream id S, `stream_reset(C,S)` indicates that
#   the stream transmitted to C on stream id S is reset (that is, a
#   RESET_STREAM frame has been sent).
#
# - For each aid C,and stream kind K, `max_stream_set(C,K)`
#   indicates that the maximum stream id has been declared.
#
# - For each aid C,and stream kind K, `max_stream(E,C,K)`
#   indicates the declared maximum stream id.
#
# - The queued frames at aid `C` are
#   represented by `queued_frames(C)` and are initially empty.
# 
# - The function queued_level(C) gives the packet type associated with the 
#   currently queued frames for aid C
#
#   TODO: Currently we can only queue frames of the same packet type,
#   We should have a separate frame queue for each packet type. 
#
# - The relation `queued_non_probing(C)` indicates that one of the queued
#   frames at aid `C` contains a non-probing frame. This is a frame
#   other than path challenge, new connection id and padding.
#
# - The relation `queued_non_ack(C)` indicates that one or more of the queued
#   frames at aid `C` is not an ACK frame with padding.
#
# - The relation `queued_close(C)` indicates that one or more of the queued
#   frames at aid `C` is a CONNECTION_CLOSE or APPLICATION_CLOSE frame.
#
# - The function num_queued_frames(C:cid) gives the number of frames
#   queue at aid `C`.
#
# - The predicate `path_challenge_pending(C,D)` that a path challenge
#   has been sent to aid C with data D, and has not yet been responded
#   to. QUESTION: should path responses be resent, or should the client
#   wait for a resent path challenge?
#
# - The function `conn_total_data(C)` represents the total number of stream
#   bytes received by aid `C`.
#
#Hamid
# - The relation `queued_ack_eliciting(C)` indicates that one or more of the queued
#   frames at aid `C` is an ACK eliciting frame, i.e. according to draft 24, frames other than ACK, PADDING, CONNECTION_CLOSE
#Hamid
#
#chris 
# - the function `queued_level_type(C:cid,T:quic_packet_type) : frame.arr` is used to  queue frames a separate frame queue for each packet type.  TODO
# - the relation `send_retire_cid(C:cid,S:stream_id)` is used to say that the next frame should be a retire_CID frame
# - the function `max_rtp_num(C:cid) : cid_seq``is used to get the maximum retire_prior_to field in new_cid frame
# - STREAM frame retransmission: 13.3.  Retransmission of Information
#    *  Application data sent in STREAM frames is retransmitted in new
#       STREAM frames unless the endpoint has sent a RESET_STREAM for that
#       stream.  Once an endpoint sends a RESET_STREAM frame, no further
#       STREAM frames are needed.
# We can consider that a STREAM frame is retransmitted if we receive a Frame twice with the same
# information. For that we use more or less the same approach than Copy-On-Write for memory
# We use a reference count (count_stream_frame) for each STREAM frame that we get. 0 meaning no reference, 1 = received once, ect
# If count_stream_frame > 1 => this frame has been retransmitted and stream_frame_restransmitted is true
# - RESET_STREAM frame retransmission =  same approach
#   *  Cancellation of stream transmission, as carried in a RESET_STREAM
#      frame, is sent until acknowledged or until all stream data is
#      acknowledged by the peer (that is, either the "Reset Recvd" or
#      "Data Recvd" state is reached on the sending part of the stream).
#      The content of a RESET_STREAM frame MUST NOT change when it is
#      sent again.
# - STREAM_DATA_BLOCKED frame retransmission =  same approach
#   *  Blocked signals are carried in DATA_BLOCKED, STREAM_DATA_BLOCKED,
#      and STREAMS_BLOCKED frames.  DATA_BLOCKED frames have connection
#      scope, STREAM_DATA_BLOCKED frames have stream scope, and
#      STREAMS_BLOCKED frames are scoped to a specific stream type.  New
#      frames are sent if packets containing the most recent frame for a
#      scope is lost, but only while the endpoint is blocked on the
#      corresponding limit.  These frames always include the limit that
#      is causing blocking at the time that they are transmitted.
# - first_ack_freq_received return true if we received the first ack_freq frame
# - last_ack_freq_seq(C:cid) return the seqnum associated to the last ack_frequency
#                            frame received 
#chris

relation stream_seen(C:cid,S:stream_id)
function max_stream_data_val(C:cid,S:stream_id) : stream_pos
relation max_stream_data_set(C:cid,S:stream_id)
function max_data_val(C:cid) : stream_pos
relation max_data_set(C:cid)
function stream_length(C:cid,S:stream_id) : stream_pos
relation stream_finished(C:cid,S:stream_id)
relation stream_reset(C:cid,S:stream_id)
relation max_stream_set(C:cid,K:stream_kind)
function max_stream(C:cid,K:stream_kind) : stream_id 
#function max_stream_id(C:cid,K:stream_kind) : cid
function queued_frames(C:cid) : frame.arr
function queued_frames_rtt(C:cid) : frame.arr
function queued_level(C:cid) : quic_packet_type
function queued_level_rtt(C:cid) : quic_packet_type
relation queued_non_probing(C:cid)
relation queued_non_ack(C:cid)
relation queued_challenge(C:cid)
relation queued_close(C:cid)
function num_queued_frames(C:cid) : frame.idx
function num_queued_frames_rtt(C:cid) : frame.idx
relation path_challenge_pending(C:cid,D:stream_data)
relation path_challenge_sent(C:cid)
function conn_total_data(C:cid) : stream_pos
#Hamid
relation queued_ack_eliciting(C:cid)
relation queued_ack_eliciting_pkt(C:stream_pos) # TODO
function num_ack_eliciting_pkt : stream_pos
function num_ack_pkt : stream_pos


import action show_num_ack_eliciting_pkt(s:stream_pos)
import action show_num_ack_pkt(s:stream_pos)
#Hamid

#chris
function queued_level_type(C:cid,T:quic_packet_type) : frame.arr
relation send_retire_cid(C:cid)
function max_rtp_num(C:cid) : cid_seq

function count_stream_frame(I:stream_id,O:stream_pos, 
                            L:stream_pos,D:stream_data) : stream_pos
relation stream_frame_restransmitted(S:stream_id)

function count_reset_frame(I:stream_id,E:error_code,O:stream_pos) : stream_pos
relation reset_frame_restransmitted(S:stream_id)

function count_sdb_frame(I:stream_id,O:stream_pos) : stream_pos
relation sdb_frame_restransmitted(S:stream_id)

function first_ack_freq_received : bool
# The largest packet number among all received ack-eliciting packets.
function largest_unacked : pkt_num
# The Largest Acknowledged value sent in an ACK frame.
function largest_acked   : pkt_num
# Packets with packet numbers between the Largest Unacked and Largest Acked that have not yet been received.
function unreported_missing : pkt_num
function last_ack_freq_seq(C:cid) : pkt_num

function count_newcid_frame(I:cid_seq,O:cid_seq, L:cid_length,D:cid,T:reset_token) : stream_pos

function count_rcid_frame(I:cid_seq) : stream_pos

relation connection_closed 

relation handshake_done_send # TODO add src-endpoints

relation handshake_done_recv # TODO add src-endpoints

function last_cid_seq(C:cid):cid_seq

function first_zrtt_pkt : cid
relation zrtt_pkt_update 

#relation is_stream_limit_test
relation is_stream_limit_test
relation is_crypto_limit_test

#TODO faire all retransmission
relation stop_sending_in_bad_state

relation newly_acked(S:stream_pos) 


# A variable-length integer representing the maximum number of ack-eliciting packets 
# the recipient of this frame receives before sending an acknowledgment. A receiving 
# endpoint SHOULD send at least one ACK frame when more than this number of 
# ack-eliciting packets have been received. A value of 0 results in a receiver 
# immediately acknowledging every ack-eliciting packet. By default, an endpoint 
# sends an ACK frame for every other ack-eliciting packet, as specified in Section 
# 13.2.2 of [QUIC-TRANSPORT], which corresponds to a value of 1.
function ack_eliciting_threshold_val(C:cid) : stream_pos
function current_ack_frequency(C:cid) : stream_pos
function ack_eliciting_threshold_current_val(C:cid) : stream_pos
function ack_out_of_order_val(C:cid) : stream_pos
function ack_out_of_order_current_val(C:cid) : stream_pos
#chris

after init {
    stream_seen(C,S) := false;
    stream_length(C,S) := 0;
    max_stream_data_set(C,S) := false;
    max_data_set(C) := false;
    stream_finished(C,S) := false;
    stream_reset(C,S) := false;
    queued_non_probing(C) := false;
    queued_non_ack(C) := false;
    queued_close(C) := false;
    path_challenge_pending(C,D) := false;
#Hamid
    queued_ack_eliciting(C) := false;
#Hamid
#chris
    max_rtp_num(C) := 0;
    send_retire_cid(C) := false;
    count_stream_frame(I,O,L,D) := 0; #B,J,F,
    stream_frame_restransmitted(S) := false;
    count_reset_frame(I,E,O) := 0;
    reset_frame_restransmitted(S) := false;
    count_sdb_frame(I,O) := 0;
    sdb_frame_restransmitted(S) := false;
    stop_sending_in_bad_state := false;
    first_ack_freq_received := true;
    last_ack_freq_seq(C) := 0;
    connection_closed := false;
    handshake_done_send := false;
    handshake_done_recv := false;
    is_stream_limit_test := false;
    is_crypto_limit_test := false;
    last_cid_seq(C) := 0;
    zrtt_pkt_update := false;
    newly_acked(S) := true;
    queued_ack_eliciting_pkt(C) := false;

    ack_eliciting_threshold_val(C) := 0;
    ack_eliciting_threshold_current_val(C) := 0;

    ack_out_of_order_val(C) := 1;
    ack_out_of_order_current_val(C) := 0;

    num_ack_eliciting_pkt := 0;
    num_ack_pkt := 0;
#chris
}


# #### ACK event

# The set of packet numbers acknowledged by an ACK frame is determined
# by the `largest_ack` field and the `ack_blocks` field. Each ACK
# block acknowledges packet numbers in the inclusive range `[last - gap, last -
# gap - blocks]` where `gap` and `ranges` are the fields of the ACK
# range and `last` is `largest_ack` minus the sum of `gap + ranges`
# for all the previous ack ranges.
#
# The `gap` field for the first ack range is always zero and is not
# present in the low-level syntax.

# Requirements:
#
# - Every acknowledged packet must have been sent by the destination endpoint [1].
# - Keys must be established for the given encryption level [4].

# Effects:
#
# - The acknowledged packets are recorded in the relation `acked_pkt(C,N)`
#   where `C` is the *source* of the acknowledged packet (not of the ACK)
#   and `N` is the packet number [2].
# - The greatest acked packet is also tracked in `max_acked(C,e)` [3]
#
# - If a packet with a connection_close frame of either type is acknowledged
#   the sending aid enters the draining state. Note that observing the ack of
#   a connection close frame is the only way we can detect that it was received.
#   

# TEMPORARY: use this to enforce new acks in testing. Without this,
# too many duplicate acks would be generated.

var force_new_ack : bool

import action is_generating(b:bool)
import action is_ack_frequency_respected(b:bool)
object frame = {
    ...
    object ack = {
        ...
        action handle(f:frame.ack,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)

	around handle {
            #call is_generating(_generating);
            # is_not_sleeping := time_api.c_timer.is_sleep_fake_timeout;
            # require (~is_not_sleeping -> ~_generating);
            # require (_generating -> is_not_sleeping);
            # var tp := trans_params(dcid);
            # if min_ack_delay.is_set(tp)  {
            # };

            if  ~_generating {
                # On receiving an ACK_FREQUENCY frame and updating its max_ack_delay and Ack-Eliciting Threshold values (Section 4), 
                # the endpoint sends an acknowledgement when one of the following conditions are met:
                # Since the last acknowledgement was sent, the number of received ack-eliciting packets is greater than the Ack-Eliciting Threshold.
                # Since the last acknowledgement was sent, max_ack_delay amount of time has passed.
                call is_ack_frequency_respected(num_ack_eliciting_pkt > ack_eliciting_threshold_val(scid));
                call is_ack_frequency_respected(num_ack_eliciting_pkt > ack_eliciting_threshold_val(dcid));
                num_ack_eliciting_pkt := 0;
            }
            
            # ack_time := time_api.c_timer.now_micros;
            # An endpoint generates an RTT sample on receiving an ACK frame that meets the following two conditions:
            # 1. the largest acknowledged packet number is newly acknowledged, and
            # 2. at least one of the newly acknowledged packets was ack-eliciting.

            require connected(dcid) & connected_to(dcid) = scid;
            if _generating  {
            	require ~(e = quic_packet_type.initial) & ~(e = quic_packet_type.handshake); #& ~(e = quic_packet_type.handshake)
                require ~conn_closed(scid);
                # An endpoint measures the delays intentionally introduced between the time the 
                # packet with the largest packet number is received and the time an acknowledgment 
                # is sent. The endpoint encodes this delay in the Ack Delay field of an ACK frame; 
                # see Section 19.3. This allows the receiver of the ACK to adjust for any intentional delays, 
                # which is important for getting a better estimate of the path RTT when acknowledgments are delayed. 
                # A packet might be held in the OS kernel or elsewhere on the host before being processed. 
                # An endpoint MUST NOT include delays that it does not control when populating the
                # Ack Delay field in an ACK frame.

                # Scaling in this fashion allows for a larger range of values with a shorter encoding at 
                # the cost of lower resolution. Because the receiver doesn't use the ACK Delay for Initial 
                # and Handshake packets, a sender SHOULD send a value of 0. TODO
            };

            require e = quic_packet_type.handshake -> established_handshake_keys(scid);  # [4]
            require e = quic_packet_type.one_rtt -> established_1rtt_keys(scid);  # [4]
            # Chris
            # TODO ECN
            require ~(e = quic_packet_type.version_negociation) & ~(e = quic_packet_type.retry) & ~(e = quic_packet_type.zero_rtt);
            # Chris
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            
            var idx : frame.ack.range.idx := 0;
            var last := f.largest_acked;
            if max_acked(dcid,e) < last {
                max_acked(dcid,e) := last;  # [3]
            };


            call show_ack_eliciting_threshold_current_val(ack_eliciting_threshold_current_val(scid));
            call show_ack_eliciting_threshold_current_val(ack_eliciting_threshold_current_val(dcid));
            call show_ack_eliciting_threshold_val(ack_eliciting_threshold_val(scid));
            call show_ack_eliciting_threshold_val(ack_eliciting_threshold_val(dcid));


            
            require f.ack_ranges.end > 0;
            var some_new_ack := false;
            while idx < f.ack_ranges.end {
                var ack_range := f.ack_ranges.value(idx);
                require idx > 0 -> ack_range.gap < last - 1;
                var upper := last - ((ack_range.gap+2) if idx > 0 else 0);
                require ack_range.ranges <= upper;
                last := upper - ack_range.ranges;
                var jdx := last;
                while jdx <= upper {
                        require sent_pkt(dcid,e,jdx);  # [1]
                        if pkt_has_close(dcid,e,jdx) {
                            conn_draining(scid) := true  # [5]
                        };
                        if ~acked_pkt(dcid,e,jdx) {
                            #if ack_eliciting_threshold_current_val(dcid) >= ack_eliciting_threshold_val(dcid) {
                                some_new_ack := true;
                                call show_ack_generated;
                                ack_eliciting_threshold_current_val(dcid) := 0;
                            #};
                        };
                    acked_pkt(dcid,e,jdx) := true;
                    jdx := jdx + 1
                };
    #           acked_pkt(dcid,N) := (last <= N & N <= upper) | acked_pkt(dcid,N);  # [2]
                idx := idx.next;
            };
            # var local_ack_delay := on_ack_sent(last_pkt_num(scid,e),e);
            # require _generating -> local_ack_delay <= local_max_ack_delay_tp;
            if _generating {
                #var local_ack_delay := on_ack_sent(last_pkt_num(scid,e),e);
                # require ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_initial_packet;
                require some_new_ack;
                require f.largest_acked = max_acked(dcid,e);
                # var local_ack_delay := on_ack_sent(max_acked(dcid,e) ,e);
                # f.ack_delay := local_ack_delay;
                # require local_ack_delay <= local_max_ack_delay_tp;
                # call show_local_delay_ack(local_ack_delay,local_max_ack_delay_tp);
                call show_ack_generated;
            } 
	    ...
            if ~_generating {
                call on_ack_received(dst_endpoint,f.largest_acked, f.ack_delay,e);
            } 
            # else {
            #     local_largest_acked_packet(e) := f.largest_acked;
            # }
            force_new_ack := false;
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

import action show_local_delay_ack(val:microseconds, val2:microseconds)
import action show_ack_generated
import action show_ack_eliciting_threshold_current_val(val:stream_pos)
import action show_ack_eliciting_threshold_val(val:stream_pos)

object frame = {
    ...
    object ack_ecn = {
        ...
        action handle(f:frame.ack_ecn,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)

	around handle {
            require connected(dcid) & connected_to(dcid) = scid;
            if _generating  {
            	require ~(e = quic_packet_type.initial) & ~(e = quic_packet_type.handshake); #& ~(e = quic_packet_type.handshake)
            };

            require e = quic_packet_type.handshake -> established_handshake_keys(scid);  # [4]
            require e = quic_packet_type.one_rtt -> established_1rtt_keys(scid);  # [4]
            #Chris
            #TODO ECN
            #require ~(e = quic_packet_type.version_negociation) & ~(e = quic_packet_type.retry);
            #Chris
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            var idx : frame.ack_ecn.range.idx := 0;
            var last := f.largest_acked;
            if max_acked(dcid,e) < last {
                max_acked(dcid,e) := last;  # [3]
            };
            require f.ack_ranges.end > 0;
            var some_new_ack := false;
            while idx < f.ack_ranges.end {
                var ack_range := f.ack_ranges.value(idx);
                require idx > 0 -> ack_range.gap < last - 1;
                var upper := last - ((ack_range.gap+2) if idx > 0 else 0);
                require ack_range.ranges <= upper;
                last := upper - ack_range.ranges;
                var jdx := last;
                while jdx <= upper {
                        require sent_pkt(dcid,e,jdx);  # [1]
                        if pkt_has_close(dcid,e,jdx) {
                            conn_draining(scid) := true  # [5]
                        };
                        if ~acked_pkt(dcid,e,jdx) {
                            some_new_ack := true;
                        };
                    acked_pkt(dcid,e,jdx) := true;
                    jdx := jdx + 1
                };
    #           acked_pkt(dcid,N) := (last <= N & N <= upper) | acked_pkt(dcid,N);  # [2]
                idx := idx.next;
            };
            if _generating {
                require some_new_ack;
            }
	    ...
            force_new_ack := false;
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}


#
# #### STREAM event
#
# STREAM frames carry stream data. 
#
# Requirements:
#
# - The upper bound of the stream frame may not exceed the current
#   value of `max_stream_data_val` for the given destination and cid, if
#   it has been set [2].
#
# - If the stream is finished, the the frame offset plus length must
#   not exceed the stream length [5].
#
# - The stream id must be less than or equal to
#   the max stream id for the kind of the stream [6].
#
# - The stream must not have been reset [7].
#
# - The connection must not have been closed by the source endpoint [8].
#
# - The connection id must have been seen at the source [9]
#   and the connection between source and destination must not be initializing [10].
#
# - The 1rtt keys have been established [11].
#
# - If the sender as reset the stream to a given length, then the
#   end of the stream frame data must not exceed the reset length [13].

# Effects:
#
# - If the stream has not been seen before, and if the
#   `initial_max_stream_data` transport parameter has been set, then
#   the `max_stream_data_val` value is set to the value of the
#   `initial_max_stream_data` transport parameter [3].
#
# - The length of the stream is updated. 
#
# - If the fin bit is set, the stream is marked as finished.
#
# - The total amount of data received on the connection is
#   updated. Note this reflects the total of the observed length of
#   all streams, including any unreceived gaps.
#

object frame = { # TODO cleanup
    ...
    object stream = {
        ...
        action handle(f:frame.stream,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)

	around handle {
            # if  e = quic_packet_type.one_rtt { #  & established_0rtt_keys(scid)
            #     require connected(dcid) & connected_to(dcid) = scid;
            #     require e = quic_packet_type.one_rtt & established_1rtt_keys(scid); #  | e = quic_packet_type.zero_rtt & established_0rtt_keys(scid) 
            #     require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            # } else {
            #call show_enc_level(e);
            #     require num_queued_frames_rtt(scid) > 0 -> e = queued_level_rtt(scid); # TODO
            # };

            if (~zero_rtt_allowed | zero_rtt_sent) & ~(e = quic_packet_type.zero_rtt) {
                require tls_handshake_finished;
                require (connected(dcid) & connected_to(dcid) = scid); # | (e = quic_packet_type.zero_rtt & established_0rtt_keys(scid)); #e = quic_packet_type.zero_rtt & 
                require (e = quic_packet_type.one_rtt & established_1rtt_keys(scid)); # | (e = quic_packet_type.zero_rtt & established_0rtt_keys(scid)); # | e = quic_packet_type.zero_rtt  | e = quic_packet_type.zero_rtt & established_0rtt_keys(scid)  
            } else {
                #require e = quic_packet_type.one_rtt | e = quic_packet_type.zero_rtt;
                require (e = quic_packet_type.one_rtt & established_1rtt_keys(scid)) | (e = quic_packet_type.zero_rtt & ~established_1rtt_keys(scid));

                #require dcid ~= the_cid;
            #     # dcid := 2;
            #     #require e = quic_packet_type.zero_rtt;
            #     #require (connected(dcid) & connected_to(dcid) = scid) | (established_0rtt_keys(scid)); #e = quic_packet_type.zero_rtt & 
            #     #require (e = quic_packet_type.one_rtt & established_1rtt_keys(scid)) | (established_0rtt_keys(scid)); # | e = quic_packet_type.zero_rtt  | e = quic_packet_type.zero_rtt & established_0rtt_keys(scid)  
            }
            #require e = quic_packet_type.zero_rtt -> established_0rtt_keys(scid);  # [11]
            if ~zero_rtt_allowed | zero_rtt_sent {
                require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            }
            #require num_queued_frames_rtt(scid) > 0 -> e = queued_level_rtt(scid); # TODO

            # [11] (e = quic_packet_type.zero_rtt & established_0rtt_keys(scid)
            #require e = quic_packet_type.zero_rtt -> established_0rtt_keys(scid);  # [11]
            #require e = quic_packet_type.one_rtt -> established_1rtt_keys(scid);

            require ~conn_closed(scid);  # [8]

            var offset := f.offset if f.off else 0;

            require ((offset) + (f.length)) <= stream_app_data_end(dcid,f.id);
    
            #if is_stream_limit_test = false { #For stream limit test & pico vuln| ~_generating  not working
            require f.data = stream_app_data(dcid,f.id).segment(offset,offset+f.length); # TODO
            require f.fin <-> (stream_app_data_finished(dcid,f.id) & offset+f.length = stream_app_data_end(dcid,f.id));

            var kind := get_stream_kind(f.id);

            # Following assertion could fail because of packet
            # re-ordering. QUESTION: what can we say?  require
            # ~stream_reset(dcid,f.id); # [7]

            if (~zero_rtt_allowed | zero_rtt_sent)  {  
                require conn_seen(scid);  # [9]
            }

            if _generating  {
                # require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
            };

            # & ~cid_mapped(f.scid)
            #quinn bug: +-deadlock with new_connection_id
            #require ((offset) + (f.length)) <= stream_max_data(dcid,f.id,e);  # [2]

            
            require stream_reset(dcid,f.id) ->
                       ((offset) + (f.length)) <= stream_length(dcid,f.id);  # [13]
	        
            #remove for stream limit test
            if ~zero_rtt_allowed | zero_rtt_sent  { # | ~_generating
                require stream_id_allowed(dcid,f.id,e);  # [6]
            } 
            else if _generating {
                require  f.id = 4; #  f.id = 8 |f.id = 4 |
            }
	        ...
            stream_seen(scid,f.id) := true;

            var offset := f.offset if f.off else 0;
            var length := offset + f.length;

            # require stream_finished(dcid,f.id) -> length <= stream_length(dcid,f.id);  # [5] deadlock client
            if stream_length(dcid,f.id) < length {
                conn_total_data(dcid) := conn_total_data(dcid) +
                                             (length - stream_length(dcid,f.id));  # [12]
                stream_length(dcid,f.id) := length
            };
            if f.fin {
                stream_finished(dcid,f.id) := true;
            };
            if (~zero_rtt_allowed | zero_rtt_sent) & ~(e = quic_packet_type.zero_rtt) { #TODO
                call enqueue_frame(scid,f,e,false,seq_num);
            } else {
                first_zrtt_pkt := dcid;
                call enqueue_frame_rtt(scid,f,e,false);
            }
        }
    }
}

#import action show_stream(pkt:stream_data)

# #### CRYPTO event
#
# CRYPTO frames carry crypto handshake data, that is, TLS records.
#
# Requirements:
#
# - The connection must not have been closed by the source endpoint [1].
# - The bytes are present in `crypto_data` [2].
#chris
# - It can be sent in all packet types except 0-RTT. [4] (implicit, needed ?)
#chris  
# Effects:
#
# - The length of the crypto stream and the present bits are updated. [3]

object frame = {
    ...
    object crypto = {
        ...
        action handle(f:frame.crypto,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)

	around handle {
	        #if ~scid=0 {
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
	        #};
            # if _generating  {
            #     # require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
            # };
            require ~conn_closed(scid);  # [1]
            #chris
            require e ~= quic_packet_type.zero_rtt;  # [4]
            #chris
	        #if  ~is_crypto_limit_test | ~_generating { #For crypto limit test
                require ((f.offset) + (f.length)) <= crypto_data_end(scid,e);  # [2]
                require f.data = crypto_data(scid,e).segment(f.offset,f.offset+f.length);  # [2]
	        #};
            ...
            #require e ~= quic_packet_type.zero_rtt;  # [4]
            var length := f.offset + f.length;
            if crypto_length(scid,e) < length {
                crypto_length(scid,e) := length;   # [3]
                #call show_crypto_length(crypto_length(scid,e));
            };
            var idx := f.offset;
            while idx < f.offset + f.length {
                crypto_data_present(scid,e,idx) := true;  # [3]
                idx := idx.next
            };
            call enqueue_frame(scid,f,e,false,seq_num);
            # TODO: is the following needed? Maybe it belongs somewhere else?
            if e = quic_packet_type.handshake {
                established_1rtt_keys(scid) := true;
            }
        }
    }
}

import action show_crypto_length(pkt:stream_pos)


#
# #### RESET_STREAM events
#
# RESET_STREAM frames cause an identified stream to be abruptly terminated,
# meaning the no further transmissions (or retransmissions) will be sent for
# this stream and the receiver may ignore any data previously transmitted.
#
# Requirements:

# - Stream id must has been created to be reset [8]. (FSM)
# - Stream id must not exceed maximim stream id for the stream kind [4].
# - QUESTION: Can a previously reset stream be reset?
# - The final stream position may not be lesser than that of any previous
#   stream frame for the same stream id [1].
# - The connection must not have been closed by the source endpoint [5].
# - The encryption level must be 0rtt or 1rtt [6].
# - If stream was previously reset or finished, final offset must be same [7].
#
# Effects:
#
# - The specified stream id is marked as reset [2].
# - The stream length is set to the given final offset [3].
#
# Question: Where is it written that reset stream frames cannot occur in
# initial or handshake packets?

object frame = { ...
    object rst_stream = { ...
        action handle(f:frame.rst_stream,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)

	around handle {
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);  # [6]
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            require ~conn_closed(scid);  # [5]
            require connected(scid) & connected_to(scid) = dcid;
            require stream_length(dcid,f.id) <= f.final_offset;  # [1]
             if _generating  {
# require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
};
            require (stream_reset(dcid,f.id) | stream_finished(dcid,f.id)) -> stream_length(dcid,f.id) = f.final_offset;
            stream_reset(dcid,f.id) := true;  # [2]
            stream_length(dcid,f.id) := f.final_offset;  #[3]
            #require stream_seen(dcid,f.id);  # [8]
            require stream_id_allowed(dcid,f.id,e);  # [4]
	    ...
            if ~_generating {
                call handle_transport_error(f.err_code);
            };
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

#
# #### STOP_SENDING event
#
# STOP_SENDING frames are sent by the receiver of s stream to indicate that stream data
# is being ignored and it should stop sending.
#
# Requirements:
#
# - Receiving a STOP_SENDING frame for a
#   locally-initiated stream that has not yet been created MUST be
#   treated as a connection error of type STREAM_STATE_ERROR.. [8] (FSM)
# - Stream id must not exceed maximim stream id for the stream kind [4].
# - QUESTION: Can a previously reset stream be reset?
# - The connection must not have been closed by the source endpoint [5].
# - The encryption level must be 0rtt or 1rtt [6].
#
# Effects:
#
#   (None)
#   An endpoint that receives a STOP_SENDING frame
#   MUST send a RESET_STREAM frame if the stream is in the Ready or Send
#   state
#

object frame = { ...
    object stop_sending = { ...
        action handle(f:frame.stop_sending,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)

	around handle {# is_not_sleeping := time_api.c_timer.is_sleep_fake_timeout;
            # require (_generating  -> is_not_sleeping);
            
            # require (~is_not_sleeping -> ~_generating);
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);  # [6]
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            if _generating  {
                # require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
            };
            require ~conn_closed(scid);  # [5]
            require connected(scid) & connected_to(scid) = dcid;
            if ~_generating { # For tests
                require stream_seen(dcid,f.id);  # [8]
                require stream_id_allowed(dcid,f.id,e);  # [4]
            };
	    ...
            if ~_generating {
                call handle_transport_error(f.err_code);
            };
            stream_seen(scid,f.id) := true;
            #receiving_ready := true;
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

#
# #### max_streams event
#
# max_streams frames cause the maximum stream id to be set. 
# The receiver of the max stream id may use stream ids up to and including
# the given maximum. Bit 1 of the stream id (the next-to-least significant)
# determines whether the limit is set for unidirectional or bidirectional
# streams. A max stream id containing a stream id lower than the current
# maximum is allowed and ignored.
#
# Requirements:
#
# - The connection must not have been closed by the source endpoint [2].
# - Max stream id frames may not occur in initial or handshake packets [3].
# - The role of the stream id must equal the role of the peer in the given connection. [4]
#   QUESTION: this requirement is not stated in the draft spec, but it is enforced
#   by picoquic (see anomaly6). The spec should state explicitly what happens in this case.
#chris
# -  a lower stream limit than an endpoint has previously received. MAX_STREAMS frames that 
#    do not increase the stream limit MUST be ignored. [5]
#chris
#
# Effects:
#
# - The maximum stream id is set [1].
#
# QUESTION: must the stream id's be less than the max or less than or equal?
# Picoquic seems to think less than, but the is not clear in the draft.

# var some_max_streams : bool;
#  var ms;

object frame = { ...
    object max_streams = { ...
        action handle(f:frame.max_streams,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)

	around handle {# is_not_sleeping := time_api.c_timer.is_sleep_fake_timeout;
            # require (_generating  -> is_not_sleeping);
            
            # require (~is_not_sleeping -> ~_generating);
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);  # [3]
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            require connected(scid) & connected_to(scid) = dcid;
             if _generating  {
# require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
};
            require ~conn_closed(scid);  # [2]

            var kind := bidir;
            if ~ (max_stream_set(dcid,kind) & f.id < max_stream(dcid,kind)) { #[5]
                max_stream_set(dcid,kind) := true;
                max_stream(dcid,kind) := f.id; #  [1]
		        #max_stream_id(dcid,kind) := cid_to_stream_id(f.id);
            }

            #  if _generating {
            #      require some_max_streams;
            #      require f.id = ms;
            #  }

	        ...

            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

object frame = { ...
    object max_streams_bidi = { ...
        action handle(f:frame.max_streams_bidi,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)

	around handle {# is_not_sleeping := time_api.c_timer.is_sleep_fake_timeout;
            # require (_generating  -> is_not_sleeping);
            
            # require (~is_not_sleeping -> ~_generating);
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);  # [3]
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            require connected(scid) & connected_to(scid) = dcid;
             if _generating  {
# require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
};
            require ~conn_closed(scid);  # [2]

            var kind := bidir;
            if ~ (max_stream_set(dcid,kind) & f.id < max_stream(dcid,kind)) { #[5]
                max_stream_set(dcid,kind) := true;
                max_stream(dcid,kind) := f.id; #  [1]
		        #max_stream_id(dcid,kind) := cid_to_stream_id(f.id);
            }

            #  if _generating {
            #      require some_max_streams;
            #      require f.id = ms;
            #  }

	        ...

            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

#
# #### CONNECT_CLOSE event
#
# CONNECT_CLOSE frames indicate to the peer that the connection is being closed.
# It is unclear what this means operationally, but it seems reasonable to assume that the
# endpoint closing the connection will not send or receive any further data on the connection,
# so it is as if all the open streams are reset by this operation.
#
# A connection close frame can occur at any time. 
#
# Questions:
#
# - Are Ack frames still allowed after connection close?
# - Are retransmissions allowed after connection close?
# - When is a connection close allowed?
#
# Requirements:
#
# - The source and destination cid's must be connected. In effect,
#   this means that a server hello message must have been sent for
#   this connection Therefore a client cannot send a connection close
#   before receiving at least one handshake message from the
#   server. QUESTION: the spec is a bit vague about this, stating
#   "Handshake packets MAY contain CONNECTION_CLOSE frames if the
#   handshake is unsuccessful." Does "unsuccessful" necessarily mean that
#   some handshake has been received? Also, can an initial packet contain
#   connection close? 
#
# Effects:
#
# - The connection state is set to closed for the source endpoint.
#

object frame = { ...
    object connection_close = { ...
        action handle(f:frame.connection_close,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle{
            
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.handshake -> established_handshake_keys(scid);
            require e = quic_packet_type.one_rtt -> established_1rtt_keys(scid);
            
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            if _generating  {
                # require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
            };
            require connected(scid) & connected_to(scid) = dcid;
            require f.reason_phrase_length = f.reason_phrase.end;
            if _generating {
                require e = quic_packet_type.one_rtt;
                require ~conn_closed(scid);
            }
            else {
                connection_closed := true;
            }; 
            conn_closed(scid) := true;
            call handle_transport_error(f.err_code);
	    ...
            # if _generating {
            #     call _finalize;
            # };
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

#
# #### APPLICATION_CLOSE event
#
# APPLICATION_CLOSE frames indicate to the peer that the connection is
# being closed.  It is unclear what this means operationally, but it
# seems reasonable to assume that the endpoint closing the connection
# will not send or receive any further data on the connection, so it
# is as if all the open streams are reset by this operation. In the
# standard, an APPLICATION_CLOSE frame is described as
# CONNECTION_CLOSE frame with a special tag field. Here, we use a
# distinct variant type to represent it.
#
# An application close frame can occur at any time. 
#
# Questions:
#
# - Are ACK frames still allowed after application close?
# - Are retransmissions allowed after application close?
# - When is a application close allowed?
#
# Requirements:
#
# (None)
#
# Effects:
#
# - The connection state is set to closed for the source endpoint.
#

object frame = { ...
    object application_close = { ...
        action handle(f:frame.application_close,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle{
            
            require connected(dcid) & connected_to(dcid) = scid;
            #require e ~= quic_packet_type.initial;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);
            #require e = quic_packet_type.handshake -> established_handshake_keys(scid);
            if _generating  {
                # require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
            };
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            require connected(scid) & connected_to(scid) = dcid;
            require f.reason_phrase_length = f.reason_phrase.end;
            conn_closed(scid) := true;
            call handle_transport_error(f.err_code);
            if ~_generating {
                connection_closed := true;
            };
	    ...
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}


#
# #### MAX_STREAM_DATA event
#
# MAX_STREAM_DATA frames set the limit on data bytes that the source endpoint is willing
# to receive for a given stream.
#
# Requirements
#
# - The stream must be open for receiving at the source endpoint [1].
#   (A MAX_STREAM_DATA frame can be sent for streams in the Recv state;)
#   (Receiving a MAX_STREAM_DATA frame for a locally-
#    initiated stream that has not yet been created MUST be treated as a
#    connection error of type STREAM_STATE_ERROR)

# Effects
# - If the given limit is greater than any previously set limit, then
#   the max stream data limit for the given stream is updated [2].
#

object frame = { ...
    object max_stream_data = { ...
        action handle(f:frame.max_stream_data,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle {
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);
             if _generating  {
# require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
};
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            require stream_seen(scid,f.id);
            if ~max_stream_data_set(scid,f.id) | f.pos > max_stream_data_val(scid,f.id) {
                max_stream_data_set(scid,f.id) := true;
                max_stream_data_val(scid,f.id) := f.pos;  # [2]
            }
	    ...
            #receiving_ready := true;
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

#
# #### stream_data_blocked event
#     | 0x15        | STREAM_DATA_BLOCKED  | Section 19.13 | __01    |
# stream_data_blocked frames indicate that sender wishes to send data on stream beyond current limit.
#
# Requirements
#
# - Connection must be established
#chris
# - The stream must be open for receiving at the destination endpoint [1]
#   An endpoint that receives a STREAM_DATA_BLOCKED frame for a send-only
#   stream MUST terminate the connection with error STREAM_STATE_ERROR.
#chris 
# Effects
#
# (None)

object frame = { ...
    object stream_data_blocked = { ...
        action handle(f:frame.stream_data_blocked,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle {
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);
             if _generating  {
# require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
};
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
	    ...
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

#
# #### data_blocked event
#     | 0x14        | DATA_BLOCKED         | Section 19.12 | __01    |
# data_blocked frames indicate that sender wishes to send data beyond current total limit
# for all streams.
#
# Requirements
#
# - Connection must be established
#
# Effects
#
# (None)

object frame = { ...
    object data_blocked = { ...
        action handle(f:frame.data_blocked,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle {
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);
             if _generating  {
# require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
};
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
	    ...
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}


#
# #### streams_blocked event
#     | 0x16 - 0x17 | STREAMS_BLOCKED      | Section 19.14 | __01    |
# streams_blocked frames indicate that sender wishes to open a stream beyond current limit
# on streams of a given kind.
#
# Requirements
#
# - Connection must be established
#chris
# A STREAMS_BLOCKED (by sender)
# frame of type 0x16 is used to indicate reaching the bidirectional
# stream limit, and a STREAMS_BLOCKED frame of type 0x17 is used to
# indicate reaching the unidirectional stream limit. => receiver should increase max_stream (TODO)
#chris
# Effects
#
# (None)

object frame = { ...
    object streams_blocked = { ...
        action handle(f:frame.streams_blocked,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle {
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
             if _generating  {
# require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
};
            #  some_max_streams := true;
            #  ms := f.id; #TODO not finished, should distinguish uni and bidi

	    ...
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

object frame = { ...
    object streams_blocked_bidi = { ...
        action handle(f:frame.streams_blocked_bidi,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle {
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
             if _generating  {
# require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
};
            #  some_max_streams := true;
            #  ms := f.id; #TODO not finished, should distinguish uni and bidi

	    ...
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}


#
# #### MAX_DATA EVENT
#     | 0x10        | MAX_DATA             | Section 19.9  | __01    |
# MAX_DATA frames set the limit on the total data bytes that the source endpoint is willing
# to receive for all streams combined.
#
# Requirements
#
# (None)
#
# Effects
# - If the given limit is greater than any previously set limit, then
#   the max data limit for the connection is updated [2].
#

object frame = { ...
    object max_data = { ...
        action handle(f:frame.max_data,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle {
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
             if _generating  {
# require ~need_sent_ack_eliciting_application_packet & ~need_sent_ack_eliciting_handshake_packet & ~need_sent_ack_eliciting_initial_packet;
};
            if ~max_data_set(scid) | f.pos > max_data_val(scid) {
                max_data_set(scid) := true;
                max_data_val(scid) := f.pos;  # [2]
            }
	    ...
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

#
# #### PING event
#     | 0x01        | PING                 | Section 19.2  | IH01    |
# PING frames contain no data and have no semantics. They can
# be used to keep a connection alive.
#

object frame = { ...
    object ping = { ...
        action handle(f:frame.ping,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle {
            require e = quic_packet_type.handshake -> established_handshake_keys(scid);
            require e = quic_packet_type.one_rtt -> established_1rtt_keys(scid);
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            if _generating {
                require ~(e = quic_packet_type.version_negociation) & ~(e = quic_packet_type.retry) & ~(e = quic_packet_type.zero_rtt);
                require need_sent_ack_eliciting_application_packet | need_sent_ack_eliciting_handshake_packet | need_sent_ack_eliciting_initial_packet;
                # require need_sent_ack_eliciting_application_packet -> e = quic_packet_type.one_rtt;
                # require need_sent_ack_eliciting_handshake_packet -> e = quic_packet_type.handshake;
                # require need_sent_ack_eliciting_initial_packet -> e = quic_packet_type.initial;
                # TODO investigate -> activate _generating event
                # require e = quic_packet_type.one_rtt;
                # require e = quic_packet_type.one_rtt -> need_sent_ack_eliciting_application_packet;
                # require e = quic_packet_type.handshake -> need_sent_ack_eliciting_handshake_packet;
                # require e = quic_packet_type.initial -> need_sent_ack_eliciting_initial_packet;
            };
            ...
            if _generating {
                need_sent_ack_eliciting_application_packet := false;
                need_sent_ack_eliciting_handshake_packet := false;
                need_sent_ack_eliciting_initial_packet := false;
            }
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

#
# #### unknown_frame event
#
# unknown_frame frames contain no data and have no semantics. They can
# be used to keep a connection alive.
#

object frame = { ...
    object unknown_frame = { ...
        action handle(f:frame.unknown_frame,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle {
            require connected(dcid) & connected_to(dcid) = scid;
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            #volontary at any time or not ?
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);            
            #require e ~= quic_packet_type.initial & e ~= quic_packet_type.handshake;
            #require e ~= quic_packet_type.retry & e ~= quic_packet_type.version_negociation;
            require ~conn_closed(scid); 
            ...
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

#
# #### PADDING event
#
# PADDING frames contain no data and have no semantics. They can
# be used to keep a connection alive.
#

#object frame = { ...
#    object padding = { ...
#        action handle(f:frame.padding,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
#	after handle {
#            call enqueue_frame(scid,f,e,true,seq_num);
#        }
#    }
#}

#
# #### HANDSHAKE_DONE  event
#
# HANDSHAKE_DONE  frames contain no data and have no semantics. They can
# be used to say handshake is done TODO
#

object frame = { ...
    object handshake_done = { ...
        action handle(f:frame.handshake_done,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle { 
            
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);  # [3]
            require e ~= quic_packet_type.initial;
	        require e ~= quic_packet_type.handshake;
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            require tls_handshake_finished;
                ...
            if _generating {
                handshake_done_send := true;
            }
            else {
                handshake_done_recv := true;
            };
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

#
# #### NEW_CONNECTION_ID event
#
# NEW_CONNECTION_ID frames are used to transmit additional cid's to the peer.
#chris
# Requirements
#
# - length field less than 1 and greater than 20 are invalid [1]
# - An endpoint that is sending packets with a zero-length Destination
#   Connection ID MUST treat receipt of a NEW_CONNECTION_ID frame as a
#   connection error of type PROTOCOL_VIOLATION. [2] 
# - Receipt of the same frame multiple times MUST NOT be treated as a connection
#   error. [3]
# - The Retire Prior To field MUST be less than or equal to the Sequence Number field [4]
#
# Effects
#
# - A receiver MUST ignore any Retire Prior To fields that do not increase the
#   largest received Retire Prior To value [5]
# - An endpoint that receives a NEW_CONNECTION_ID frame with a sequence
#   number smaller than the Retire Prior To field of a previously
#   received NEW_CONNECTION_ID frame MUST send a corresponding
#   RETIRE_CONNECTION_ID frame that retires the newly received connection
#   ID, unless it has already done so for that sequence number. [6] 
# -  An endpoint that selects a zero-length connection ID during the	
#    handshake cannot issue a new connection ID.  [7]
#
#chris

object frame = { ...
    object new_connection_id = { ...
        action handle(f:frame.new_connection_id,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle {
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);
            require num_queued_frames(scid) > 0 -> e = queued_level(scid); #Will change with implementing TODO
            #chris
            #require f.length >= 0x1 & f.length <= 0x14; #[1]

            require ~issued_zero_length_cid; # [7]

            if ~_generating { # For error test, carefull, should be specified in generating so
                require f.retire_prior_to <= f.seq_num; #[4]
            };
            require f.seq_num < max_rtp_num(scid) -> send_retire_cid(dcid); #[6] 
            #chris
            ...
            
	        cid_mapped(f.scid) := true;
                #cid_mapped(f.dcid) := true;
	        cid_to_aid(f.scid) := scid;
                #cid_to_aid(f.dcid) := dcid;
            seqnum_to_cid(scid,f.seq_num) := f.scid;
            last_cid_seq(scid) := f.seq_num; # ncid quant vuln
            #seqnum_to_cid(dcid,f.seq_num) := f.dcid;
            #call map_cids(scid,dcid); # ncid quant vuln ?
            #call map_cids(dcid,scid);
            count_newcid_frame(f.seq_num,f.retire_prior_to,f.length,f.scid,f.token) := count_newcid_frame(f.seq_num,f.retire_prior_to,f.length,f.scid,f.token) + 1;
            if  count_newcid_frame(f.seq_num,f.retire_prior_to,f.length,f.scid,f.token) = 1 {
                num_conn(dcid) := num_conn(dcid) + 1;
                var tp := trans_params(dcid);
                if ~_generating & active_connection_id_limit.is_set(tp)  {
                    require acti_coid_check(dcid,num_conn(dcid));
                };
            };
            
            #chris
            if (f.retire_prior_to > max_rtp_num(scid)) {
               max_rtp_num(scid) := f.retire_prior_to; #[5] 
            };
            #chris
            #Hamid
            if (f.seq_num > max_seq_num(scid)) {
                max_seq_num(scid) := f.seq_num;
            };
            #Hamid 
	        call enqueue_frame(scid,f,e,true,seq_num);
        }
    }
}

#
# #### RETIRE_CONNECTION_ID event
#
# RETIRE_CONNECTION_ID frames are used to tell the sender of the new connection id that the connection id will no longer be used.
#
# Requirements:
#  - Receipt of a RETIRE_CONNECTION_ID frame containing a sequence number
#    greater than any previously sent to the peer MUST be treated as a
#    connection error of type PROTOCOL_VIOLATION. [1]
#  - The sequence number specified in a RETIRE_CONNECTION_ID frame MUST
#    NOT refer to the Destination Connection ID field of the packet in
#    which the frame is contained.  The peer MAY treat this as a
#    connection error of type PROTOCOL_VIOLATION. [2]
#  - An endpoint that is sending packets with a zero-length Destination
#    Connection ID MUST treat receipt of a NEW_CONNECTION_ID frame as a
#    connection error of type PROTOCOL_VIOLATION. [3] TODO
object frame = { ...
    object retire_connection_id = { ...
        action handle(f:frame.retire_connection_id,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	    around handle {require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);
            # Will change with implementing TODO
            require num_queued_frames(scid) > 0 -> e = queued_level(scid); 
            # TODO remember the highest sequence number that was sent
            #Hamid
            require f.seq_num <= max_seq_num(dcid); #[1]
            #Hamid 
            # TODO specify that you cannot retire the connection id of the current packet
            #
	        ... 
	        cid_mapped(seqnum_to_cid(dcid, f.seq_num)) := false; #[2]
            count_rcid_frame(f.seq_num) := count_rcid_frame(f.seq_num) + 1;
            if  count_rcid_frame(f.seq_num) = 1 {
                num_conn(dcid) := num_conn(dcid) - 1;
            };
            #Hamid
            # the connection id seqnum_to_cid is being retired, append it to an array and iterate over the array in packet
            #Hamid
	        call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}


#
# #### PATH_CHALLENGE event
#
# Path challenge frames are used to request verification of ownership
# of an endpoint by a peer.
#
# A pending path challenge value me not be retransmitted [1]. That is,
# according to quic-transport-draft-18, section 13.2:
#
#     PATH_CHALLENGE frames include a different payload each time they are sent.
#
# Notice that we do allow a PATH_CHALLENGE payload to be re-used after
# it is responded to, on the theory that this is a new challenge and
# not a retransmission, however, it is unclear that this is the
# intention of the standard.

object frame = { ...
    object path_challenge = { ...
        action handle(f:frame.path_challenge,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle {require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);
            require handshake_done_recv | handshake_done_send;
            # if _generating {
            #     require handshake_done_send;
            # } else {
            #     require handshake_done_recv;
            # };
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            require f.data.end = 8;
            require ~path_challenge_pending(dcid,f.data);
            ...
            path_challenge_pending(dcid,f.data) := true;
            call enqueue_frame(scid,f,e,true,seq_num);
        }
    }
}

#
# #### PATH_RESPONSE event
#
# PATH_RESPONSE frames are used to verify ownership of an endpoint in
# response to a path_challenge frame.

object frame = { ...
    object path_response = { ...
        action handle(f:frame.path_response,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle { 
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);
            if _generating {
                require ~path_challenge_sent(dcid); # avoid auto response
            };
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            require f.data.end = 8;
            require path_challenge_pending(scid,f.data);
            ...
            path_challenge_pending(scid,f.data) := false;
            path_validated := true; # TODO
            path_validated_pkt_num := seq_num;
            call enqueue_frame(scid,f,e,true,seq_num);
        }
    }
}

#
# #### NEW_TOKEN event
#
# NEW_TOKEN frames are sent by the server to provide the client a
# token for establishing a new connection.

object frame = { ...
    object new_token = { ...
        action handle(f:frame.new_token,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)
	around handle {
            # TODO for now we save token in clinet & server
            require connected(dcid) & connected_to(dcid) = scid;
            require e = quic_packet_type.one_rtt & established_1rtt_keys(scid);
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            if ~_generating {
                require ~is_client(scid);
            };
            ...

            call tls_api.upper.save_token(f.data);
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}

include quic_ack_frequency_extension

object frame = {
    ...
    object malicious_frame = {
        ...
        action handle(f:frame.malicious_frame,scid:cid,dcid:cid,e:quic_packet_type,seq_num:pkt_num)

	around handle {
            require tls_handshake_finished;

            require connected(dcid) & connected_to(dcid) = scid;
            require (e = quic_packet_type.one_rtt) & established_1rtt_keys(scid); # | e = quic_packet_type.zero_rtt  | e = quic_packet_type.zero_rtt & established_0rtt_keys(scid) 
            require num_queued_frames(scid) > 0 -> e = queued_level(scid);
            require ~conn_closed(scid);  # [8]
            require conn_seen(scid);  # [9]
	        ...
            call enqueue_frame(scid,f,e,false,seq_num);
        }
    }
}



# Procedures
# ----------

# Frame events cause frames to be enqueued for transmission in a
# packet. This action enqueues a frame.
#
# Effects:
#
# - Appends frame to the frame queue for the given source endpoint and cid.
# - Updates auxiliary functions `num_queued_frames` and `queued_level`.
#
# Note: the auxilary functions contain redundant information that is useful for
# specifying packet events. By encoding history information in this way, we make
# it easier for constraint solvers to construct tests.
# 
# The argument probing indicates that the frame is a probing frame, according to [9.1]
# of the transport document( as of draft 23)
action enqueue_frame(scid:cid, f:frame, e:quic_packet_type, probing:bool, seq: pkt_num) = {
    queued_frames(scid) := queued_frames(scid).append(f);
    num_queued_frames(scid) := queued_frames(scid).end;
    queued_level(scid) := e;
    if ~probing {
        queued_non_probing(scid) := true;
    };
    if ~(f isa frame.ack){ #& ~(f isa frame.padding){
        queued_non_ack(scid) := true;
    };
    if  f isa frame.path_challenge {
        queued_challenge(scid) := true;
    };
    if (f isa frame.connection_close) | (f isa frame.application_close) {
        queued_close(scid) := true;
    };
    #Hamid
    if ~(f isa frame.ack) & ~(f isa frame.connection_close) { #& ~(f isa frame.padding){ & ~queued_ack_eliciting(scid)
	    queued_ack_eliciting(scid) := true;
        if _generating {
            queued_ack_eliciting_pkt(seqnum_to_streampos(last_pkt_num(scid,e) + 0x1)) := true;  # TODO add client, vs server
            # call show_seqnum(seq);
            # call show_seqnum(last_pkt_num(scid,e) + 0x1);
            # call show_seqnum_to_streampos(seqnum_to_streampos(seq));
            # call show_seqnum_to_streampos(seqnum_to_streampos(last_pkt_num(scid,e) + 0x1));
        };
    }
    #Hamid
}

action enqueue_frame_rtt(scid:cid, f:frame, e:quic_packet_type, probing:bool) = {
    queued_frames_rtt(scid) := queued_frames_rtt(scid).append(f);
    num_queued_frames_rtt(scid) := queued_frames_rtt(scid).end;
    queued_level_rtt(scid) := e;
    if ~(f isa frame.ack){ #& ~(f isa frame.padding){
        queued_non_ack(scid) := true;
    };
}

#
# The maximum number of bytes that may be transmitted to a give aid on a given stream is
# computed by the following procedure. The number of bytes is the maximum of:
#
# - The receiver's `initial_max_stream_data_uni` transport parameter, if the stream
#   is unidirectional.
#
# - The receiver's `initial_max_stream_data_bidi_local` transport parameter, if the stream
#   is bidirectional and is initiated by the receiver.
#
# - The receiver's `initial_max_stream_data_bidi_remote` transport parameter, if the stream
#   is bidirectional and is initiated by the sender.
#
# An alternative maximum lenght is given by the maximum total data
# limit for the receiving aid.  That is, it can be no greater than the
# current stream length plus the maximum total additional
# bytes allowed on all streams.

# An aid is the initiator of a stream if its protocol role (client or
# server) matches the role of the stream id.

# TODO manage NCI
action stream_max_data(dcid:cid,id:stream_id, e:quic_packet_type) returns (max:stream_pos) = {
    var tp := trans_params(dcid);
    max := 0;
    if get_stream_kind(id) = unidir {
        if initial_max_stream_data_uni.is_set(tp) {
            max := initial_max_stream_data_uni.value(trans_params(dcid)).stream_pos_32
        }
    } else {
        if is_client(dcid) <-> get_stream_role(id) = role.client {
            if initial_max_stream_data_bidi_local.is_set(tp) {
                max := initial_max_stream_data_bidi_local.value(trans_params(dcid)).stream_pos_32
            }
        } else {
            if initial_max_stream_data_bidi_remote.is_set(tp) {
                max := initial_max_stream_data_bidi_remote.value(trans_params(dcid)).stream_pos_32
            }
        }
    };
    if max_stream_data_set(dcid,id) {
        var msdv := max_stream_data_val(dcid,id); 
        max := msdv if msdv > max else max;
    };
    var alt_max := max_additional_data(dcid) + stream_length(dcid,id);
    max := alt_max if alt_max < max else max;
    if (zero_rtt_allowed & ~zero_rtt_sent) | (e = quic_packet_type.zero_rtt) { # TODO
        max := 1000;
    };
}

#
# Whether a given stream can be opened by a peer of a given aid is
# computed by the following procedure. The id of a remotely initiated
# stream must be less than the maximum of:
#
# - Four times the aid's `initial_max_stream_id_uni` transport
#   parameter, if the stream is unidirectional [3].
#
# - Four times the aid's `initial_max_stream_id_bidi` transport
#   parameter, if the stream is bidirectional [4].
#
# - The stream id parameter of any MAX_STREAM_ID frame sent by the
#   aid, if it is of the same kind.

action stream_id_allowed(dcid:cid,id:stream_id,e: quic_packet_type) returns (ok:bool) = {
    ok := false;
    var tp := trans_params(dcid);
    var kind := get_stream_kind(id);
    var idhi : stream_id := id / 4;

    # if (zero_rtt_allowed & ~zero_rtt_sent) | e = quic_packet_type.zero_rtt { # TODO
    #     ok := idhi <= 20;
    # }
    # else 
    if ~(is_client(dcid) <-> get_stream_role(id) = role.client) {  # if stream remotely initiated
        if kind = unidir {
            if initial_max_stream_id_uni.is_set(tp) {
                ok := idhi < (initial_max_stream_id_uni.value(tp).stream_id_16)  # [3]
            }
        } else {
            if initial_max_stream_id_bidi.is_set(tp) {
                ok := idhi < (initial_max_stream_id_bidi.value(tp).stream_id_16);  # [4]
            }
        };
        ok := ok | max_stream_set(dcid,kind) & idhi < max_stream(dcid,kind);
    }
    else  {
        ok := stream_seen(dcid, id); # TODO: locally initiated streams must have been seen!
    }
}

action stream_id_to_cid(bytes:stream_id) returns (val:cid) = {
    <<<
    val.val = 0;
    for (unsigned i = 0; i < bytes.size(); i++)
        val.val = (val.val << 8) + bytes[i];
    >>>
}

action cid_to_stream_id(c:cid,len:cid_length) returns(res:stream_id) = {
    <<<
    res.resize(len);
    for (unsigned i = 0; i < len; i++) {
        res[len-i-1] = 0xff & (c.val >> (i * 8));
    }
    >>>
}


# The procedure computes the maximum number of additional bytes that a given
# destination aid can receive, based on the `initial_max_data` transport parameter
# and the highest position sent by the aid in a max data frame. This is computed as the
# maximum of these two values, less the total data already received.

action max_additional_data(dcid:cid) returns (max:stream_pos) = {
    var tp := trans_params(dcid);
    max := 0;
    if initial_max_data.is_set(tp) {
        max := initial_max_data.value(tp).stream_pos_32
    };
    if max_data_set(dcid) {
        var smax := max_data_val(dcid);
        max := smax if smax > max else max
    };
    max := max - conn_total_data(dcid);  # note the substraction is saturating
}



action scale_ack_delay(delay:milliseconds, ack_delay_exponent:microsecs) returns (scaled:microseconds) = {
   <<<
    if (ack_delay_exponent == 0) {
        ack_delay_exponent = 3;
    }
    std::cerr << "ack_delay_exponent " << ack_delay_exponent << "\n";
    std::cerr << "delay " << delay << "\n";
    std::cerr << "scaled " << delay * pow(ack_delay_exponent,2) << "\n";
    scaled = delay * pow(ack_delay_exponent,2);
   >>> 
}


# action unscale_ack_delay(delay:milliseconds, ack_delay_exponent:microsecs) returns (scaled:microseconds) = {
#    <<<

#    >>> 
# }

# Check that the number of connection id proposed is not higher than active_connection_id_limit

action acti_coid_check(scid:cid,count:stream_pos) returns (ok:bool) = {
    ok := true;
    var max : stream_pos := 0;
    var tp := trans_params(scid);
    if active_connection_id_limit.is_set(tp) {
        max := active_connection_id_limit.value(tp).stream_pos_32;
        ok := count <= max;
    };
}

import action show_ack_delay(t:microseconds)
import action show_pkt_num(p:pkt_num)
import action show_newly_acked(s:bool)
import action show_seqnum_to_streampos(p:stream_pos)
import action show_seqnum(p:pkt_num)
```

- the shim components that will be used to connect the protocol to the network.
Example for QUIC can be found at: https://github.com/ElNiak/Protocols-Ivy/tree/master/protocol-testing/quic/quic_shims/

- components for the different protocol endpoints.
Example for QUIC can be found at: https://github.com/ElNiak/Protocols-Ivy/tree/master/protocol-testing/quic/quic_entities

- components for the endpoints behavior.
Example for QUIC can be found at: https://github.com/ElNiak/Protocols-Ivy/tree/master/protocol-testing/quic/quic_entities_behavior

- the protocol's serialization and deserialization functions.
Example for QUIC can be found at: https://github.com/ElNiak/Protocols-Ivy/tree/master/protocol-testing/quic/quic_utils/
Here is an example of deserialization for long and short packet and their allowed frames:
```ivy
#lang ivy1.7

# a fake deserializer for quic

object quic_deser = {}

<<< member

    class `quic_deser`;

>>>

<<< impl

   typedef struct transport_error_struct {
        const char *name;
        int value;
    } *transport_error_struct_ptr;

    struct transport_error_map : hash_space::hash_map<std::string,int> {};
    
    struct transport_error_struct transport_error_codes[17] = {
        {"no_error",0x0},
        {"internal_error",0x1},
        {"server_busy",0x2},
        {"flow_control_error",0x3},
        {"stream_limit_error",0x4},
        {"stream_state_error",0x5},
        {"final_size_error",0x6},
        {"frame_encoding_error",0x7},
        {"transport_parameter_error",0x8},
        {"connection_id_limit_error",0x9},
        {"protocol_violation",0xa},
        {"invalid_token",0xb},
        {"application_error",0xc},
        {"crypto_buffer_exceeded",0xd},
        {"crypto_error",-1},
       {0,0}
    };
    transport_error_map transport_error_codes_map;

    void transport_error_name_map(transport_error_struct *vals, transport_error_map &map) {
        while (vals->name) {
            map[vals->name] = vals->value;
            vals++;
        }
    }

    #define QUIC_DESER_FAKE_CHECKSUM_LENGTH 0
    //TODO
    #if defined(IS_NOT_DOCKER) 
        #include "/home/user/Documents/QUIC-RFC9000/QUIC-Ivy-Attacker/doc/examples/quic/quic_utils/quic_ser_deser.h"
    #else 
         #include "/PFV/QUIC-Ivy-Attacker/protocol-testing/quic/quic_utils/quic_ser_deser.h"
    #endif
    int scid_h = 8;
    int dcid_h = 8;

    class `quic_deser` : public ivy_binary_deser_128 {
    //class `quic_deser` : public ivy_binary_deser {
        enum {quic_s_init,
              quic_s_type,
              quic_s_version,
	          quic_s_dcil,
	          quic_s_scil,
              quic_s_dcid,
              quic_s_scid,
              quic_s_retry_token_length,
              quic_s_retry_token,
	          quic_s_payload_length,
              quic_s_pkt_num,
              quic_s_payload,
              quic_stream_id,
              quic_stream_off,
              quic_stream_len,
              quic_stream_fin,
              quic_stream_offset,
              quic_stream_length,
              quic_stream_data,
              quic_crypto_offset,
              quic_crypto_length,
              quic_crypto_data,
              quic_ack_largest,
              quic_ack_delay,
              quic_ack_block_count,
              quic_ack_gap,
              quic_ack_block,
              quic_reset_stream_id,
              quic_reset_err_code,
              quic_reset_final_offset,
              quic_stop_sending_id,
              quic_stop_sending_err_code,
              quic_connection_close_err_code,
              quic_connection_close_frame_type,
              quic_connection_close_reason_length,
              quic_connection_close_reason,
              quic_application_close_err_code,
              quic_max_stream_data_id,
              quic_new_connection_id_length,
              quic_new_connection_id_seq_num,
              quic_new_connection_id_retire_prior_to,
              quic_new_connection_id_scid,
              quic_new_connection_id_token,
              quic_path_challenge_data,
              quic_retire_connection_id_seq_num,
              quic_handshake_done,
              quic_immediate_ack,
              quic_ack_frequency, //seq_num
              quic_ack_frequency_ack_eliciting_threshold,
              quic_ack_frequency_request_max_ack_delay,
              quic_ack_frequency_reordering_threshold,
              quic_padding,
              quic_unknow,
              quic_ping,
              quic_s_done} state;
        bool long_format;
        char hdr_type;
        int dcil_long;
        int dcil;
        int scil;
        long frame_type;
        int data_remaining;
        int128_t ack_blocks_expected;
        int128_t ack_block_count;
        //long long ack_blocks_expected;
        //long long ack_block_count;
        int payload_length;
        int fence;
	    bool have_scid = false;
        bool ecn = false;
        int token_length;
        int token_count = 0;
        int token_len = 0;

    
    public:
        quic_deser(const std::vector<char> &inp) : ivy_binary_deser_128(inp),state(quic_s_init) {
        //quic_deser(const std::vector<char> &inp) : ivy_binary_deser(inp),state(quic_s_init) {
            // pos = 42; // skip 42 bytes of IP and UDP header
            fence = 0;
        }
        virtual void  get(int128_t &res) {
        //virtual void  get(long long &res) {
            switch (state) {
            case quic_s_init:
            {
                getn(res,1);
                long_format = (res & 0x80) ? true : false;
                //0x7f is 0111 1111 in binary. This means the lower 7 bits of res are significant.
                //0x30    0011 0000
                hdr_type = res & 0x7f; //0x7f;
                //This is then shifted by 4 so that only the original 0xxx 0000 (3) bits are significant.
                res = long_format ? ((hdr_type & 0x30) >> 4) : 3;
                state = quic_s_version;
            }
            break;
            case quic_s_version:
            {
                if (long_format) {
                    ivy_binary_deser_128::getn(res,4);
                    //ivy_binary_deser::getn(res,4);
	        	}
                else
                    res = 0;
                state = quic_s_dcid;
            }
            break;
            case quic_s_dcid:
            {   
                if (long_format) {
                    int128_t cil;
                    //long long cil;
                    getn(cil,1);
                    std::cerr << "dstID size " << cil << "\n";
                    dcil = cil;
                    dcid_h = cil;
                } else {
                    dcil = dcid_h; //dcil_long
                }
		        getn(res,(dcil));
                std::cerr << "dstID res " << res << "\n";
                state = quic_s_scid;
            }
            break;
            case quic_s_scid:
            {
                if (long_format) {
                    int128_t cil;
                    //long long cil;
                    getn(cil,1);
                    std::cerr << "sourceID size " << cil << "\n";  
                    if(cil > 0)
                        have_scid = true;
                    else 
                        have_scid = false;
                    scil = cil;
                    scid_h = cil;
                } else {
                    scil = 0;
                }
                getn(res,scil);
                /*if(scil != 8) { //tricks
                tls_field_bytes_map["scid"] = scil;
                }*/
                std::cerr << "sourceID res " << res << "\n";
                int128_t len;
                //long long len;
                if (long_format & ((hdr_type & 0x30) == 0x00)){
                    get_var_int(len);
		        }
                else len = 0;
                data_remaining = len;
		        std::cerr << "sourceID data_remaining " << data_remaining << "\n";
                state = quic_s_retry_token;
            }
            break;
            case quic_s_pkt_num:
            {
                fence = 0;
                if (payload_length > 0) {
                    fence = pos + payload_length - QUIC_DESER_FAKE_CHECKSUM_LENGTH;
                } else {
                    fence = inp.size() - QUIC_DESER_FAKE_CHECKSUM_LENGTH;
                }
                get_pkt_num(res);
                state = quic_s_payload;
            }
            break;
            case quic_stream_off:
            {
                res = (0x04 & frame_type) ? 1 : 0;
                state = quic_stream_len;
            }
            break;
            case quic_stream_len:
            {
                res = (0x02 & frame_type) ? 1 : 0;
                state = quic_stream_fin;
            }
            break;
            case quic_stream_fin:
            {
                res = (0x01 & frame_type) ? 1 : 0;
                state = quic_stream_id;
            }
            break;
            case quic_stream_id:
            {
                get_var_int(res);
                state = quic_stream_offset;
            }
            break;
            case quic_stream_offset:
            {
                if (0x04 & frame_type)
                    get_var_int(res);
                else res = 0;
                state = quic_stream_length;
            }
            break;
            case quic_stream_length:
            {
                if (0x02 & frame_type)
                    get_var_int(res);
                else {
                    res = fence - pos;
                }
                data_remaining = res;
                state = quic_stream_data;
            }
            break;
            case quic_crypto_offset:
            {
                get_var_int(res);
                state = quic_crypto_length;
            }
            break;
            case quic_crypto_length:
            {
                get_var_int(res);
                data_remaining = res;
                state = quic_crypto_data;
                std::cerr << "quic_crypto_length \n";
            }
            break;
            case quic_stream_data:
            case quic_crypto_data:
            case quic_path_challenge_data:
            case quic_connection_close_reason:
            case quic_padding:
            case quic_ping:
            case quic_unknow:
            case quic_handshake_done: // TODO ?
            case quic_immediate_ack:
            case quic_s_retry_token:
            {
		        //std::cerr << "sourceID quic_s_retry_token 1 " <<  std::hex <<  res << "\n";
                ivy_binary_deser_128::getn(res,1);
                //ivy_binary_deser::getn(res,1);
                /*if(const char* env_p3 = std::getenv("RETRY_TOKEN_LENGTH")) {
                        std::cerr << "RETRY_TOKEN_LENGTH " << env_p3 << "\n";
                        token_len = atoi(env_p3);
                    }
                    if(token_count == 0)
                        token_len = token_length;

                    std::cerr << "token_count " << token_count << "\n";
                    
                    if(token_count < token_len){
                        getn(res,1);    
                        token_count += 1;
                        if(token_count == token_len)
                        state = quic_s_pkt_num;
                        else
                        state = quic_s_retry_token; //useless ?
                    }
                    else 
                        state = quic_s_pkt_num;*/
		       // std::cerr << "sourceID quic_s_retry_token 2" << std::hex << res << "\n";
            }
            break;
            case quic_ack_largest:
            {
                get_var_int(res);
                state = quic_ack_delay;
            }
            break;
            case quic_ack_delay:
            {
                get_var_int(res);
                state = quic_ack_block_count;
            }
            break;
            case quic_ack_gap:
            {
                if (ack_block_count == 0)
                    res = 0; // first ack block has no gap
                else
                    get_var_int(res);
                state = quic_ack_block;
            }
            break;
            case quic_ack_block:
            {
                get_var_int(res);
                state = quic_ack_gap;
                ack_block_count++;
            }
            break;
            case quic_reset_stream_id:
            {
                get_var_int(res);
                state = quic_reset_err_code;
            }
            break;
            case quic_reset_err_code:
            {
                get_var_int(res);
                state = quic_reset_final_offset;
            }
            break;
            case quic_reset_final_offset:
            {
                get_var_int(res);
            }
            break;
            case quic_stop_sending_id:
            {
                get_var_int(res);
                state = quic_stop_sending_err_code;
            }
            break;
            case quic_stop_sending_err_code:
            {
                get_var_int(res);
            }
            break;
            case quic_connection_close_err_code:
            {
                get_var_int(res);
                state = quic_connection_close_frame_type;
            }
            break;
            case quic_connection_close_frame_type:
            {
                get_var_int(res);
                state = quic_connection_close_reason_length;
            }
            break;
            case quic_connection_close_reason_length:
            {
                get_var_int(res);
                data_remaining = res;
                state = quic_connection_close_reason;
            }
            break;
            case quic_application_close_err_code:
            {
                get_var_int(res);
                state = quic_connection_close_reason_length;
            }
            break;
            case quic_max_stream_data_id:
            {
                get_var_int(res);
                state = quic_reset_final_offset;
            }
            break;
            case quic_new_connection_id_length:
            {
                getn(res,1);
                scil = res;
                state = quic_new_connection_id_scid;
            }
            break;
            case quic_new_connection_id_seq_num:
            {
                get_var_int(res);
                state = quic_new_connection_id_retire_prior_to;
            }
            break;
            case quic_new_connection_id_retire_prior_to:
            {
                get_var_int(res);
                state = quic_new_connection_id_length;
            }
            break;
            case quic_new_connection_id_scid:
            {
                getn(res,scil);
                state = quic_new_connection_id_token;
            }
            break;
            case quic_new_connection_id_token:
            {
                getn(res,16);
            }
            break;
            case quic_retire_connection_id_seq_num:
            {
                get_var_int(res);
            }
            break;
            case quic_ack_frequency: //TODO
            {
                get_var_int(res);
		        std::cerr << "deser: quic_ack_frequency   = quic_ack_frequency\n"; 
                state = quic_ack_frequency_ack_eliciting_threshold;
            }
            break;
            case quic_ack_frequency_ack_eliciting_threshold: 
            {
                get_var_int(res);
		        std::cerr << "deser: quic_ack_frequency   = quic_ack_frequency_ack_eliciting_threshold\n"; 
                state = quic_ack_frequency_request_max_ack_delay;
            }
            break;
            case quic_ack_frequency_request_max_ack_delay: 
            {
                get_var_int(res);
		        std::cerr << "deser: quic_ack_frequency   = quic_ack_frequency_request_max_ack_delay\n"; 
                state = quic_ack_frequency_reordering_threshold;
            }
            break;
            case quic_ack_frequency_reordering_threshold:
            {
		        std::cerr << "deser: quic_ack_frequency   = quic_ack_frequency_reordering_threshold\n"; 
                //getn(res,1);
                get_var_int(res);
            }
            break;
            default:
                std::cerr << "quic_deser 3\n";  
                throw deser_err();
            }
        }

        void get_var_int(int128_t &res) {
        //void get_var_int(long long &res) {
            static int lens[4] = {0,1,3,7};
            int128_t lobyte;
            ivy_binary_deser_128::getn(lobyte,1);
            //long long lobyte;
            //ivy_binary_deser::getn(lobyte,1);
            int bytes = lens[(lobyte & 0xc0) >> 6];
            ivy_binary_deser_128::getn(res,bytes);
            //ivy_binary_deser::getn(res,bytes);
            res |= (lobyte & 0x3f) << (bytes << 3);
        }

        void get_pkt_num(int128_t &res) {
            ivy_binary_deser_128::getn(res,(hdr_type & 3)+1);
       // void get_pkt_num(long long &res) {
       //     ivy_binary_deser::getn(res,(hdr_type & 3)+1);
            return;
            static int lens[4] = {0,0,1,3};
            int128_t lobyte;
            ivy_binary_deser_128::getn(lobyte,1);
            //long long lobyte;
            //ivy_binary_deser::getn(lobyte,1);
            int bytes = lens[(lobyte & 0xc0) >> 6];
            if (bytes == 0) {
                res = lobyte;
                return;
            }
            ivy_binary_deser_128::getn(res,bytes);
            //ivy_binary_deser::getn(res,bytes);
            res |= (lobyte & 0x3f) << (bytes << 3);
        }

        virtual int open_tag(const std::vector<std::string> &tags) {
            if (state == quic_s_payload) {
                int128_t ft;
                ivy_binary_deser_128::getn(ft,1); // could be bigger
                //long long ft;
                //ivy_binary_deser::getn(ft,1); // could be bigger

                /* 
                TODO we should get varint and then parse in consequence like in tls_deser_ser 
                */

                frame_type = ft;
                std::cerr << "recv frame_type = " << frame_type << "\n";
                if (frame_type == 0x01) {
                    state = quic_ping;
                    return 0;
                }
                if (frame_type == 0x02) { //JF
                    ecn = false;
                    state = quic_ack_largest;
                    return 1;
                }
                if (frame_type == 0x03) {
                    ecn = true;
                    state = quic_ack_largest;
                    return 2;
                }
                if (frame_type == 0x04) {
                    state = quic_reset_stream_id;
                    return 3;
                }
                if (frame_type == 0x05) {
                    state = quic_stop_sending_id;  // stream_blocked equivalent to this
                    return 4;
                }
                if (frame_type == 0x06) {
                    state = quic_crypto_offset;
                    return 5;
                }
                if (frame_type == 0x07) {  // new token frame
                    state = quic_crypto_length;  // new token equivalent to this
                    return 6;
                }
                if (frame_type >= 0x08 && frame_type <= 0x0f) {
                    state = quic_stream_off;
                    return 7;
                }
                if (frame_type == 0x10) {  // new token frame
                    state = quic_reset_final_offset;  // max_data equivalent to this
                    return 8;
                }
                if (frame_type == 0x11) {
                    state = quic_max_stream_data_id;
                    return 9;
                }
                if (frame_type == 0x12) { //JF
                    state = quic_reset_stream_id; // max_stream_id state equivalent to this
                    return 10;
                }
                if (frame_type == 0x13) { 
                    state = quic_reset_stream_id; // max_stream_id state equivalent to this
                    return 11;
                }
                if (frame_type == 0x14) {
                    state = quic_reset_final_offset;  // blocked equivalent to this
                    return 12;
                }
                if (frame_type == 0x15) {
                    state = quic_max_stream_data_id;  // stream_blocked equivalent to this
                    return 13;
                }
                if (frame_type == 0x16) {
                    state = quic_reset_final_offset;
                    return 14;
                }
                if (frame_type == 0x17) {
                    state = quic_reset_final_offset;
                    return 15;
                }
                if (frame_type == 0x18) {
                    state = quic_new_connection_id_seq_num;
                    return 16;
                }
                if (frame_type == 0x19) {
                    state = quic_retire_connection_id_seq_num;
                    return 17;
                }
                if (frame_type == 0x1a) {
                    data_remaining = 8;
                    state = quic_path_challenge_data;
                    return 18;
                }
                if (frame_type == 0x1b) {
                    data_remaining = 8;
                    state = quic_path_challenge_data;
                    return 19;
                }
                if (frame_type == 0x1c) {
                    state = quic_connection_close_err_code;
                    return 20;
                }
                if (frame_type == 0x1d) {
                    state = quic_application_close_err_code;
                    return 21;
                }
                if (frame_type == 0x1e) {
                    state = quic_handshake_done;
                    return 22;
                }
                if (frame_type == 0x40) {
                    ft = 0;
                    //ivy_binary_deser::getn(ft,1); // could be bigger
                    ivy_binary_deser_128::getn(ft,1); // could be bigger
                    frame_type = ft;
                    if (frame_type == 0xAF) { //0x40af
                        state = quic_ack_frequency;
                        return 23;
                    }
                    if (frame_type == 0xAC) { //0x40af
                        state = quic_immediate_ack;
                        return 24;
                    }
                    if (frame_type == 0x42) {
                        state = quic_unknow;
                        return 25;
                    }
                }
                /*if (frame_type == 0x00) {
                    state = quic_padding;
                    return 25;
                }*/
                std::cerr << "saw tag " << ft << "\n";  
            }
            std::cerr << "state          = " << state << "\n";  
            std::cerr << "quic_s_payload = " << quic_s_payload << "\n";
            std::cerr << "quic_s_payload == " << (quic_s_payload == state) << "\n";
            std::cerr << "quic_deser 2\n";  
            throw deser_err();
        }

        virtual bool open_list_elem() {
            if (state == quic_s_payload) {
                // We must use/take in count the padding frame since Picoquic client sometimes send packet
                // only with 1 padding frame which make fails the requirement saying that a 
                // packet cannot be empty
               while ((fence == 0 || pos < fence) && more(1) && inp[pos] == 0)
                   pos++;  // skip padding frames
               return (fence == 0 || pos < fence) && more(1);
            }
            if (state == quic_ack_gap) {
                return ack_block_count < ack_blocks_expected;
            }
            if (state == quic_stream_data)
                return data_remaining-- > 0;
            if (state == quic_connection_close_reason)
                return data_remaining-- > 0;
            if (state == quic_s_retry_token)
                return data_remaining-- > 0;
            //if (state == quic_s_retry_token) {
                // We must use/take in count the padding frame since Picoquic client sometimes send packet
                // only with 1 padding frame which make fails the requirement saying that a 
                // packet cannot be empty
               /*while ((fence == 0 || pos < fence) && more(1) && inp[pos] == 0)
                   pos++;  // skip padding frames
                */
               //return token_count < token_len; //(fence == 0 || pos < fence) && more(1);
            //}
            if (state == quic_crypto_data)
                return data_remaining-- > 0;
            if (state == quic_path_challenge_data)
                return data_remaining-- > 0;
            if (state == quic_s_init)
                return more(1);

            //TODO
            if (state == quic_ack_frequency_reordering_threshold)
                    return data_remaining-- > 0;
            if (state == quic_ack_frequency)
                    return data_remaining-- > 0;
            if (state == quic_ack_frequency_request_max_ack_delay)
                    return data_remaining-- > 0;
            if (state == quic_ack_frequency_ack_eliciting_threshold)
                    return data_remaining-- > 0;


            std::cerr << "quic_deser 1\n";  
            throw deser_err();
        }

        void open_list() {
            if (state == quic_ack_block_count) {
                get_var_int(ack_blocks_expected);
                ack_blocks_expected++;  // block count doesn't include first
                ack_block_count = 0;
                state = quic_ack_gap;
            }
        }
        void close_list() {
            if (state == quic_s_payload) {
                state = quic_s_init;
                pos += QUIC_DESER_FAKE_CHECKSUM_LENGTH; // skip the fake checksum
            }
            if (state == quic_s_retry_token) {
                int128_t len;
                //long long len;
                if (long_format) {
                    get_var_int(len);
                } else {
                    len = 0;
                }
                payload_length = len;
                state = quic_s_pkt_num;
            }
        }
        void close_list_elem() {}

        virtual void close_tag() {
            state = quic_s_payload;
        }

        ~quic_deser(){}
    };

>>>


<<< init
    
    transport_error_name_map(transport_error_codes,transport_error_codes_map);

>>>
```
And here is an example of serialization for long and short packet and their allowed frames:
```ivy
#lang ivy1.7

# a fake serializer for quic

object quic_ser = {}

<<< member

    class `quic_ser`;

>>>

<<< impl

    //TODO
    //TODO
    #if defined(IS_NOT_DOCKER) 
        #include "/home/user/Documents/QUIC-RFC9000/QUIC-Ivy-Attacker/doc/examples/quic/quic_utils/quic_ser_deser.h"
    #else 
         #include "/PFV/QUIC-Ivy-Attacker/protocol-testing/quic/quic_utils/quic_ser_deser.h"
    #endif
    
    class `quic_ser` : public ivy_binary_ser_128 {
    //class `quic_ser` : public ivy_binary_ser {
        enum {quic_s_init,
              quic_s_version,
	          quic_s_dcil,
	          quic_s_scil,
              quic_s_dcid,
              quic_s_scid,
              quic_s_retry_token_length,
              quic_s_retry_token,
	          quic_s_payload_length,
              quic_s_pkt_num,
              quic_s_payload,
              quic_stream_id,
              quic_stream_off,
              quic_stream_len,
              quic_stream_fin,
              quic_stream_offset,
              quic_stream_length,
              quic_stream_data,
              quic_crypto_offset,
              quic_crypto_length,
              quic_crypto_data,
              quic_ack_largest,
              quic_ack_delay,
              quic_ack_block_count,
              quic_ack_gap,
              quic_ack_block,
              quic_reset_stream_id,
              quic_reset_err_code,
              quic_reset_final_offset,
              quic_stop_sending_id,
              quic_stop_sending_err_code,
              quic_connection_close_err_code,
              quic_connection_close_frame_type,
              quic_connection_close_reason_length,
              quic_connection_close_reason,
              quic_application_close_err_code,
              quic_max_stream_data_id,
              quic_path_challenge_data,
              quic_new_connection_id_length,
              quic_new_connection_id_seq_num,
              quic_new_connection_id_retire_prior_to,
              quic_new_connection_id_scid,
              quic_new_connection_id_token,
              quic_retire_connection_id_seq_num,
              quic_handshake_done,
              quic_padding,
              quic_ping,
              quic_unknow,
              quic_malicious,
              quic_immediate_ack, //seq_num
              quic_ack_frequency, //seq_num
              quic_ack_frequency_ack_eliciting_threshold,
              quic_ack_frequency_request_max_ack_delay,
              quic_ack_frequency_reordering_threshold,
              quic_s_done} state;
        bool long_format;
        char hdr_type;
        int dcil;
        int scil;
        long frame_type;
        int data_remaining;
        int128_t ack_blocks_expected;
        int128_t ack_block_count;
        //long long ack_blocks_expected;
        //long long ack_block_count;
        int payload_length_pos;
        int fence;
        int tcount = 0;
        bool done = false;

    public:
        quic_ser() : state(quic_s_init) {
        }
        virtual void  set(int128_t res) {
        //virtual void  set(long long res) {
            switch (state) {
            case quic_s_init:
            {
                //std::cerr << "ser res init " << res << "\n";
                long_format = res != 3;
                hdr_type = (long_format ? ((res & 3) << 4) : 0) | 0x43 ;
		        setn(hdr_type | (long_format ? 0x80 : 0), 1);
                state = quic_s_version;
            }
            break;
            case quic_s_version:
            {
                if (long_format)
                    setn(res,4);
                state = quic_s_dcid;
            }
            break;    
            case quic_s_dcid:
            {
                //std::cerr << "ser res dcid 1 " << res << "\n";
                if (long_format) {
                    if((res != 0 && res != 1) || scid_h == 0)
                        setn(scid_h,1);
                    else 
                        setn(8,1);
                }
                if((res != 0 && res != 1) || scid_h == 0)
                    setn(res,scid_h); //scid_h
                else 
                    setn(res,8); 
                //std::cerr << "ser res dcid 2 " << res << "\n";
                state = quic_s_scid;
            }
            break;
            case quic_s_scid:
            {
		        //std::cerr << "ser res scid_h 1 " << res << "\n";
                if (long_format) {
                    if((res == 0 || res == 1) && scid_h != 0){
                        setn(8,1);
                        setn(res,8);
                    } else {
                    	setn(dcid_h,1);
		    	        setn(res,dcid_h);
		            }
                }
		        //std::cerr << "ser res scid_h 1 " << res << "\n";
                state = quic_s_retry_token_length;
            }
            break;
            case quic_s_pkt_num:
            {
                set_pkt_num(res);
                state = quic_s_payload;
            }
            break;
            case quic_stream_off:
            {
                frame_type |= res ? 0x04 : 0;
                state = quic_stream_len;
            }
            break;
            case quic_stream_len:
            {
                frame_type |= res ? 0x02 : 0;
                state = quic_stream_fin;
            }
            break;
            case quic_stream_fin:
            {
                frame_type |= res ? 0x01 : 0;
		        setn(frame_type,1);
                state = quic_stream_id;
            }
            break;
            case quic_stream_id:
            {
                set_var_int(res);
                state = quic_stream_offset;
            }
            break;
            case quic_stream_offset:
            {
                if (0x04 & frame_type)
                    set_var_int(res);
                state = quic_stream_length;
            }
            break;
            case quic_stream_length:
            {
                if (0x02 & frame_type)
                    set_var_int(res);
                data_remaining = res;
                state = quic_stream_data;
            }
            break;
            case quic_crypto_offset:
            {
                //std::cerr << "ser: quic_crypto_offset   = " << res << "\n";
                if(const char* env_p4 = std::getenv("RETRY_TOKEN_LENGTH")) {
                    //std::cerr << "RETRY_TOKEN_LENGTH 1 " << env_p4 << "\n";
                    if(!done)
                        set_var_int(0);
                    else
                        set_var_int(res);
                } else {
                    set_var_int(res);
                }

                //set_var_int(res);
                state = quic_crypto_length;
            }
            break;
            case quic_crypto_length:
            {
                set_var_int(res);
                data_remaining = res;
                state = quic_crypto_data;
            }
            break;
            case quic_malicious:
            case quic_stream_data:
            case quic_crypto_data:
            case quic_connection_close_reason:
            case quic_path_challenge_data:
            case quic_padding:
            case quic_ping:
            case quic_unknow:
            case quic_handshake_done: // TODO
            case quic_immediate_ack:
            case quic_s_retry_token:
            {   
               // int128_t packet_size = res.size();
               // std::cerr << "packet_size ser " << packet_size << "\n";
               // int128_t token_length = packet_size - 1 - dcil - 1 - scil - 1 - 4;
               // std::cerr << "token_length ser " << token_length << "\n";    
               // std::cerr << "quic_s_retry_token ser "  << tcount << "\n";
               // tcount += 1; 
               /* if (const char* env_p3 = std::getenv("RETRY_TOKEN")) {
                    std::cerr << "ser: quic_s_retry_token   = " << res << "\n"; 
                    if(const char* env_p4 = std::getenv("RETRY_TOKEN_LENGTH")) {
                        std::cerr << "RETRY_TOKEN " << env_p3 << "\n";
                        std::cerr << "RETRY_TOKEN_LENGTH " << env_p4 << "\n";
                        setn(res,1);
                        tls_field_bytes_map["dcid"] = atoi(env_p3);
                    }
                }
                else 
                if(const char* env_p4 = std::getenv("RETRY_TOKEN_LENGTH") && false) {
                    std::cerr << "RETRY_TOKEN_LENGTH 1 " << env_p4 << "\n";
                    setn(res,atoi(env_p4));
                } else {
                setn(res,1);
                }*/

                setn(res,1);
            }
            break;
            /*case quic_s_retry_token_length:
            {   
               if (const char* env_p3 = std::getenv("RETRY_TOKEN")) {
                    std::cerr << "ser: quic_s_retry_token   = " << res << "\n"; 
                    if(const char* env_p4 = std::getenv("RETRY_TOKEN_LENGTH")) {
                        std::cerr << "RETRY_TOKEN_LENGTH 2" << env_p4 << "\n";
                        setn(atoi(env_p3),1);
                        state = quic_s_retry_token;
                    }
                }
            }
            break;*/
            case quic_ack_largest:
            {
                set_var_int(res);
                state = quic_ack_delay;
            }
            break;
            case quic_ack_delay:
            {
                set_var_int(res);
                state = quic_ack_block_count;
            }
            break;
            case quic_ack_gap:
            {
                if (ack_block_count == 0)
                    {} // first ack block has no gap
                else
                    set_var_int(res);
                state = quic_ack_block;
            }
            break;
            case quic_ack_block:
            {
                set_var_int(res);
                state = quic_ack_gap;
                ack_block_count++;
            }
            break;
            case quic_reset_stream_id:
            {
                set_var_int(res);
                state = quic_reset_err_code;
            }
            break;
            case quic_reset_err_code:
            {
                set_var_int(res);
                state = quic_reset_final_offset;
            }
            break;
            case quic_reset_final_offset:
            {
                set_var_int(res);
            }
            break;
            case quic_stop_sending_id:
            {
                set_var_int(res);
                state = quic_stop_sending_err_code;
            }
            break;
            case quic_stop_sending_err_code:
            {
                set_var_int(res);
            }
            break;
            case quic_connection_close_err_code:
            {
                set_var_int(res);
                state = quic_connection_close_frame_type;
            }
            break;
            case quic_connection_close_frame_type:
            {
                set_var_int(res);
                state = quic_connection_close_reason_length;
            }
            break;
            case quic_connection_close_reason_length:
            {
                set_var_int(res);
                data_remaining = res;
                state = quic_connection_close_reason;
            }
            break;
            case quic_application_close_err_code:
            {
                set_var_int(res);
                state = quic_connection_close_reason_length;
            }
            break;
            case quic_max_stream_data_id:
            {
                set_var_int(res);
                state = quic_reset_final_offset;
            }
            break;
            case quic_new_connection_id_length:
            {
                setn(res,1);
                scil = res;
                state = quic_new_connection_id_scid;
            }
            break;
            case quic_new_connection_id_seq_num:
            {
                set_var_int(res);
                state = quic_new_connection_id_retire_prior_to;
            }
            break;
            case quic_new_connection_id_retire_prior_to:
            {
                set_var_int(res);
                state = quic_new_connection_id_length;
            }
            break;
            case quic_new_connection_id_scid:
            {
                setn(res,scil);
                state = quic_new_connection_id_token;
            }
            break;
            case quic_new_connection_id_token:
            {
                setn(res,16);
            }
            break;
            case quic_retire_connection_id_seq_num:
            {
                set_var_int(res);
            }
            break;
            case quic_ack_frequency: //TODO
            {
                set_var_int(res);
		        //std::cerr << "ser: quic_ack_frequency   = quic_ack_frequency\n"; 
                state = quic_ack_frequency_ack_eliciting_threshold;
            }
            break;
            case quic_ack_frequency_ack_eliciting_threshold:
            {
                set_var_int(res);
		        //std::cerr << "ser: quic_ack_frequency   = quic_ack_frequency_ack_eliciting_threshold\n"; 
                state = quic_ack_frequency_request_max_ack_delay;
            }
            break;
            case quic_ack_frequency_request_max_ack_delay: 
            {
                set_var_int(res);
		        //std::cerr << "ser: quic_ack_frequency   = quic_ack_frequency_request_max_ack_delay\n"; 
                state = quic_ack_frequency_reordering_threshold;
            }
            break;
            case quic_ack_frequency_reordering_threshold: 
            {
		        //std::cerr << "ser: quic_ack_frequency   = quic_ack_frequency_reordering_threshold\n"; 
                //setn(res,1);
                set_var_int(res);
            }
            break;
            default:
            //std::cerr << "quic_ser 2\n";  
            throw deser_err();
            }
        }

        void set_var_int(int128_t res) {
            int128_t val = res & 0x3fffffffffffffff; //TODO modify with 16 bytes mask ?
        //void set_var_int(long long res) {
        //    long long val = res & 0x3fffffffffffffff; 
            int bytecode = res <= 0x3f ? 0 : res <= 0x3fff ? 1 : res <= 0x3fffffff ? 2 : 3;
            int bytes = 1 << bytecode;
            val |= bytecode << ((bytes << 3) - 2);
            setn(val,bytes);
        }

        void set_pkt_num(int128_t &res) {
        //void set_pkt_num(long long &res) {
            // setn(0xc0000000 | (0x3fffffff & res),4);
            // pkt number length is low two bits of first packet byte, plus one 
            setn(res,(hdr_type & 3) + 1);
        }

        virtual void open_tag(int tag, const std::string &) {
            if (state == quic_s_payload) {
                int sz = 1;
                if (tag == 0) {
                    frame_type = 0x01;
                    state = quic_ping;
                }
                else if (tag == 1) {
                    state = quic_ack_largest;
                    frame_type = 0x02;
                }
                else if (tag == 2) {
                    state = quic_ack_largest;
                    frame_type = 0x03;
                }
                else if (tag == 3) {
                    state = quic_reset_stream_id;
                    frame_type = 0x04;
                }
                else if (tag == 4) {
                    state = quic_stop_sending_id;
                    frame_type = 0x05;
                }
                else if (tag == 5) {
                    frame_type = 0x06;
                    state = quic_crypto_offset;
                }
                else if (tag == 6) {
                    frame_type = 0x07; 
                    state = quic_s_retry_token_length;  // new_token TODOODO
                }
                else if (tag == 7) {
		            frame_type = 0x08;
                    state = quic_stream_off;
                    return;
                }
                else if (tag == 8) {
                    frame_type = 0x10;  // max_data
                    state = quic_reset_final_offset;
                }
                else if (tag == 9) {
                    state = quic_max_stream_data_id;
                    frame_type = 0x11;
                }
                else if (tag == 10) {
                    state = quic_reset_stream_id; // max_stream_id state equivalent to this
                    frame_type = 0x13;
                }
                else if (tag == 11) {
                    state = quic_reset_stream_id; // max_stream_id state equivalent to this
                    frame_type = 0x12;
                }
                else if (tag == 12) {
                    state = quic_reset_final_offset;
                    frame_type = 0x14;
                }
                else if (tag == 13) {
                    state = quic_max_stream_data_id;
                    frame_type = 0x15;
                }
                else if (tag == 14) {
                    state = quic_reset_final_offset;
                    frame_type = 0x16;
                }
                else if (tag == 15) {
                    state = quic_reset_final_offset;
                    frame_type = 0x17;
                }
                else if (tag == 16) {
                    frame_type = 0x18;
                    state = quic_new_connection_id_seq_num;
                }
                else if (tag == 17) {
                    state = quic_retire_connection_id_seq_num;
                    frame_type = 0x19;
                }
                else if (tag == 18) {
                    frame_type = 0x1a;
                    state = quic_path_challenge_data;
                }
                else if (tag == 19) {
                    frame_type = 0x1b;
                    state = quic_path_challenge_data;
                }
                else if (tag == 20) {
                    state = quic_connection_close_err_code;
                    frame_type = 0x1c;
                }
                else if (tag == 21) {
                    frame_type = 0x1d;
                    state = quic_application_close_err_code;
                }    
                else if (tag == 22) {
                    state = quic_handshake_done;
                    frame_type = 0x1e;
                }
                else if (tag == 23) {
                    state = quic_ack_frequency;
                    frame_type = 0x40AF; // 0100 0000 AF
                    sz = 2;
                }
                else if (tag == 24) {
                    state = quic_immediate_ack;
                    frame_type = 0x40AC; // 0100 0000 AC
                    sz = 2;
                }
                else if (tag == 25) {
                    state = quic_unknow;
                    frame_type = 0x4042; 
                    sz = 2;                
                }
                else if (tag == 26) {
                    std::cerr << "quic_ser malicious\n";  
                    state = quic_malicious;
                    frame_type = 0x4041; 
                    sz = 2;  
                }
                /*else if (tag == 25) {
                    state = quic_padding;
                    frame_type = 0x00;
                }*/
	            else {
                    //std::cerr << "saw frame tag " << tag << "\n";  
                    throw deser_err();
	            }
                setn(frame_type,sz);
                return;
            }
            //std::cerr << "quic_ser 1\n";  
            throw deser_err();
        }

        virtual void open_list_elem() {
        }

        void open_list(int len) {
	        ack_blocks_expected = len;
            if (state == quic_ack_block_count) {
                set_var_int(ack_blocks_expected - 1); // block count doesn't include first
                ack_block_count = 0;
                state = quic_ack_gap;
            } else if (state == quic_s_retry_token_length) {
                if (long_format & ((hdr_type & 0x30) == 0x00)) {
                    //std::cerr << "open_list len " << len << "\n";
                    set_var_int(len);
                    data_remaining = len;
                }
                state = quic_s_retry_token;
            }
        }
        void close_list() {
            if (state == quic_s_payload) {
                if (long_format && (hdr_type & 0x30) == 0x00)
                    while (res.size() < 1200)
                        res.push_back(0);  // pad initial packet to 1200 bytes
                /*else if ((hdr_type & 0x30) == 0x20){
                            while (res.size() < 2000)
                                res.push_back(0);  // pad initial packet to 1200 bytes
                }*/
                for(unsigned i = 0; i < 16; i++)
                    res.push_back(0);
                if (long_format) {
                    int len = res.size() - (payload_length_pos+2) ;
                    res[payload_length_pos] = 0x40 | ((len >> 8) & 0x3f);
                    res[payload_length_pos+1] = len & 0xff;
                    state = quic_s_init;
                }
            }
            else if (state == quic_s_retry_token) {
                payload_length_pos = this->res.size();
                if (long_format) {
                    setn(0,2);  // will fill in correct value later
                }
                state = quic_s_pkt_num;
            }
        }
        void close_list_elem() {}

        virtual void close_tag() {
            state = quic_s_payload;
        }

        ~quic_ser(){}
    };

>>>

<<< init
    
>>>
```

Complete Example for QUIC can be found at: https://github.com/ElNiak/Protocols-Ivy/tree/master/protocol-testing/quic/

### Step 4: Create the protocol's test files

#### Description of the step

For each identified component, create an Ivy file that defines the component's tests. The tests should reflect the protocol behavior as defined in the RFCs and other documents and border cases.

#### Example: QUIC 

Example for QUIC can be found at: https://github.com/ElNiak/Protocols-Ivy/tree/master/protocol-testing/quic/quic_tests/client_tests and https://github.com/ElNiak/Protocols-Ivy/tree/master/protocol-testing/quic/quic_tests/server_tests

