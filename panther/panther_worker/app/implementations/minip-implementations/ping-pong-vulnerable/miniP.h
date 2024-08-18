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
    strcpy(&(buf->msg), str);
    buf->type2 = t2;
    buf->timestamp = timestamp; //htonl(timestamp);
}

void print_msg(struct msg buf) {
    printf("Received message:");
    printf("type1: %i ", buf.type1);
    printf("msg:");
    printf(&buf.msg);
    printf("type2: %i ", buf.type2);
    printf("timestamp: %llu\n", buf.timestamp);
}

