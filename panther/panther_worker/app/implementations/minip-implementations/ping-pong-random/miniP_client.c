#include <sys/socket.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <arpa/inet.h>
#include <string.h>
#include <stdbool.h>
#include <unistd.h>
#include <sys/poll.h>
#include <time.h>
#include <sys/time.h>
#include "miniP.h"
#include "delay.h"

int main(int argc, char* argv[])
{
    char *ip_dst = NULL;
    char opt;
    int port_dst = 0;
    while ((opt = getopt(argc, argv, "i:p:")) != -1) {
        switch (opt) {
        case 'i': ip_dst = optarg; break;
        case 'p': port_dst = atoi(optarg); break;
        default:
            fprintf(stderr, "Usage: %s -i destination IP -p destination port \n", argv[0]);
            exit(EXIT_FAILURE);
        }
    }
    if (!ip_dst || !port_dst ) {
        fprintf(stderr, "1Usage: %s -i destination IP -p destination port\n", argv[0]);
        exit(EXIT_FAILURE);
    }
    
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd <= 0) {
        perror("socket: socket");
        exit(EXIT_FAILURE);
    }
    
    struct sockaddr_in v_src = {};
    inet_pton(AF_INET, "127.0.0.1", &v_src.sin_addr.s_addr);
    v_src.sin_port = htons(9444);
    v_src.sin_family = AF_INET;

    struct sockaddr_in v_dst = {};
    inet_pton(AF_INET, ip_dst, &v_dst.sin_addr.s_addr);
    v_dst.sin_port = htons(port_dst);
    v_dst.sin_family = AF_INET;
    
    struct pollfd fds[1];
    fds[0].fd = fd;
    fds[0].events = POLLIN;
    
    int ret = 0;
    struct timeval tv;
    struct msg buf;
    do {
        printf("Sending Ping...\n");
        gettimeofday(&tv, NULL);
        encode_msg(&buf, 1, 
            "ping", 3,
            (unsigned long long)(tv.tv_sec)*1000+(unsigned long long)(tv.tv_usec)/1000);
        if (sendto(fd, (void*) &buf, sizeof(struct msg), 0, (struct sockaddr*)&v_dst, sizeof(struct sockaddr_in)) != sizeof(struct msg)) {
            perror("sendto");
            exit(EXIT_FAILURE);
            }
        ret = poll(fds, 1, TIMEOUT * 1000);
            if (ret == -1) {
            perror ("poll");
            exit(EXIT_FAILURE);
        } else if (ret) {
            recv(fd, (void*) &buf, sizeof(struct msg), 0);
            print_msg(buf);
            sleep(MIN_DELAY); //pre sleep
            srand (time(NULL));
            int sl = rand()%((TIMEOUT-MIN_DELAY-SAFETY_MARGIN)*1001);
            usleep(sl*1000);
        }
    } while(ret);
    printf("Server did not respond in time\n");

    return -1;
}
