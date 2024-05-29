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
#include <sys/socket.h>
#include <string.h>

#include <warpcore/warpcore.h>

#include "cid.h"
#include "quic.h"
#include "tls.h"

struct q_conn;
struct q_stream;

#define MIN_INI_LEN 1200
#define MAX_UPS 65527
#define MIN_SRT_PKT_LEN 5 + SRT_LEN ///< min SRT length, incl. the fixed bits

#define HEAD_FORM 0x80 ///< header form (1 = long, 0 = short)
#define HEAD_FIXD 0x40 ///< fixed bit (= 1)
#define HEAD_PNRL_MASK 0x03 ///< packet number length mask

#define LH (HEAD_FORM | HEAD_FIXD)
#define LH_TYPE_MASK 0x30 ///< long header: packet type mask
#define LH_INIT 0x00 ///< long header packet type: Initial
#define LH_0RTT 0x10 ///< long header packet type: 0-RTT Protected
#define LH_HSHK 0x20 ///< long header packet type: Handshake
#define LH_RTRY 0x30 ///< long header packet type: Retry
#define LH_RSVD_MASK 0x0c ///< long header: reserved bits mask (= 0)

#define SH HEAD_FIXD
#define SH_SPIN 0x20 ///< short header: spin bit
#define SH_RSVD_MASK 0x18 ///< short header: reserved bits mask (= 0)
#define SH_KYPH 0x04 ///< short header: key phase bit

#define MAX_PKT_NR_LEN 4 ///< Maximum packet number length allowed by spec.

#define ERR_NONE 0x0
#define ERR_INTL 0x1
// #define ERR_SERVER_BUSY 0x2
#define ERR_FC 0x3
#define ERR_STRM_LIMT 0x4
#define ERR_STRM_STAT 0x5
#define ERR_FINL_SIZE 0x6
#define ERR_FRAM_ENC 0x7
#define ERR_TP 0x8
#define ERR_CID_LIMT 0x9
#define ERR_PV 0xa
#define ERR_INVL_TOK 0xb
// #define ERR_APP_ERROR 0xc
#define ERR_TLS(type) (0x100 + (type))


#define default_max_ups(af) ((af) == AF_INET ? 1252 : 1232)


static inline bool __attribute__((const, no_instrument_function))
is_lh(const uint8_t flags)
{
    return is_set(HEAD_FORM, flags);
}


static inline uint8_t __attribute__((const, no_instrument_function))
pkt_type(const uint8_t flags)
{
    return is_lh(flags) ? flags & LH_TYPE_MASK : SH;
}


static inline uint8_t __attribute__((const, no_instrument_function))
pkt_nr_len(const uint8_t flags)
{
    return (flags & HEAD_PNRL_MASK) + 1;
}


static inline epoch_t __attribute__((const, no_instrument_function))
epoch_for_pkt_type(const uint8_t type)
{
    switch (type) {
    case LH_INIT:
    case LH_RTRY:
        return ep_init;
    case LH_0RTT:
        return ep_0rtt;
    case LH_HSHK:
        return ep_hshk;
    default:
        return ep_data;
    }
}


static inline const char * __attribute__((const,
                                          nonnull,
                                          no_instrument_function))
pkt_type_str(const uint8_t flags, const void * const vers)
{
    if (is_lh(flags)) {
        uint32_t v;
        memcpy(&v, vers, sizeof(v));
        if (v == 0)
            return "Version Negotiation";
        switch (pkt_type(flags)) {
        case LH_INIT:
            return "Initial";
        case LH_RTRY:
            return "Retry";
        case LH_HSHK:
            return "Handshake";
        case LH_0RTT:
            return "0-RTT Protected";
        }
    } else if (pkt_type(flags) == SH)
        return "Short";
    return RED "Unknown" NRM;
}


static inline bool __attribute__((const, no_instrument_function))
has_pkt_nr(const uint8_t flags, const uint32_t vers)
{
    return is_lh(flags) == false || (vers && pkt_type(flags) != LH_RTRY);
}


extern bool __attribute__((nonnull(1, 2)))
xor_hp(struct w_iov * const xv,
       const struct pkt_meta * const m,
       const struct cipher_ctx * const ctx,
       const uint16_t pkt_nr_pos,
       const uint8_t * const enc_mask);

extern bool __attribute__((nonnull))
dec_pkt_hdr_beginning(struct w_iov * const xv,
                      struct w_iov * const v,
                      struct pkt_meta * const m,
                      struct w_iov_sq * const x,
                      const bool is_clnt,
                      uint8_t * const tok,
                      uint16_t * const tok_len,
                      uint8_t * const rit,
                      const uint8_t dcid_len,
                      bool * decoal);

extern bool __attribute__((nonnull))
dec_pkt_hdr_remainder(struct w_iov * const xv,
                      struct w_iov * const v,
                      struct pkt_meta * const m,
                      struct q_conn * const c);

extern struct q_conn * __attribute__((nonnull))
is_srt(const struct w_iov * const xv, struct pkt_meta * const m);

extern bool __attribute__((nonnull)) enc_pkt(struct q_stream * const s,
                                             const bool rtx,
                                             const bool enc_data,
                                             const bool tx_ack_eliciting,
                                             const bool pmtud,
                                             struct w_iov * const v,
                                             struct pkt_meta * const m);

extern uint16_t __attribute__((nonnull)) coalesce(struct w_iov_sq * const q,
                                                  const uint16_t max_ups,
                                                  const bool do_pmtud);

extern void __attribute__((nonnull(1, 2, 3, 4)))
enc_lh_cids(uint8_t ** pos,
            const uint8_t * const end,
            struct pkt_meta * const m,
            const struct cid * const dcid,
            const struct cid * const scid);

extern void __attribute__((nonnull)) validate_pmtu(struct q_conn * const c);

extern void __attribute__((nonnull))
pad_with_rand(struct w_iov * const v, const uint16_t len);

#ifndef NDEBUG
extern void __attribute__((nonnull(1, 2))) log_pkt(const char * const dir,
                                                   const struct w_iov * const v,
                                                   const uint8_t * const tok,
                                                   const uint16_t tok_len,
                                                   const uint8_t * const rit);
#else
#define log_pkt(...)                                                           \
    do {                                                                       \
    } while (0)
#endif
