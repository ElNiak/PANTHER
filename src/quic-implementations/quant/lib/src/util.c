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

#include <stdbool.h>
#include <string.h>
#include <unistd.h>

#include <quant/quant.h>

#include "stream.h"

struct q_conn;


void q_chunk_str(struct w_engine * const w,
                 const struct q_conn * const c,
                 const int af,
                 const char * const str,
                 const size_t len,
                 struct w_iov_sq * o)
{
    // allocate tail queue
    q_alloc(w, o, c, af, len);

    // chunk up string
    const char * i = str;
    struct w_iov * v;
    sq_foreach (v, o, next) {
        memcpy((char *)v->buf, i, v->len);
        i += v->len;
    }
}


void q_write_str(struct w_engine * const w,
                 struct q_stream * const s,
                 const char * const str,
                 const size_t len,
                 const bool fin)
{
    // allocate tail queue
    struct w_iov_sq o = w_iov_sq_initializer(o);
    q_chunk_str(w, s->c, q_conn_af(s->c), str, len, &o);

    // write it and free tail queue
    q_write(s, &o, fin);
    q_free(&o);
}


void q_write_file(struct w_engine * const w,
                  struct q_stream * const s,
                  const int f,
                  const size_t len,
                  const bool fin)
{
    // allocate tail queue
    struct w_iov_sq o = w_iov_sq_initializer(o);
    q_alloc(w, &o, s->c, q_conn_af(s->c), len);

    struct w_iov * v;
    sq_foreach (v, &o, next) {
        const ssize_t ret = read(f, v->buf, v->len);
        ensure(ret != -1, "cannot read");
    }

    // write it and free tail queue and iov
    q_write(s, &o, fin);
    q_free(&o);
}
