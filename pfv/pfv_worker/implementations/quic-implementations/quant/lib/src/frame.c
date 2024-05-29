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

#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <sys/param.h>
#include <time.h>

#ifndef NO_MIGRATION
#include <sys/socket.h>
#endif

#ifdef __FreeBSD__
#include <netinet/in.h>
#endif

#include <quant/quant.h>
#include <timeout.h>

#include "bitset.h"
#include "cid.h"
#include "conn.h"
#include "diet.h"
#include "frame.h"
#include "loop.h"
#include "marshall.h"
#include "pkt.h"
#include "pn.h"
#include "quic.h"
#include "recovery.h"
#include "stream.h"
#include "tls.h"

#ifndef NO_OOO_DATA
#include "tree.h"
#endif


#ifndef NDEBUG
#define pcr_str(chlg_resp)                                                     \
    hex2str((chlg_resp), sizeof(chlg_resp),                                    \
            (char[hex_str_len(PATH_CHLG_LEN)]){""},                            \
            hex_str_len(PATH_CHLG_LEN))
#endif


static void track_frame(struct pkt_meta * const m,
                        struct q_conn_info * const ci
#ifdef NO_QINFO
                        __attribute__((unused))
#endif
                        ,
                        const uint8_t type,
                        const uint_t n
#ifdef NO_QINFO
                        __attribute__((unused))
#endif
)
{
    bit_set(FRM_MAX, type, &m->frms);
#ifndef NO_QINFO
    assure(type < sizeof(ci->frm_cnt[0]) / sizeof(ci->frm_cnt[0][0]),
           "unhandled frame type");
    ci->frm_cnt[m->txed ? 0 : 1][type] += n;
#endif
}


#define err_close_return(c, code, ...)                                         \
    do {                                                                       \
        err_close((c), (code), __VA_ARGS__);                                   \
        return false;                                                          \
    } while (0)


#define dec1_chk(val, pos, end, c, type)                                       \
    do {                                                                       \
        if (unlikely(dec1((val), (pos), (end)) == false))                      \
            err_close_return((c), ERR_FRAM_ENC, (type), "dec1 %s in %s:%u",    \
                             #val, __FILE__, __LINE__);                        \
    } while (0)


#define decv_chk(val, pos, end, c, type)                                       \
    do {                                                                       \
        uint64_t _v;                                                           \
        if (unlikely(decv(&_v, (pos), (end)) == false))                        \
            err_close_return((c), ERR_FRAM_ENC, (type), "decv %s in %s:%u",    \
                             #val, __FILE__, __LINE__);                        \
        *(val) = (uint_t)_v;                                                   \
    } while (0)

#define decb_chk(val, pos, end, len, c, type)                                  \
    do {                                                                       \
        if (unlikely(decb((val), (pos), (end), (len)) == false))               \
            err_close_return((c), ERR_FRAM_ENC, (type), "decb %s in %s:%u",    \
                             #val, __FILE__, __LINE__);                        \
    } while (0)


#define chk_finl_size(fs, s, type)                                             \
    do {                                                                       \
        if (unlikely((fs) != (s)->in_data_off))                                \
            err_close_return((s)->c, ERR_FINL_SIZE, (type),                    \
                             "fs %" PRIu " != %" PRIu, (fs),                   \
                             (s)->in_data_off);                                \
                                                                               \
    } while (0)


#ifndef NDEBUG
void log_stream_or_crypto_frame(const bool rtx,
                                const struct pkt_meta * const m,
                                const uint8_t fl,
                                const dint_t sid,
                                const bool in,
                                const strm_data_type_t kind)
{
    const struct q_conn * const c = m->pn->c;
    const struct q_stream * const s = m->strm;
    static const char * const kind_str[sdt_ign + 1] = {
        [sdt_inv] = BLD RED "invalid" NRM,
        [sdt_seq] = "seq",
        [sdt_ooo] = BLD YEL "ooo" NRM,
        [sdt_dup] = RED "dup" NRM,
        [sdt_ign] = YEL "ign" NRM};

    if (sid >= 0)
        warn(INF,
             "%sSTREAM" NRM " 0x%02x=%s%s%s%s%s id=" FMT_SID "/%" PRIu
             " off=%" PRIu "/%" PRIu " len=%u coff=%" PRIu "/%" PRIu " %s[%s]",
             in ? FRAM_IN : FRAM_OUT, fl, is_set(F_STREAM_FIN, fl) ? "FIN" : "",
             is_set(F_STREAM_FIN, fl) &&
                     (is_set(F_STREAM_LEN, fl) || is_set(F_STREAM_OFF, fl))
                 ? "|"
                 : "",
             is_set(F_STREAM_LEN, fl) ? "LEN" : "",
             is_set(F_STREAM_LEN, fl) && is_set(F_STREAM_OFF, fl) ? "|" : "",
             is_set(F_STREAM_OFF, fl) ? "OFF" : "", sid, max_sid(sid, c),
             m->strm_off,
             in ? (s ? s->in_data_max : 0) : (s ? s->out_data_max : 0),
             m->strm_data_len, in ? c->in_data_str : c->out_data_str,
             in ? c->tp_mine.max_data : c->tp_peer.max_data,
             rtx ? REV BLD GRN "[RTX]" NRM " " : "", kind_str[kind]);
    else
        warn(INF, "%sCRYPTO" NRM " off=%" PRIu " len=%u %s[%s]",
             in ? FRAM_IN : FRAM_OUT, m->strm_off, m->strm_data_len,
             rtx ? REV BLD GRN "[RTX]" NRM " " : "", kind_str[kind]);
}
#endif


static uint_t __attribute__((nonnull)) trim_frame(struct pkt_meta * const p)
{
    const uint_t diff = p->strm->in_data_off - p->strm_off;
    p->strm_off += diff;
    p->strm_data_pos += diff;
    p->strm_data_len -= diff;
    return diff;
}


static struct q_stream * __attribute__((nonnull))
get_and_validate_strm(struct q_conn * const c,
                      const dint_t sid,
                      const uint8_t type,
                      const bool ok_when_writer)
{
    if (is_uni(sid) && unlikely(is_srv_ini(sid) ==
                                (ok_when_writer ? is_clnt(c) : !is_clnt(c))))
        err_close(c, ERR_STRM_STAT, type,
                  "got frame 0x%02x for uni sid %" PRId " but am %s", type, sid,
                  conn_type(c));
    else {
        struct q_stream * s = get_stream(c, sid);
        if (unlikely(s == 0)) {
            if (unlikely(diet_find(&c->clsd_strms, (uint_t)sid)))
                warn(NTE,
                     "ignoring 0x%02x frame for closed strm " FMT_SID
                     " on %s conn %s",
                     type, sid, conn_type(c), cid_str(c->scid));
            else
                err_close(c, ERR_STRM_STAT, type, "unknown strm %" PRId, sid);
        }
        return s;
    }
    return 0;
}


#define concat(q, k) q##k

#ifndef NO_QINFO
#define incr_q_info(knd) concat(c->i.strm_frms_in_, knd)++
#else
#define incr_q_info(knd)                                                       \
    do {                                                                       \
    } while (0)
#endif


#ifndef NDEBUG
#define track_sd_frame(knd, dsp)                                               \
    do {                                                                       \
        kind = concat(sdt_, knd);                                              \
        ignore = (dsp);                                                        \
        incr_q_info(knd);                                                      \
    } while (0)
#else
#define track_sd_frame(knd, dsp)                                               \
    do {                                                                       \
        ignore = (dsp);                                                        \
        incr_q_info(knd);                                                      \
    } while (0)
#endif


#define strm_data_len_adj(sdl) ((sdl) - ((sdl) ? 1 : 0))


static bool __attribute__((nonnull))
dec_stream_or_crypto_frame(const uint8_t type,
                           const uint8_t ** pos,
                           const uint8_t * const end,
                           struct pkt_meta * const m,
                           struct w_iov * const v)
{
    struct pn_space * const pn = m->pn;
    if (unlikely(pn == 0))
        return false;
    struct q_conn * const c = pn->c;
    m->strm_frm_pos = (uint16_t)(*pos - v->buf) - 1;

    dint_t sid = 0;
    if (unlikely(type == FRM_CRY)) {
        const epoch_t e = epoch_for_pkt_type(m->hdr.type);
        if (unlikely(c->cstrms[e] == 0))
            err_close_return(c, ERR_STRM_STAT, type, "epoch %u abandoned", e);
        sid = crpt_strm_id[e];
        m->strm = c->cstrms[e];
    } else {
        m->is_fin = is_set(F_STREAM_FIN, type);
        decv_chk((uint_t *)&sid, pos, end, c, type);
        m->strm = get_stream(c, sid);
    }

    if (is_set(F_STREAM_OFF, type) || unlikely(type == FRM_CRY))
        decv_chk(&m->strm_off, pos, end, c, type);
    else
        m->strm_off = 0;

    uint_t l = 0;
    if (is_set(F_STREAM_LEN, type) || unlikely(type == FRM_CRY)) {
        decv_chk(&l, pos, end, c, type);
        if (unlikely(*pos + l > end))
            err_close_return(c, ERR_FRAM_ENC, type, "illegal strm len");
    } else
        // stream data extends to end of packet
        l = (uint16_t)(end - *pos);

    const dint_t max = max_sid(sid, c);
    if (unlikely(sid > max)) {
        log_stream_or_crypto_frame(false, m, type, sid, true, 0);
        err_close_return(c, ERR_STRM_LIMT, type, "sid %" PRId " > max %" PRId,
                         sid, max);
    }

    m->strm_data_pos = (uint16_t)(*pos - v->buf);
    m->strm_data_len = (uint16_t)l;

    // deliver data into stream
    bool ignore = false;
#ifndef NDEBUG
    strm_data_type_t kind = sdt_ign;
#endif

    if (unlikely(m->strm_data_len == 0 && !m->is_fin)) {
#ifdef DEBUG_EXTRA
        warn(WRN, "zero-len strm/crypt frame on sid " FMT_SID ", ignoring",
             sid);
#endif
        track_sd_frame(ign, true);
        goto done;
    }

    if (unlikely(m->strm == 0)) {
        if (unlikely(diet_find(&c->clsd_strms, (uint_t)sid))) {
#ifdef DEBUG_STREAMS
            warn(NTE,
                 "ignoring STREAM frame for closed strm " FMT_SID
                 " on %s conn %s",
                 sid, conn_type(c), cid_str(c->scid));
#endif
            track_sd_frame(ign, true);
            goto done;
        }

        if (unlikely(is_srv_ini(sid) != is_clnt(c))) {
            log_stream_or_crypto_frame(false, m, type, sid, true, 0);
            err_close_return(c, ERR_STRM_STAT, type,
                             "got sid %" PRId " but am %s", sid, conn_type(c));
        }

        m->strm = new_stream(c, sid);
    }
    ensure(m->strm, "have a stream");

    // best case: new in-order data
    if (m->strm->in_data_off >= m->strm_off &&
        m->strm->in_data_off <=
            m->strm_off + strm_data_len_adj(m->strm_data_len)) {

        if (unlikely(m->strm->state == strm_hcrm ||
                     m->strm->state == strm_clsd)) {
#ifdef DEBUG_STREAMS
            warn(NTE,
                 "ignoring STREAM frame for %s strm " FMT_SID " on %s conn %s",
                 strm_state_str[m->strm->state], sid, conn_type(c),
                 cid_str(c->scid));
#endif
            track_sd_frame(ign, true);
            goto done;
        }

        if (unlikely(m->strm->in_data_off > m->strm_off))
            // already-received data at the beginning of the frame, trim
            trim_frame(m);

        track_bytes_in(m->strm, m->strm_data_len);
        m->strm->in_data_off += m->strm_data_len;
        sq_insert_tail(&m->strm->in, v, next);
        track_sd_frame(seq, false);

#ifndef NO_OOO_DATA
        // check if a hole has been filled that lets us dequeue ooo data
        struct pkt_meta * p = splay_min(ooo_by_off, &m->strm->in_ooo);
        while (p) {
            struct pkt_meta * const nxt =
                splay_next(ooo_by_off, &m->strm->in_ooo, p);

            if (unlikely(p->strm_off + strm_data_len_adj(p->strm_data_len) <
                         m->strm->in_data_off)) {
                // right edge of p < left edge of stream
                warn(WRN, "drop stale frame [%" PRIu "..%" PRIu "]",
                     p->strm_off,
                     p->strm_off + strm_data_len_adj(p->strm_data_len));
                splay_remove(ooo_by_off, &m->strm->in_ooo, p);
                p = nxt;
                continue;
            }

            // right edge of p >= left edge of stream
            if (p->strm_off > m->strm->in_data_off)
                // also left edge of p > left edge of stream: still a gap
                break;

            // left edge of p <= left edge of stream: overlap, trim & enqueue
            struct w_iov * const vv = w_iov(c->w, pm_idx(c->w, p));
            if (unlikely(p->strm->in_data_off > p->strm_off)) {
                const uint_t diff = trim_frame(p);
                // adjust w_iov start and len to stream frame data
                vv->buf += diff;
                vv->len -= diff;
            }
            sq_insert_tail(&m->strm->in, vv, next);
            m->strm->in_data_off += p->strm_data_len;
            splay_remove(ooo_by_off, &m->strm->in_ooo, p);

            // mark ooo crypto data for freeing by rx_crypto()
            if (p->strm->id < 0)
                p->strm = 0;
            p = nxt;
        }
#endif

        // check if we have delivered a FIN, and act on it if we did
        // cppcheck-suppress nullPointer
        struct w_iov * const last = sq_last(&m->strm->in, w_iov, next);
        if (last) {
            const struct pkt_meta * const m_last = &meta(last);
            if (unlikely(v != last))
                adj_iov_to_start(last, m_last);
            if (m_last->is_fin) {
                chk_finl_size(m_last->strm_off + m_last->strm_data_len, m->strm,
                              type);
                m->pn->imm_ack = true;
                strm_to_state(m->strm, m->strm->state <= strm_hcrm ? strm_hcrm
                                                                   : strm_clsd);
            }
            if (unlikely(v != last))
                adj_iov_to_data(last, m_last);
        }

        if (likely(type != FRM_CRY)) {
            do_stream_fc(m->strm, 0);
            do_conn_fc(c, 0);
            c->have_new_data = true;
            maybe_api_return(q_read_stream, c, m->strm);
        }
        goto done;
    }

    // data is a complete duplicate
    if (m->strm_off + m->strm_data_len <= m->strm->in_data_off) {
#ifndef NO_SERVER
        // if this is a dup Initial and we are server, mark server flight lost
        if (unlikely(is_clnt(c) == false && m->hdr.type == LH_INIT))
            detect_all_lost_pkts(c, false);
#endif
        track_sd_frame(dup, true);
        goto done;
    }

#ifndef NO_OOO_DATA
    // data is out of order - check if it overlaps with already stored ooo data
    if (unlikely(m->strm->state == strm_hcrm || m->strm->state == strm_clsd)) {
        warn(NTE, "ignoring STREAM frame for %s strm " FMT_SID " on %s conn %s",
             strm_state_str[m->strm->state], sid, conn_type(c),
             cid_str(c->scid));
        track_sd_frame(ign, true);
        goto done;
    }

    struct pkt_meta * p = splay_min(ooo_by_off, &m->strm->in_ooo);
    while (p && p->strm_off + strm_data_len_adj(p->strm_data_len) < m->strm_off)
        p = splay_next(ooo_by_off, &m->strm->in_ooo, p);

    // right edge of p >= left edge of v
    if (p && p->strm_off <= m->strm_off + strm_data_len_adj(m->strm_data_len)) {
        // left edge of p <= right edge of v
        warn(ERR,
             "[%" PRIu "..%" PRIu "] have existing overlapping ooo data [%" PRIu
             "..%" PRIu "]",
             m->strm_off, m->strm_off + strm_data_len_adj(m->strm_data_len),
             p->strm_off, p->strm_off + strm_data_len_adj(p->strm_data_len));
        track_sd_frame(ign, true);
        goto done;
    }

    // this ooo data doesn't overlap with anything
    track_sd_frame(ooo, false);
    track_bytes_in(m->strm, m->strm_data_len);
    splay_insert(ooo_by_off, &m->strm->in_ooo, m);
#else
    // signal to the ACK logic to not ACK this packet
    log_stream_or_crypto_frame(false, m, type, sid, true, sdt_ooo);
    m->strm_off = UINT_T_MAX;
    goto reallydone;
#endif

done:
    log_stream_or_crypto_frame(false, m, type, sid, true, kind);

    if (m->strm && likely(type != FRM_CRY) &&
        unlikely(m->strm_off + strm_data_len_adj(m->strm_data_len) >
                 m->strm->in_data_max - 1))
        err_close_return(c, ERR_FC, type,
                         "stream %" PRIu " off %" PRIu " >= in_data_max %" PRIu,
                         m->strm->id,
                         m->strm_off + strm_data_len_adj(m->strm_data_len),
                         m->strm->in_data_max);

#ifdef NO_OOO_DATA
reallydone:
#endif
    if (ignore)
        // this indicates to callers that the w_iov was not placed in a stream
        m->strm = 0;

    *pos = &v->buf[m->strm_data_pos + m->strm_data_len];
    return true;
}


#ifndef NDEBUG
static uint_t __attribute__((const))
shorten_ack_nr(const uint_t ack, const uint_t diff)
{
    if (unlikely(diff == 0))
        return ack;

    uint_t div = 10;
    while ((ack - diff) % div + diff >= div)
        div *= 10;
    return ack % div;
}
#endif


#ifndef NO_ECN
static void __attribute__((nonnull)) disable_ecn(struct q_conn * const c)
{
    c->sockopt.enable_ecn = false;
    w_set_sockopt(c->sock, &c->sockopt);
}


#if 0
#define log_ecn(msg, e)                                                        \
    warn(ERR, "%s: not=%" PRIu ", ect0=%" PRIu ", ect1=%" PRIu ", ce=%" PRIu,  \
         (msg), (e)[ECN_NOT], (e)[ECN_ECT0], (e)[ECN_ECT1], (e)[ECN_CE])
#endif
#endif


static bool __attribute__((nonnull)) dec_ack_frame(const uint8_t type,
                                                   const uint8_t ** pos,
                                                   const uint8_t * const start,
                                                   const uint8_t * const end,
                                                   struct pkt_meta * const m)
{
    if (unlikely(m->ack_frm_pos))
        warn(WRN, "packet contains multiple ACK frames");
    else
        m->ack_frm_pos = (uint16_t)(*pos - start) - 1; // -1 to include type

    struct pn_space * const pn = m->pn;
    if (unlikely(pn == 0))
        return false;
    struct q_conn * const c = pn->c;

    uint_t lg_ack_in_frm = 0;
    decv_chk(&lg_ack_in_frm, pos, end, c, type);

    uint64_t ack_delay_raw = 0;
    decv_chk(&ack_delay_raw, pos, end, c, type);

    // TODO: figure out a better way to handle huge ACK delays
    if (sizeof(uint64_t) != sizeof(uint_t) &&
        unlikely(ack_delay_raw > UINT32_MAX / 2))
        err_close_return(c, ERR_FRAM_ENC, type, "ACK delay raw %" PRIu,
                         (uint_t)ack_delay_raw);

    // handshake pkts always use the default ACK delay exponent
    const uint_t ade = (m->hdr.type == LH_INIT || m->hdr.type == LH_HSHK)
                           ? DEF_ACK_DEL_EXP
                           : c->tp_peer.ack_del_exp;
    uint_t ack_delay = (uint_t)(ack_delay_raw << ade);

#ifdef DEBUG_EXTRA
    if (unlikely(ack_delay_raw &&
                 (m->hdr.type == LH_INIT || m->hdr.type == LH_HSHK)))
        warn(WRN,
             "ack_delay %" PRIu " usec is not zero in Initial or Handshake ACK",
             ack_delay);
    else if (unlikely(ack_delay > c->tp_peer.max_ack_del * US_PER_MS))
        warn(WRN, "ack_delay %" PRIu " > max_ack_del %" PRIu, ack_delay,
             c->tp_peer.max_ack_del * US_PER_MS);
#endif

    uint_t ack_rng_cnt = 0;
    decv_chk(&ack_rng_cnt, pos, end, c, type);

    const struct ival * const cum_ack_ival = diet_min_ival(&pn->acked_or_lost);
    const uint_t cum_ack = cum_ack_ival ? cum_ack_ival->hi : UINT_T_MAX;

    uint_t lg_ack = lg_ack_in_frm;
    bool got_new_ack = false;
#ifndef NO_ECN
    uint64_t lg_ack_in_frm_t = 0;
    uint_t new_acked_ect0 = 0;
#endif
    for (uint_t n = ack_rng_cnt + 1; n > 0; n--) {
        uint_t gap = 0;
        uint_t ack_rng = 0;
        decv_chk(&ack_rng, pos, end, c, type);

        if (unlikely(ack_rng > (UINT16_MAX << 4)))
            err_close_return(c, ERR_INTL, type, "ACK rng len %" PRIu, ack_rng);

        if (unlikely(ack_rng > lg_ack))
            err_close_return(c, ERR_FRAM_ENC, type,
                             "ACK rng len %" PRIu " > lg_ack %" PRIu, ack_rng,
                             lg_ack);

#ifndef NDEBUG
        if (ack_rng == 0) {
            if (n == ack_rng_cnt + 1)
                warn(INF,
                     FRAM_IN "ACK" NRM " 0x%02x%s lg=" FMT_PNR_OUT
                             " delay=%" PRIu " (%" PRIu " usec) cnt=%" PRIu
                             " rng=%" PRIu " [" FMT_PNR_OUT "]",
                     type, type == FRM_ACE ? "=ECN" : "", lg_ack_in_frm,
                     (uint_t)ack_delay_raw, ack_delay, ack_rng_cnt, ack_rng,
                     lg_ack_in_frm);
            else
                warn(INF,
                     FRAM_IN "ACK" NRM " gap=%" PRIu " rng=%" PRIu
                             " [" FMT_PNR_OUT "]",
                     gap, ack_rng, lg_ack);
        } else {
            if (n == ack_rng_cnt + 1)
                warn(INF,
                     FRAM_IN "ACK" NRM " 0x%02x%s lg=" FMT_PNR_OUT
                             " delay=%" PRIu " (%" PRIu " usec) cnt=%" PRIu
                             " rng=%" PRIu " [" FMT_PNR_OUT ".." FMT_PNR_OUT
                             "]",
                     type, type == FRM_ACE ? "=ECN" : "", lg_ack_in_frm,
                     (uint_t)ack_delay_raw, ack_delay, ack_rng_cnt, ack_rng,
                     lg_ack - ack_rng, shorten_ack_nr(lg_ack, ack_rng));
            else
                warn(INF,
                     FRAM_IN "ACK" NRM " gap=%" PRIu " rng=%" PRIu
                             " [" FMT_PNR_OUT ".." FMT_PNR_OUT "]",
                     gap, ack_rng, lg_ack - ack_rng,
                     shorten_ack_nr(lg_ack, ack_rng));
        }
#endif

        uint_t ack = lg_ack;
        while (ack_rng >= lg_ack - ack) {
            if (likely(cum_ack != UINT_T_MAX) && ack <= cum_ack)
                // we can skip the remainder of this range entirely
                goto next_rng;

            if (diet_find(&pn->acked_or_lost, ack))
                goto next_ack;

            struct pkt_meta * m_acked;
            struct w_iov * const acked = find_sent_pkt(pn, ack, &m_acked);
            if (unlikely(acked == 0))
#ifndef FUZZING
                // this is just way too noisy when fuzzing
                err_close_return(c, ERR_PV, type,
                                 "got ACK for %s pkt %" PRIu " never sent",
                                 pn_type_str[pn->type], ack);
#else
                goto next_ack;
#endif

            got_new_ack = true;
            if (unlikely(ack == lg_ack_in_frm)) {
                // call this only for the largest ACK in the frame
                on_ack_received_1(m_acked, ack_delay);
#ifndef NO_ECN
                lg_ack_in_frm_t = m_acked->t;
#endif
            }

            on_pkt_acked(acked, m_acked);

#ifndef NO_ECN
            // if the ACK'ed pkt was sent with ECT, verify peer and path support
            if (likely(c->sockopt.enable_ecn &&
                       is_set(ECN_ECT0, acked->flags))) {
                if (unlikely(type != FRM_ACE)) {
                    warn(WRN,
                         "ECN verification failed for %s conn %s, no ECN "
                         "counts rx'ed",
                         conn_type(c), cid_str(c->scid));
                    disable_ecn(c);
                } else
                    new_acked_ect0++;
            }
#endif

        next_ack:
            if (likely(ack > 0))
                ack--;
            else
                break;
        }

    next_rng:
        if (n > 1) {
            decv_chk(&gap, pos, end, c, type);
            if (unlikely((lg_ack - ack_rng) < gap + 2)) {
                warn(DBG, "lg_ack=%" PRIu ", ack_rng=%" PRIu ", gap=%" PRIu,
                     lg_ack, ack_rng, gap);
                err_close_return(c, ERR_PV, type, "illegal ACK frame");
            }
            lg_ack -= ack_rng + gap + 2;
        }
    }

    if (type == FRM_ACE) {
        // decode ECN
        uint_t ecn_cnt[ECN_MASK + 1] = {0};
        decv_chk(&ecn_cnt[ECN_ECT0], pos, end, c, type);
        decv_chk(&ecn_cnt[ECN_ECT1], pos, end, c, type);
        decv_chk(&ecn_cnt[ECN_CE], pos, end, c, type);
        warn(INF,
             FRAM_IN "ECN" NRM " ect0=%s%" PRIu NRM " ect1=%s%" PRIu NRM
                     " ce=%s%" PRIu NRM,
             ecn_cnt[ECN_ECT0] ? GRN : NRM, ecn_cnt[ECN_ECT0],
             ecn_cnt[ECN_ECT1] ? GRN : NRM, ecn_cnt[ECN_ECT1],
             ecn_cnt[ECN_CE] ? GRN : NRM, ecn_cnt[ECN_CE]);

#ifndef NO_ECN
        if (got_new_ack) {
            // log_ecn("ref", pn->ecn_ref);
            const uint_t ecn_inc[ECN_MASK + 1] = {
                // ECN_NOT is not used
                // [ECN_NOT] = ecn_cnt[ECN_NOT] - pn->ecn_ref[ECN_NOT],
                [ECN_ECT0] = ecn_cnt[ECN_ECT0] - pn->ecn_ref[ECN_ECT0],
                [ECN_ECT1] = ecn_cnt[ECN_ECT1] - pn->ecn_ref[ECN_ECT1],
                [ECN_CE] = ecn_cnt[ECN_CE] - pn->ecn_ref[ECN_CE]};
            // log_ecn("inc", ecn_inc);

            if (unlikely(ecn_inc[ECN_ECT0] + ecn_inc[ECN_ECT1] +
                             ecn_inc[ECN_CE] <
                         new_acked_ect0)) {
                warn(WRN,
                     "ECN verification failed for %s conn %s, "
                     "inc %" PRIu " + %" PRIu " + %" PRIu " < %" PRIu,
                     conn_type(c), cid_str(c->scid), ecn_inc[ECN_ECT0],
                     ecn_inc[ECN_ECT1], ecn_inc[ECN_CE], new_acked_ect0);
                disable_ecn(c);
            } else if (unlikely(ecn_inc[ECN_ECT0] + ecn_cnt[ECN_CE] <
                                new_acked_ect0)) {
                warn(WRN,
                     "ECN verification failed for %s conn %s, "
                     "ECT0 inc %" PRIu " + %" PRIu " < %" PRIu,
                     conn_type(c), cid_str(c->scid), ecn_inc[ECN_ECT0],
                     ecn_inc[ECN_CE], new_acked_ect0);
                disable_ecn(c);
                // NOTE: we don't verify ect1 since we never send it
            } else {
                if (ecn_cnt[ECN_CE] > pn->ecn_ref[ECN_CE])
                    // ProcessECN
                    congestion_event(c, lg_ack_in_frm_t);

                // remember ECN counts
                memcpy(pn->ecn_ref, ecn_cnt, sizeof(pn->ecn_ref));
            }
        }
#endif
    }

    if (got_new_ack)
        on_ack_received_2(pn);

    bit_zero(FRM_MAX, &pn->tx_frames);
    return true;
}


static bool __attribute__((nonnull))
dec_close_frame(const uint8_t type,
                const uint8_t ** pos,
                const uint8_t * const end,
                const struct pkt_meta * const m)
{
    struct pn_space * const pn = m->pn;
    if (unlikely(pn == 0))
        return false;
    struct q_conn * const c = pn->c;

    uint_t err_code;
    decv_chk(&err_code, pos, end, c, type);

    uint_t frame_type = 0;
    if (type == FRM_CLQ)
        decv_chk(&frame_type, pos, end, c, type);

    uint_t reas_len = 0;
    decv_chk(&reas_len, pos, end, c, type);

    const uint16_t act_reas_len =
        (uint16_t)MIN(reas_len, (uint16_t)(end - *pos));
    assure(act_reas_len <= ped(c->w)->scratch_len, "scratch insufficient");
    unpoison_scratch(ped(c->w)->scratch, ped(c->w)->scratch_len);

    if (act_reas_len)
        decb_chk(ped(c->w)->scratch, pos, end, act_reas_len, c, type);

    warn(INF,
         FRAM_IN "CONNECTION_CLOSE" NRM " 0x%02x=%s err=%s0x%" PRIx NRM
                 " frame=0x%" PRIx " rlen=%" PRIu "%s%s%.*s" NRM,
         type, type == FRM_CLQ ? "quic" : "app", err_code ? RED : NRM, err_code,
         frame_type, reas_len, err_code ? RED : NRM, reas_len ? " reason=" : "",
         (int)reas_len, ped(c->w)->scratch);
    poison_scratch(ped(c->w)->scratch, ped(c->w)->scratch_len);

    if (unlikely(reas_len != act_reas_len))
        err_close_return(c, ERR_FRAM_ENC, type, "illegal reason len");

    if (c->state == conn_clsg) {
        conn_to_state(c, conn_drng);
        timeouts_add(ped(c->w)->wheel, &c->closing_alarm, 0);
    } else {
        conn_to_state(c, conn_clsg);
        c->needs_tx = true;
        enter_closing(c);
    }

    return true;
}


static bool __attribute__((nonnull))
dec_max_strm_data_frame(const uint8_t ** pos,
                        const uint8_t * const end,
                        const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;
    dint_t sid = 0;
    decv_chk((uint_t *)&sid, pos, end, c, FRM_MSD);

    uint_t max = 0;
    decv_chk(&max, pos, end, c, FRM_MSD);

    warn(INF, FRAM_IN "MAX_STREAM_DATA" NRM " id=" FMT_SID " max=%" PRIu, sid,
         max);

    struct q_stream * const s = get_and_validate_strm(c, sid, FRM_MSD, true);
    if (unlikely(s == 0))
        return true;

    if (max > s->out_data_max) {
        s->out_data_max = max;
        if (s->blocked) {
            s->blocked = false;
            c->needs_tx = true;
            need_ctrl_update(s);
        }
    } else if (max < s->out_data_max)
        warn(NTE, "MAX_STREAM_DATA %" PRIu " < current value %" PRIu, max,
             s->out_data_max);

    return true;
}


static bool __attribute__((nonnull))
dec_max_strms_frame(const uint8_t type,
                    const uint8_t ** pos,
                    const uint8_t * const end,
                    const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;

    uint_t max = 0;
    decv_chk(&max, pos, end, c, type);

    warn(INF, FRAM_IN "MAX_STREAMS" NRM " 0x%02x=%s max=%" PRIu, type,
         type == FRM_MSU ? "uni" : "bi", max);

#ifdef HAVE_64BIT
    if (unlikely(max > UINT64_C(1) << 60))
        err_close_return(c, ERR_PV, type, "MAX_STREAMS > 2^60");
#endif

    uint_t * const max_streams = type == FRM_MSU ? &c->tp_peer.max_strms_uni
                                                 : &c->tp_peer.max_strms_bidi;

    if (max > *max_streams) {
        *max_streams = max;
        maybe_api_return(q_rsv_stream, c, 0);
    } else if (max < *max_streams)
        warn(NTE, "RX'ed max_%s_streams %" PRIu " < current value %" PRIu,
             type == FRM_MSU ? "uni" : "bidi", max, *max_streams);

    return true;
}


static bool __attribute__((nonnull))
dec_max_data_frame(const uint8_t ** pos,
                   const uint8_t * const end,
                   const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;
    uint_t max = 0;
    decv_chk(&max, pos, end, c, FRM_MCD);

    warn(INF, FRAM_IN "MAX_DATA" NRM " max=%" PRIu, max);

    if (max > c->tp_peer.max_data) {
        c->tp_peer.max_data = max;
        c->blocked = false;
    } else if (max < c->tp_peer.max_data)
        warn(NTE, "MAX_DATA %" PRIu " < current value %" PRIu, max,
             c->tp_peer.max_data);

    return true;
}


static bool __attribute__((nonnull))
dec_strm_data_blocked_frame(const uint8_t ** pos,
                            const uint8_t * const end,
                            const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;
    dint_t sid = 0;
    decv_chk((uint_t *)&sid, pos, end, c, FRM_SDB);

    uint_t off = 0;
    decv_chk(&off, pos, end, c, FRM_SDB);

    warn(INF, FRAM_IN "STREAM_DATA_BLOCKED" NRM " id=" FMT_SID " lim=%" PRIu,
         sid, off);

    struct q_stream * const s = get_and_validate_strm(c, sid, FRM_SDB, false);
    if (unlikely(s == 0))
        return true;

    do_stream_fc(s, 0);
    return true;
}


static bool __attribute__((nonnull))
dec_data_blocked_frame(const uint8_t ** pos,
                       const uint8_t * const end,
                       const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;
    uint_t off = 0;
    decv_chk(&off, pos, end, c, FRM_CDB);

    warn(INF, FRAM_IN "DATA_BLOCKED" NRM " lim=%" PRIu, off);

    do_conn_fc(c, 0);
    // because do_conn_fc() only sets this when increasing the FC window
    c->tx_max_data = true;

    return true;
}


static bool __attribute__((nonnull))
dec_streams_blocked_frame(const uint8_t type,
                          const uint8_t ** pos,
                          const uint8_t * const end,
                          const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;

    uint_t max = 0;
    decv_chk(&max, pos, end, c, FRM_SBB);

    warn(INF, FRAM_IN "STREAMS_BLOCKED" NRM " 0x%02x=%s max=%" PRIu, type,
         type == FRM_SBB ? "bi" : "uni", max);

#ifdef HAVE_64BIT
    if (unlikely(max > UINT64_C(1) << 60))
        err_close_return(c, ERR_PV, type, "STREAMS_BLOCKED > 2^60");
#endif

    do_stream_id_fc(c, max, type == FRM_SBB, false);

    return true;
}


static bool __attribute__((nonnull))
dec_stop_sending_frame(const uint8_t ** pos,
                       const uint8_t * const end,
                       const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;
    dint_t sid = 0;
    decv_chk((uint_t *)&sid, pos, end, c, FRM_STP);

    uint_t err_code;
    decv_chk(&err_code, pos, end, c, FRM_STP);

    warn(INF, FRAM_IN "STOP_SENDING" NRM " id=" FMT_SID " err=%s0x%" PRIx NRM,
         sid, err_code ? RED : NRM, err_code);

    struct q_stream * const s = get_and_validate_strm(c, sid, FRM_STP, true);
    if (unlikely(s == 0))
        return true;

    return true;
}


static bool __attribute__((nonnull))
dec_path_challenge_frame(const uint8_t ** pos,
                         const uint8_t * const end,
                         const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;
    decb_chk(c->path_chlg_in, pos, end, PATH_CHLG_LEN, c, FRM_PCL);

    warn(INF, FRAM_IN "PATH_CHALLENGE" NRM " data=%s",
         pcr_str(c->path_chlg_in));

    if (unlikely(m->udp_len < MIN_INI_LEN))
        warn(NTE, "UDP len %u of PATH_CHALLENGE < %u", m->udp_len, MIN_INI_LEN);

    memcpy(c->path_resp_out, c->path_chlg_in, PATH_CHLG_LEN);
    c->needs_tx = c->tx_path_resp = true;

    return true;
}


static bool __attribute__((nonnull))
dec_path_response_frame(const uint8_t ** pos,
                        const uint8_t * const end,
                        const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;

#ifndef NO_MIGRATION
    decb_chk(c->path_resp_in, pos, end, PATH_CHLG_LEN, c, FRM_PRP);

    warn(INF, FRAM_IN "PATH_RESPONSE" NRM " data=%s", pcr_str(c->path_resp_in));

    if (unlikely(m->udp_len < MIN_INI_LEN)) {
        warn(NTE, "UDP len %u of PATH_RESPONSE < %u, ignoring", m->udp_len,
             MIN_INI_LEN);
        return true;
    }

    if (unlikely(c->tx_path_chlg == false)) {
        warn(NTE, "unexpected PATH_RESPONSE %s, ignoring",
             pcr_str(c->path_resp_in));
        return true;
    }

    if (unlikely(memcmp(c->path_resp_in, c->path_chlg_out, PATH_CHLG_LEN))) {
        warn(NTE, "PATH_RESPONSE %s != %s, ignoring", pcr_str(c->path_resp_in),
             pcr_str(c->path_chlg_out));
        return true;
    }

    warn(NTE, "migration from %s%s%s:%u to %s%s%s:%u complete",
         c->peer.addr.af == AF_INET6 ? "[" : "", w_ntop(&c->peer.addr, ip_tmp),
         c->peer.addr.af == AF_INET6 ? "]" : "", bswap16(c->peer.port),
         c->migr_peer.addr.af == AF_INET6 ? "[" : "",
         w_ntop(&c->migr_peer.addr, ip_tmp),
         c->migr_peer.addr.af == AF_INET6 ? "]" : "",
         bswap16(c->migr_peer.port));

    c->peer = c->migr_peer;
    if (c->holds_sock)
        w_close(c->sock);
    c->sock = c->migr_sock;
    c->migr_sock = 0;
    c->holds_migr_sock = c->tx_path_chlg = false;
    c->tx_limit = 0;

#else
    uint8_t pri[PATH_CHLG_LEN];
    decb_chk(pri, pos, end, PATH_CHLG_LEN, c, FRM_PRP);
    warn(INF, FRAM_IN "PATH_RESPONSE" NRM " data=%s", pcr_str(pri));
    warn(NTE, "unexpected PATH_RESPONSE %s, ignoring", pcr_str(pri));
#endif

    return true;
}


static bool __attribute__((nonnull))
dec_new_cid_frame(const uint8_t ** pos,
                  const uint8_t * const end,
                  const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;
    struct cid dcid = {.seq = 0
#ifndef NO_SRT_MATCHING
                       ,
                       .has_srt = true
#endif
    };
    uint_t rpt = 0;

    decv_chk(&dcid.seq, pos, end, c, FRM_CID);
    decv_chk(&rpt, pos, end, c, FRM_CID);
    dec1_chk(&dcid.len, pos, end, c, FRM_CID);

#ifndef NO_SRT_MATCHING
    uint8_t * const srt = dcid.srt;
#else
    uint8_t srt[SRT_LEN];
#endif

    if (likely(dcid.len <= CID_LEN_MAX)) {
        decb_chk(dcid.id, pos, end, dcid.len, c, FRM_CID);
        decb_chk(srt, pos, end, SRT_LEN, c, FRM_CID);
    }

#if !defined(NO_MIGRATION) || !defined(NDEBUG)
    const bool dup =
#ifndef NO_MIGRATION
        cid_by_seq(&c->dcids.act, dcid.seq) != 0 || dcid.seq <= c->dcid->seq;
#else
        false;
#endif
#endif

    warn(INF,
         FRAM_IN "NEW_CONNECTION_ID" NRM " seq=%" PRIu " rpt=%" PRIu
                 " len=%u dcid=%s srt=%s%s",
         dcid.seq, rpt, dcid.len, cid_str(&dcid), srt_str(srt),
         dup ? " [" RED "dup" NRM "]" : "");

    if (unlikely(dcid.len == 0 && c->dcid->len != 0))
        err_close_return(c, ERR_FRAM_ENC, FRM_CID,
                         "NEW_CONNECTION_ID len == 0");

    if (unlikely(dcid.len != 0 && c->dcid->len == 0))
        err_close_return(c, ERR_FRAM_ENC, FRM_CID,
                         "NEW_CONNECTION_ID len != 0");

#ifndef NO_MIGRATION
    const uint_t max_act_cids =
        c->tp_mine.act_cid_lim + (c->tp_peer.pref_addr.cid.len ? 1 : 0);
    if (likely(dup == false) && unlikely(cid_cnt(&c->dcids) > max_act_cids))
        err_close_return(c, ERR_CID_LIMT, FRM_CID,
                         "illegal seq %" PRIu " (have %" PRIu "/%" PRIu ")",
                         dcid.seq, cid_cnt(&c->dcids), max_act_cids);

    if (unlikely(rpt > dcid.seq))
        err_close_return(c, ERR_PV, FRM_CID, "illegal rpt %" PRIu, rpt);

    if (unlikely(dcid.len > CID_LEN_MAX))
        err_close_return(c, ERR_PV, FRM_CID, "illegal len %u", dcid.len);

    if (rpt > c->rpt_max) {
        retire_prior_to(&c->dcids, rpt);
        c->rpt_max = rpt;
        if (c->dcid->seq < rpt) {
            c->tx_retire_cid = true;
            use_next_dcid(c, false);
        }

    } else if (c->rpt_max)
        warn(INF, "rpt %" PRIu " <= prev max %" PRIu ", ignoring", rpt,
             c->rpt_max);

    if (dup == false) {
        struct cid * const ndcid = cid_ins(&c->dcids, &dcid);
        if (unlikely(ndcid == 0))
            err_close_return(c, ERR_PV, FRM_CID, "cannot ins cid %s",
                             cid_str(&dcid));
#ifndef NO_SRT_MATCHING
        if (unlikely(conns_by_srt_ins(c, ndcid->srt) == false))
            err_close_return(c, ERR_PV, FRM_CID, "cannot ins srt %s",
                             srt_str(ndcid->srt));
#endif
    }

#else
    err_close_return(c, ERR_PV, FRM_CID,
                     "migration disabled but got NEW_CONNECTION_ID");
#endif

    return true;
}


static bool __attribute__((nonnull))
dec_reset_stream_frame(const uint8_t ** pos,
                       const uint8_t * const end,
                       const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;
    dint_t sid = 0;
    decv_chk((uint_t *)&sid, pos, end, c, FRM_RST);

    uint_t err_code;
    decv_chk(&err_code, pos, end, c, FRM_RST);

    uint_t off = 0;
    decv_chk(&off, pos, end, c, FRM_RST);

    warn(INF,
         FRAM_IN "RESET_STREAM" NRM " id=" FMT_SID " err=%s0x%" PRIx NRM
                 " off=%" PRIu,
         sid, err_code ? RED : NRM, err_code, off);

    struct q_stream * const s = get_and_validate_strm(c, sid, FRM_RST, false);
    if (unlikely(s == 0))
        return true;

    // FIXME: not sure is this is even needed here:
    // chk_finl_size(off, s, FRM_RST);
    strm_to_state(s, strm_clsd);

    return true;
}


static bool __attribute__((nonnull))
dec_retire_cid_frame(const uint8_t ** pos,
                     const uint8_t * const end,
                     const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;
    uint_t seq = 0;
    decv_chk(&seq, pos, end, c, FRM_RTR);

    warn(INF, FRAM_IN "RETIRE_CONNECTION_ID" NRM " seq=%" PRIu, seq);

#ifndef NO_MIGRATION
    if (likely(c->scid) && unlikely(c->scid->seq == seq))
        err_close_return(c, ERR_PV, FRM_RTR, "can't retire current cid");

    struct cid * const scid = cid_by_seq(&c->scids.act, seq);
    if (unlikely(scid == 0)) {
        warn(INF, "no cid seq %" PRIu, seq);
        goto done;
    } else if (c->scid->seq == scid->seq) {
        struct cid * const next_scid = next_cid(&c->scids, scid->seq);
        if (unlikely(next_scid == 0))
            err_close_return(c, ERR_INTL, FRM_RTR, "no next scid");
        c->scid = next_scid;
    }
    conns_by_id_del(scid);
    cid_del(&c->scids, scid);

    // rx of RETIRE_CONNECTION_ID means we should send more
    c->tx_ncid = true;
done:
#endif
    return true;
}


static bool __attribute__((nonnull))
dec_new_token_frame(const uint8_t ** pos,
                    const uint8_t * const end,
                    const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;
    uint_t tok_len = 0;
    decv_chk(&tok_len, pos, end, c, FRM_TOK);

    const uint_t act_tok_len = MIN(tok_len, (uint_t)(end - *pos));

    if (unlikely(act_tok_len > MAX_TOK_LEN))
        err_close_return(c, ERR_FRAM_ENC, FRM_TOK, "tok len > max");

    uint8_t tok[MAX_TOK_LEN];
    decb_chk(tok, pos, end, (uint16_t)act_tok_len, c, FRM_TOK);

    warn(INF, FRAM_IN "NEW_TOKEN" NRM " len=%" PRIu " tok=%s", tok_len,
         tok_str(tok, tok_len));

    if (unlikely(is_clnt(c) == false))
        err_close_return(c, ERR_PV, FRM_TOK, "serv rx'ed NEW_TOKEN");

    if (unlikely(tok_len != act_tok_len))
        err_close_return(c, ERR_FRAM_ENC, FRM_TOK, "illegal tok len");

    // TODO: actually do something with the token

    return is_clnt(c); // only servers may send NEW_TOKEN frames
}


bool dec_frames(struct q_conn * const c,
                struct w_iov ** vv,
                struct pkt_meta ** mm)
{
#ifndef NO_QINFO
    struct q_conn_info * const ci = &c->i;
#else
    void * const ci = 0;
#endif
    struct w_iov * v = *vv;
    struct pkt_meta * m = *mm;
    const uint8_t * pos = v->buf + m->hdr.hdr_len;
    const uint8_t * start = v->buf;
    const uint8_t * end = v->buf + v->len;
    bool ok = false;

#if !defined(NDEBUG) && !defined(FUZZING) && defined(FUZZER_CORPUS_COLLECTION)
    // when called from the fuzzer, v->wv_af is zero
    if (v->wv_af)
        write_to_corpus(corpus_frm_dir, pos, (size_t)(end - pos));
#endif

    while (likely(pos < end)) {
        uint8_t type = *(pos++); // dec1_chk not needed here, pos is < len

        // check that frame type is allowed in this pkt type
        static const struct frames frame_ok[] = {
            [ep_init] = bitset_t_initializer(1 << FRM_PAD | 1 << FRM_PNG |
                                             1 << FRM_CRY | 1 << FRM_CLQ |
                                             1 << FRM_ACK | 1 << FRM_ACE),
            [ep_0rtt] = bitset_t_initializer(
                1 << FRM_PAD | 1 << FRM_PNG | 1 << FRM_RST | 1 << FRM_STP |
                1 << FRM_STR | 1 << FRM_STR_09 | 1 << FRM_STR_0a |
                1 << FRM_STR_0b | 1 << FRM_STR_0c | 1 << FRM_STR_0d |
                1 << FRM_STR_0e | 1 << FRM_STR_0f | 1 << FRM_MCD |
                1 << FRM_MSD | 1 << FRM_MSB | 1 << FRM_MSU | 1 << FRM_CDB |
                1 << FRM_SDB | 1 << FRM_SBB | 1 << FRM_SBU | 1 << FRM_CID |
                1 << FRM_PCL),
            [ep_hshk] = bitset_t_initializer(1 << FRM_PAD | 1 << FRM_PNG |
                                             1 << FRM_CRY | 1 << FRM_CLQ |
                                             1 << FRM_ACK | 1 << FRM_ACE),
            [ep_data] = bitset_t_initializer(
                1 << FRM_PAD | 1 << FRM_PNG | 1 << FRM_CRY | 1 << FRM_CLQ |
                1 << FRM_CLA | 1 << FRM_ACK | 1 << FRM_ACE | 1 << FRM_RST |
                1 << FRM_STP | 1 << FRM_TOK | 1 << FRM_STR | 1 << FRM_STR_09 |
                1 << FRM_STR_0a | 1 << FRM_STR_0b | 1 << FRM_STR_0c |
                1 << FRM_STR_0d | 1 << FRM_STR_0e | 1 << FRM_STR_0f |
                1 << FRM_MCD | 1 << FRM_MSD | 1 << FRM_MSB | 1 << FRM_MSU |
                1 << FRM_CDB | 1 << FRM_SDB | 1 << FRM_SBB | 1 << FRM_SBU |
                1 << FRM_CID | 1 << FRM_RTR | 1 << FRM_PCL | 1 << FRM_PRP |
                1 << FRM_HSD)};
        if (likely(type < FRM_MAX) &&
            unlikely(bit_isset(FRM_MAX, type,
                               &frame_ok[epoch_for_pkt_type(m->hdr.type)]) ==
                     false))
            err_close_return(c, ERR_PV, type, "0x%02x frame not OK in %s pkt",
                             type, pkt_type_str(m->hdr.flags, &m->hdr.vers));

        // special-case for optimized parsing of padding ranges
        if (type == FRM_PAD) {
            const uint8_t * const pad_start = pos;

            while (likely(type == FRM_PAD)) {
                uint64_t pad = UINT64_MAX;
                const size_t left = (size_t)(end - pos);
                memcpy(&pad, pos, MIN(left, sizeof(uint64_t)));
                if (pad == 0)
                    pos += sizeof(pad);
                else {
                    pos += __builtin_ctzll(pad) >> 3;
                    type = *(pos++);
                    break;
                }
            }
            const uint16_t pad_len = (uint16_t)(pos - pad_start);
            track_frame(m, ci, FRM_PAD, pad_len);
            warn(INF, FRAM_IN "PADDING" NRM " len=%u", pad_len);
            if (pos >= end)
                break;
        }

        switch (type) {
        case FRM_CRY:
        case FRM_STR:
        case FRM_STR_09:
        case FRM_STR_0a:
        case FRM_STR_0b:
        case FRM_STR_0c:
        case FRM_STR_0d:
        case FRM_STR_0e:
        case FRM_STR_0f:;
            static const struct frames cry_or_str =
                bitset_t_initializer(1 << FRM_CRY | 1 << FRM_STR);
            if (unlikely(bit_overlap(FRM_MAX, &m->frms, &cry_or_str)) &&
                m->strm) {
                // already had at least one stream or crypto frame in this
                // packet with non-duplicate data, so generate (another) copy
#ifdef DEBUG_EXTRA
                warn(DBG, "addtl stream or crypto frame, copy");
#endif
                const uint16_t off = (uint16_t)(pos - v->buf - 1);
                struct pkt_meta * mdup;
                struct w_iov * const vdup = dup_iov(v, &mdup, off);
                if (unlikely(vdup == 0)) {
                    warn(WRN, "could not alloc iov");
                    break;
                }
                pm_cpy(mdup, m, false);
                // adjust w_iov start and len to stream frame data
                v->buf += m->strm_data_pos;
                v->len = m->strm_data_len;
                // continue parsing in the copied w_iov
                v = *vv = vdup;
                m = *mm = mdup;
                pos = v->buf + 1;
                start = v->buf;
                end = v->buf + v->len;
            }
            ok = dec_stream_or_crypto_frame(type, &pos, end, m, v);
            type = type == FRM_CRY ? FRM_CRY : FRM_STR;
            break;

        case FRM_ACE:
        case FRM_ACK:
            ok = dec_ack_frame(type, &pos, start, end, m);
            type = FRM_ACK; // only enc FRM_ACK in bitstr_t
            break;

        case FRM_RST:
            ok = dec_reset_stream_frame(&pos, end, m);
            break;

        case FRM_CLQ:
        case FRM_CLA:
            ok = dec_close_frame(type, &pos, end, m);
            break;

        case FRM_PNG:
            warn(INF, FRAM_IN "PING" NRM);
            ok = true;
            break;

        case FRM_HSD:
            warn(INF, FRAM_IN "HANDSHAKE_DONE" NRM);
            ok = is_clnt(c);
            if (likely(ok)) {
                if (unlikely(c->pns[pn_hshk].abandoned == false))
                    abandon_pn(&c->pns[pn_hshk]);
            } else
                err_close_return(c, ERR_PV, FRM_HSD,
                                 "serv rx'ed HANDSHAKE_DONE");
            break;

        case FRM_MSD:
            ok = dec_max_strm_data_frame(&pos, end, m);
            break;

        case FRM_MSB:
        case FRM_MSU:
            ok = dec_max_strms_frame(type, &pos, end, m);
            break;

        case FRM_MCD:
            ok = dec_max_data_frame(&pos, end, m);
            break;

        case FRM_SDB:
            ok = dec_strm_data_blocked_frame(&pos, end, m);
            break;

        case FRM_CDB:
            ok = dec_data_blocked_frame(&pos, end, m);
            break;

        case FRM_SBB:
        case FRM_SBU:
            ok = dec_streams_blocked_frame(type, &pos, end, m);
            break;

        case FRM_STP:
            ok = dec_stop_sending_frame(&pos, end, m);
            break;

        case FRM_PCL:
            ok = dec_path_challenge_frame(&pos, end, m);
            break;

        case FRM_PRP:
            ok = dec_path_response_frame(&pos, end, m);
            break;

        case FRM_CID:
            ok = dec_new_cid_frame(&pos, end, m);
            break;

        case FRM_TOK:
            ok = dec_new_token_frame(&pos, end, m);
            break;

        case FRM_RTR:
            ok = dec_retire_cid_frame(&pos, end, m);
            break;

        default:
            err_close_return(c, ERR_FRAM_ENC, type,
                             "unknown 0x%02x frame at pos %u", type,
                             (uint16_t)(pos - v->buf));
        }

        if (unlikely(ok == false))
            // there was an error parsing a frame
            err_close_return(c, ERR_FRAM_ENC, type,
                             "error parsing 0x%02x frame at pos %lu", type,
                             pos - v->buf);

        // record this frame type in the meta data
        track_frame(m, ci, type, 1);
    }

    if (m->strm_data_pos) {
        // adjust w_iov start and len to stream frame data
        v->buf += m->strm_data_pos;
        v->len = m->strm_data_len;
    }

    // packets MUST have at least one frame
    if (unlikely(bit_empty(FRM_MAX, &m->frms)))
        err_close_return(c, ERR_PV, 0, "rx'ed pkt w/o frames");

    // track outstanding frame types in the pn space
    bit_or(FRM_MAX, &m->pn->rx_frames, &m->frms);

    return true;
}


void enc_padding_frame(struct q_conn_info * const ci,
                       uint8_t ** pos,
                       const uint8_t * const end
#ifdef NDEBUG
                       __attribute__((unused))
#endif
                       ,
                       struct pkt_meta * const m,
                       const uint16_t len)
{
    if (unlikely(len == 0))
        return;
    assure(*pos + len <= end, "buffer overflow w/len %u", len);
    memset(*pos, FRM_PAD, len);
    *pos += len;
    warn(INF, FRAM_OUT "PADDING" NRM " len=%u", len);
    track_frame(m, ci, FRM_PAD, len);
}


#define encv_chk(pos, end, val)                                                \
    do {                                                                       \
        if (unlikely(*(pos) + varint_size(val) > (end))) {                     \
            warn(DBG, "out of space, ACK frame not encoded");                  \
            goto no_ack;                                                       \
        }                                                                      \
        encv((pos), (end), (val));                                             \
    } while (0)


bool enc_ack_frame(struct q_conn_info * const ci,
                   uint8_t ** pos,
                   const uint8_t * const start,
                   const uint8_t * const end,
                   struct pkt_meta * const m,
                   struct pn_space * const pn)
{
    const uint8_t type =
#ifndef NO_ECN
        (pn->ecn_rxed[ECN_ECT0] || pn->ecn_rxed[ECN_ECT1] ||
         pn->ecn_rxed[ECN_CE])
            ? FRM_ACE
            :
#endif
            FRM_ACK;
    uint8_t * const init_pos = *pos;
    if (unlikely(*pos + 1 > end))
        goto no_ack;
    enc1(pos, end, type);

    const struct ival * const first_rng = diet_max_ival(&pn->recv);
    if (unlikely(first_rng == 0))
        goto no_ack;
    encv_chk(pos, end, first_rng->hi);

    // handshake pkts always use the default ACK delay exponent
    struct q_conn * const c = pn->c;
    const uint_t ade = m->hdr.type == LH_INIT || m->hdr.type == LH_HSHK
                           ? DEF_ACK_DEL_EXP
                           : c->tp_mine.ack_del_exp;
    const uint64_t ack_delay =
        NS_TO_US(w_now(CLOCK_MONOTONIC_RAW) - diet_timestamp(first_rng)) >> ade;
    encv_chk(pos, end, ack_delay);

    const uint_t ack_rng_cnt = diet_cnt(&pn->recv) - 1;
    encv_chk(pos, end, ack_rng_cnt);

    uint_t prev_lo = 0;
    struct ival * b;
    diet_foreach_rev (b, diet, &pn->recv) {
        uint_t gap = 0;
        if (prev_lo) {
            gap = prev_lo - b->hi - 2;
            encv_chk(pos, end, gap);
        }
        const uint_t ack_rng = b->hi - b->lo;
#ifndef NDEBUG
        if (ack_rng) {
            if (prev_lo)
                warn(INF,
                     FRAM_OUT "ACK" NRM " gap=%" PRIu " rng=%" PRIu
                              " [" FMT_PNR_IN ".." FMT_PNR_IN "]",
                     gap, ack_rng, b->lo, shorten_ack_nr(b->hi, ack_rng));
            else
                warn(INF,
                     FRAM_OUT "ACK" NRM " 0x%02x%s lg=" FMT_PNR_IN
                              " delay=%" PRIu " (%" PRIu " usec) cnt=%" PRIu
                              " rng=%" PRIu " [" FMT_PNR_IN ".." FMT_PNR_IN "]",
                     type, type == FRM_ACE ? "=ECN" : "", first_rng->hi,
                     (uint_t)ack_delay, (uint_t)ack_delay << ade, ack_rng_cnt,
                     ack_rng, b->lo, shorten_ack_nr(b->hi, ack_rng));

        } else {
            if (prev_lo)
                warn(INF,
                     FRAM_OUT "ACK" NRM " gap=%" PRIu " rng=%" PRIu
                              " [" FMT_PNR_IN "]",
                     gap, ack_rng, b->hi);
            else
                warn(INF,
                     FRAM_OUT "ACK" NRM " 0x%02x%s lg=" FMT_PNR_IN
                              " delay=%" PRIu " (%" PRIu " usec) cnt=%" PRIu
                              " rng=%" PRIu " [" FMT_PNR_IN "]",
                     type, type == FRM_ACE ? "=ECN" : "", first_rng->hi,
                     (uint_t)ack_delay, (uint_t)ack_delay << ade, ack_rng_cnt,
                     ack_rng, first_rng->hi);
        }
#endif
        encv_chk(pos, end, ack_rng);
        prev_lo = b->lo;
    }

#ifndef NO_ECN
    if (type == FRM_ACE) {
        // encode ECN
        encv_chk(pos, end, pn->ecn_rxed[ECN_ECT0]);
        encv_chk(pos, end, pn->ecn_rxed[ECN_ECT1]);
        encv_chk(pos, end, pn->ecn_rxed[ECN_CE]);
        warn(INF,
             FRAM_OUT "ECN" NRM " ect0=%s%" PRIu NRM " ect1=%s%" PRIu NRM
                      " ce=%s%" PRIu NRM,
             pn->ecn_rxed[ECN_ECT0] ? BLU : NRM, pn->ecn_rxed[ECN_ECT0],
             pn->ecn_rxed[ECN_ECT1] ? BLU : NRM, pn->ecn_rxed[ECN_ECT1],
             pn->ecn_rxed[ECN_CE] ? BLU : NRM, pn->ecn_rxed[ECN_CE]);
    }
#endif

    timeouts_del(ped(c->w)->wheel, &c->ack_alarm);
    bit_zero(FRM_MAX, &pn->rx_frames);
    pn->pkts_lost_since_last_ack_tx = pn->pkts_rxed_since_last_ack_tx = 0;
    pn->imm_ack = false;
    track_frame(m, ci, FRM_ACK, 1);
    m->ack_frm_pos = (uint16_t)(init_pos - start);
    return true;

no_ack:;
    *pos = init_pos;
    return false;
}


void calc_lens_of_stream_or_crypto_frame(struct pkt_meta * const m,
                                         const struct w_iov * const v,
                                         const struct q_stream * const s,
                                         const bool rtx)
{
    const bool enc_strm = s->id >= 0;
    m->strm_data_len = (uint16_t)(v->len - m->strm_data_pos);
    uint16_t hlen = 1; // type byte

    const uint_t off = unlikely(rtx) ? m->strm_off : s->out_data;
    if (likely(enc_strm)) {
        hlen += varint_size((uint_t)s->id);
        if (likely(off))
            hlen += varint_size(off);
        if (unlikely(rtx && is_set(F_STREAM_LEN, v->buf[m->strm_frm_pos])) ||
            m->strm_data_len != s->c->rec.max_ups - AEAD_LEN - DATA_OFFSET)
            hlen += varint_size(m->strm_data_len);
    } else {
        hlen += varint_size(off);
        hlen += varint_size(m->strm_data_len);
    }
    m->strm_frm_pos = m->strm_data_pos - hlen;
}


void enc_stream_or_crypto_frame(uint8_t ** pos,
                                const uint8_t * const end,
                                struct pkt_meta * const m,
                                struct w_iov * const v,
                                struct q_stream * const s)
{
    const bool enc_strm = s->id >= 0;
    uint8_t type = likely(enc_strm) ? FRM_STR : FRM_CRY;

    m->strm = s;
    m->strm_off = s->out_data;

    (*pos)++;
    if (likely(enc_strm))
        encv(pos, end, (uint_t)s->id);
    if (m->strm_off || unlikely(!enc_strm)) {
        if (likely(enc_strm))
            type |= F_STREAM_OFF;
        encv(pos, end, m->strm_off);
    }
    if (m->strm_data_len != s->c->rec.max_ups - AEAD_LEN - DATA_OFFSET ||
        unlikely(!enc_strm)) {
        if (likely(enc_strm))
            type |= F_STREAM_LEN;
        encv(pos, end, m->strm_data_len);
    }
    if (likely(enc_strm) && unlikely(m->is_fin))
        type |= F_STREAM_FIN;
    *pos = v->buf + m->strm_frm_pos;
    enc1(pos, end, type);

    *pos = v->buf + m->strm_data_pos + m->strm_data_len;
    log_stream_or_crypto_frame(false, m, type, s->id, false, sdt_seq);

    track_bytes_out(s, m->strm_data_len);
    assure(!enc_strm || m->strm_off < s->out_data_max,
           "exceeded fc window: %" PRIu " >= %" PRIu, m->strm_off,
           s->out_data_max);
    track_frame(m,
#ifndef NO_QINFO
                &s->c->i
#else
                0
#endif
                ,
                type == FRM_CRY ? FRM_CRY : FRM_STR, 1);
}


void enc_close_frame(struct q_conn_info * const ci,
                     uint8_t ** pos,
                     const uint8_t * const end,
                     struct pkt_meta * const m)
{
    const struct q_conn * const c = m->pn->c;
    const uint8_t type =
        (c->err_frm == 0 && c->err_code != ERR_PV) ? FRM_CLA : FRM_CLQ;

    enc1(pos, end, type);
    encv(pos, end, c->err_code);
    if (type == FRM_CLQ)
        enc1(pos, end, c->err_frm);

#ifndef NO_ERR_REASONS
    const uint8_t reas_len = c->err_reason_len;
    const char * const reas = c->err_reason;
#else
    const uint8_t reas_len = 0;
    const char reas[] = "";
#endif

    encv(pos, end, reas_len);
    if (reas_len)
        encb(pos, end, (const uint8_t *)reas, reas_len);

    warn(INF,
         FRAM_OUT "CONNECTION_CLOSE" NRM " 0x%02x=%s err=%s0x%" PRIx NRM
                  " frame=0x%02x rlen=%u%s%s%.*s" NRM,
         type, type == FRM_CLQ ? "quic" : "app", c->err_code ? RED : NRM,
         c->err_code, c->err_frm, reas_len, c->err_code ? RED : NRM,
         reas_len ? " reason=" : "", (int)reas_len, reas);

    track_frame(m, ci, type, 1);
}


void enc_max_strm_data_frame(struct q_conn_info * const ci,
                             uint8_t ** pos,
                             const uint8_t * const end,
                             struct pkt_meta * const m,
                             struct q_stream * const s)
{
    enc1(pos, end, FRM_MSD);
    encv(pos, end, (uint_t)s->id);
    encv(pos, end, s->in_data_max);

    warn(INF, FRAM_OUT "MAX_STREAM_DATA" NRM " id=" FMT_SID " max=%" PRIu,
         s->id, s->in_data_max);

    m->max_strm_data_sid = s->id;
    m->max_strm_data = s->in_data_max;
    s->tx_max_strm_data = false;
    track_frame(m, ci, FRM_MSD, 1);
}


void enc_max_data_frame(struct q_conn_info * const ci,
                        uint8_t ** pos,
                        const uint8_t * const end,
                        struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;
    enc1(pos, end, FRM_MCD);
    encv(pos, end, c->tp_mine.max_data);

    warn(INF, FRAM_OUT "MAX_DATA" NRM " max=%" PRIu, c->tp_mine.max_data);

    m->max_data = c->tp_mine.max_data;
    c->tx_max_data = false;
    track_frame(m, ci, FRM_MCD, 1);
}


void enc_max_strms_frame(struct q_conn_info * const ci,
                         uint8_t ** pos,
                         const uint8_t * const end,
                         struct pkt_meta * const m,
                         const bool bidi)
{
    struct q_conn * const c = m->pn->c;
    const uint8_t type = bidi ? FRM_MSB : FRM_MSU;
    enc1(pos, end, type);
    const uint_t max =
        bidi ? c->tp_mine.max_strms_bidi : c->tp_mine.max_strms_uni;
    encv(pos, end, max);

    warn(INF, FRAM_OUT "MAX_STREAMS" NRM " 0x%02x=%s max=%" PRIu, type,
         bidi ? "bi" : "uni", max);

    if (bidi)
        c->tx_max_sid_bidi = false;
    else
        c->tx_max_sid_uni = false;
    track_frame(m, ci, type, 1);
}


void enc_strm_data_blocked_frame(struct q_conn_info * const ci,
                                 uint8_t ** pos,
                                 const uint8_t * const end,
                                 struct pkt_meta * const m,
                                 struct q_stream * const s)
{
    enc1(pos, end, FRM_SDB);
    encv(pos, end, (uint_t)s->id);
    m->strm_data_blocked = s->out_data_max;
    encv(pos, end, m->strm_data_blocked);

    warn(INF, FRAM_OUT "STREAM_DATA_BLOCKED" NRM " id=" FMT_SID " lim=%" PRIu,
         s->id, m->strm_data_blocked);

    track_frame(m, ci, FRM_SDB, 1);
}


void enc_data_blocked_frame(struct q_conn_info * const ci,
                            uint8_t ** pos,
                            const uint8_t * const end,
                            struct pkt_meta * const m)
{
    enc1(pos, end, FRM_CDB);

    m->data_blocked = m->pn->c->tp_peer.max_data + m->strm_data_len;
    encv(pos, end, m->data_blocked);

    warn(INF, FRAM_OUT "DATA_BLOCKED" NRM " lim=%" PRIu, m->data_blocked);

    track_frame(m, ci, FRM_CDB, 1);
}


void enc_streams_blocked_frame(struct q_conn_info * const ci,
                               uint8_t ** pos,
                               const uint8_t * const end,
                               struct pkt_meta * const m,
                               const bool bidi)
{
    struct q_conn * const c = m->pn->c;
    const uint8_t type = bidi ? FRM_SBB : FRM_SBU;
    enc1(pos, end, type);
    const uint_t lim =
        bidi ? c->tp_peer.max_strms_bidi : c->tp_peer.max_strms_uni;
    encv(pos, end, lim);

    warn(INF, FRAM_OUT "STREAMS_BLOCKED" NRM " 0x%02x=%s lim=%" PRIu, type,
         type == FRM_SBB ? "bi" : "uni", lim);

    if (bidi)
        c->sid_blocked_bidi = false;
    else
        c->sid_blocked_uni = false;
    track_frame(m, ci, type, 1);
}


void enc_path_response_frame(struct q_conn_info * const ci,
                             uint8_t ** pos,
                             const uint8_t * const end,
                             struct pkt_meta * const m)
{
    const struct q_conn * const c = m->pn->c;
    enc1(pos, end, FRM_PRP);
    encb(pos, end, c->path_resp_out, sizeof(c->path_resp_out));

    warn(INF, FRAM_OUT "PATH_RESPONSE" NRM " data=%s",
         pcr_str(c->path_resp_out));

    track_frame(m, ci, FRM_PRP, 1);
}


#ifndef NO_MIGRATION
void enc_path_challenge_frame(struct q_conn_info * const ci,
                              uint8_t ** pos,
                              const uint8_t * const end,
                              struct pkt_meta * const m)
{
    const struct q_conn * const c = m->pn->c;
    enc1(pos, end, FRM_PCL);
    encb(pos, end, c->path_chlg_out, sizeof(c->path_chlg_out));

    warn(INF, FRAM_OUT "PATH_CHALLENGE" NRM " data=%s",
         pcr_str(c->path_chlg_out));

    // FIXME: suspend TX until path is verified

    track_frame(m, ci, FRM_PCL, 1);
}
#endif


#ifndef NO_MIGRATION
void enc_new_cid_frame(struct q_conn_info * const ci,
                       uint8_t ** pos,
                       const uint8_t * const end,
                       struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;

    const uint_t max_scid = max_seq(&c->scids);
    const uint_t min_scid = min_seq(&c->scids);
#ifdef DEBUG_EXTRA
    warn(ERR, "min_scid %" PRIu " max_scid %" PRIu, min_scid, max_scid);
    warn(ERR, "max_cid_seq_out %" PRIu " -> %" PRIu, c->max_cid_seq_out,
         MAX(min_scid, c->max_cid_seq_out + 1));
#endif
    c->max_cid_seq_out = MAX(min_scid, c->max_cid_seq_out + 1);
    struct cid ncid = {.seq = c->max_cid_seq_out};

#ifdef DEBUG_EXTRA
    warn(ERR, "min_scid=%" PRIu ", max_scid=%" PRIu ", max_cid_seq_out=%" PRIu,
         min_scid, max_scid, c->max_cid_seq_out);
    struct cid * id;
    sl_foreach (id, &c->scids.act, next)
        warn(ERR, "%s", cid_str(id));
#endif

    // FIXME: send an actual rpt
    uint_t rpt = 0;

#ifndef NO_SRT_MATCHING
    uint8_t * srt;
#else
    uint8_t srt[SRT_LEN];
#endif

    struct cid * enc_cid = &ncid;
    if (ncid.seq <= max_scid) {
        enc_cid = cid_by_seq(&c->scids.act, ncid.seq);
        assure(enc_cid, "max_scid %" PRIu " ncid.seq %" PRIu, max_scid,
               ncid.seq);
#ifndef NO_SRT_MATCHING
        srt = enc_cid->srt;
#endif
    } else {
        mk_rand_cid(&ncid,
                    is_clnt(c) ? ped(c->w)->conf.client_cid_len
                               : ped(c->w)->conf.server_cid_len,
                    true);
        struct cid * const nscid = cid_ins(&c->scids, &ncid);
        if (unlikely(nscid == 0)) {
            err_close(c, ERR_PV, FRM_CID, "cannot ins cid %s", cid_str(&ncid));
            return;
        }
        if (unlikely(conns_by_id_ins(c, nscid) == false)) {
            err_close(c, ERR_PV, FRM_CID, "cannot ins cid %s", cid_str(nscid));
            return;
        }

#ifndef NO_SRT_MATCHING
        srt = ncid.srt;
#endif
    }

    m->min_cid_seq = m->min_cid_seq == 0 ? enc_cid->seq : m->min_cid_seq;

    enc1(pos, end, FRM_CID);
    encv(pos, end, enc_cid->seq);
    encv(pos, end, rpt);
    enc1(pos, end, enc_cid->len);
    encb(pos, end, enc_cid->id, enc_cid->len);
    encb(pos, end, srt, SRT_LEN);

    warn(INF,
         FRAM_OUT "NEW_CONNECTION_ID" NRM " seq=%" PRIu " rpt=%" PRIu
                  " len=%u cid=%s srt=%s %s",
         enc_cid->seq, rpt, enc_cid->len, cid_str(enc_cid), srt_str(srt),
         enc_cid == &ncid ? "" : BLD REV GRN "[RTX]" NRM);

    track_frame(m, ci, FRM_CID, 1);
}
#endif


void enc_new_token_frame(struct q_conn_info * const ci,
                         uint8_t ** pos,
                         const uint8_t * const end,
                         struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;
    enc1(pos, end, FRM_TOK);
    encv(pos, end, c->tok_len);
    encb(pos, end, c->tok, c->tok_len);

    warn(INF, FRAM_OUT "NEW_TOKEN" NRM " len=%u tok=%s", c->tok_len,
         tok_str(c->tok, c->tok_len));

    c->tx_new_tok = false;
    track_frame(m, ci, FRM_TOK, 1);
}


#ifndef NO_MIGRATION
void enc_retire_cid_frame(struct q_conn_info * const ci,
                          uint8_t ** pos,
                          const uint8_t * const end,
                          struct pkt_meta * const m,
                          const uint_t seq)
{
    enc1(pos, end, FRM_RTR);
    encv(pos, end, seq);

    warn(INF, FRAM_OUT "RETIRE_CONNECTION_ID" NRM " seq=%" PRIu, seq);

    m->pn->c->tx_retire_cid = false;
    m->retire_cid_seq = seq;
    track_frame(m, ci, FRM_RTR, 1);
}
#endif


void enc_ping_frame(struct q_conn_info * const ci,
                    uint8_t ** pos,
                    const uint8_t * const end,
                    struct pkt_meta * const m)
{
    enc1(pos, end, FRM_PNG);

    warn(INF, FRAM_OUT "PING" NRM);

    track_frame(m, ci, FRM_PNG, 1);
}


void enc_hshk_done_frame(struct q_conn_info * const ci,
                         uint8_t ** pos,
                         const uint8_t * const end,
                         struct pkt_meta * const m)
{
    enc1(pos, end, FRM_HSD);

    warn(INF, FRAM_OUT "HANDSHAKE_DONE" NRM);

    track_frame(m, ci, FRM_HSD, 1);
    m->pn->c->tx_hshk_done = false;
}
