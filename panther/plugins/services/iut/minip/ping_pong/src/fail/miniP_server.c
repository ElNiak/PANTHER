#include <poll.h>
#include <time.h>
#include <sys/socket.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <arpa/inet.h>
#include <string.h>
#include <stdbool.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/time.h>
#include "miniP.h"
#include "delay_fail.h"

int pthread_create(pthread_t *restrict thread,
                          const pthread_attr_t *restrict attr,
                          void *(*start_routine)(void *),
                          void *restrict arg);

int fd;

int respond(int fd) {
    int ret = 0;
    struct timeval tv;
    struct pollfd fds[1];
    struct msg buf;
    fds[0].fd = fd;
    fds[0].events = POLLIN;
    do {
	sleep(MIN_DELAY); //pre sleep
	srand (time(NULL));
	int sl = rand()%((TIMEOUT-MIN_DELAY-SAFETY_MARGIN)*1001);
	usleep(sl*1000);
	printf("Sending Pong...\n");
	gettimeofday(&tv, NULL);
	encode_msg(&buf, 2, "pong", 3,
		(unsigned long long)(tv.tv_sec)*1000+(unsigned long long)(tv.tv_usec)/1000);

	if (send(fd, (void*) &buf, sizeof(struct msg), 0) != sizeof(struct msg)) {
	    perror("send");
	    exit(EXIT_FAILURE);
	}
	printf("Pong sent\n");
	ret = poll(fds, 1, TIMEOUT * 1000);
        if (ret == -1) {
            perror ("poll");
            exit(EXIT_FAILURE);
	} else if (ret) {
            recv(fd, (void*) &buf, sizeof(struct msg), 0);
            print_msg(buf);
	}
    } while(ret);
    return 0;
}

int main(int argc, char* argv[])
{
    char *ip = NULL;
    int port = 0;
    char opt;
    while ((opt = getopt(argc, argv, "i:p:")) != -1) {
        switch (opt) {
        case 'i': ip = optarg; break;
        case 'p': port = atoi(optarg); break;
        default:
            fprintf(stderr, "Usage: %s -i IP -d device -p port [-f]\n", argv[0]);
            exit(EXIT_FAILURE);
        }
    }

    if (!ip || !port) {
	fprintf(stderr, "1Usage: %s -i destination IP -p destination port\n", argv[0]);
        exit(EXIT_FAILURE);
    }

    fd = socket(AF_INET, SOCK_DGRAM,0);
    if (fd <= 0) {
        printf("socket: socket\n");
        exit(EXIT_FAILURE);
    }
    
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
  
    struct msg buf;
    struct sockaddr_in from;
    socklen_t fromlen = sizeof(from);
    if (recvfrom(fd, (void*) &buf, sizeof(struct msg), 0, (struct sockaddr*) &from, &fromlen) == -1) {
        perror("recv");
        exit(EXIT_FAILURE);
    }
    print_msg(buf);
    if(connect(fd, (struct sockaddr*) &from, fromlen)) {
	perror("connect");
	exit(EXIT_FAILURE);
    }
    respond(fd);
}

