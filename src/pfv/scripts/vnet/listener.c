#include <sys/socket.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <arpa/inet.h>
#include <string.h>
#include <stdbool.h>
#include <unistd.h>

int main(int argc, char* argv[])
{
    char *ip;
    char *dev;
    bool free = false;
    char opt;
    int port;
    while ((opt = getopt(argc, argv, "i:d:p:f")) != -1) {
        switch (opt) {
        case 'i': ip = optarg; break;
        case 'd': dev = optarg; break;
        case 'p': port = atoi(optarg); break;
        case 'f': free = true; break;
        default:
            fprintf(stderr, "Usage: %s -i IP -d device -p port [-f]\n", argv[0]);
            exit(EXIT_FAILURE);
        }
    }
    int l = strlen(dev);
    int fd = socket(AF_INET, SOCK_DGRAM,0);
    if (fd <= 0) {
        printf("socket: socket\n");
        exit(EXIT_FAILURE);
    }
    if (free) {
        int v = 1;
        if (setsockopt(fd, SOL_IP, IP_FREEBIND, &v, sizeof(v)) < 0) {
            perror("setsockopt: freebind");
            exit(EXIT_FAILURE);
        }
    }
    if (setsockopt(fd, SOL_SOCKET, SO_BINDTODEVICE, dev, l) < 0) {
        char s[100];
        sprintf(s, "setsockopt: bind to device %s", dev);
        perror(s);
        exit(EXIT_FAILURE);
    }
    
    if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &(int){1}, sizeof(int)) < 0 || setsockopt(fd, SOL_SOCKET, SO_REUSEPORT, &(int){1}, sizeof(int)) < 0)
        perror("setsockopt(SO_REUSEADDR) failed");
    
    struct sockaddr_in v_dst = {};
    inet_pton(AF_INET, ip, &v_dst.sin_addr.s_addr);
    v_dst.sin_port = htons(port);
    v_dst.sin_family = AF_INET;
    
    if (bind(fd, (struct sockaddr*) &v_dst, sizeof(struct sockaddr_in)) != 0) {
            char s[100];
            sprintf(s, "bind to addr %s", ip);
            perror(s);
        exit(EXIT_FAILURE);
    }
    
  
    char buf[100];
    int len = 100;
    if (recv(fd, buf, len, 0) == -1) {
        perror("recv");
        exit(EXIT_FAILURE);
    }
    printf("%s: %s\n", dev, buf);
}
