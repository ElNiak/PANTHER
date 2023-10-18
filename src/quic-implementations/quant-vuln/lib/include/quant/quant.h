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

#ifdef __cplusplus
extern "C" {
#endif

#include <netinet/in.h>
#include <stdbool.h>
#include <stdint.h>

#include <quant/config.h>      // IWYU pragma: export
#include <warpcore/warpcore.h> // IWYU pragma: export


struct w_iov_sq;
struct q_stream;


struct q_conn_conf {
    uint_t idle_timeout;             // seconds
    uint_t tls_key_update_frequency; // seconds
    uint_t initial_rtt;              // milliseconds
    uint8_t enable_spinbit : 1;
    uint8_t enable_udp_zero_checksums : 1;
    uint8_t enable_tls_key_updates : 1; // TODO default to on eventually
    uint8_t disable_active_migration : 1;
    uint8_t enable_quantum_readiness_test : 1; // TODO: is temporary
    uint8_t : 3;
    uint32_t version;
};


struct q_conf {
    const struct q_conn_conf * const conn_conf;
    const char * const ticket_store; // ignored for server
    const char * const tls_cert;     // required for server
    const char * const tls_key;      // required for server
    const char * const tls_log;
    const char * const qlog_dir;
    uint32_t num_bufs;
    uint8_t enable_tls_cert_verify : 1;
    uint8_t force_retry : 1;    // ignored on client
    uint8_t force_chacha20 : 1; // TODO: is temporary
    uint8_t : 5;
    uint8_t client_cid_len;
    uint8_t server_cid_len;
};


struct q_conn_info {
    uint_t pkts_in_valid;
    uint_t pkts_in_invalid;

    uint_t pkts_out;
    uint_t pkts_out_lost;
    uint_t pkts_out_rtx;

    uint_t strm_frms_in_seq;
    uint_t strm_frms_in_ooo;
    uint_t strm_frms_in_dup;
    uint_t strm_frms_in_ign;

    float rtt;
    float rttvar;
    float min_rtt;
    float max_rtt;

    uint_t cwnd;
    uint_t max_cwnd;
    uint_t ssthresh;
    uint_t pto_cnt;

    // 0x1e = max. frame type
    uint_t frm_cnt[2][0x1e + 1]; // 0 = out (tx), 1 = in (rx)
};


extern struct w_engine * __attribute__((nonnull(1)))
q_init(const char * const ifname, const struct q_conf * const conf);

extern void __attribute__((nonnull)) q_cleanup(struct w_engine * const w);

extern struct q_conn * __attribute__((nonnull(1, 2, 3)))
q_connect(struct w_engine * const w,
          const struct sockaddr * const peer,
          const char * const peer_name,
          struct w_iov_sq * const early_data,
          struct q_stream ** const early_data_stream,
          const bool fin,
          const char * const alpn,
          const struct q_conn_conf * const conf);

extern void __attribute__((nonnull(1)))
q_close(struct q_conn * const c, const uint_t code, const char * const reason);

extern struct q_conn * __attribute__((nonnull))
q_bind(struct w_engine * const w, const uint16_t addr_idx, const uint16_t port);

extern struct q_conn * q_accept(struct w_engine * const w,
                                const struct q_conn_conf * const conf);

extern bool __attribute__((nonnull))
q_is_new_serv_conn(const struct q_conn * const c);

extern bool __attribute__((nonnull))
q_write(struct q_stream * const s, struct w_iov_sq * const q, const bool fin);

extern struct q_stream * __attribute__((nonnull))
q_read(struct q_conn * const c, struct w_iov_sq * const q, const bool all);

extern struct q_stream * __attribute__((nonnull))
q_rsv_stream(struct q_conn * const c, const bool bidi);

extern void __attribute__((nonnull)) q_close_stream(struct q_stream * const s);

extern void __attribute__((nonnull)) q_free_stream(struct q_stream * const s);

extern void __attribute__((nonnull))
q_stream_get_written(struct q_stream * const s, struct w_iov_sq * const q);

extern void __attribute__((nonnull(1, 2)))
q_alloc(struct w_engine * const w,
        struct w_iov_sq * const q,
        const struct q_conn * const c,
        const int af,
        const size_t len);

extern void __attribute__((nonnull)) q_free(struct w_iov_sq * const q);

extern void __attribute__((nonnull))
q_cid(struct q_conn * const c, uint8_t * const buf, size_t * const buf_len);

extern const char * __attribute__((nonnull))
q_cid_str(struct q_conn * const c, char * const buf, const size_t buf_len);

extern uint_t __attribute__((nonnull)) q_sid(const struct q_stream * const s);

extern void __attribute__((nonnull(1, 4, 6)))
q_chunk_str(struct w_engine * const w,
            const struct q_conn * const c,
            const int af,
            const char * const str,
            const size_t len,
            struct w_iov_sq * o);

extern void __attribute__((nonnull)) q_write_str(struct w_engine * const w,
                                                 struct q_stream * const s,
                                                 const char * const str,
                                                 const size_t len,
                                                 const bool fin);

extern void __attribute__((nonnull)) q_write_file(struct w_engine * const w,
                                                  struct q_stream * const s,
                                                  const int f,
                                                  const size_t len,
                                                  const bool fin);

extern bool __attribute__((nonnull))
q_is_stream_closed(const struct q_stream * const s);

extern bool __attribute__((nonnull))
q_peer_closed_stream(const struct q_stream * const s);

extern bool __attribute__((nonnull))
q_is_conn_closed(const struct q_conn * const c);

extern bool __attribute__((nonnull)) q_read_stream(struct q_stream * const s,
                                                   struct w_iov_sq * const q,
                                                   const bool all);

extern bool q_ready(struct w_engine * const w,
                    const uint64_t nsec,
                    struct q_conn ** const ready);

extern bool __attribute__((nonnull))
q_is_uni_stream(const struct q_stream * const s);

#ifndef NO_MIGRATION
extern bool __attribute__((nonnull(1)))
q_migrate(struct q_conn * const c,
          const bool switch_ip,
          const struct sockaddr * const alt_peer);
#endif

extern void __attribute__((nonnull))
q_info(struct q_conn * const c, struct q_conn_info * const ci);

extern int __attribute__((nonnull)) q_conn_af(const struct q_conn * const c);

#ifdef __cplusplus
}
#endif
