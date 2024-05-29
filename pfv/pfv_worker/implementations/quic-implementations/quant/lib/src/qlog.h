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

#ifndef NO_QLOG

struct pkt_meta;
struct q_conn;
struct w_iov;


typedef enum { pkt_tx, pkt_rx, pkt_dp } qlog_pkt_evt_t;


extern void __attribute__((nonnull)) qlog_init(struct q_conn * const c);

extern void qlog_close(struct q_conn * const c);

extern void __attribute__((nonnull))
qlog_transport(const qlog_pkt_evt_t evt,
               const char * const trg,
               struct w_iov * const v,
               const struct pkt_meta * const m);


typedef enum { rec_mu, rec_pl } qlog_rec_evt_t;

extern void __attribute__((nonnull(3)))
qlog_recovery(const qlog_rec_evt_t evt,
              const char * const trg,
              struct q_conn * const c,
              const struct pkt_meta * const m);

#else

#define qlog_close(...)                                                        \
    do {                                                                       \
    } while (0)

#define qlog_init(...)                                                         \
    do {                                                                       \
    } while (0)

#define qlog_recovery(...)                                                     \
    do {                                                                       \
    } while (0)

#define qlog_transport(...)                                                    \
    do {                                                                       \
    } while (0)


#endif
