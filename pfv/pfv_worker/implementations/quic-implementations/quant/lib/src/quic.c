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

#include <inttypes.h>
#include <netinet/in.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>

#include <picotls.h>
#include <quant/quant.h>
#include <timeout.h>

#if !defined(NDEBUG) && !defined(FUZZING) && defined(FUZZER_CORPUS_COLLECTION)
#include <errno.h>
#include <fcntl.h>
#include <sys/param.h>
#include <unistd.h>
#endif

#ifdef PARTICLE
#include <arpa/inet.h>
#endif

#include "conn.h"
#include "loop.h"
#include "pkt.h"
#include "pn.h"
#include "quic.h"
#include "recovery.h"
#include "stream.h"
#include "tls.h"

#ifndef NO_OOO_0RTT
#include "tree.h"
#endif


char __srt_str[hex_str_len(SRT_LEN)];
char __tok_str[hex_str_len(MAX_TOK_LEN)];
char __rit_str[hex_str_len(RIT_LEN)];


/// QUIC version supported by this implementation in order of preference.
const uint32_t ok_vers[] = {
#ifndef NDEBUG
    0xbabababa, // reserved version to trigger negotiation
#endif
    0x1,                            // v1
    0x45474700 + DRAFT_VERSION,     // quant private version -xx
    0xff000000 + DRAFT_VERSION,     // draft-ietf-quic-transport-xx
    0x45474700 + DRAFT_VERSION - 1, // quant private version -xx-1
    0xff000000 + DRAFT_VERSION - 1, // draft-ietf-quic-transport-xx-1
};

/// Length of the @p ok_vers array.
const uint8_t ok_vers_len = sizeof(ok_vers) / sizeof(ok_vers[0]);

#if !defined(NDEBUG) && !defined(FUZZING) && defined(FUZZER_CORPUS_COLLECTION)
int corpus_pkt_dir, corpus_frm_dir;
#endif


void alloc_off(struct w_engine * const w,
               struct w_iov_sq * const q,
               const struct q_conn * const c,
               const int af,
               const uint32_t len,
               const uint16_t off)
{
    uint16_t pkt_len = default_max_ups(af);
    if (c && c->rec.max_ups_af) {
        pkt_len = c->rec.max_ups;
        if (af != c->rec.max_ups_af) {
            if (c->rec.max_ups_af == AF_INET)
                pkt_len -= 20;
            else
                pkt_len += 20;
        }
    }

    w_alloc_len(w, af, q, len, pkt_len - AEAD_LEN - off, off);
    struct w_iov * v;
    sq_foreach (v, q, next) {
        struct pkt_meta * const m = &meta(v);
        ASAN_UNPOISON_MEMORY_REGION(m, sizeof(*m));
        m->strm_data_pos = off;
    }
}


void free_iov(struct w_iov * const v, struct pkt_meta * const m)
{
    if (m->txed) {
        if (m->acked == false && m->lost == false && m->pn &&
            m->pn->abandoned == false) {
            m->strm = 0;
            on_pkt_lost(m, false);
        }

        struct pkt_meta * m_rtx = sl_first(&m->rtx);
        if (unlikely(m_rtx)) {
            // this pkt has prior or later RTXs
            if (m->has_rtx) {
                // this pkt has an RTX
                sl_remove(&m_rtx->rtx, m, pkt_meta, rtx_next);

            } else {
                // this is the last ("real") RTX of a packet
                while (m_rtx) {
                    m_rtx->strm = 0;
                    assure(m_rtx->has_rtx, "was RTX'ed");
                    sl_remove_head(&m->rtx, rtx_next);
                    sl_remove_head(&m_rtx->rtx, rtx_next);
                    m_rtx = sl_next(m_rtx, rtx_next);
                }
            }
        }
    }

    memset(m, 0, sizeof(*m));
    ASAN_POISON_MEMORY_REGION(m, sizeof(*m));
    w_free_iov(v);
}


struct w_iov * alloc_iov(struct w_engine * const w,
                         const int af,
                         const uint16_t len,
                         const uint16_t off,
                         struct pkt_meta ** const m)
{
    struct w_iov * const v = w_alloc_iov(w, af, len, off);
    if (likely(v)) {
        *m = &meta(v);
        ASAN_UNPOISON_MEMORY_REGION(*m, sizeof(**m));
        (*m)->strm_data_pos = off;
    }
    return v;
}


struct w_iov * dup_iov(const struct w_iov * const v,
                       struct pkt_meta ** const mdup,
                       const uint16_t off)
{
    struct w_iov * const vdup = w_alloc_iov(v->w, v->wv_af, v->len - off, 0);
    if (likely(vdup)) {
        if (mdup) {
            *mdup = &meta(vdup);
            ASAN_UNPOISON_MEMORY_REGION(*mdup, sizeof(**mdup));
        }
        memcpy(vdup->buf, v->buf + off, v->len - off);
        memcpy(&vdup->saddr, &v->saddr, sizeof(v->saddr));
        vdup->flags = v->flags;
        vdup->ttl = v->ttl;
    }
    return vdup;
}


void q_alloc(struct w_engine * const w,
             struct w_iov_sq * const q,
             const struct q_conn * const c,
             const int af,
             const size_t len)
{
    ensure(len <= UINT32_MAX, "len %zu too long", len);
    alloc_off(w, q, c, af, (uint32_t)len, DATA_OFFSET);
}


void q_free(struct w_iov_sq * const q)
{
    while (!sq_empty(q)) {
        struct w_iov * const v = sq_first(q);
        sq_remove_head(q, next);
        sq_next(v, next) = 0;
        free_iov(v, &meta(v));
    }
}


static void __attribute__((nonnull)) mark_fin(struct w_iov_sq * const q)
{
    // cppcheck-suppress nullPointer
    struct w_iov * const last = sq_last(q, w_iov, next);
    assure(last, "got last buffer");
    meta(last).is_fin = true;
}


struct q_conn * q_connect(struct w_engine * const w,
                          const struct sockaddr * const peer,
                          const char * const peer_name,
                          struct w_iov_sq * const early_data,
                          struct q_stream ** const early_data_stream,
                          const bool fin,
                          const char * const alpn,
                          const struct q_conn_conf * const conf)
{
    // make new connection
    struct w_sockaddr p;

    uint16_t idx = UINT16_MAX;
    if (peer->sa_family == AF_INET && w->have_ip4) {
        idx = w->addr4_pos;
        p.port = ((const struct sockaddr_in *)(const void *)peer)->sin_port;
    } else if (peer->sa_family == AF_INET6 && w->have_ip6) {
        const bool local_peer = IN6_IS_ADDR_LINKLOCAL(
            &((const struct sockaddr_in6 *)(const void *)peer)->sin6_addr);
        for (idx = 0;
             idx < (uint16_t)(w->have_ip4 ? w->addr4_pos : w->addr_cnt); idx++)
            if (local_peer == w_is_linklocal(&w->ifaddr[idx].addr))
                break;
        if (idx == (w->have_ip4 ? w->addr4_pos : w->addr_cnt)) {
            warn(WRN, "could not find suitable addr to talk to %s peer",
                 local_peer ? "link-local" : "global");
            return 0;
        }
        p.port = ((const struct sockaddr_in6 *)(const void *)peer)->sin6_port;
    }

    if (unlikely(idx == UINT16_MAX || w_to_waddr(&p.addr, peer) == false)) {
        warn(CRT, "address family error");
        return 0;
    }

    struct q_conn * const c = new_conn(w, idx, 0, 0, &p, peer_name, 0, 0, conf);

    // init TLS
    init_tls(c, peer_name, alpn);
    init_tp(c);

    // if we have no early data, we're not trying 0-RTT
    c->try_0rtt &= early_data && early_data_stream;

    warn(WRN,
         "new %u-RTT %s conn %s to %s%s%s:%u, %" PRIu " byte%s queued for TX",
         c->try_0rtt ? 0 : 1, conn_type(c), cid_str(c->scid),
         p.addr.af == AF_INET6 ? "[" : "", w_ntop(&p.addr, ip_tmp),
         p.addr.af == AF_INET6 ? "]" : "", bswap16(p.port),
         early_data ? w_iov_sq_len(early_data) : 0,
         plural(early_data ? w_iov_sq_len(early_data) : 0));

    restart_idle_alarm(c);

    // start TLS handshake
    tls_io(c->cstrms[ep_init], 0);

    if (early_data && !sq_empty(early_data)) {
        assure(early_data_stream, "early data without stream pointer");
        // queue up early data
        if (fin)
            mark_fin(early_data);
        *early_data_stream = new_stream(c, c->next_sid_bidi);
        concat_out(*early_data_stream, early_data);
    } else if (early_data_stream)
        *early_data_stream = 0;

    timeouts_add(ped(w)->wheel, &c->tx_w, 0);

    warn(DBG, "waiting for connect on %s conn %s to %s%s%s:%u", conn_type(c),
         cid_str(c->scid), p.addr.af == AF_INET6 ? "[" : "",
         w_ntop(&p.addr, ip_tmp), p.addr.af == AF_INET6 ? "]" : "",
         bswap16(p.port));
    conn_to_state(c, conn_opng);
    loop_run(w, (func_ptr)q_connect, c, 0);

    if (fin && early_data_stream && *early_data_stream &&
        (*early_data_stream)->state != strm_clsd)
        strm_to_state(*early_data_stream,
                      (*early_data_stream)->state == strm_hcrm ? strm_clsd
                                                               : strm_hclo);
    c->try_0rtt = false;

    if (c->state != conn_estb && c->state != conn_clsg &&
        c->state != conn_drng) {
        warn(WRN, "%s conn %s not connected", conn_type(c), cid_str(c->scid));
        return 0;
    }

    warn(WRN, "%s conn %s connected%s, cipher %s", conn_type(c),
         cid_str(c->scid), c->did_0rtt ? " after 0-RTT" : "",
         c->pns[pn_data]
             .data.out_1rtt[c->pns[pn_data].data.out_kyph]
             .aead->algo->name);
    DSTACK_LOG("DSTACK 3" DSTACK_LOG_NEWLINE);

    return c;
}


bool q_write(struct q_stream * const s,
             struct w_iov_sq * const q,
             const bool fin)
{
    struct q_conn * const c = s->c;
    if (unlikely(c->state == conn_qlse || c->state == conn_drng ||
                 c->state == conn_clsd)) {
        warn(ERR, "%s conn %s is in state %s, can't write", conn_type(c),
             cid_str(c->scid), conn_state_str[c->state]);
        return false;
    }

    if (unlikely(s->state == strm_hclo || s->state == strm_clsd)) {
        warn(ERR, "%s conn %s strm " FMT_SID " is in state %s, can't write",
             conn_type(c), cid_str(c->scid), s->id, strm_state_str[s->state]);
        return false;
    }

    // add to stream
    if (fin) {
        if (sq_empty(q)) {
            alloc_off(c->w, q, s->c, q_conn_af(s->c), 1, DATA_OFFSET);
            // cppcheck-suppress nullPointer
            struct w_iov * const last = sq_last(q, w_iov, next);
            assure(last, "got last buffer");
            last->len = 0;
        }
        mark_fin(q);
    }

    warn(WRN,
         "writing %" PRIu " byte%s %sin %" PRIu
         " buf%s on %s conn %s strm " FMT_SID,
         w_iov_sq_len(q), plural(w_iov_sq_len(q)), fin ? "(and FIN) " : "",
         w_iov_sq_cnt(q), plural(w_iov_sq_cnt(q)), conn_type(c),
         cid_str(c->scid), s->id);

    concat_out(s, q);

    // kick TX watcher
    timeouts_add(ped(c->w)->wheel, &c->tx_w, 0);
    return true;
}


static struct q_stream * __attribute__((nonnull))
find_ready_strm(khash_t(strms_by_id) * const sbi, const bool all)
{
    struct q_stream * s = 0;
    bool found = false;
    kh_foreach_value(sbi, s, {
        if (s->state == strm_clsd ||
            (!sq_empty(&s->in) && (!all || s->state == strm_hcrm))) {
            found = true;
            break;
        }
    });

    // stream is closed, or has data (and a a FIN, if we're reading all)
    return found ? s : 0;
}


struct q_stream *
q_read(struct q_conn * const c, struct w_iov_sq * const q, const bool all)
{
    struct q_stream * const s = find_ready_strm(&c->strms_by_id, all);
    if (s)
        q_read_stream(s, q, all);
    return s;
}


bool q_read_stream(struct q_stream * const s,
                   struct w_iov_sq * const q,
                   const bool all)
{
    struct q_conn * const c = s->c;

    if (q_peer_closed_stream(s) == false && all) {
        warn(WRN, "reading all on %s conn %s strm " FMT_SID, conn_type(c),
             cid_str(c->scid), s->id);
    again:
        loop_run(c->w, (func_ptr)q_read_stream, c, s);
    }

    if (sq_empty(&s->in))
        return false;

    // cppcheck-suppress nullPointer
    struct w_iov * const last = sq_last(&s->in, w_iov, next);
    const struct pkt_meta * const m_last = &meta(last);

    warn(WRN,
         "read %" PRIu " new byte%s %sin %" PRIu " buf%s on %s "
         "conn %s strm " FMT_SID,
         w_iov_sq_len(&s->in), plural(w_iov_sq_len(&s->in)),
         m_last->is_fin ? "(and FIN) " : "", w_iov_sq_cnt(&s->in),
         plural(w_iov_sq_cnt(&s->in)), conn_type(c), cid_str(c->scid), s->id);

    sq_concat(q, &s->in);

    const struct q_stream * const sr = find_ready_strm(&c->strms_by_id, all);
    c->have_new_data = sr != 0;

    if (all && m_last->is_fin == false)
        goto again;

    return true;
}


struct q_conn * q_bind(struct w_engine * const w
#ifdef NO_SERVER
                       __attribute__((unused))
#endif
                       ,
                       const uint16_t addr_idx
#ifdef NO_SERVER
                       __attribute__((unused))
#endif
                       ,
                       const uint16_t port
#ifdef NO_SERVER
                       __attribute__((unused))
#endif
)
{
#ifndef NO_SERVER
    // bind socket and create new embryonic server connection
    struct q_conn * const c =
        new_conn(w, addr_idx, 0, 0, 0, 0, bswap16(port), 0, 0);
    if (likely(c)) {
        warn(INF, "bound %s socket to %s%s%s:%u", conn_type(c),
             c->sock->ws_laddr.af == AF_INET6 ? "[" : "",
             w_ntop(&c->sock->ws_laddr, ip_tmp),
             c->sock->ws_laddr.af == AF_INET6 ? "]" : "", port);
        sl_insert_head(&c_embr, c, node_embr);
    }
    return c;
#else
    return 0;
#endif
}


static void cancel_api_call(struct timeout * const api_alarm)
{
#ifdef DEBUG_EXTRA
    warn(DBG, "canceling API call");
#endif
    timeout_del(api_alarm);
    maybe_api_return(q_ready, 0, 0);
}


static void __attribute__((nonnull))
restart_api_alarm(struct w_engine * const w, const uint64_t nsec)
{
#ifdef DEBUG_TIMERS
    warn(DBG, "next API alarm in %.3f sec", (double)nsec / NS_PER_S);
#endif

    timeouts_add(ped(w)->wheel, &ped(w)->api_alarm, nsec);
}


struct q_stream * q_rsv_stream(struct q_conn * const c, const bool bidi)
{
    if (unlikely(c->state == conn_drng || c->state == conn_clsd))
        return 0;

    const uint_t * const max_streams =
        bidi ? &c->tp_peer.max_strms_bidi : &c->tp_peer.max_strms_uni;

    if (unlikely(*max_streams == 0))
        warn(WRN, "peer hasn't allowed %s streams", bidi ? "bi" : "uni");

    dint_t * const next_sid = bidi ? &c->next_sid_bidi : &c->next_sid_uni;
    const uint_t next = (uint_t)(*next_sid >> 2);
    if (unlikely(next >= *max_streams)) {
        // we hit the max stream limit, wait for MAX_STREAMS frame
        warn(WRN, "need %s MAX_STREAMS increase (%" PRIu " >= %" PRIu ")",
             bidi ? "bi" : "uni", next, *max_streams);
        if (bidi)
            c->sid_blocked_bidi = true;
        else
            c->sid_blocked_uni = true;
        loop_run(c->w, (func_ptr)q_rsv_stream, c, 0);
    }

    // stream blocking is handled by new_stream
    return new_stream(c, *next_sid);
}


#if !defined(NDEBUG) && !defined(FUZZING) && defined(FUZZER_CORPUS_COLLECTION)
static int __attribute__((nonnull))
mk_or_open_dir(const char * const path, mode_t mode)
{
    int fd = mkdir(path, mode);
    ensure(fd == 0 || (fd == -1 && errno == EEXIST), "mkdir %s", path);
    fd = open(path, O_RDONLY | O_CLOEXEC);
    ensure(fd != -1, "open %s", path);
    return fd;
}
#endif


struct w_engine * q_init(const char * const ifname,
                         const struct q_conf * const conf)
{
#if !defined(PARTICLE) && !defined(RIOT_VERSION)
    umask(S_IWGRP | S_IWOTH);
#endif

    // initialize warpcore on the given interface
    const uint32_t num_bufs = conf && conf->num_bufs ? conf->num_bufs : 10000;
    struct w_engine * const w = w_init(ifname, 0, num_bufs);
    const uint_t num_bufs_ok = w_iov_sq_cnt(&w->iov);
    if (num_bufs_ok < num_bufs)
        warn(WRN, "only allocated %" PRIu "/%" PRIu32 " warpcore buffers ",
             num_bufs_ok, num_bufs);

    w->data = calloc(1, sizeof(struct per_engine_data) + w->mtu);
    ensure(w->data, "could not calloc");
    ped(w)->scratch_len = w->mtu;
    poison_scratch(ped(w)->scratch, ped(w)->scratch_len);

    ped(w)->pkt_meta = calloc(num_bufs, sizeof(*ped(w)->pkt_meta));
    ensure(ped(w)->pkt_meta, "could not calloc");
    ASAN_POISON_MEMORY_REGION(ped(w)->pkt_meta,
                              num_bufs * sizeof(*ped(w)->pkt_meta));

    if (conf)
        memcpy(&ped(w)->conf, conf, sizeof(*conf));
    ped(w)->conf.num_bufs = num_bufs;
    if (ped(w)->conf.client_cid_len)
        ped(w)->conf.client_cid_len =
            MIN(ped(w)->conf.client_cid_len, CID_LEN_MAX);
    if (ped(w)->conf.server_cid_len)
        ped(w)->conf.server_cid_len =
            MIN(ped(w)->conf.server_cid_len, CID_LEN_MAX);
    else
        ped(w)->conf.server_cid_len = 4; // could be another value

    ped(w)->default_conn_conf =
        (struct q_conn_conf){.initial_rtt = 500,
                             .idle_timeout = 10,
                             .enable_udp_zero_checksums = true,
                             .tls_key_update_frequency = 3,
                             .version = ok_vers[0],
                             .enable_quantum_readiness_test = false,
                             .disable_pmtud = false,
                             .enable_grease = false,
                             .enable_spinbit =
#ifndef NDEBUG
                                 true
#else
                                 false
#endif
        };

    if (conf && conf->conn_conf) {
        // update default connection configuration
        ped(w)->default_conn_conf.version =
            get_conf(w, conf->conn_conf, version);
        ped(w)->default_conn_conf.initial_rtt =
            get_conf(w, conf->conn_conf, initial_rtt);
        ped(w)->default_conn_conf.idle_timeout =
            get_conf_uncond(w, conf->conn_conf, idle_timeout);
        ped(w)->default_conn_conf.tls_key_update_frequency =
            get_conf(w, conf->conn_conf, tls_key_update_frequency);
        ped(w)->default_conn_conf.enable_spinbit =
            get_conf_uncond(w, conf->conn_conf, enable_spinbit);
        ped(w)->default_conn_conf.enable_udp_zero_checksums =
            get_conf_uncond(w, conf->conn_conf, enable_udp_zero_checksums);
        ped(w)->default_conn_conf.enable_tls_key_updates =
            get_conf_uncond(w, conf->conn_conf, enable_tls_key_updates);
        ped(w)->default_conn_conf.disable_active_migration =
            get_conf_uncond(w, conf->conn_conf, disable_active_migration);
        ped(w)->default_conn_conf.enable_quantum_readiness_test =
            get_conf_uncond(w, conf->conn_conf, enable_quantum_readiness_test);
        ped(w)->default_conn_conf.disable_pmtud =
            get_conf_uncond(w, conf->conn_conf, disable_pmtud);
        ped(w)->default_conn_conf.enable_grease =
            get_conf_uncond(w, conf->conn_conf, enable_grease);
    }

    // initialize some globals
#ifndef NO_MIGRATION
    memset(&conns_by_id, 0, sizeof(conns_by_id));
#endif
#ifndef NO_SRT_MATCHING
    memset(&conns_by_srt, 0, sizeof(conns_by_srt));
#endif

    // initialize the event loop
    timeout_init(&ped(w)->api_alarm, 0);
    loop_init();
    int err;
    ped(w)->wheel = timeouts_open(TIMEOUT_nHZ, &err);
    timeouts_update(ped(w)->wheel, w_now(CLOCK_MONOTONIC_RAW));
    timeout_setcb(&ped(w)->api_alarm, cancel_api_call, &ped(w)->api_alarm);

    warn(INF, "%s/%s (%s) %s/%s ready", quant_name, w->backend_name,
         w->backend_variant, quant_version, QUANT_COMMIT_HASH_ABBREV_STR);
    warn(DBG, "submit bug reports at https://github.com/NTAP/quant/issues");

    // initialize TLS context
    init_tls_ctx(conf, ped(w));

#if !defined(NDEBUG) && defined(FUZZER_CORPUS_COLLECTION)
#ifdef FUZZING
    warn(CRT, "%s compiled for fuzzing - will not communicate", quant_name);
#else
    // create the directories for exporting fuzzer corpus data
    warn(NTE, "debug build, storing fuzzer corpus data");
    corpus_pkt_dir = mk_or_open_dir("../corpus_pkt", 0755);
    corpus_frm_dir = mk_or_open_dir("../corpus_frm", 0755);
#endif
#endif

    return w;
}


void q_close_stream(struct q_stream * const s)
{
    warn(WRN, "closing strm " FMT_SID " on %s conn %s", s->id, conn_type(s->c),
         cid_str(s->c->scid));
    struct w_iov_sq q = w_iov_sq_initializer(q);
    q_write(s, &q, true);
}


void q_free_stream(struct q_stream * const s)
{
    free_stream(s);
}


void q_stream_get_written(struct q_stream * const s, struct w_iov_sq * const q)
{
    if (s->out_una == 0) {
        sq_concat(q, &s->out);
        return;
    }

    struct w_iov * v = sq_first(&s->out);
    while (v != s->out_una) {
        sq_remove_head(&s->out, next);
        sq_next(v, next) = 0;
        sq_insert_tail(q, v, next);
        v = sq_first(&s->out);
    }
}


void q_close(struct q_conn * const c,
             const uint_t code,
             const char * const reason
#if defined(NO_ERR_REASONS) && defined(NDEBUG)
             __attribute__((unused))
#endif
)
{
    warn(WRN, "closing %s conn %s on %s%s%s:%u w/err %s0x%" PRIx "%s%s%s" NRM,
         conn_type(c), cid_str(c->scid),
         c->sock->ws_laddr.af == AF_INET6 ? "[" : "",
         w_ntop(&c->sock->ws_laddr, ip_tmp),
         c->sock->ws_laddr.af == AF_INET6 ? "]" : "",
         bswap16(c->sock->ws_lport), code ? RED : NRM, code, reason ? " (" : "",
         reason ? reason : "", reason ? ")" : "");

    c->err_code = code;
#ifndef NO_ERR_REASONS
    if (reason) {
        strncpy(c->err_reason, reason, MAX_ERR_REASON_LEN);
        c->err_reason[MAX_ERR_REASON_LEN - 1] = 0;
        c->err_reason_len = (uint8_t)strnlen(reason, MAX_ERR_REASON_LEN);
    }
#endif

    if (c->state == conn_idle || c->state == conn_clsd ||
        (!is_clnt(c) && c->holds_sock))
        // we don't need to do the closing dance in these cases
        goto done;

    if (c->state != conn_clsg && c->state != conn_drng) {
        conn_to_state(c, conn_qlse);
        timeouts_add(ped(c->w)->wheel, &c->tx_w, 0);
    }

    loop_run(c->w, (func_ptr)q_close, c, 0);

done:
#if !defined(NO_QINFO) && !defined(PARTICLE)
    if (c->scid && c->i.pkts_in_valid > 0) {
        static const char * const frm_typ_str[] = {
            [0x00] = "PADDING",
            [0x01] = "PING",
            [0x02] = "ACK",
            [0x03] = "ACK_ECN",
            [0x04] = "RESET_STREAM",
            [0x05] = "STOP_SENDING",
            [0x06] = "CRYPTO",
            [0x07] = "NEW_TOKEN",
            [0x08] = "STREAM",
            [0x09] = "STREAM_09",
            [0x0a] = "STREAM_0a",
            [0x0b] = "STREAM_0b",
            [0x0c] = "STREAM_0c",
            [0x0d] = "STREAM_0d",
            [0x0e] = "STREAM_0e",
            [0x0f] = "STREAM_0f",
            [0x10] = "MAX_DATA",
            [0x11] = "MAX_STREAM_DATA",
            [0x12] = "MAX_STREAMS_UNDI",
            [0x13] = "MAX_STREAMS_BIDI",
            [0x14] = "DATA_BLOCKED",
            [0x15] = "STREAM_DATA_BLOCKED",
            [0x16] = "STREAMS_BLOCKED_UNDI",
            [0x17] = "STREAMS_BLOCKED_BIDI",
            [0x18] = "NEW_CONNECTION_ID",
            [0x19] = "RETIRE_CONNECTION_ID",
            [0x1a] = "PATH_CHALLENGE",
            [0x1b] = "PATH_RESPONSE",
            [0x1c] = "CONNECTION_CLOSE_QUIC",
            [0x1d] = "CONNECTION_CLOSE_APP",
            [0x1e] = "HANDSHAKE_DONE",
        };

        conn_info_populate(c);

#ifndef NDEBUG
#define qinfo_log(...) warn(INF, __VA_ARGS__)
#else
#define qinfo_log(...)                                                         \
    do {                                                                       \
        fprintf(stderr, __VA_ARGS__);                                          \
        fputc('\n', stderr);                                                   \
    } while (0)
#endif

        qinfo_log("%s conn %s stats:", conn_type(c), cid_str(c->scid));
        qinfo_log("pkts_in_valid = %s%" PRIu NRM,
                  c->i.pkts_in_valid ? NRM : BLD RED, c->i.pkts_in_valid);
        qinfo_log("pkts_in_invalid = %s%" PRIu NRM,
                  c->i.pkts_in_invalid ? BLD RED : NRM, c->i.pkts_in_invalid);
        qinfo_log("pkts_out = %" PRIu, c->i.pkts_out);
        qinfo_log("pkts_out_lost = %" PRIu, c->i.pkts_out_lost);
        qinfo_log("pkts_out_rtx = %" PRIu, c->i.pkts_out_rtx);
        qinfo_log("rtt = %.3f (min = %.3f, max = %.3f, var = %.3f)",
                  (double)c->i.rtt, (double)c->i.min_rtt, (double)c->i.max_rtt,
                  (double)c->i.rttvar);
        qinfo_log("cwnd = %" PRIu " (max = %" PRIu ")", c->i.cwnd,
                  c->i.max_cwnd);
        qinfo_log("ssthresh = %" PRIu,
                  c->i.ssthresh == UINT_T_MAX ? 0 : c->i.ssthresh);
        qinfo_log("pto_cnt = %" PRIu, c->i.pto_cnt);
        qinfo_log("%-22s %s %10s %10s", "frame", "code", "out", "in");
        for (size_t i = 0;
             i < sizeof(c->i.frm_cnt[0]) / sizeof(c->i.frm_cnt[0][0]); i++) {
            if (c->i.frm_cnt[0][i] || c->i.frm_cnt[1][i])
                qinfo_log("%-22s 0x%02lx %10" PRIu " %10" PRIu, frm_typ_str[i],
                          (unsigned long)i, c->i.frm_cnt[0][i],
                          c->i.frm_cnt[1][i]);
        }
        qinfo_log("strm_frms_in_seq = %" PRIu, c->i.strm_frms_in_seq);
        qinfo_log("strm_frms_in_ooo = %" PRIu, c->i.strm_frms_in_ooo);
        qinfo_log("strm_frms_in_dup = %" PRIu, c->i.strm_frms_in_dup);
        qinfo_log("strm_frms_in_ign = %" PRIu, c->i.strm_frms_in_ign);
    }
#endif

#ifndef NO_SERVER
    if (is_clnt(c) == false && c->holds_sock)
        sl_remove(&c_embr, c, q_conn, node_embr);
#endif
    free_conn(c);
}


void q_cleanup(struct w_engine * const w)
{
    // close all connections
    struct q_conn * c;
#ifndef NO_MIGRATION
    kh_foreach_value(&conns_by_id, c, { q_close(c, 0, 0); });
#else
#endif

#ifndef NO_SRT_MATCHING
    kh_foreach_value(&conns_by_srt, c, { q_close(c, 0, 0); });
#endif

    struct q_conn * tmp;
    sl_foreach_safe (c, &c_zcid, node_zcid_int, tmp)
        q_close(c, 0, 0);

#ifndef NO_SERVER
    sl_foreach_safe (c, &c_embr, node_embr, tmp)
        q_close(c, 0, 0);
#endif

    // stop the event loop
    timeouts_close(ped(w)->wheel);

#ifndef NO_OOO_0RTT
    // free 0-RTT reordering cache
    while (!splay_empty(&ooo_0rtt_by_cid)) {
        struct ooo_0rtt * const zo =
            splay_min(ooo_0rtt_by_cid, &ooo_0rtt_by_cid);
        splay_remove(ooo_0rtt_by_cid, &ooo_0rtt_by_cid, zo);
        free(zo);
    }
#endif

#if defined(HAVE_ASAN) && defined(HAVE_ASAN_ADDRESS_IS_POISONED)
    for (uint_t i = 0; i < ped(w)->conf.num_bufs; i++) {
        struct pkt_meta * const m = &ped(w)->pkt_meta[i];
        if (__asan_address_is_poisoned(m) == false) {
            warn(DBG, "buffer %" PRIu " still in use for %cX'ed %s pkt %" PRIu,
                 i, m->txed ? 'T' : 'R',
                 pkt_type_str(m->hdr.flags, &m->hdr.vers),
                 has_pkt_nr(m->hdr.flags, m->hdr.vers) ? m->hdr.nr : 0);
        }
    }
#endif

#ifndef NO_MIGRATION
    kh_release(conns_by_id, &conns_by_id);
#endif
#ifndef NO_SRT_MATCHING
    kh_release(conns_by_srt, &conns_by_srt);
#endif

    free_tls_ctx(ped(w));
    free(ped(w)->pkt_meta);
    free(w->data);
    w_cleanup(w);

#if !defined(NDEBUG) && !defined(FUZZING) && defined(FUZZER_CORPUS_COLLECTION)
    close(corpus_pkt_dir);
    close(corpus_frm_dir);
#endif
}


void q_cid(struct q_conn * const c, uint8_t * const buf, size_t * const buf_len)
{
    ensure(*buf_len >= CID_LEN_MAX, "buf too short (need at least %d)",
           CID_LEN_MAX);

    memcpy(buf, c->odcid.id, c->odcid.len);
    *buf_len = c->odcid.len;
}


const char *
q_cid_str(struct q_conn * const c, char * const buf, const size_t buf_len)
{
    ensure(buf_len >= hex_str_len(CID_LEN_MAX),
           "buf too short (need at least %d)", hex_str_len(CID_LEN_MAX));
    if (c->odcid.len)
        hex2str(c->odcid.id, c->odcid.len, buf, buf_len);
    else
        *buf = 0;
    return buf;
}


uint_t q_sid(const struct q_stream * const s)
{
    return (uint_t)s->id;
}


bool q_is_stream_closed(const struct q_stream * const s)
{
    return s->state == strm_clsd;
}


bool q_peer_closed_stream(const struct q_stream * const s)
{
    return s->state == strm_hcrm || s->state == strm_clsd;
}


bool q_is_conn_closed(const struct q_conn * const c)
{
    return c->state == conn_clsd;
}


#if !defined(NDEBUG) && !defined(FUZZING) && defined(FUZZER_CORPUS_COLLECTION)
void write_to_corpus(const int dir, const void * const data, const size_t len)
{
    const uint64_t rand = w_rand64();
    char file[MAXPATHLEN];
    hex2str((const uint8_t *)&rand, sizeof(rand), file, sizeof(file));
    const int fd =
        openat(dir, file, O_CREAT | O_EXCL | O_WRONLY | O_CLOEXEC, 0644);
    if (fd == -1) {
        warn(ERR, "cannot open corpus file %s", file);
        goto done;
    }
    if (write(fd, data, len) == -1) {
        warn(ERR, "cannot write corpus file %s", file);
        goto done;
    }
done:
    close(fd);
}
#endif


bool q_ready(struct w_engine * const w,
             const uint64_t nsec,
             struct q_conn ** const ready)
{
    if (sl_empty(&c_ready)) {
        if (nsec)
            restart_api_alarm(w, nsec);
#ifdef DEBUG_EXTRA
        warn(WRN, "waiting for conn to get ready");
#endif
        loop_run(w, (func_ptr)q_ready, 0, 0);
    }

    if (ready == 0)
        goto done;

    struct q_conn * /*const*/ c = sl_first(&c_ready);
    if (c) {
#if defined(DEBUG_EXTRA) && !defined(NO_SERVER)
        warn(WRN, "%s conn %s ready to %s", conn_type(c), cid_str(c->scid),
             c->state == conn_clsd ? "close" : "rx");
#endif
        sl_remove_head(&c_ready, node_rx_ext);
        c->in_c_ready = false;
    } else
        warn(WRN, "no conn ready");
    *ready = c;
done:;
#ifndef NO_MIGRATION
#ifdef DEBUG_EXTRA
    struct cid * id;
    kh_foreach(&conns_by_id, id, c, {
        char cs[CID_STR_LEN];
        cid2str(id, cs, sizeof(cs));
        warn(ERR, "conns_by_id has %s conn %s -> %s", conn_type(c), cs,
             cid_str(c->scid));
    });
    warn(ERR, "conns_by_id size %" PRIu32, kh_size(&conns_by_id));
#endif
    return kh_size(&conns_by_id);
#else
    return sl_empty(&ped(w)->conns);
#endif
}


int q_conn_af(const struct q_conn * const c)
{
    return c->sock->ws_af;
}


#ifndef NO_MIGRATION
bool q_migrate(struct q_conn * const c,
               const bool switch_ip,
               const struct sockaddr * const alt_peer)
{
    if (switch_ip) {
        // make sure we have a dcid to migrate to
        if (next_cid(&c->dcids, c->dcid->seq) == 0) {
#ifdef DEBUG_EXTRA
            warn(DBG, "no new dcid available, can't migrate");
#endif
            return false;
        }
        // make sure the handshake has completed
        if (hshk_done(c) == false) {
#ifdef DEBUG_EXTRA
            warn(DBG, "handshake not yet complete, can't migrate");
#endif
            return false;
        }
    }

    ensure(is_clnt(c), "can only rebind w_sock on client");
    struct w_engine * const w = c->w;

    // find the index of the currently used local address
    uint16_t idx;
    for (idx = 0; idx < w->addr_cnt; idx++)
        if (w_addr_cmp(&w->ifaddr[idx].addr, &c->sock->ws_laddr))
            break;
    ensure(idx < w->addr_cnt, "could not find local address index");

#ifndef NDEBUG
    char old_ip[IP_STRLEN];
    const uint16_t old_port = bswap16(c->sock->ws_lport);
    const int old_af = c->sock->ws_laddr.af;
    w_ntop(&c->sock->ws_laddr, old_ip);
#endif

    if (switch_ip) {
        // try and find an IP address of another AF
        uint16_t other_idx;
        for (other_idx = 0; other_idx < w->addr_cnt; other_idx++)
            if (w->ifaddr[idx].addr.af != w->ifaddr[other_idx].addr.af &&
                (w->ifaddr[other_idx].addr.af != AF_INET6 ||
                 !w_is_private(&w->ifaddr[other_idx].addr)))
                break;

        if (other_idx < w->addr_cnt) {
            idx = other_idx;
            if ((w->ifaddr[other_idx].addr.af == AF_INET &&
                 memcmp(&c->tp_peer.pref_addr.addr4.addr.ip4,
                        &(char[IP4_LEN]){0}, IP4_LEN) != 0) ||
                (w->ifaddr[other_idx].addr.af == AF_INET6 &&
                 memcmp(&c->tp_peer.pref_addr.addr6.addr.ip4,
                        &(char[IP6_LEN]){0}, IP6_LEN) != 0)) {
                // use corresponding preferred_address as peer
                c->migr_peer = w->ifaddr[other_idx].addr.af == AF_INET
                                   ? c->tp_peer.pref_addr.addr4
                                   : c->tp_peer.pref_addr.addr6;
            } else if (alt_peer) {
                // use alt_peer
                w_to_waddr(&c->migr_peer.addr, alt_peer);
                c->migr_peer.port =
                    alt_peer->sa_family == AF_INET
                        ? ((const struct sockaddr_in *)(const void *)alt_peer)
                              ->sin_port
                        : ((const struct sockaddr_in6 *)(const void *)alt_peer)
                              ->sin6_port;
            } else
                goto fail;
        } else
            goto fail;

        rand_bytes(&c->path_chlg_out, sizeof(c->path_chlg_out));
        c->tx_path_chlg = c->needs_tx = true;
        c->tx_limit = 1;
        // also switch to new dcid
        use_next_dcid(c, true);
    }

    struct w_sock * const new_sock = w_bind(w, idx, 0, &c->sockopt);
    if (new_sock == 0)
        goto fail;

    if (switch_ip) {
        c->migr_sock = new_sock;
        c->holds_migr_sock = true;
    } else {
        // close the current w_sock
        w_close(c->sock);
        c->sock = new_sock;
    }

    warn(WRN, "%s for %s conn %s from %s%s%s:%u to %s%s%s:%u",
         switch_ip ? "conn migration" : "simulated NAT rebinding", conn_type(c),
         c->scid ? cid_str(c->scid) : "-", old_af == AF_INET6 ? "[" : "",
         old_ip, old_af == AF_INET6 ? "]" : "", old_port,
         new_sock->ws_laddr.af == AF_INET6 ? "[" : "",
         w_ntop(&new_sock->ws_laddr, ip_tmp),
         new_sock->ws_laddr.af == AF_INET6 ? "]" : "",
         bswap16(new_sock->ws_lport));

    timeouts_add(ped(w)->wheel, &c->tx_w, 0);
    return true;

fail:
    warn(ERR, "%s failed for %s conn %s from %s%s%s:%u",
         switch_ip ? "conn migration" : "simulated NAT rebinding", conn_type(c),
         c->scid ? cid_str(c->scid) : "-", old_af == AF_INET6 ? "[" : "",
         old_ip, old_af == AF_INET6 ? "]" : "", old_port);
    return false;
}
#endif


void q_info(struct q_conn * const c
#ifdef NO_QINFO
            __attribute__((unused))
#endif
            ,
            struct q_conn_info * const ci
#ifdef NO_QINFO
            __attribute__((unused))
#endif
)
{
#ifndef NO_QINFO
    conn_info_populate(c);
    memcpy(ci, &c->i, sizeof(*ci));
#endif
}


char * hex2str(const uint8_t * const src,
               const size_t len_src,
               char * const dst,
               const size_t len_dst)
{
    static const char hex[] = "0123456789abcdef";

    size_t i;
    for (i = 0; i < len_src && i * 2 + 1 < len_dst; i++) {
        dst[i * 2] = hex[(src[i] >> 4) & 0x0f];
        dst[i * 2 + 1] = hex[src[i] & 0x0f];
    }

    if (i * 2 + 1 <= len_dst)
        dst[i * 2] = 0;
    else {
        size_t l = len_dst;
        if (l)
            dst[--l] = 0;
        if (l)
            dst[--l] = '.';
        if (l)
            dst[--l] = '.';
        if (l)
            dst[--l] = '.';
    }

    return dst;
}
