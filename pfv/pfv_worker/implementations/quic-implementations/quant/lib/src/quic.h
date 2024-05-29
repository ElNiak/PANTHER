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
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <sys/param.h>

#include <picotls.h>
#include <timeout.h>

#ifdef WITH_OPENSSL
#include <openssl/ossl_typ.h>
#include <picotls/openssl.h>
#endif

#include <quant/quant.h>

#ifdef HAVE_ASAN
#include <sanitizer/asan_interface.h>
#else
#define ASAN_POISON_MEMORY_REGION(x, y)
#define ASAN_UNPOISON_MEMORY_REGION(x, y)
#endif

#include "cid.h"
#include "frame.h"
#include "tree.h"

#ifndef NO_SERVER
#include "tls.h"
#endif

struct q_conn;

// #define DEBUG_EXTRA ///< Set to log various extra details.
// #define DEBUG_STREAMS ///< Set to log stream scheduling details.
// #define DEBUG_TIMERS  ///< Set to log timer details.
// #define DEBUG_PROT    ///< Set to log packet protection/encryption details.

#define DATA_OFFSET 48 ///< Offsets of stream frame payload data we TX.

#define PATH_CHLG_LEN 8 ///< Length of a path challenge.
#define MAX_TOK_LEN 166
#define AEAD_LEN 16
#define RIT_LEN 16 ///< Length of Retry integrity tag.

// Maximum reordering in packets before packet threshold loss detection
// considers a packet lost. The RECOMMENDED value is 3.
#define kPacketThreshold 3

// Timer granularity. This is a system-dependent value. However, implementations
// SHOULD use a value no smaller than 1ms.
#define kGranularity (1 * US_PER_MS)

/// Default limit on the initial amount of outstanding data in flight, in bytes.
/// Taken from [RFC6928]. The RECOMMENDED value is the minimum of 10 *
/// max_ups and max(2* max_ups, 14720)).
#define kInitialWindow(max_ups) MIN(10 * (max_ups), MAX(2 * (max_ups), 14720))

/// Minimum congestion window in bytes.
#define kMinimumWindow(max_ups) (2 * (max_ups))

/// Reduction in congestion window when a new loss event is detected.
#define kLossReductionDivisor 2 // kLossReductionFactor

/// Number of consecutive PTOs after which network is considered to be
/// experiencing persistent congestion. The RECOMMENDED value for
/// kPersistentCongestionThreshold is 3, which is equivalent to having two TLPs
/// before an RTO in TCP.
#define kPersistentCongestionThreshold 3


#define FMT_PNR_IN BLU "%" PRIu NRM
#define FMT_PNR_OUT GRN "%" PRIu NRM
#define FMT_SID BLD YEL "%" PRId NRM


struct pkt_hdr {
    struct cid dcid;  ///< Destination CID.
    struct cid scid;  ///< Source CID.
    uint_t nr;        ///< Packet number.
    uint16_t len;     ///< Content of length field in long header.
    uint16_t hdr_len; ///< Length of entire QUIC header.
    uint32_t vers;    ///< QUIC version in long header.
    uint8_t flags;    ///< First (raw) byte of packet.
    uint8_t type;     ///< Parsed packet type. TODO: remove?
#if HAVE_64BIT
    uint8_t _unused[6];
#else
    uint8_t _unused[2];
#endif
};


/// Packet meta-data information associated with w_iov buffers
struct pkt_meta {
    // XXX need to potentially change pm_cpy() below if fields are reordered
    splay_entry(pkt_meta) off_node;
    sl_entry(pkt_meta) rtx_next;
    sl_head(pm_sl, pkt_meta) rtx; ///< List of pkt_meta structs of previous TXs.

    // pm_cpy(true) starts copying from here:
    struct frames frms;     ///< Frames present in pkt.
    struct q_stream * strm; ///< Stream this data was written on.
    uint_t strm_off;        ///< Stream data offset.
    uint16_t strm_frm_pos;  ///< Offset of stream frame header.
    uint16_t strm_data_pos; ///< Offset of first byte of stream frame data.
    uint16_t strm_data_len; ///< Length of stream frame data.

    uint16_t ack_frm_pos; ///< Offset of (first, on RX) ACK frame.

    dint_t max_strm_data_sid; ///< MAX_STREAM_DATA sid, if sent.
    uint_t max_strm_data;     ///< MAX_STREAM_DATA limit, if sent.
    uint_t max_data;          ///< MAX_DATA limit, if sent.
    dint_t max_strms_bidi;    ///< MAX_STREAM_ID bidir limit, if sent.
    dint_t max_strms_uni;     ///< MAX_STREAM_ID unidir limit, if sent.
    uint_t strm_data_blocked; ///< STREAM_DATA_BLOCKED value, if sent.
    uint_t data_blocked;      ///< DATA_BLOCKED value, if sent.
    uint_t min_cid_seq;    ///< Smallest NEW_CONNECTION_ID seq in pkt, if sent.
    uint_t retire_cid_seq; ///< RETIRE_CONNECTION_ID value, if sent.

    // pm_cpy(false) starts copying from here:
    struct pn_space * pn; ///< Packet number space.
    struct pkt_hdr hdr;   ///< Parsed packet header.
    uint64_t t;           ///< TX or RX timestamp.

    uint16_t udp_len;          ///< Length of protected UDP packet at TX/RX.
    uint8_t has_rtx : 1;       ///< Does the w_iov hold truncated data?
    uint8_t is_reset : 1;      ///< This packet is a stateless reset.
    uint8_t is_fin : 1;        ///< This packet has a stream FIN bit.
    uint8_t in_flight : 1;     ///< Does this pkt count towards in_flight?
    uint8_t ack_eliciting : 1; ///< Is this packet ACK-eliciting?

    uint8_t acked : 1; ///< Was this packet ACKed?
    uint8_t lost : 1;  ///< Have we marked this packet as lost?
    uint8_t txed : 1;  ///< Did we TX this pkt?

    uint8_t _unused2[5];
};


struct per_engine_data {
    struct timeouts * wheel;
    struct pkt_meta * pkt_meta;
    struct q_conn_conf default_conn_conf;
    struct q_conf conf;
    struct timeout api_alarm;

    ptls_context_t tls_ctx;
    ptls_aead_context_t * rid_ctx;

#ifdef WITH_OPENSSL
    ptls_openssl_sign_certificate_t sign_cert;
    ptls_openssl_verify_certificate_t verify_cert;
    X509_STORE * ca_store;
#endif

#ifndef NO_SERVER
    struct cipher_ctx dec_tick_tok;
    struct cipher_ctx enc_tick_tok;
#endif

#ifdef NO_MIGRATION
    sl_head(conn_head, q_conn) conns;
#endif

#ifndef NO_TLS_LOG
    int tls_log;
#else
    uint8_t _unused[4];
#endif

    uint32_t scratch_len;
    uint8_t scratch[]; // packet-sized scratch space to avoid stack alloc
};


#define ped(w) ((struct per_engine_data *)((w)->data))


/// The versions of QUIC supported by this implementation
extern const uint32_t ok_vers[];
extern const uint8_t ok_vers_len;


extern void __attribute__((nonnull(1, 2)))
alloc_off(struct w_engine * const w,
          struct w_iov_sq * const q,
          const struct q_conn * const c,
          const int af,
          const uint32_t len,
          const uint16_t off);

extern void __attribute__((nonnull))
free_iov(struct w_iov * const v, struct pkt_meta * const m);


extern struct w_iov * __attribute__((nonnull))
alloc_iov(struct w_engine * const w,
          const int af,
          const uint16_t len,
          const uint16_t off,
          struct pkt_meta ** const m);


extern struct w_iov * __attribute__((nonnull(1)))
dup_iov(const struct w_iov * const v,
        struct pkt_meta ** const mdup,
        const uint16_t off);


#if !defined(NDEBUG) && !defined(FUZZING) && defined(FUZZER_CORPUS_COLLECTION)
extern int corpus_pkt_dir, corpus_frm_dir;

extern void __attribute__((nonnull))
write_to_corpus(const int dir, const void * const data, const size_t len);
#endif


/// Is flag @p f set in flags variable @p v?
///
/// @param      f     Flag.
/// @param      v     Variable.
///
/// @return     True if set, false otherwise.
///
#define is_set(f, v) (((v) & (f)) == (f))


/// Return the pkt_meta entry for a given w_iov.
///
/// @param      v     Pointer to a w_iov.
///
/// @return     Pointer to the pkt_meta entry for the w_iov.
///
#define meta(v) ped((v)->w)->pkt_meta[w_iov_idx(v)]


/// Return the w_iov index of a given pkt_meta.
///
/// @param      w     Pointer to warpcore engine.
/// @param      m     Pointer to a pkt_meta entry.
///
/// @return     Index of the struct w_iov the struct pkt_meta holds meta data
///             for.
///
#define pm_idx(w, m) (uint32_t)((m)-ped(w)->pkt_meta)


extern char * __attribute__((nonnull, no_instrument_function))
hex2str(const uint8_t * const src,
        const size_t len_src,
        char * const dst,
        const size_t len_dst);


extern char __srt_str[hex_str_len(SRT_LEN)];
extern char __tok_str[hex_str_len(MAX_TOK_LEN)];
extern char __rit_str[hex_str_len(RIT_LEN)];

#define srt_str(srt) hex2str((srt), SRT_LEN, __srt_str, sizeof(__srt_str))

#define tok_str(tok, tok_len)                                                  \
    hex2str((tok), (tok_len), __tok_str, sizeof(__tok_str))

#define rit_str(rit) hex2str((rit), RIT_LEN, __rit_str, sizeof(__rit_str))

#define has_strm_data(p) (p)->strm_frm_pos


#define get_conf(w, conf, val)                                                 \
    ((conf) && (conf)->val ? (conf)->val : ped(w)->default_conn_conf.val)


#define get_conf_uncond(w, conf, val)                                          \
    ((conf) ? (conf)->val : ped(w)->default_conn_conf.val)


#ifdef HAVE_ASAN
#ifdef HAVE_ASAN_ADDRESS_IS_POISONED
#define is_poisoned(x) __asan_address_is_poisoned(x)
#define is_unpoisoned(x) (__asan_address_is_poisoned(x) == fase)
#else
#define is_poisoned(x) true
#define is_unpoisoned(x) true
#endif

#define poison_scratch(s, l)                                                   \
    do {                                                                       \
        ensure(is_unpoisoned((s)), "scratch already poisoned");                \
        ASAN_POISON_MEMORY_REGION((s), (l));                                   \
    } while (0)


#define unpoison_scratch(s, l)                                                 \
    do {                                                                       \
        ensure(is_poisoned((s)), "scratch already unpoisoned");                \
        ASAN_UNPOISON_MEMORY_REGION((s), (l));                                 \
    } while (0)
#else
#define poison_scratch(s, l)
#define unpoison_scratch(s, l)
#endif


static inline void __attribute__((nonnull))
pm_cpy(struct pkt_meta * const dst,
       const struct pkt_meta * const src,
       const bool also_frame_info)
{
    const size_t off = also_frame_info ? offsetof(struct pkt_meta, frms)
                                       : offsetof(struct pkt_meta, pn);
    memcpy((uint8_t *)dst + off, (const uint8_t *)src + off,
           sizeof(*dst) - off);
}


static inline void __attribute__((nonnull))
adj_iov_to_start(struct w_iov * const v, const struct pkt_meta * const m)
{
    v->buf -= m->strm_data_pos;
    v->len += m->strm_data_pos;
}


static inline void __attribute__((nonnull))
adj_iov_to_data(struct w_iov * const v, const struct pkt_meta * const m)
{
    v->buf += m->strm_data_pos;
    v->len -= m->strm_data_pos;
}
