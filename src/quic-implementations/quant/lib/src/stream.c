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

#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/param.h>

#include <quant/quant.h>

#include "cid.h"
#include "conn.h"
#include "diet.h"
#include "quic.h"
#include "stream.h"


#ifndef NO_OOO_DATA
SPLAY_GENERATE(ooo_by_off, pkt_meta, off_node, ooo_by_off_cmp)
#endif


#undef STRM_STATE
#define STRM_STATE(k, v) [v] = #k


const char * const strm_state_str[] = {STRM_STATES};

struct q_stream * get_stream(struct q_conn * const c, const dint_t id)
{
    const khiter_t k = kh_get(strms_by_id, &c->strms_by_id, (khint64_t)id);
    if (unlikely(k == kh_end(&c->strms_by_id)))
        return 0;
    return kh_val(&c->strms_by_id, k);
}


dint_t max_sid(const dint_t sid, const struct q_conn * const c)
{
    const uint_t max = is_srv_ini(sid) == is_clnt(c)
                           ? (is_uni(sid) ? c->tp_mine.max_strms_uni
                                          : c->tp_mine.max_strms_bidi)
                           : (is_uni(sid) ? c->tp_peer.max_strms_uni
                                          : c->tp_peer.max_strms_bidi);
    return unlikely(max == 0)
               ? 0
               : (dint_t)((max - 1) << 2) | ((STRM_FL_SRV | STRM_FL_UNI) & sid);
}


void apply_stream_limits(struct q_stream * const s)
{
    struct q_conn * const c = s->c;
    s->in_data_max =
        is_srv_ini(s->id) == is_clnt(c)
            ? (is_uni(s->id) ? c->tp_mine.max_strm_data_uni
                             : c->tp_mine.max_strm_data_bidi_remote)
            : (is_uni(s->id) ? c->tp_mine.max_strm_data_uni
                             : c->tp_mine.max_strm_data_bidi_local);
    s->out_data_max =
        is_srv_ini(s->id) == is_clnt(c)
            ? (is_uni(s->id) ? c->tp_peer.max_strm_data_uni
                             : c->tp_peer.max_strm_data_bidi_remote)
            : (is_uni(s->id) ? c->tp_peer.max_strm_data_uni
                             : c->tp_peer.max_strm_data_bidi_local);

    if (s->id >= 0)
        do_stream_fc(s, 0);
}


struct q_stream * new_stream(struct q_conn * const c, const dint_t id)
{
    struct q_stream * const s = calloc(1, sizeof(*s));
    ensure(s, "could not calloc q_stream");
    sq_init(&s->out);
    sq_init(&s->in);
    s->c = c;
    s->id = id;
    strm_to_state(s, strm_open);

    if (unlikely(id < 0)) {
        c->cstrms[strm_epoch(s)] = s;
        return s;
    }

    int ret;
    const khiter_t k =
        kh_put(strms_by_id, &c->strms_by_id, (khint64_t)id, &ret);
    assure(ret >= 1, "inserted");
    kh_val(&c->strms_by_id, k) = s;

    apply_stream_limits(s);
    const bool is_local = (is_srv_ini(id) != is_clnt(c));
    const uint_t cnt = (uint_t)((id >> 2) + 1);
    if (is_local) {
        if (is_uni(id)) {
            c->cnt_uni = MAX(cnt, c->cnt_uni);
            c->next_sid_uni += 4;
        } else {
            c->next_sid_bidi += 4;
            c->cnt_bidi = MAX(cnt, c->cnt_bidi);
        }
    }
    do_stream_id_fc(c, cnt, !is_uni(id), is_local);

    return s;
}


void free_stream(struct q_stream * const s)
{
    struct q_conn * const c = s->c;
    if (likely(s->id >= 0)) {
        warn(DBG, "freeing strm " FMT_SID " on %s conn %s", s->id, conn_type(c),
             cid_str(c->scid));
        diet_insert(&c->clsd_strms, (uint_t)s->id, 0);
        const khiter_t k =
            kh_get(strms_by_id, &c->strms_by_id, (khint64_t)s->id);
        assure(k != kh_end(&c->strms_by_id), "found");
        kh_del(strms_by_id, &c->strms_by_id, k);
    }
#ifndef FUZZING
    else
        s->c->cstrms[strm_epoch(s)] = 0;
#endif

#ifndef NO_OOO_DATA
    while (!splay_empty(&s->in_ooo)) {
        struct pkt_meta * const p = splay_min(ooo_by_off, &s->in_ooo);
        splay_remove(ooo_by_off, &s->in_ooo, p);
        free_iov(w_iov(c->w, pm_idx(c->w, p)), p);
    }
#endif

    if (s->in_ctrl)
        sl_remove(&c->need_ctrl, s, q_stream, node_ctrl);

    q_free(&s->out);
    q_free(&s->in);
#ifndef FUZZING
    free(s);
#endif
}


void track_bytes_in(struct q_stream * const s, const uint_t n)
{
    if (likely(s->id >= 0))
        // crypto "streams" don't count
        s->c->in_data_str += n;
    s->in_data += n;
}


void track_bytes_out(struct q_stream * const s, const uint_t n)
{
    if (likely(s->id >= 0))
        // crypto "streams" don't count
        s->c->out_data_str += n;
    s->out_data += n;
}


void reset_stream(struct q_stream * const s, const bool forget)
{
#ifdef DEBUG_STREAMS
    warn(DBG, "reset strm %u " FMT_SID " on %s conn %s", forget, s->id,
         conn_type(s->c), cid_str(s->c->scid));
#endif

    // reset stream offsets and other data
    s->lost_cnt = s->in_data_off = s->in_data = s->out_data = 0;
    s->out_last = 0;

    if (forget) {
        s->out_una = 0;
        q_free(&s->out);
        q_free(&s->in);
        return;
    }

    struct w_iov * v = s->out_una;
    sq_foreach_from (v, &s->out, next) {
        struct pkt_meta * const m = &meta(v);
        if (m->pn)
            // remove trailing padding
            v->len = m->strm_data_len;

        // don't reset stream-data-related fields
        // TODO: redo this with offsetof magic
        const bool fin = m->is_fin;
        const uint16_t shp = m->strm_frm_pos;
        const uint16_t sds = m->strm_data_pos;
        const uint16_t sdl = m->strm_data_len;
        memset(m, 0, sizeof(*m));
        m->is_fin = fin;
        m->strm_frm_pos = shp;
        m->strm_data_pos = sds;
        m->strm_data_len = sdl;
    }
}


void do_stream_fc(struct q_stream * const s, const uint16_t len)
{
#ifndef NDEBUG
    uint_t actual_lost_cnt = 0;
    struct w_iov * v = 0;
    sq_foreach_from (v, &s->out, next)
        if (meta(v).lost)
            actual_lost_cnt++;
    assure(actual_lost_cnt == s->lost_cnt,
           "stream " FMT_SID ": actual %" PRIu " != cnt %" PRIu, s->id,
           actual_lost_cnt, s->lost_cnt);
#endif

    const bool blocked_orig = s->blocked;
    s->blocked = (s->out_data + len > s->out_data_max);

    const bool tx_msd_orig = s->tx_max_strm_data;
    if (s->in_data * 4 > s->in_data_max) {
        s->tx_max_strm_data = true;
        s->in_data_max *= 4;
    }

    if (blocked_orig != s->blocked || tx_msd_orig != s->tx_max_strm_data)
        need_ctrl_update(s);
}


void do_stream_id_fc(struct q_conn * const c,
                     const uint_t cnt,
                     const bool bidi,
                     const bool local)
{
    if (local) {
        // this is a local stream
        if (bidi && c->sid_blocked_bidi == false)
            c->sid_blocked_bidi = (cnt == c->tp_peer.max_strms_bidi);
        else if (c->sid_blocked_uni == false)
            c->sid_blocked_uni =
                (c->tp_peer.max_strms_uni && cnt == c->tp_peer.max_strms_uni);
        return;
    }

    // this is a remote stream
    if (bidi) {
        if (cnt == c->tp_mine.max_strms_bidi) {
            c->tx_max_sid_bidi = true;
            c->tp_mine.max_strms_bidi *= 2;
        }
    } else {
        if (cnt == c->tp_mine.max_strms_uni) {
            c->tx_max_sid_uni = true;
            c->tp_mine.max_strms_uni *= 2;
        }
    }
}


void concat_out(struct q_stream * const s, struct w_iov_sq * const q)
{
    if (s->out_una == 0)
        s->out_una = sq_first(q);

    sq_concat(&s->out, q);
}


bool q_is_uni_stream(const struct q_stream * const s)
{
    return is_uni(s->id);
}
