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
    char *ip_dst = NULL;
    char *ip_src = NULL;
    char *dev = NULL;
    bool free = false;
    char opt;
    int port_dst = 0;
    char *buf = NULL;
    int port_src = 0;
    while ((opt = getopt(argc, argv, "i:d:p:m:s:z:")) != -1) {
        switch (opt) {
        case 'i': ip_dst = optarg; break;
        case 'd': dev = optarg; break;
        case 'p': port_dst = atoi(optarg); break;
        case 'm': buf = optarg; break;
        case 's': free = true;
                  ip_src = optarg;
                  break;
        case 'z': free = true;
                  port_src = atoi(optarg);
                  break;
        default:
            fprintf(stderr, "Usage: %s -i destination IP -d device -p destination port -m message [-s source IP -z source port]\n", argv[0]);
            exit(EXIT_FAILURE);
        }
    }
    if (!ip_dst || !dev || !port_dst  || !buf || (free && (!ip_src || !port_src ))) {
        fprintf(stderr, "Usage: %s -i destination IP -d device -p destination port -m message [-s source IP -z source port]\n", argv[0]);
        exit(EXIT_FAILURE);
    }
    
    int len = strlen(buf)+1;
    if (len > 100) {
        len = 100;
        buf[99] = '\0';
        printf("message trucated to %s\n", buf);
    }
    int l = strlen(dev);
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd <= 0) {
        perror("socket: socket");
        exit(EXIT_FAILURE);
    }
    
    if (setsockopt(fd, SOL_SOCKET, SO_BINDTODEVICE, dev, l) < 0) {
        perror("setsockopt: bind to device");
        exit(EXIT_FAILURE);
    }
    
    if (free) {
        int v = 1;
        if (setsockopt(fd, SOL_IP, IP_FREEBIND, &v, sizeof(v)) < 0) {
            perror("setsockopt: freebind");
            exit(EXIT_FAILURE);
        }
        struct sockaddr_in v_src = {};
        inet_pton(AF_INET, ip_src, &v_src.sin_addr.s_addr);
        v_src.sin_port = htons(port_src);
        v_src.sin_family = AF_INET;
        
        
        if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &(int){1}, sizeof(int)) < 0 || setsockopt(fd, SOL_SOCKET, SO_REUSEPORT, &(int){1}, sizeof(int)) < 0)
            perror("setsockopt(SO_REUSEADDR) failed");
    
        if (bind(fd, (struct sockaddr*) &v_src, sizeof(struct sockaddr_in)) != 0) {
            char s[100];
            sprintf(s, "bind to addr %s", ip_src);
            perror(s);
            exit(EXIT_FAILURE);
        }
    }
    
    struct sockaddr_in v_dst = {};
    inet_pton(AF_INET, ip_dst, &v_dst.sin_addr.s_addr);
    v_dst.sin_port = htons(port_dst);
    v_dst.sin_family = AF_INET;
    if (sendto(fd, buf, len, 0, (struct sockaddr*)&v_dst, sizeof(struct sockaddr_in)) != len) {
        char s[100];
        sprintf(s, "sendto %s", buf);
        perror(s);
        exit(EXIT_FAILURE);
    }
}
