// Copyright (c) 2014-2022, NetApp, Inc.
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

#include <stdint.h>
#include <string.h>
#include <sys/param.h>
#include <sys/socket.h>

#include <quant/quant.h>

#include <conn.h>
#include <frame.h>
#include <pn.h>
#include <quic.h>
#include <stream.h>
#include <tls.h>

#include "fuzz.h"


int LLVMFuzzerTestOneInput(const uint8_t * data, const size_t size)
{
    static int needs_init = 1;
again:
    if (needs_init)
        needs_init = init();

    struct w_iov_sq i = w_iov_sq_initializer(i);
    q_alloc(w, &i, c, AF_INET6, 256); // arbitrary value
    struct w_iov * v = sq_first(&i);
    if (unlikely(v == 0)) {
        warn(CRT, "using new connection");
        needs_init = 1;
        goto again;
    }

    v->len = (uint16_t)MIN(size, v->len);
    memcpy(v->buf, data, v->len);

    struct pkt_meta * m = &meta(v);
    m->pn = &c->pns[w_rand_uniform32(pn_data + 1)];
    dec_frames(c, &v, &m);
    if (m->strm == 0)
        free_iov(v, m);

    struct q_stream * s;
    kh_foreach_value(&c->strms_by_id, s, { free_stream(s); });

    for (epoch_t e = ep_init; e <= ep_data; e++)
        if (c->cstrms[e])
            free_stream(c->cstrms[e]);

    return 0;
}
