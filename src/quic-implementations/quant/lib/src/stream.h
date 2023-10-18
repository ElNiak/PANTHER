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

#pragma once

#include <stdbool.h>
#include <stdint.h>

#include <quant/quant.h>

#include "conn.h"
#include "quic.h"
#include "tls.h"

#ifndef NO_OOO_DATA
#include "tree.h"
#endif

#ifdef DEBUG_STREAMS
#include "cid.h"
#endif


#define STRM_FL_SRV 0x01
#define STRM_FL_UNI 0x02

#define INIT_STRM_DATA_BIDI 0xffff
#define INIT_STRM_DATA_UNI 0x7ff
#define INIT_MAX_UNI_STREAMS 128
#define INIT_MAX_BIDI_STREAMS 128

#define STRM_STATE(k, v) k = v
#define STRM_STATES                                                            \
    STRM_STATE(strm_idle, 0), STRM_STATE(strm_open, 1),                        \
        STRM_STATE(strm_hcrm, 2), STRM_STATE(strm_hclo, 3),                    \
        STRM_STATE(strm_clsd, 4)

// Define stream states.
// \dotfile conn-states.dot "Connection state diagram."
typedef enum { STRM_STATES } strm_state_t;

extern const char * const strm_state_str[];


#ifndef NO_OOO_DATA
static inline int __attribute__((nonnull))
ooo_by_off_cmp(const struct pkt_meta * const a, const struct pkt_meta * const b)
{
    return (a->strm_off > b->strm_off) - (a->strm_off < b->strm_off);
}


splay_head(ooo_by_off, pkt_meta);

SPLAY_PROTOTYPE(ooo_by_off, pkt_meta, off_node, ooo_by_off_cmp)
#endif


struct q_stream {
    sl_entry(q_stream) node_ctrl;

    struct q_conn * c; ///< Connection this stream is a part of.

    struct w_iov_sq out;     ///< Tail queue containing outbound data.
    struct w_iov * out_una;  ///< Lowest un-ACK'ed data chunk.
    struct w_iov * out_last; ///< Highest (last sent) un-ACK'ed data chunk.

    struct w_iov_sq in; ///< Tail queue containing inbound data.
#ifndef NO_OOO_DATA
    struct ooo_by_off in_ooo; ///< Out-of-order inbound data.
#endif

    dint_t id; ///< Stream ID.

    uint_t out_data;     ///< Current outbound stream offset (= data sent).
    uint_t out_data_max; ///< Outbound max_strm_data.

    uint_t in_data_max; ///< Inbound max_strm_data.
    uint_t in_data;     ///< In-order stream data received (total).
    uint_t in_data_off; ///< Next in-order stream data offset expected.

    uint_t lost_cnt;    ///< Number of pkts in out that are marked lost.
    strm_state_t state; ///< Stream state.

    uint8_t in_ctrl : 1; ///< Stream is in connections "needs ctrl" list.
    uint8_t tx_max_strm_data : 1; ///< We need to open the receive window.
    uint8_t blocked : 1;          ///< We are receive-window-blocked.
    uint8_t : 5;

#if HAVE_64BIT
    uint8_t _unused[3];
#else
    uint8_t _unused[7];
#endif
};


#if !defined(NDEBUG) && defined(DEBUG_STREAMS) && !defined(FUZZING)
#define strm_to_state(s, new_state)                                            \
    do {                                                                       \
        if ((s)->id >= 0) {                                                    \
            warn(                                                              \
                DBG,                                                           \
                "%s%s conn %s strm " FMT_SID " (%s, %s) state %s -> " YEL      \
                "%s" NRM,                                                      \
                (s)->state == (new_state) ? BLD RED "useless transition: " NRM \
                                          : "",                                \
                conn_type((s)->c), (s)->c->scid ? cid_str((s)->c->scid) : "?", \
                (s)->id, is_uni((s)->id) ? "uni" : "bi",                       \
                is_srv_ini((s)->id) ? "serv" : "clnt",                         \
                strm_state_str[(s)->state], strm_state_str[(new_state)]);      \
        }                                                                      \
        if (likely((s)->state != strm_clsd))                                   \
            (s)->state = (new_state);                                          \
    } while (0)
#else
#define strm_to_state(s, new_state)                                            \
    do {                                                                       \
        if (likely((s)->state != strm_clsd))                                   \
            (s)->state = (new_state);                                          \
    } while (0)
#endif


#define is_uni(id) is_set(STRM_FL_UNI, (id))
#define is_srv_ini(id) is_set(STRM_FL_SRV, (id))


static inline bool __attribute__((nonnull))
out_fully_acked(const struct q_stream * const s)
{
    return s->out_una == 0;
}


static const dint_t crpt_strm_id[] =
    {[ep_init] = -4, [ep_hshk] = -2, [ep_data] = -1};


static inline epoch_t __attribute__((nonnull))
strm_epoch(const struct q_stream * const s)
{
    if (unlikely(s->id < 0)) {
        static const epoch_t id_ep[] = {
            [4] = ep_init, [2] = ep_hshk, [1] = ep_data};
        return id_ep[-s->id];
    }

    if (unlikely(is_clnt(s->c) == true && s->c->state == conn_opng))
        return ep_0rtt;

    return ep_data;
}


static inline bool __attribute__((nonnull))
needs_ctrl(const struct q_stream * const s)
{
    return s->tx_max_strm_data || s->blocked;
}


static inline void __attribute__((nonnull))
need_ctrl_update(struct q_stream * const s)
{
    if (unlikely(needs_ctrl(s) != s->in_ctrl)) {
        if (s->in_ctrl == false)
            sl_insert_head(&s->c->need_ctrl, s, node_ctrl);
        else
            sl_remove(&s->c->need_ctrl, s, q_stream, node_ctrl);
        s->in_ctrl = !s->in_ctrl;
    }
}


extern struct q_stream * __attribute__((nonnull))
get_stream(struct q_conn * const c, const dint_t id);

extern struct q_stream * new_stream(struct q_conn * const c, const dint_t id);

extern void __attribute__((nonnull)) free_stream(struct q_stream * const s);

extern void __attribute__((nonnull))
track_bytes_in(struct q_stream * const s, const uint_t n);

extern void __attribute__((nonnull))
track_bytes_out(struct q_stream * const s, const uint_t n);

extern void __attribute__((nonnull))
reset_stream(struct q_stream * const s, const bool forget);

extern void __attribute__((nonnull))
apply_stream_limits(struct q_stream * const s);

extern void __attribute__((nonnull))
do_stream_fc(struct q_stream * const s, const uint16_t len);

extern void __attribute__((nonnull)) do_stream_id_fc(struct q_conn * const c,
                                                     const uint_t cnt,
                                                     const bool bidi,
                                                     const bool local);

extern void __attribute__((nonnull))
concat_out(struct q_stream * const s, struct w_iov_sq * const q);

extern dint_t __attribute__((nonnull))
max_sid(const dint_t sid, const struct q_conn * const c);
