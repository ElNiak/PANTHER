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
#include <stdint.h>
#include <stdlib.h>
#include <sys/param.h>
#include <time.h>

#ifndef NDEBUG
#include <stdio.h>
#endif

#include <quant/quant.h>

#include "bitset.h"
#include "cid.h"
#include "conn.h"
#include "diet.h"
#include "frame.h"
#include "loop.h"
#include "marshall.h"
#include "pkt.h"
#include "pn.h"
#include "qlog.h"
#include "quic.h"
#include "recovery.h"
#include "stream.h"
#include "tls.h"
#include "tree.h"


static inline bool __attribute__((nonnull))
in_cong_recovery(const struct q_conn * const c, const uint64_t sent_t)
{
    // see InRecovery() pseudo code
    return sent_t <= c->rec.rec_start_t;
}


static bool __attribute__((nonnull)) have_1rtt_keys(struct q_conn * const c)
{
    const struct pn_space * const pn = &c->pns[pn_data];
    return (pn->data.in_1rtt[0].aead && pn->data.out_1rtt[0].aead) ||
           (pn->data.in_1rtt[1].aead && pn->data.out_1rtt[1].aead);
}


static void __attribute__((nonnull)) maybe_open_wnd(struct q_conn * const c)
{
    const bool prev_no_wnd = c->no_wnd;
    c->no_wnd = has_wnd(c, w_max_udp_payload(c->sock)) == false;
    if (c->no_wnd == false && prev_no_wnd)
        c->needs_tx = true;
}


static struct pn_space * __attribute__((nonnull))
earliest_pn(struct q_conn * const c, const bool by_loss_t)
{
    pn_t pna = pn_init;
    while (c->pns[pna].abandoned)
        pna++;

    struct pn_space * pn = &c->pns[pna];
    uint64_t t = by_loss_t ? pn->loss_t : pn->last_ae_tx_t;

    for (pn_t p = pna + 1; p <= pn_data; p++) {
        struct pn_space * const pn_p = &c->pns[p];
        const uint64_t pn_t = by_loss_t ? pn_p->loss_t : pn_p->last_ae_tx_t;

        if (pn_t && (t == 0 || pn_t < t) &&
            (p != pn_data || c->state >= conn_estb)) {
            pn = pn_p;
            t = pn_t;
        }
    }
    return pn;
}


#if !defined(NDEBUG) || !defined(NO_QLOG)
void log_cc(struct q_conn * const c)
{
    const uint_t ssthresh =
        c->rec.cur.ssthresh == UINT_T_MAX ? 0 : c->rec.cur.ssthresh;
    const dint_t delta_in_flight =
        (dint_t)c->rec.cur.in_flight - (dint_t)c->rec.prev.in_flight;
    const dint_t delta_cwnd =
        (dint_t)c->rec.cur.cwnd - (dint_t)c->rec.prev.cwnd;
    const dint_t delta_ssthresh =
        (dint_t)ssthresh -
        (dint_t)(c->rec.prev.ssthresh == UINT_T_MAX ? 0 : c->rec.prev.ssthresh);
    const dint_t delta_srtt =
        (dint_t)c->rec.cur.srtt - (dint_t)c->rec.prev.srtt;
    const dint_t delta_rttvar =
        (dint_t)c->rec.cur.rttvar - (dint_t)c->rec.prev.rttvar;
    if (delta_in_flight || delta_cwnd || delta_ssthresh || delta_srtt ||
        delta_rttvar) {
        warn(DBG,
             "%s conn %s: in_flight=%" PRIu " (%s%+" PRId NRM "), cwnd" NRM
             "=%" PRIu " (%s%+" PRId NRM "), ssthresh=%" PRIu " (%s%+" PRId NRM
             "), srtt=%.3f (%s%+.3f" NRM "), rttvar=%.3f (%s%+.3f" NRM ")",
             conn_type(c), cid_str(c->scid), c->rec.cur.in_flight,
             delta_in_flight > 0 ? GRN : delta_in_flight < 0 ? RED : "",
             delta_in_flight, c->rec.cur.cwnd,
             delta_cwnd > 0 ? GRN : delta_cwnd < 0 ? RED : "", delta_cwnd,
             ssthresh, delta_ssthresh > 0 ? GRN : delta_ssthresh < 0 ? RED : "",
             delta_ssthresh, (float)c->rec.cur.srtt / US_PER_S,
             delta_srtt > 0 ? GRN : delta_srtt < 0 ? RED : "",
             (float)delta_srtt / US_PER_S, (float)c->rec.cur.rttvar / US_PER_S,
             delta_rttvar > 0 ? GRN : delta_rttvar < 0 ? RED : "",
             (float)delta_rttvar / US_PER_S);
    }

    qlog_recovery(rec_mu, "default", c, 0);
    c->rec.prev = c->rec.cur;
}
#endif


static bool peer_not_awaiting_addr_val(struct q_conn * const c)
{
    if (!is_clnt(c))
        return true;

    return hshk_done(c) ||
           bit_isset(FRM_MAX, FRM_ACK, &c->pns[pn_init].rx_frames) ||
           bit_isset(FRM_MAX, FRM_ACK, &c->pns[pn_hshk].rx_frames);
}


void set_ld_timer(struct q_conn * const c)
{
    if (c->state == conn_idle || c->state == conn_clsg || c->state == conn_drng)
        // don't do LD while idle or draining
        return;

    // see SetLossDetectionTimer() pseudo code

    const uint64_t now = w_now(CLOCK_MONOTONIC_RAW);
    const struct pn_space * const pn = earliest_pn(c, true);
    if (pn->loss_t) {
        c->rec.ld_alarm_val = pn->loss_t;
        goto set_to;
    }

    if (unlikely(c->rec.ae_in_flight == 0 && peer_not_awaiting_addr_val(c))) {
#ifdef DEBUG_TIMERS
        warn(DBG, "no RTX-able pkts in flight, stopping ld_alarm on %s conn %s",
             conn_type(c), cid_str(c->scid));
#endif
        timeout_del(&c->rec.ld_alarm);
        return;
    }

    timeout_t to =
        unlikely(c->rec.cur.srtt == 0)
            ? (2 * c->rec.initial_rtt) * NS_PER_US
            : ((c->rec.cur.srtt + MAX(4 * c->rec.cur.rttvar, kGranularity)) *
                   NS_PER_US +
               c->tp_peer.max_ack_del * NS_PER_MS);
    to *= 1 << c->rec.pto_cnt;
    const uint64_t last_ae_tx_t = earliest_pn(c, false)->last_ae_tx_t;
    c->rec.ld_alarm_val = (last_ae_tx_t ? last_ae_tx_t : now) + to;
    // XXX do an RTX at least every 8 seconds (spec violation)
    c->rec.ld_alarm_val = MIN(c->rec.ld_alarm_val, now + 8 * NS_PER_S);

set_to:;
    if (unlikely(c->rec.ld_alarm_val < now)) {
#ifdef DEBUG_TIMERS
        warn(WRN, "LD alarm expired %.3f sec ago",
             (double)(now - c->rec.ld_alarm_val) / NS_PER_S);
#endif
        c->rec.ld_alarm_val = 0;
    } else
        c->rec.ld_alarm_val -= now;

#ifdef DEBUG_TIMERS
    warn(DBG, "LD alarm in %.3f sec on %s conn %s",
         (double)c->rec.ld_alarm_val / NS_PER_S, conn_type(c),
         cid_str(c->scid));
#endif
    timeouts_add(ped(c->w)->wheel, &c->rec.ld_alarm, c->rec.ld_alarm_val);
}


void congestion_event(struct q_conn * const c, const uint64_t sent_t)
{
    // see CongestionEvent() pseudo code

    if (in_cong_recovery(c, sent_t))
        return;

    c->rec.rec_start_t = w_now(CLOCK_MONOTONIC_RAW);
    c->rec.cur.cwnd /= kLossReductionDivisor;
    c->rec.cur.ssthresh = c->rec.cur.cwnd =
        MAX(c->rec.cur.cwnd, kMinimumWindow(c->rec.max_ups));
}


static bool __attribute__((nonnull))
in_persistent_cong(struct pn_space * const pn __attribute__((unused)),
                   const uint_t lg_lost __attribute__((unused)))
{
    // struct q_conn * const c = pn->c;

    // // see InPersistentCongestion() pseudo code
    // const uint64_t cong_period =
    //     kPersistentCongestionThreshold *
    //     (c->rec.cur.srtt + MAX(4 * c->rec.cur.rttvar, kGranularity) +
    //      c->tp_mine.max_ack_del * NS_PER_MS);

    // const struct ival * const i = diet_find(&pn->lost, lg_lost);
    // warn(DBG,
    //      "lg_lost_ival %" PRIu "-%" PRIu ", lg_lost %" PRIu ", period
    //      %.3f", i->lo, i->hi, lg_lost, cong_period);
    // return i->lo + cong_period < lg_lost;
    return false;
}


static void remove_from_in_flight(const struct pkt_meta * const m)
{
    struct q_conn * const c = m->pn->c;
    assure(c->rec.cur.in_flight >= m->udp_len, "in_flight underrun %" PRIu,
           m->udp_len - c->rec.cur.in_flight);
    c->rec.cur.in_flight -= m->udp_len;
    if (m->ack_eliciting) {
        c->rec.ae_in_flight--;
        if (c->rec.ae_in_flight == 0)
            m->pn->last_ae_tx_t = 0;
    }
}


void on_pkt_lost(struct pkt_meta * const m, const bool is_lost)
{
    struct pn_space * const pn = m->pn;
    struct q_conn * const c = pn->c;

    if (m->in_flight) {
        remove_from_in_flight(m);
        if (m->ack_eliciting)
            pn->pkts_lost_since_last_ack_tx++;
    }

    // rest of function is not from pseudo code

    if (unlikely(c->pmtud_pkt != UINT16_MAX &&
                 m->hdr.nr == (c->pmtud_pkt & 0x3fff) &&
                 m->hdr.type == (c->pmtud_pkt >> 14))) {
        c->rec.max_ups = default_max_ups(c->sock->ws_af);
        warn(NTE, RED "PMTU %u not validated, using %u" NRM,
             MIN(w_max_udp_payload(c->sock), (uint16_t)c->tp_peer.max_ups),
             c->rec.max_ups);
        c->pmtud_pkt = UINT16_MAX;
    }

    diet_insert(&pn->acked_or_lost, m->hdr.nr, 0);
    pm_by_nr_del(&pn->sent_pkts, m);

    if (is_lost == false)
        return;

    // if we lost connection or stream control frames, possibly RTX them
    qlog_recovery(rec_pl, "unknown", c, m);

    static const struct frames all_ctrl = bitset_t_initializer(
        1 << FRM_RST | 1 << FRM_STP | 1 << FRM_TOK | 1 << FRM_MCD |
        1 << FRM_MSD | 1 << FRM_MSB | 1 << FRM_MSU | 1 << FRM_CDB |
        1 << FRM_SDB | 1 << FRM_SBB | 1 << FRM_SBU | 1 << FRM_CID |
        1 << FRM_RTR | 1 << FRM_HSD);
    struct frames lost = bitset_t_initializer(0);
    bit_and2(FRM_MAX, &lost, &all_ctrl, &m->frms);
    uint8_t i = (uint8_t)bit_ffs(FRM_MAX, &lost);
    if (i)
        for (i = i - 1; i < FRM_MAX; i++)
            if (bit_isset(FRM_MAX, i, &lost)) {
#ifdef DEBUG_EXTRA
                warn(DBG, "%s pkt %" PRIu " lost ctrl frame: 0x%02x",
                     pkt_type_str(m->hdr.flags, &m->hdr.vers), m->hdr.nr, i);
#endif
                switch (i) {
                case FRM_CID:
                    c->max_cid_seq_out = m->min_cid_seq - 1;
                    break;
                case FRM_CDB:
                case FRM_SDB:
                    // DATA_BLOCKED and STREAM_DATA_BLOCKED RTX'ed automatically
                    break;
                case FRM_HSD:
                    c->tx_hshk_done = true;
                    break;
                case FRM_TOK:
                    c->tx_new_tok = true;
                    break;
                case FRM_SBB:
                    c->sid_blocked_bidi = true;
                    break;
                case FRM_SBU:
                    c->sid_blocked_uni = true;
                    break;
#ifndef NO_MIGRATION
                case FRM_RTR:
                    c->tx_retire_cid = true;
                    break;
#endif
                case FRM_MCD:
                    c->tx_max_data = true;
                    break;
                case FRM_MSD:;
                    struct q_stream * const s =
                        get_stream(c, m->max_strm_data_sid);
                    if (s) {
                        s->tx_max_strm_data = true;
                        need_ctrl_update(s);
                    }
                    break;
                    // NOTE: we never send FRM_RST or FRM_STP, they would need
                    // to be handled like FRM_MSD, with a new meta field
                default:
                    die("unhandled RTX of 0x%02x frame", i);
                }
                c->needs_tx = true;
            }

    m->lost = true;
    if (m->strm && !m->has_rtx) {
        m->strm->lost_cnt++;
        m->strm->out_last = 0;
        assure(m->strm->lost_cnt <= w_iov_sq_cnt(&m->strm->out),
               "strm " FMT_SID " cnt %" PRIu " < lost %" PRIu, m->strm->id,
               w_iov_sq_cnt(&m->strm->out), m->strm->lost_cnt);
    }
}


#ifndef NO_QINFO
#define incr_out_lost c->i.pkts_out_lost++
#else
#define incr_out_lost                                                          \
    do {                                                                       \
    } while (0)
#endif


static void __attribute__((nonnull))
detect_lost_pkts(struct pn_space * const pn, const bool do_cc)
{
    if (unlikely(pn->abandoned))
        return;

    struct q_conn * const c = pn->c;
    pn->loss_t = 0;

    // Minimum time of kGranularity before packets are deemed lost.
    const uint64_t loss_del =
        MAX(kGranularity,
            NS_PER_US * 9 * MAX(c->rec.cur.latest_rtt, c->rec.cur.srtt) / 8);

    // Packets sent before this time are deemed lost.
    const uint64_t lost_send_t = w_now(CLOCK_MONOTONIC_RAW) - loss_del;

    struct diet lost = diet_initializer(lost);
    uint_t lg_lost = UINT_T_MAX;
    uint64_t lg_lost_tx_t = 0;
    bool in_flight_lost = false;

    struct ival * i = 0;
    diet_foreach (i, diet, &pn->sent_pkt_nrs) {
        if (i->lo > pn->lg_acked)
            // diet only has higher values
            break;

        for (uint_t ua = i->lo; ua <= MIN(i->hi, pn->lg_acked - 1); ua++) {
            struct pkt_meta * m;
            find_sent_pkt(pn, ua, &m);

            assure(m, "%s ACKed pkt %" PRIu " not found in sent_pkts",
                   conn_type(c), ua);
            assure(m->acked == false, "%s ACKed %s pkt %" PRIu " in sent_pkts",
                   conn_type(c), pkt_type_str(m->hdr.flags, &m->hdr.vers),
                   m->hdr.nr);
            assure(m->lost == false, "%s lost %s pkt %" PRIu " in sent_pkts",
                   conn_type(c), pkt_type_str(m->hdr.flags, &m->hdr.vers),
                   m->hdr.nr);

            // Mark packet as lost, or set time when it should be marked.
            if (m->t <= lost_send_t ||
                pn->lg_acked >= m->hdr.nr + kPacketThreshold) {
                m->lost = true;
                in_flight_lost |= m->in_flight;
                incr_out_lost;
                if (unlikely(lg_lost == UINT_T_MAX) || m->hdr.nr > lg_lost) {
                    lg_lost = m->hdr.nr;
                    lg_lost_tx_t = m->t;
                }
                diet_insert(&lost, m->hdr.nr, 0);
            } else {
                if (unlikely(!pn->loss_t))
                    pn->loss_t = m->t + loss_del;
                else
                    pn->loss_t = MIN(pn->loss_t, m->t + loss_del);
            }
        }
    }

#ifndef NDEBUG
    int pos = 0;
    unpoison_scratch(ped(c->w)->scratch, ped(c->w)->scratch_len);
    const uint32_t tmp_len = ped(c->w)->scratch_len;
    uint8_t * const tmp = ped(c->w)->scratch;
#endif
    diet_foreach (i, diet, &lost) {
#ifndef NDEBUG
        if ((size_t)pos >= tmp_len) {
            tmp[tmp_len - 2] = tmp[tmp_len - 3] = tmp[tmp_len - 4] = '.';
            tmp[tmp_len - 1] = 0;
            break;
        }

        if (i->lo == i->hi)
            pos += snprintf((char *)&tmp[pos], tmp_len - (size_t)pos,
                            FMT_PNR_OUT "%s", i->lo,
                            splay_next(diet, &lost, i) ? ", " : "");
        else
            pos += snprintf((char *)&tmp[pos], tmp_len - (size_t)pos,
                            FMT_PNR_OUT ".." FMT_PNR_OUT "%s", i->lo, i->hi,
                            splay_next(diet, &lost, i) ? ", " : "");
#endif
        // OnPacketsLost
        for (uint_t ua = i->lo; ua <= i->hi; ua++) {
            struct pkt_meta * m;
            struct w_iov * const v = find_sent_pkt(pn, ua, &m);
            on_pkt_lost(m, true);
            if (m->strm == 0 || m->has_rtx)
                free_iov(v, m);
        }
    }
    diet_free(&lost);

#ifndef NDEBUG
    if (pos)
        warn(DBG, "%s %s lost: %s", conn_type(c), pn_type_str[pn->type], tmp);
    poison_scratch(ped(c->w)->scratch, ped(c->w)->scratch_len);
#endif

    // OnPacketsLost
    if (do_cc && in_flight_lost) {
        congestion_event(c, lg_lost_tx_t);
        if (in_persistent_cong(pn, lg_lost))
            c->rec.cur.cwnd = kMinimumWindow(c->rec.max_ups);
    }

    log_cc(c);
    maybe_open_wnd(c);
    if (lg_lost != UINT_T_MAX)
        timeouts_add(ped(c->w)->wheel, &c->tx_w, 0);
}


void detect_all_lost_pkts(struct q_conn * const c, const bool do_cc)
{
    for (pn_t p = pn_init; p <= pn_data; p++)
        if (unlikely(c->pns[p].abandoned == false))
            detect_lost_pkts(&c->pns[p], do_cc);
}


static void __attribute__((nonnull)) on_ld_timeout(struct q_conn * const c)
{
    // see OnLossDetectionTimeout pseudo code
    struct pn_space * const pn = earliest_pn(c, true);

    if (pn->loss_t) {
#ifdef DEBUG_TIMERS
        warn(DBG, "%s TT alarm on %s conn %s", pn_type_str[pn->type],
             conn_type(c), cid_str(c->scid));
#endif
        detect_all_lost_pkts(c, true);
        set_ld_timer(c);
        return;
    }

    if (have_1rtt_keys(c) == false) {
        // I-D says always 1, but that breaks RTX of Initial+0-RTT
        c->tx_limit = is_clnt(c) && c->try_0rtt ? 2 : 1;
#ifdef DEBUG_TIMERS
        warn(DBG, "anti-deadlock RTX on %s conn %s, limit %u", conn_type(c),
             cid_str(c->scid), c->tx_limit);
#endif
        detect_all_lost_pkts(c, false);
    } else {
        c->tx_limit = 2;
#ifdef DEBUG_TIMERS
        warn(DBG, "PTO alarm #%u on %s conn %s, limit %u", c->rec.pto_cnt,
             conn_type(c), cid_str(c->scid), c->tx_limit);
#endif
    }
    tx(c);

    c->rec.pto_cnt++;
#ifndef NO_QINFO
    c->i.pto_cnt++;
#endif
}


static void __attribute__((nonnull))
track_acked_pkts(struct w_iov * const v, struct pkt_meta * const m)
{
    adj_iov_to_start(v, m);
    const uint8_t * pos = v->buf + m->ack_frm_pos;
    const uint8_t * const end = v->buf + v->len;

    uint64_t lg_ack = 0;
    decv(&lg_ack, &pos, end);
    uint64_t ack_delay = 0;
    decv(&ack_delay, &pos, end);
    uint64_t ack_rng_cnt = 0;
    decv(&ack_rng_cnt, &pos, end);

    // this is a similar loop as in dec_ack_frame() - keep changes in sync
    for (uint64_t n = ack_rng_cnt + 1; n > 0; n--) {
        uint64_t ack_rng = 0;
        decv(&ack_rng, &pos, end);
        diet_remove_ival(&m->pn->recv,
                         &(const struct ival){.lo = (uint_t)(lg_ack - ack_rng),
                                              .hi = (uint_t)lg_ack});
        if (n > 1) {
            uint64_t gap = 0;
            decv(&gap, &pos, end);
            lg_ack -= ack_rng + gap + 2;
        }
    }

    adj_iov_to_data(v, m);
}


void on_pkt_sent(struct pkt_meta * const m)
{
    // see OnPacketSent() pseudo code

    const uint64_t now = w_now(CLOCK_MONOTONIC_RAW);
    m->txed = true;
    pm_by_nr_ins(&m->pn->sent_pkts, m);
    // nr is set in enc_pkt()
    m->t = now;
    // ack_eliciting is set in enc_pkt()
    m->in_flight = m->ack_eliciting || has_frm(m->frms, FRM_PAD);
    // size is set in enc_pkt()

    struct q_conn * const c = m->pn->c;
    if (likely(m->in_flight)) {
        if (likely(m->ack_eliciting)) {
            m->pn->last_ae_tx_t = now;
            c->rec.ae_in_flight++;
        }

        // OnPacketSentCC
        c->rec.cur.in_flight += m->udp_len;
    }

    // we call set_ld_timer(c) once for a TX'ed burst in do_tx() instead of here
}


static void __attribute__((nonnull))
update_rtt(struct q_conn * const c, uint_t ack_del)
{
    // see UpdateRtt() pseudo code
    if (unlikely(c->rec.cur.srtt == 0)) {
        c->rec.cur.min_rtt = c->rec.cur.srtt = c->rec.cur.latest_rtt;
        c->rec.cur.rttvar = c->rec.cur.latest_rtt / 2;
        return;
    }

    c->rec.cur.min_rtt = MIN(c->rec.cur.min_rtt, c->rec.cur.latest_rtt);
    ack_del = MIN(ack_del, c->tp_peer.max_ack_del) * NS_PER_MS;

    const uint_t adj_rtt = c->rec.cur.latest_rtt > c->rec.cur.min_rtt + ack_del
                               ? c->rec.cur.latest_rtt - ack_del
                               : c->rec.cur.latest_rtt;

    c->rec.cur.rttvar = 3 * c->rec.cur.rttvar / 4 +
                        (uint_t)
#if HAVE_64BIT
                                llabs
#else
                                labs
#endif
                            ((dint_t)c->rec.cur.srtt - (dint_t)adj_rtt) /
                            4;
    c->rec.cur.srtt = (7 * c->rec.cur.srtt / 8) + adj_rtt / 8;

#ifndef NO_QINFO
    const float latest_rtt = (float)c->rec.cur.latest_rtt / US_PER_S;
    c->i.min_rtt = MIN(c->i.min_rtt, latest_rtt);
    c->i.max_rtt = MAX(c->i.max_rtt, latest_rtt);
#endif
}


void on_ack_received_1(struct pkt_meta * const lg_ack, const uint_t ack_del)
{
    // see OnAckReceived() pseudo code
    struct pn_space * const pn = lg_ack->pn;
    struct q_conn * const c = pn->c;
    pn->lg_acked = unlikely(pn->lg_acked == UINT_T_MAX)
                       ? lg_ack->hdr.nr
                       : MAX(pn->lg_acked, lg_ack->hdr.nr);

    if (is_ack_eliciting(&pn->tx_frames)) {
        c->rec.cur.latest_rtt =
            (uint_t)NS_TO_US(w_now(CLOCK_MONOTONIC_RAW) - lg_ack->t);
        update_rtt(c, likely(pn->type == pn_data) ? ack_del : 0);
    }

    // ProcessECN() is done in dec_ack_frame()
}


void on_ack_received_2(struct pn_space * const pn)
{
    // see OnAckReceived() pseudo code

    struct q_conn * const c = pn->c;
    detect_lost_pkts(pn, true);
    c->rec.pto_cnt = 0;
    set_ld_timer(c);
}


static void __attribute__((nonnull))
on_pkt_acked_cc(const struct pkt_meta * const m)
{
    // OnPacketAckedCC
    remove_from_in_flight(m);

    struct q_conn * const c = m->pn->c;
    if (in_cong_recovery(c, m->t))
        return;

    // TODO: IsAppLimited check

    if (c->rec.cur.cwnd < c->rec.cur.ssthresh)
        c->rec.cur.cwnd += m->udp_len;
    else
        c->rec.cur.cwnd +=
            (c->rec.max_ups * (uint_t)m->udp_len) / c->rec.cur.cwnd;

#ifndef NO_QINFO
    c->i.max_cwnd = MAX(c->i.max_cwnd, c->rec.cur.cwnd);
#endif
}


void on_pkt_acked(struct w_iov * const v, struct pkt_meta * m)
{
    // see OnPacketAcked() pseudo code
    struct pn_space * const pn = m->pn;
    struct q_conn * const c = pn->c;
    if (m->in_flight && m->lost == false)
        on_pkt_acked_cc(m);
    diet_insert(&pn->acked_or_lost, m->hdr.nr, 0);
    pm_by_nr_del(&pn->sent_pkts, m);

    // rest of function is not from pseudo code

    if (unlikely(c->pmtud_pkt != UINT16_MAX &&
                 m->hdr.nr == (c->pmtud_pkt & 0x3fff) &&
                 m->hdr.type == (c->pmtud_pkt >> 14)))
        validate_pmtu(c);

    // stop ACK'ing packets contained in the ACK frame of this packet
    if (has_frm(m->frms, FRM_ACK))
        track_acked_pkts(v, m);

    struct pkt_meta * const m_rtx = sl_first(&m->rtx);
    if (unlikely(m_rtx)) {
        // this ACKs a pkt with prior or later RTXs
        if (m->has_rtx) {
            // this ACKs a pkt that was since (again) RTX'ed
#ifdef DEBUG_EXTRA
            warn(DBG, "%s %s pkt " FMT_PNR_OUT " was RTX'ed as " FMT_PNR_OUT,
                 conn_type(c), pkt_type_str(m->hdr.flags, &m->hdr.vers),
                 m->hdr.nr, m_rtx->hdr.nr);
#endif
            assure(sl_next(m_rtx, rtx_next) == 0, "RTX chain corrupt");
            if (m_rtx->acked == false) {
                // treat RTX'ed data as ACK'ed; use stand-in w_iov for RTX info
                const uint_t acked_nr = m->hdr.nr;
                pm_by_nr_del(&pn->sent_pkts, m_rtx);
                m->hdr.nr = m_rtx->hdr.nr;
                m_rtx->hdr.nr = acked_nr;
                const uint16_t acked_udp_len = m->udp_len;
                m->udp_len = m_rtx->udp_len;
                m_rtx->udp_len = acked_udp_len;
                pm_by_nr_ins(&pn->sent_pkts, m);
                m = m_rtx;
                // XXX caller will not be aware that we mucked around with m!
            }
#ifdef DEBUG_EXTRA
        } else {
            // this ACKs the last ("real") RTX of a packet
            warn(DBG, "pkt nr=%" PRIu " was earlier TX'ed as %" PRIu,
                 has_pkt_nr(m->hdr.flags, m->hdr.vers) ? m->hdr.nr : 0,
                 has_pkt_nr(m_rtx->hdr.flags, m_rtx->hdr.vers) ? m_rtx->hdr.nr
                                                               : 0);
#endif
        }
    }

    m->acked = true;

    if (unlikely(has_frm(m->frms, FRM_RTR))) {
        struct cid * const id = cid_by_seq(&c->dcids.ret, m->retire_cid_seq);
        // if it doesn't exist, it's been deleted already by previous ACK
        if (id) {
#ifndef NO_SRT_MATCHING
            if (id->has_srt)
                conns_by_srt_del(id->srt);
#endif
            cid_del(&c->dcids, id);
        }
    }

    struct q_stream * const s = m->strm;
    if (s && m->has_rtx == false) {
        // if this ACKs its stream's out_una, move that forward
        bool fin_acked = false;
        struct w_iov * tmp;
        sq_foreach_from_safe (s->out_una, &s->out, next, tmp) {
            struct pkt_meta * const mou = &meta(s->out_una);
            if (mou->acked == false)
                break;
            if (mou->is_fin)
                fin_acked = true;
            // if this ACKs a crypto packet, we can free it
            if (unlikely(s->id < 0 && mou->lost == false)) {
                sq_remove(&s->out, s->out_una, w_iov, next);
                sq_next(s->out_una, next) = 0;
                free_iov(s->out_una, mou);
            }
        }

        if (s->id >= 0 && out_fully_acked(s)) {
            if (unlikely(fin_acked || c->did_0rtt)) {
                // this ACKs a FIN
                c->have_new_data = true;
                strm_to_state(s, s->state == strm_hcrm ? strm_clsd : strm_hclo);
            }
            if (c->did_0rtt)
                maybe_api_return(q_connect, c, 0);
        }

    } else
        free_iov(v, m);
}


void init_rec(struct q_conn * const c)
{
    timeout_del(&c->rec.ld_alarm);
    c->rec.pto_cnt = 0;
    c->rec.max_ups = MIN_INI_LEN;
    c->rec.cur = (struct cc_state){.cwnd = kInitialWindow(c->rec.max_ups),
                                   .ssthresh = UINT_T_MAX,
                                   .min_rtt = UINT_T_MAX};
#if !defined(NDEBUG) || !defined(NO_QLOG)
    c->rec.prev = c->rec.cur;
#endif
    timeout_setcb(&c->rec.ld_alarm, on_ld_timeout, c);
}
