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
#include "delay.h"

int pthread_create(pthread_t *restrict thread,
                          const pthread_attr_t *restrict attr,
                          void *(*start_routine)(void *),
                          void *restrict arg);

#define NUMBER_THREAD 2
int fds[NUMBER_THREAD];

void* respond(void* fd_p) {
    int fd = *(int *)fd_p;
    int ret = 0;
    struct timeval tv;
    struct pollfd fds[1];
    struct msg buf;
    fds[0].fd = fd;
    fds[0].events = POLLIN;
    do {
	printf("sizeof struct :%i\n", sizeof(struct msg));
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

    for (int i = 0 ; i < NUMBER_THREAD ; i++) {
	fds[i] = socket(AF_INET, SOCK_DGRAM,0);
	if (fds[i] <= 0) {
	    printf("socket: socket\n");
	    exit(EXIT_FAILURE);
	}
   
	    if (setsockopt(fds[i], SOL_SOCKET, SO_REUSEADDR, &(int){1}, sizeof(int)) < 0 ||
		    setsockopt(fds[i], SOL_SOCKET, SO_REUSEPORT, &(int){1}, sizeof(int)) < 0)
	    perror("setsockopt(SO_REUSEADDR|SO_REUSEPORT) failed");
	struct sockaddr_in v_dst = {};
	inet_pton(AF_INET, ip, &v_dst.sin_addr.s_addr);
	v_dst.sin_port = htons(port);
	v_dst.sin_family = AF_INET;
    
	if (bind(fds[i], (struct sockaddr*) &v_dst, sizeof(struct sockaddr_in)) != 0) {
            char s[100];
            sprintf(s, "bind to addr %s", ip);
            perror(s);
	    exit(EXIT_FAILURE);
	}
    }

    pthread_t thread_id[NUMBER_THREAD]; 
    for (int i = 0 ; i < NUMBER_THREAD ; i++) {
	struct msg buf;
	struct sockaddr_in from;
	socklen_t fromlen = sizeof(from);
	if (recvfrom(fds[i], (void*) &buf, sizeof(struct msg), 0, (struct sockaddr*) &from, &fromlen) == -1) {
	    perror("recv");
	    exit(EXIT_FAILURE);
	}
	print_msg(buf);
	if(connect(fds[i], (struct sockaddr*) &from, fromlen)) {
	    perror("connect");
	    exit(EXIT_FAILURE);
	}
	pthread_create(thread_id+i, NULL, respond, (void*)(fds+i)); 
    }
    for (int i = 0 ; i < NUMBER_THREAD ; i++) {
	pthread_join(thread_id[i], NULL);
    }
}

