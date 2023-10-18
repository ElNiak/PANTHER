// SPDX-License-Identifier: BSD-2-Clause
//
// Copyright (c) 2016-2020, NetApp, Inc.
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//
// 1. Redistributions of source code must retain the above copyright notice,
//    this list of conditions and the following disclaimer.
//
// 2. Redistributions in binary form must reproduce the above copyright notice,
//    this list of conditions and the following disclaimer in the documentation
//    and/or other materials provided with the distribution.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
// ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
// LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
// CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
// SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
// INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
// CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
// ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
// POSSIBILITY OF SUCH DAMAGE.

#include <arpa/inet.h>
#include <fcntl.h>
#include <libgen.h>
#include <netinet/in.h>
#include <stdbool.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#ifndef NDEBUG
#include <stdlib.h>
#include <sys/param.h>
#endif

#include <quant/quant.h>


int main(int argc
#ifdef NDEBUG
         __attribute__((unused))
#endif
         ,
         char * argv[])
{
#ifndef NDEBUG
    util_dlevel = DLEVEL; // default to maximum compiled-in verbosity
    int ch;
    while ((ch = getopt(argc, argv, "v:")) != -1)
        if (ch == 'v')
            util_dlevel = MIN(DLEVEL, MAX(0, (short)strtoul(optarg, 0, 10)));
#endif

    // init
    const int cwd = open(".", O_CLOEXEC);
    ensure(cwd != -1, "cannot open");
    ensure(chdir(dirname(argv[0])) == 0, "cannot chdir");
    __extension__ const struct q_conf conf = {.tls_cert = "dummy.crt",
                                              .tls_key = "dummy.key"};
    struct w_engine * const w = q_init("lo"
#ifndef __linux__
                                       "0"
#endif
                                       ,
                                       &conf);
    ensure(fchdir(cwd) == 0, "cannot fchdir");

    // bind server socket
    q_bind(w, 0, 55555);

    // connect to server
    struct sockaddr_in6 sip = {.sin6_family = AF_INET6,
                               .sin6_port = bswap16(55555)};
    inet_pton(AF_INET6, "::1", &sip.sin6_addr);
    struct q_conn * const cc = q_connect(w, (const struct sockaddr *)&sip,
                                         "localhost", 0, 0, true, 0, 0);
    ensure(cc, "is zero");

    // accept connection
    struct q_conn * const sc = q_accept(w, 0);
    ensure(sc, "is zero");

    // reserve a new stream
    struct q_stream * const cs = q_rsv_stream(cc, true);

    // allocate buffers to transmit a packet
    struct w_iov_sq o = w_iov_sq_initializer(o);
    q_alloc(w, &o, cc, AF_INET, 65536);
    struct w_iov * const ov = sq_first(&o);

    // send the data
    q_write(cs, &o, true);

again:;
    struct q_conn * c;
    do
        q_ready(w, 0, &c);
    while (c != sc);

    // read the data
    struct w_iov_sq i = w_iov_sq_initializer(i);
    struct q_stream * const ss = q_read(sc, &i, true);
    struct w_iov * const iv = sq_first(&i);
    if (iv == 0)
        goto again;

    ensure(strncmp((char *)ov->buf, (char *)iv->buf, ov->len) == 0,
           "data mismatch");
    q_close_stream(ss);
    q_close_stream(cs);

    q_free(&i);
    q_free(&o);

    // close connections
    q_close(cc, 0, 0);
    q_close(sc, 0, 0);
    q_cleanup(w);
}
