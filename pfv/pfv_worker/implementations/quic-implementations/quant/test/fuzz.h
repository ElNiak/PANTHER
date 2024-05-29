// SPDX-License-Identifier: BSD-2-Clause
//
// Copyright (c) 2016-2022, NetApp, Inc.
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

#pragma once

#include <netinet/in.h>
#include <stdint.h>

#include <quant/quant.h>

#include "conn.h"

extern int LLVMFuzzerTestOneInput(const uint8_t * data, size_t size);

static void * w;
static struct q_conn * c = 0;


static void mk_conn()
{
    if (likely(c))
        free_conn(c);

    c = new_conn(w, 0, 0, 0,
                 &(struct w_sockaddr){
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wmany-braces-around-scalar-init"
                     .addr = {.af = AF_INET6, .ip6 = IN6ADDR_LOOPBACK_INIT},
#pragma clang diagnostic pop
                     .port = bswap16(5678)},
                 "fuzzer", 0, 0, 0);
    init_tls(c, "", 0);
}


static int init(void)
{
    util_dlevel = CRT;
    w = q_init("lo"
#ifndef __linux__
               "0"
#endif
               ,
               0);

    w_init_rand();
    mk_conn();
    return 0;
}
