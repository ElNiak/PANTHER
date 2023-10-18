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

#ifndef NO_QLOG

#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#include <quant/quant.h>

#include "bitset.h"
#include "cid.h"
#include "conn.h"
#include "frame.h"
#include "marshall.h"
#include "pkt.h"
#include "pn.h"
#include "qlog.h"
#include "quic.h"
#include "recovery.h"
#include "stream.h"


static const char * __attribute__((const, nonnull))
qlog_pkt_type_str(const uint8_t flags, const void * const vers)
{
    if (is_lh(flags)) {
        if (((const uint8_t * const)vers)[0] == 0 &&
            ((const uint8_t * const)vers)[1] == 0 &&
            ((const uint8_t * const)vers)[2] == 0 &&
            ((const uint8_t * const)vers)[3] == 0)
            return "version_negotiation";
        switch (pkt_type(flags)) {
        case LH_INIT:
            return "initial";
        case LH_RTRY:
            return "retry";
        case LH_HSHK:
            return "handshake";
        case LH_0RTT:
            return "zerortt";
        }
    } else if (pkt_type(flags) == SH)
        return "onertt";
    return "unknown";
}


static void qlog_common(struct q_conn * const c)
{
    const uint64_t now = w_now(CLOCK_REALTIME);
    dprintf(c->qlog, "%s[%" PRIu, likely(c->qlog_last_t) ? "," : "",
            (uint_t)NS_TO_US(now - c->qlog_last_t));
    c->qlog_last_t = now;
}


void qlog_init(struct q_conn * const c)
{
    // remove existing file and create new one; this happens during vneg
    if (c->qlog) {
        remove(c->qlog_file);
        c->qlog_last_t = 0;
        c->qlog = 0;
    }

    snprintf(c->qlog_file, sizeof(c->qlog_file), "%s/%s.%s.qlog",
             ped(c->w)->conf.qlog_dir,
             is_clnt(c) ? hex2str(c->dcid->id, c->dcid->len,
                                  (char[hex_str_len(CID_LEN_MAX)]){""},
                                  hex_str_len(CID_LEN_MAX))
                        : hex2str(c->scid->id, c->scid->len,
                                  (char[hex_str_len(CID_LEN_MAX)]){""},
                                  hex_str_len(CID_LEN_MAX)),
             is_clnt(c) ? "clnt" : "serv");

    c->qlog = open(c->qlog_file, O_CREAT | O_WRONLY | O_CLOEXEC,
                   S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH);
    warn(DBG, "qlog file is %s", c->qlog_file);
    if (unlikely(c->qlog < 0)) {
        warn(ERR, "could not open %s: %s", c->qlog_file, strerror(errno));
        return;
    }

    dprintf(c->qlog,
            "{\"qlog_version\":\"draft-01\",\"title\":\"%s %s/%s "
            "qlog\",\"traces\":[{\"vantage_point\":{\"type\":\"%s\"},"
            "\"configuration\":{\"time_units\":\"us\"},\"common_fields\":{"
            "\"group_id\":\"%s\",\"protocol_type\":\"QUIC_HTTP3\"},\"event_"
            "fields\":[\"delta_time\",\"category\","
            "\"event\",\"trigger\",\"data\"],\"events\":[",
            quant_name, quant_version, QUANT_COMMIT_HASH_ABBREV_STR,
            is_clnt(c) ? "client" : "server",
            hex2str(c->odcid.id, c->odcid.len,
                    (char[hex_str_len(CID_LEN_MAX)]){""},
                    hex_str_len(CID_LEN_MAX)));
}


void qlog_close(struct q_conn * const c)
{
    if (c->qlog) {
        dprintf(c->qlog, "]}]}");
        close(c->qlog);
    }
}


void qlog_transport(const qlog_pkt_evt_t evt,
                    const char * const trg,
                    struct w_iov * const v,
                    const struct pkt_meta * const m)
{
    if (m->pn == 0)
        return;

    struct q_conn * const c = m->pn->c;

    if (c->qlog == 0)
        return;

    qlog_common(c);

    static const char * const evt_str[] = {[pkt_tx] = "packet_sent",
                                           [pkt_rx] = "packet_received",
                                           [pkt_dp] = "packet_dropped"};
    dprintf(c->qlog,
            ",\"transport\",\"%s\",\"%s\",{\"packet_type\":\"%s\",\"header\":{"
            "\"packet_size\":%u",
            evt_str[evt], trg, qlog_pkt_type_str(m->hdr.flags, &m->hdr.vers),
            m->udp_len);
    if (is_lh(m->hdr.flags) == false || (m->hdr.vers && m->hdr.type != LH_RTRY))
        dprintf(c->qlog, ",\"packet_number\":%" PRIu, m->hdr.nr);
    dprintf(c->qlog, "}");

    if (evt == pkt_dp)
        goto done;

    static const struct frames qlog_frm =
        bitset_t_initializer(1 << FRM_ACK | 1 << FRM_STR);
    if (bit_overlap(FRM_MAX, &m->frms, &qlog_frm) == false)
        goto done;

    dprintf(c->qlog, ",\"frames\":[");
    int prev_frame = 0;
    if (has_frm(m->frms, FRM_STR)) {
        prev_frame = dprintf(c->qlog,
                             "%s{\"frame_type\":\"stream\",\"stream_id\":%" PRId
                             ",\"length\":%u,\"offset\":%" PRIu,
                             /* prev_frame ? "," : */ "", m->strm->id,
                             m->strm_data_len, m->strm_off);
        if (m->is_fin)
            dprintf(c->qlog, ",\"fin\":true");
        dprintf(c->qlog, "}");
    }

    if (has_frm(m->frms, FRM_ACK)) {
        adj_iov_to_start(v, m);
        const uint8_t * pos = v->buf + m->ack_frm_pos;
        const uint8_t * const end = v->buf + v->len;

        uint8_t type = *pos++;
        uint64_t lg_ack = 0;
        decv(&lg_ack, &pos, end);
        uint64_t ack_delay = 0;
        decv(&ack_delay, &pos, end);
        uint64_t ack_rng_cnt = 0;
        decv(&ack_rng_cnt, &pos, end);

        // prev_frame =
        dprintf(c->qlog,
                "%s{\"frame_type\":\"ack\",\"ack_delay\":%" PRIu
                ",\"acked_ranges\":[",
                prev_frame ? "," : "", (uint_t)ack_delay);

        // this is a similar loop as in dec_ack_frame() - keep changes in sync
        for (uint64_t n = ack_rng_cnt + 1; n > 0; n--) {
            uint64_t ack_rng = 0;
            decv(&ack_rng, &pos, end);
            dprintf(c->qlog, "%s[%" PRIu ",%" PRIu "]",
                    (n <= ack_rng_cnt ? "," : ""), (uint_t)lg_ack - ack_rng,
                    (uint_t)lg_ack);
            if (n > 1) {
                uint64_t gap = 0;
                decv(&gap, &pos, end);
                lg_ack -= ack_rng + gap + 2;
            }
        }
        dprintf(c->qlog, "]");

        if (type == FRM_ACE) {
            uint64_t ect0;
            decv(&ect0, &pos, end);
            uint64_t ect1;
            decv(&ect1, &pos, end);
            uint64_t ce;
            decv(&ce, &pos, end);

            // prev_frame =
            dprintf(c->qlog,
                    ",\"ect0\":%" PRIu ",\"ect1\":%" PRIu ",\"ce\":%" PRIu,
                    ect0, ect1, ce);
        }

        adj_iov_to_data(v, m);
        dprintf(c->qlog, "}");
    }
    dprintf(c->qlog, "]");

done:
    dprintf(c->qlog, "}]");
}


void qlog_recovery(const qlog_rec_evt_t evt,
                   const char * const trg,
                   struct q_conn * const c,
                   const struct pkt_meta * const m)
{
    if (c->qlog == 0)
        return;

    qlog_common(c);

    static const char * const evt_str[] = {
        [rec_mu] = "metrics_updated", [rec_pl] = "packet_lost"};
    dprintf(c->qlog, ",\"recovery\",\"%s\",\"%s\",{", evt_str[evt], trg);

    if (evt == rec_pl) {
        dprintf(c->qlog, "\"packet_number\":%" PRIu, m->hdr.nr);
        goto done;
    }

    int prev_metric = 0;
    if (c->rec.cur.in_flight != c->rec.prev.in_flight)
        prev_metric =
            dprintf(c->qlog, "%s\"bytes_in_flight\":%" PRIu,
                    /* prev_metric ? "," : */ "", c->rec.cur.in_flight);
    if (c->rec.cur.cwnd != c->rec.prev.cwnd)
        prev_metric = dprintf(c->qlog, "%s\"cwnd\":%" PRIu,
                              prev_metric ? "," : "", c->rec.cur.cwnd);
    if (c->rec.cur.ssthresh != UINT_T_MAX &&
        c->rec.cur.ssthresh != c->rec.prev.ssthresh)
        prev_metric = dprintf(c->qlog, "%s\"ssthresh\":%" PRIu,
                              prev_metric ? "," : "", c->rec.cur.ssthresh);
    if (c->rec.cur.srtt != c->rec.prev.srtt)
        prev_metric = dprintf(c->qlog, "%s\"smoothed_rtt\":%" PRIu,
                              prev_metric ? "," : "", c->rec.cur.srtt);
    if (c->rec.cur.min_rtt < UINT_T_MAX &&
        c->rec.cur.min_rtt != c->rec.prev.min_rtt)
        prev_metric = dprintf(c->qlog, "%s\"min_rtt\":%" PRIu,
                              prev_metric ? "," : "", c->rec.cur.min_rtt);
    if (c->rec.cur.latest_rtt != c->rec.prev.latest_rtt)
        prev_metric = dprintf(c->qlog, "%s\"latest_rtt\":%" PRIu,
                              prev_metric ? "," : "", c->rec.cur.latest_rtt);
    if (c->rec.cur.rttvar != c->rec.prev.rttvar)
        // prev_metric =
        dprintf(c->qlog, "%s\"rtt_variance\":%" PRIu, prev_metric ? "," : "",
                c->rec.cur.rttvar);

done:
    dprintf(c->qlog, "}]");
}

#else

static void * _unused __attribute__((unused));

#endif
