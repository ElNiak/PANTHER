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

#include <stdbool.h>
#include <stdint.h>

#include <quant/quant.h>
#include <timeout.h>

struct pkt_meta;
struct pn_space;
struct q_conn;


struct cc_state {
    // these are kept in usec:
    uint_t latest_rtt; // latest_rtt
    uint_t min_rtt;    // min_rtt
    uint_t rttvar;     // rttvar
    uint_t srtt;       // smoothed_rtt

    uint_t ae_in_flight; // nr of ACK-eliciting pkts inflight
    uint_t cwnd;         // congestion_window
    uint_t in_flight;    // bytes_in_flight
    uint_t ssthresh;     // sshtresh
};


struct recovery {
    uint_t initial_rtt; // kInitialRtt config knob, in usec

    struct timeout ld_alarm; // loss_detection_timer
    timeout_t ld_alarm_val;

    uint64_t rec_start_t; // recovery_start_time
    uint_t ae_in_flight;  // nr of ACK-eliciting pkts inflight

    // largest_sent_packet -> pn->lg_sent
    // largest_acked_packet -> pn->lg_acked
    // max_ack_delay -> c->tp_peer.max_ack_del

    // CC state

    struct cc_state cur;
#if !defined(NDEBUG) || !defined(NO_QLOG)
    struct cc_state prev;
#endif

    uint16_t pto_cnt; // pto_count
    uint16_t max_ups; // max_datagram_size
    int max_ups_af;   // address family we checked max_ups under
};


#if !defined(NDEBUG) || !defined(NO_QLOG)
extern void __attribute__((nonnull)) log_cc(struct q_conn * const c);
#else
#define log_cc(...)
#endif

extern void __attribute__((nonnull)) init_rec(struct q_conn * const c);

extern void __attribute__((nonnull)) on_pkt_sent(struct pkt_meta * const m);

extern void __attribute__((nonnull))
on_ack_received_1(struct pkt_meta * const lg_ack, const uint_t ack_del);

extern void __attribute__((nonnull))
on_ack_received_2(struct pn_space * const pn);

extern void __attribute__((nonnull))
on_pkt_acked(struct w_iov * const v, struct pkt_meta * m);

extern void __attribute__((nonnull))
congestion_event(struct q_conn * const c, const uint64_t sent_t);

extern void __attribute__((nonnull)) set_ld_timer(struct q_conn * const c);

extern void __attribute__((nonnull))
on_pkt_lost(struct pkt_meta * const m, const bool is_lost);

extern void __attribute__((nonnull))
detect_all_lost_pkts(struct q_conn * const c, const bool do_cc);
