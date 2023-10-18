/*
* Author: Christian Huitema
* Copyright (c) 2020, Private Octopus, Inc.
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

/* Socket loop implements the "wait for messages" loop common to most servers
 * and many clients.
 *
 * Second step: support simple servers and simple client.
 *
 * The "call loop back" function is called: when ready, after receiving, and after sending. The
 * loop will terminate if the callback return code is not zero -- except for special processing
 * of the migration testing code.
 * TODO: in Windows, use WSA asynchronous calls instead of sendmsg, allowing for multiple parallel sends.
 * TODO: in Linux, use multiple send per call API
 * TDOO: trim the #define list.
 * TODO: support the QuicDoq scenario, manage extra socket.
 */

#ifdef _WINDOWS
#define WIN32_LEAN_AND_MEAN
#include <WinSock2.h>
#include <Windows.h>
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
#ifndef WSA_LAST_ERROR
#define WSA_LAST_ERROR(x) WSAGetLastError()
#endif
#ifndef socklen_t
#define socklen_t int
#endif

#else /* Linux */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>

#ifndef __USE_XOPEN2K
#define __USE_XOPEN2K
#endif
#ifndef __USE_POSIX
#define __USE_POSIX
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
#endif

#include "picosocks.h"
#include "picoquic.h"
#include "picoquic_internal.h"
#include "picoquic_packet_loop.h"

int picoquic_packet_loop_open_sockets(int local_port, int local_af, SOCKET_TYPE * s_socket, int * sock_af, int nb_sockets_max)
{
    int nb_sockets = (local_af == AF_UNSPEC) ? 2 : 1;

    /* Compute how many sockets are necessary */
    if (nb_sockets > nb_sockets_max) {
        DBG_PRINTF("Cannot open %d sockets, max set to %d\n", nb_sockets, nb_sockets_max);
        nb_sockets = 0;
    } else if (local_af == AF_UNSPEC) {
        sock_af[0] = AF_INET;
        sock_af[1] = AF_INET6;
    }
    else if (local_af == AF_INET || local_af == AF_INET6) {
        sock_af[0] = local_af;
    }
    else {
        DBG_PRINTF("Cannot open socket(AF=%d), unsupported AF\n", local_af);
        nb_sockets = 0;
    }

    for (int i = 0; i < nb_sockets; i++) {
        int recv_set = 0;
        int send_set = 0;
        
        if ((s_socket[i] = socket(sock_af[i], SOCK_DGRAM, IPPROTO_UDP)) == INVALID_SOCKET ||
            picoquic_socket_set_ecn_options(s_socket[i], sock_af[i], &recv_set, &send_set) != 0 ||
            picoquic_socket_set_pkt_info(s_socket[i], sock_af[i]) != 0 ||
            (local_port != 0 && picoquic_bind_to_port(s_socket[i], sock_af[i], local_port) != 0)) {
            DBG_PRINTF("Cannot set socket (af=%d, port = %d)\n", sock_af[i], local_port);
            for (int j = 0; j < i; j++) {
                if (s_socket[i] != INVALID_SOCKET) {
                    SOCKET_CLOSE(s_socket[i]);
                    s_socket[i] = INVALID_SOCKET;
                }
            }
            nb_sockets = 0;
            break;
        }
    }

    return nb_sockets;
}

int picoquic_packet_loop(picoquic_quic_t* quic,
    int local_port,
    int local_af,
    int dest_if,
    picoquic_packet_loop_cb_fn loop_callback,
    void* loop_callback_ctx)
{
    int ret = 0;
    uint64_t current_time = picoquic_get_quic_time(quic);
    int64_t delay_max = 10000000;
    struct sockaddr_storage addr_from;
    struct sockaddr_storage addr_to;
    int if_index_to;
    uint8_t buffer[1536];
    uint8_t send_buffer[1536];
    size_t send_length = 0;
    int bytes_recv;
    uint64_t loop_count_time = current_time;
    int nb_loops = 0;
    picoquic_connection_id_t log_cid;
    SOCKET_TYPE s_socket[PICOQUIC_PACKET_LOOP_SOCKETS_MAX];
    int sock_af[PICOQUIC_PACKET_LOOP_SOCKETS_MAX];
    int nb_sockets = 0;
    uint16_t socket_port = (uint16_t)local_port;
    int testing_migration = 0; /* Hook for the migration test */
    uint16_t next_port = 0; /* Data for the migration test */
    picoquic_cnx_t* last_cnx = NULL;
#ifdef _WINDOWS
    WSADATA wsaData = { 0 };
    (void)WSA_START(MAKEWORD(2, 2), &wsaData);
#endif
    memset(sock_af, 0, sizeof(sock_af));

    if ((nb_sockets = picoquic_packet_loop_open_sockets(local_port, local_af, s_socket, sock_af, PICOQUIC_PACKET_LOOP_SOCKETS_MAX)) == 0) {
        ret = PICOQUIC_ERROR_UNEXPECTED_ERROR;
    }
    else if (loop_callback != NULL) {
        ret = loop_callback(quic, picoquic_packet_loop_ready, loop_callback_ctx);
    }

    /* Wait for packets */
    /* TODO: add stopping condition, was && (!just_once || !connection_done) */
    while (ret == 0) {
        int socket_rank = -1;
        int64_t delta_t = picoquic_get_next_wake_delay(quic, current_time, delay_max);
        unsigned char received_ecn;

        if_index_to = 0;

        bytes_recv = picoquic_select_ex(s_socket, nb_sockets,
            &addr_from,
            &addr_to, &if_index_to, &received_ecn,
            buffer, sizeof(buffer),
            delta_t, &socket_rank, &current_time);

        nb_loops++;
        if (nb_loops >= 100) {
            uint64_t loop_delta = current_time - loop_count_time;

            loop_count_time = current_time;
            DBG_PRINTF("Looped %d times in %llu microsec, file: %d, line: %d\n",
                nb_loops, (unsigned long long) loop_delta, quic->wake_file, quic->wake_line);
            picoquic_log_context_free_app_message(quic, &log_cid, "Looped %d times in %llu microsec, file: %d, line: %d",
                nb_loops, (unsigned long long) loop_delta, quic->wake_file, quic->wake_line);

            nb_loops = 0;
        }

        if (bytes_recv < 0) {
            ret = -1;
        }
        else {
            uint64_t loop_time = current_time;
            uint16_t current_recv_port = socket_port;

            if (bytes_recv > 0) {
                /* track the local port value if not known yet */
                if (socket_port == 0 && nb_sockets == 1) {
                    struct sockaddr_storage local_address;
                    if (picoquic_get_local_address(s_socket[0], &local_address) != 0) {
                        memset(&local_address, 0, sizeof(struct sockaddr_storage));
                        fprintf(stderr, "Could not read local address.\n");
                    }
                    else if (addr_to.ss_family == AF_INET6) {
                        socket_port = ((struct sockaddr_in6*) & local_address)->sin6_port;
                    }
                    else if (addr_to.ss_family == AF_INET) {
                        socket_port = ((struct sockaddr_in*) & local_address)->sin_port;
                    }
                    current_recv_port = socket_port;
                }
                if (testing_migration) {
                    if (socket_rank == 0) {
                        current_recv_port = socket_port;
                    }
                    else {
                        current_recv_port = next_port;
                    }
                }
                /* Document incoming port */
                if (addr_to.ss_family == AF_INET6) {
                    ((struct sockaddr_in6*) & addr_to)->sin6_port = current_recv_port;
                }
                else if (addr_to.ss_family == AF_INET) {
                    ((struct sockaddr_in*) & addr_to)->sin_port = current_recv_port;
                }
                /* Submit the packet to the server */
                (void)picoquic_incoming_packet(quic, buffer,
                    (size_t)bytes_recv, (struct sockaddr*) & addr_from,
                    (struct sockaddr*) & addr_to, if_index_to, received_ecn,
                    current_time);

                if (loop_callback != NULL) {
                    ret = loop_callback(quic, picoquic_packet_loop_after_receive, loop_callback_ctx);
                }
            }

            while (ret == 0) {
                struct sockaddr_storage peer_addr;
                struct sockaddr_storage local_addr;
                int if_index = dest_if;
                int sock_ret = 0;
                int sock_err = 0;

                ret = picoquic_prepare_next_packet(quic, loop_time,
                    send_buffer, sizeof(send_buffer), &send_length,
                    &peer_addr, &local_addr, &if_index, &log_cid, &last_cnx);

                if (ret == 0 && send_length > 0) {
                    SOCKET_TYPE send_socket = INVALID_SOCKET;
                    loop_count_time = current_time;
                    nb_loops = 0;
                    for (int i = 0; i < nb_sockets; i++) {
                        if (sock_af[i] == peer_addr.ss_family) {
                            send_socket = s_socket[i];
                            break;
                        }
                    }

                    if (testing_migration) {
                        /* This code path is only used in the migration tests */
                        uint16_t send_port = (local_addr.ss_family == AF_INET) ?
                            ((struct sockaddr_in*) & local_addr)->sin_port :
                            ((struct sockaddr_in6*) & local_addr)->sin6_port;

                        if (send_port == next_port) {
                            send_socket = s_socket[nb_sockets - 1];
                        }
                    }

                    sock_ret = picoquic_send_through_socket(send_socket,
                        (struct sockaddr*) & peer_addr, (struct sockaddr*) & local_addr, if_index,
                        (const char*)send_buffer, (int)send_length, &sock_err);

                    if (sock_ret <= 0) {
                        if (last_cnx == NULL) {
                            picoquic_log_context_free_app_message(quic, &log_cid, "Could not send message to AF_to=%d, AF_from=%d, if=%d, ret=%d, err=%d",
                                peer_addr.ss_family, local_addr.ss_family, if_index, sock_ret, sock_err);
                        }
                        else {
                            picoquic_log_app_message(last_cnx, "Could not send message to AF_to=%d, AF_from=%d, if=%d, ret=%d, err=%d",
                                peer_addr.ss_family, local_addr.ss_family, if_index, sock_ret, sock_err);
                        }
                    }
                }
                else {
                    break;
                }
            }

            if (ret == 0 && loop_callback != NULL) {
                ret = loop_callback(quic, picoquic_packet_loop_after_send, loop_callback_ctx);
            }
        }

        if (ret == PICOQUIC_NO_ERROR_SIMULATE_NAT || ret == PICOQUIC_NO_ERROR_SIMULATE_MIGRATION) {
            /* Two pseudo error codes used for testing migration!
             * What follows is really test code, which we write here because it has to handle
             * the sockets, which interferes a lot with the handling of the packet loop.
             */
            SOCKET_TYPE s_mig = INVALID_SOCKET;
            int s_mig_af;
            int sock_ret;
            int testing_nat = (ret == PICOQUIC_NO_ERROR_SIMULATE_NAT);
            
            next_port = (testing_nat) ? 0 : socket_port + 1;
            sock_ret = picoquic_packet_loop_open_sockets(next_port, sock_af[0], &s_mig, &s_mig_af, 1);
            if (sock_ret != 1 || s_mig == INVALID_SOCKET) {
                if (last_cnx != NULL) {
                    picoquic_log_app_message(last_cnx, "Could not create socket for migration test, port=%d, af=%d, err=%d",
                        next_port, sock_af[0], sock_ret);
                }
            }
            else if (testing_nat) {
                if (s_socket[0] != INVALID_SOCKET) {
                    SOCKET_CLOSE(s_socket[0]);
                }
                s_socket[0] = s_mig;
                ret = 0;
            } else {
                /* Testing organized migration */
                if (nb_sockets < PICOQUIC_PACKET_LOOP_SOCKETS_MAX && last_cnx != NULL) {
                    struct sockaddr_storage local_address;
                    picoquic_store_addr(&local_address, (struct sockaddr*)& last_cnx->path[0]->local_addr);
                    if (local_address.ss_family == AF_INET6) {
                        ((struct sockaddr_in6*) & local_address)->sin6_port = next_port;
                    }
                    else if (local_address.ss_family == AF_INET) {
                        ((struct sockaddr_in*) & local_address)->sin_port = next_port;
                    }
                    s_socket[nb_sockets] = s_mig;
                    nb_sockets++;
                    testing_migration = 1;
                    ret = picoquic_probe_new_path(last_cnx, (struct sockaddr*)&last_cnx->path[0]->peer_addr,
                        (struct sockaddr*) &local_address, current_time);
                }
                else {
                    SOCKET_CLOSE(s_mig);
                }
            }
        }
    }

    if (ret == PICOQUIC_NO_ERROR_TERMINATE_PACKET_LOOP) {
        /* Normal termination requested by the application, returns no error */
        ret = 0;
    }

    /* Close the sockets */
    for (int i = 0; i < nb_sockets; i++) {
        if (s_socket[i] != INVALID_SOCKET) {
            SOCKET_CLOSE(s_socket[i]);
            s_socket[i] = INVALID_SOCKET;
        }
    }

    return ret;
}