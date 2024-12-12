#include <stdint.h>

#pragma pack(1)
struct msg {
    char type1;
    char msg[4];
    char type2;
    unsigned long long timestamp;
};

void encode_msg(struct msg* buf, char t1, char* str, char t2, unsigned long long timestamp) {
    buf->type1 = t1;
    memcpy(&(buf->msg), str, 4);
    buf->type2 = t2;
    buf->timestamp = timestamp; //htonl(timestamp);
}

void print_msg(struct msg buf) {
    printf("Received message {%i: %.*s, %i: %llu}\n", buf.type1, 4, &buf.msg, buf.type2, ntohl(buf.timestamp));
}

