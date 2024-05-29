#ifndef __quic_ser_deser_h__
#define __quic_ser_deser_h__
extern int scid_h;
extern int dcid_h;
//extern bool handshake_finished;
//extern bool handshake_done_send;
#include <inttypes.h>


    /*typedef struct transport_error_struct {
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
    }*/


typedef __int128_t int128_t;
typedef __uint128_t uint128_t;

//https://stackoverflow.com/questions/25114597/how-to-print-int128-in-g

std::ostream &
operator<<(std::ostream &dest, __int128_t value)
{
    std::ostream::sentry s(dest);
    if (s)
    {
        __uint128_t tmp = value < 0 ? -value : value;
        char buffer[128];
        char *d = std::end(buffer);
        do
        {
            --d;
            *d = "0123456789"[tmp % 10];
            tmp /= 10;
        } while (tmp != 0);
        if (value < 0)
        {
            --d;
            *d = '-';
        }
        int len = std::end(buffer) - d;
        if (dest.rdbuf()->sputn(d, len) != len)
        {
            dest.setstate(std::ios_base::badbit);
        }
    }
    return dest;
}

typedef struct tls_name_struct
{
    const char *name;
    int128_t value;
    //long long value;
} * tls_name_struct_ptr;
struct tls_name_map : hash_space::hash_map<std::string, int128_t> { };
//struct tls_name_map : hash_space::hash_map<std::string,long long> {};

std::string quic_params[18] = {
    "quic_transport_parameters",
    "initial_max_stream_data_bidi_local",
    "initial_max_data",
    "initial_max_stream_id_bidi",
    "max_idle_timeout",
    "preferred_address",
    "max_packet_size",
    "stateless_reset_token",
    "ack_delay_exponent",
    "initial_max_stream_id_uni",
    "disable_migration",
    "active_connection_id_limit",
    "initial_max_stream_data_bidi_remote",
    "initial_max_stream_data_uni",
    "max_ack_delay",
    "version_information",
    "initial_source_connection_id",
    "loss_bits"
};

struct tls_name_struct tls_field_length_bytes[46] = {
    {"fragment", 2},
    {"content", 2},
    {"content_psk",2},
    {"tls.client_hello", 3},
    {"tls.server_hello", 3},
    {"tls.new_session_ticket", 3},
    {"tls.encrypted_extensions", 3},
    {"tls.finished", 3},
    {"tls.early_data", 2},
    {"tls.pre_shared_key_client", 2},
    {"tls.pre_shared_key_server", 2},
    //{"tls.psk_key_exchange_modes", 2},
    //{"tls.pre_shared_key", 2},
    {"unknown_message_bytes", 3},
    {"session_id", 1},
    {"cipher_suites", 2},
    {"compression_methods", 1},
    {"extensions", 2},
    {"psk_binder", 2},
    {"identity", 2},
   // {"obfuscated_ticket_age", 0},
    {"psk_identities", 2},
    {"quic_transport_parameters", 2},
    //{"transport_parameters",2}, // Parameter length field removal
    {"initial_max_stream_data_bidi_local", 1},
    {"original_destination_connection_id", 1},
    {"initial_max_data", 1},
    {"initial_max_stream_id_bidi", 1},
    {"max_idle_timeout", 1},
    {"preferred_address", 1},
    {"max_packet_size", 1},
    {"stateless_reset_token", 1},
    {"ack_delay_exponent", 1},
    {"initial_max_stream_id_uni", 1},
    {"disable_active_migration", 1},
    {"active_connection_id_limit", 1},
    {"initial_max_stream_data_bidi_remote", 1},
    {"initial_max_stream_data_uni", 1},
    {"max_ack_delay", 1},
    {"initial_source_connection_id", 1},
    {"retry_source_connection_id", 1},
    {"loss_bits", 1},       //for picoquic TODO test
    {"grease_quic_bit", 1}, //for picoquic
    //{"enable_time_stamp",1}, //for picoquic TODO test
    {"min_ack_delay", 1},
    {"version_information", 1},
    {"unknown_transport_parameter", 1},
    {"unknown_ignore", 1},
    //{"max_early_data_size", 2},
    {"ticket_nonce", 1},
    {"ticket", 2},
    {0, 0}};
tls_name_map tls_field_length_bytes_map;

struct tls_name_struct tls_field_bytes[43] = {
    {"version", 2},
    {"client_version", 2}, //0x0303 = 2 bytes
    {"server_version", 2},
    {"etype", 2},
    {"mtype", 1},
    {"gmt_unix_time", 4},
    {"cipher_suites", 2},
    {"the_cipher_suite", 2},    
    {"compression_methods", 1},
    {"the_compression_method", 1},
    {"session_id", 1},
    {"content", 1},
    //{"content_psk",1}, //1 108 145
    {"initial_version", 4},
    {"stream_pos_32", -1},
    {"unknown", 0},
    {"stream_id_16", -1},
    {"seconds_16", -1},
    {"stream_pos_16", -1},
    {"exponent_8", -1},
    {"data_8", 16},
    {"dcid", 8},
    {"scid", 8},
    {"rcid", 8},
    {"pcid", 4},
    {"chosen_version", 4},
    {"other_version", 4}, //TODO
    {"ip_addr", 4},
    {"ip_port", 2},
    {"ip6_addr", 16},
    //{"ip6_addr2", 8},
    {"ip6_port", 2},
    {"pref_token", 16},
    {"pcid_len", 1},
    {"max_early_data_size", 4},
    {"ticket_lifetime", 4},
    {"ticket_age_add", 4},
    {"ticket_nonce", 1},
    {"ticket", 1},
    {"psk_binder", 1},
    {"identity", 1},
    {"psk_identities", -1},
    {"obfuscated_ticket_age", 4},
    {"selected_identity", 2},
    {0, 0}};
tls_name_map tls_field_bytes_map;

//TODO check old version
struct tls_name_struct tls_tags[39] = {
    {"tls.handshake_record", 22},
    {"tls.application_data_record", 23},
    {"tls.change_cipher_spec", 20},
    {"tls.client_hello", 1},
    {"tls.server_hello", 2},
    {"tls.encrypted_extensions", 0x08},
    {"tls.finished", 20},
    {"tls.early_data", 0x002a},
    {"tls.psk_key_exchange_modes", 0x002d},
    {"tls.pre_shared_key_client", 0x0029},
    {"tls.pre_shared_key_server", 0x0029},
    {"tls.new_session_ticket", 4},
    {"tls.unknown_message", -1},
    {"tls.unknown_extension", -1},
    {"quic_transport_parameters", 0x39}, //DRAFTversion: 0xffa5 -> TODO test 0x39 - TODO RETRY VULN
    {"initial_max_stream_data_bidi_local", 0x05},
    {"initial_max_data", 0x04},
    {"initial_max_stream_id_bidi", 0x08},
    {"original_destination_connection_id", 0x00},
    {"max_idle_timeout", 0x01},
    {"preferred_address", 0x0d},
    {"max_packet_size", 0x03},
    {"stateless_reset_token", 0x02},
    {"ack_delay_exponent", 0x0a},
    {"initial_max_stream_id_uni", 0x09},
    {"disable_active_migration", 0x0c},
    {"active_connection_id_limit", 0x0e},
    {"initial_max_stream_data_bidi_remote", 0x06},
    {"initial_max_stream_data_uni", 0x07},
    {"max_ack_delay", 0x0b},
    {"initial_source_connection_id", 0x0f},
    {"retry_source_connection_id", 0x10}, //0x10 = 0100 0000 = 2 bytes with varint 0x10
    {"loss_bits", 0x1057},                  //for picoquic
    {"grease_quic_bit", 0x2ab2},            //for picoquic
    //{"enable_time_stamp",0x7158}, //for picoquic
    {"min_ack_delay", -4611686014149009894},       //0xFF02DE1A ||  0xc0000000FF02DE1A (13835058059560541722) OR 8000DE1A
    {"version_information", -4611686018410646565}, //0xFF73DB ||    0xc000000000FF73DB (-4611686018410646565) OR 8000DE1A
    {"unknown_transport_parameter", -2},
    {"unknown_ignore", 0x4042},
    {0, 0}};
tls_name_map tls_tags_map;

struct tls_name_struct tls_tag_bytes[31] = {
    {"tls.unknown_extension", 2},
    {"tls.early_data", 2},
    {"tls.new_session_ticket", 1},
    {"tls.psk_key_exchange_modes", 2},
    {"tls.pre_shared_key_client", 2},
    {"tls.pre_shared_key_server", 2},
    {"quic_transport_parameters", 2},
    {"initial_max_stream_data_bidi_local", 1},
    {"initial_max_data", 1},
    {"initial_max_stream_id_bidi", 1},
    {"max_idle_timeout", 1},
    {"preferred_address", 1},
    {"max_packet_size", 1},
    {"stateless_reset_token", 1},
    {"ack_delay_exponent", 1},
    {"initial_max_stream_id_uni", 1},
    {"original_destination_connection_id", 1},
    {"disable_migration", 1},
    {"active_connection_id_limit", 1},
    {"initial_max_stream_data_bidi_remote", 1},
    {"initial_max_stream_data_uni", 1},
    {"max_ack_delay", 1},
    {"initial_source_connection_id", 1},
    {"retry_source_connection_id", 1},
    {"disable_active_migration", 1},
    {"loss_bits", 2},       //for picoquic
    {"grease_quic_bit", 2}, //for picoquic
    {"min_ack_delay", 8},
    {"version_information", 8},
    {"unknown_ignore", 2},
    //{"enable_time_stamp",2}, //for picoquic
    //{"unknown_transport_parameter",2},
    {0, 0}};
tls_name_map tls_tag_bytes_map;

void tls_make_name_map(tls_name_struct *vals, tls_name_map &map)
{
    while (vals->name)
    {
        map[vals->name] = vals->value;
        vals++;
    }
}

#endif
