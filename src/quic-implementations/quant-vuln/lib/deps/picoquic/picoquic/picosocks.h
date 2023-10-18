/*
* Author: Christian Huitema
* Copyright (c) 2017, Private Octopus, Inc.
* All rights reserved.
*
* Permission to use, copy, modify, and distribute this software for any
* purpose with or without fee is hereby granted, provided that the above
* copyright notice and this permission notice appear in all copies.
*
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
* ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL Private Octopus, Inc. BE LIABLE FOR ANY
* DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
* ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

#ifndef PICOSOCKS_H
#define PICOSOCKS_H

#ifdef _WINDOWS
/* clang-format off */
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <Ws2def.h>
#include <WinSock2.h>
#include <ws2ipdef.h>
#include <Mswsock.h>
#include <assert.h>
#include <iphlpapi.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <ws2tcpip.h>

#ifndef SOCKET_TYPE
#define SOCKET_TYPE SOCKET
#endif
#ifndef SOCKET_CLOSE
#define SOCKET_CLOSE(x) closesocket(x)
#endif
#ifndef WSA_START_DATA
#define WSA_START_DATA WSADATA
#endif
#ifndef WSA_START
#define WSA_START(x, y) WSAStartup((x), (y))
#endif
#ifndef WSA_LAST_ERROR
#define WSA_LAST_ERROR(x) WSAGetLastError()
#endif
#ifndef socklen_t
#define socklen_t int
#endif
/* clang-format on */
#else /* Linux */

#include "getopt.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef __USE_XOPEN2K
#define __USE_XOPEN2K
#endif
#ifndef __USE_POSIX
#define __USE_POSIX
#endif
#ifndef __USE_GNU
#define __USE_GNU
#endif
#ifndef __APPLE_USE_RFC_3542
#define __APPLE_USE_RFC_3542 /* IPV6_PKTINFO */
#endif

#include <arpa/inet.h>
#include <errno.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/select.h>

#ifndef SOCKET_TYPE
#define SOCKET_TYPE int
#endif
#ifndef INVALID_SOCKET
#define INVALID_SOCKET -1
#endif
#ifndef SOCKET_CLOSE
#define SOCKET_CLOSE(x) close(x)
#endif
#ifndef WSA_LAST_ERROR
#define WSA_LAST_ERROR(x) ((long)(x))
#endif
#ifndef IPV6_RECVPKTINFO
#define IPV6_RECVPKTINFO IPV6_PKTINFO /* Cygwin */
#endif
#endif

#include "picoquic.h"

#ifdef __cplusplus
extern "C" {
#endif

#ifdef _WINDOWS
typedef struct st_picoquic_recvmsg_async_ctx_t {
    WSAOVERLAPPED overlap;
    WSABUF dataBuf;
    WSAMSG msg;
    char cmsg_buffer[1024];
    uint8_t buffer[PICOQUIC_MAX_PACKET_SIZE];
    struct sockaddr_storage addr_from;
    struct sockaddr_storage* addr_dest;
    socklen_t from_length;
    socklen_t dest_length;
    SOCKET_TYPE fd;
    int dest_if;
    unsigned char received_ecn;
    int bytes_recv;
    int is_started;
} picoquic_recvmsg_async_ctx_t;

picoquic_recvmsg_async_ctx_t * picoquic_create_async_socket(int af);
void picoquic_delete_async_socket(picoquic_recvmsg_async_ctx_t * ctx);
int picoquic_recvmsg_async_start(picoquic_recvmsg_async_ctx_t * ctx); 
int picoquic_recvmsg_async_finish(picoquic_recvmsg_async_ctx_t * ctx);

#endif

#define PICOQUIC_NB_SERVER_SOCKETS 2

typedef struct st_picoquic_server_sockets_t {
    SOCKET_TYPE s_socket[PICOQUIC_NB_SERVER_SOCKETS];
} picoquic_server_sockets_t;

int picoquic_bind_to_port(SOCKET_TYPE fd, int af, int port);

int picoquic_get_local_address(SOCKET_TYPE sd, struct sockaddr_storage * addr);

SOCKET_TYPE picoquic_open_client_socket(int af);

int picoquic_open_server_sockets(picoquic_server_sockets_t* sockets, int port);

void picoquic_close_server_sockets(picoquic_server_sockets_t* sockets);

int picoquic_socket_set_ecn_options(SOCKET_TYPE sd, int af, int * recv_set, int * send_set);

int picoquic_select(SOCKET_TYPE* sockets, int nb_sockets,
    struct sockaddr_storage* addr_from,
    struct sockaddr_storage* addr_dest,
    int* dest_if,
    unsigned char * received_ecn,
    uint8_t* buffer, int buffer_max,
    int64_t delta_t,
    uint64_t* current_time);

int picoquic_send_through_socket(
    SOCKET_TYPE fd,
    struct sockaddr* addr_dest,
    struct sockaddr* addr_from, int from_if,
    const char* bytes, int length, int* sock_err);

int picoquic_send_through_server_sockets(
    picoquic_server_sockets_t* sockets,
    struct sockaddr* addr_dest, 
    struct sockaddr* addr_from, int from_if,
    const char* bytes, int length, int * sock_err);

int picoquic_get_server_address(const char* ip_address_text, int server_port,
    struct sockaddr_storage* server_address,
    int* is_name);

/* Wireshark needs the session keys in order to decrypt and analyze packets.
 * In Unix and Windows, Wireshark reads these keys from a file. The name
 * of the file is passed in the environment variable SSLKEYLOGFILE,
 * which is accessed through system dependent API.
 */

void picoquic_set_key_log_file_from_env(picoquic_quic_t* quic);

#ifdef __cplusplus
}
#endif
#endif
