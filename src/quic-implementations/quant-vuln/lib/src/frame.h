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

#include <picotls.h>
#include <quant/quant.h>

#include "bitset.h"
#include "cid.h"

struct pkt_meta;
struct pn_space;
struct q_conn;
struct q_stream;


#define FRM_PAD 0x00 ///< PADDING
#define FRM_PNG 0x01 ///< PING
#define FRM_ACK 0x02 ///< ACK (only type encoded in the frames bitstr_t)
#define FRM_ACE 0x03 ///< ACK w/ECN
#define FRM_RST 0x04 ///< RESET_STREAM
#define FRM_STP 0x05 ///< STOP_SENDING
#define FRM_CRY 0x06 ///< CRYPTO
#define FRM_TOK 0x07 ///< NEW_TOKEN
#define FRM_STR 0x08 ///< STREAM (only type encoded in the frames bitstr_t)
#define FRM_STR_09 0x09
#define FRM_STR_0a 0x0a
#define FRM_STR_0b 0x0b
#define FRM_STR_0c 0x0c
#define FRM_STR_0d 0x0d
#define FRM_STR_0e 0x0e
#define FRM_STR_0f 0x0f
#define FRM_MCD 0x10 ///< MAX_DATA (connection)
#define FRM_MSD 0x11 ///< MAX_STREAM_DATA
#define FRM_MSB 0x12 ///< MAX_STREAMS (bidirectional)
#define FRM_MSU 0x13 ///< MAX_STREAMS (unidirectional)
#define FRM_CDB 0x14 ///< (connection) DATA_BLOCKED
#define FRM_SDB 0x15 ///< STREAM_DATA_BLOCKED
#define FRM_SBB 0x16 ///< STREAMS_BLOCKED (bidirectional)
#define FRM_SBU 0x17 ///< STREAMS_BLOCKED (unidirectional)
#define FRM_CID 0x18 ///< NEW_CONNECTION_ID
#define FRM_RTR 0x19 ///< RETIRE_CONNECTION_ID
#define FRM_PCL 0x1a ///< PATH_CHALLENGE
#define FRM_PRP 0x1b ///< PATH_RESPONSE
#define FRM_CLQ 0x1c ///< CONNECTION_CLOSE (QUIC layer)
#define FRM_CLA 0x1d ///< CONNECTION_CLOSE (application)
#define FRM_HSD 0x1e ///< HANDSHAKE_DONE

#define FRM_MAX (FRM_HSD + 1)

bitset_define(frames, FRM_MAX);


static const uint8_t max_frame_len[] = {
    // NOTE: the type field is really a uint_t, change for extensions frames!
    [FRM_PAD] = sizeof(uint8_t),
    [FRM_PNG] = sizeof(uint8_t),
    [FRM_ACK] = UINT8_MAX, // special case
    [FRM_ACE] = UINT8_MAX, // special case
    [FRM_RST] = UINT8_MAX, // we don't encode this
    [FRM_STP] = UINT8_MAX, // we don't encode this
    [FRM_CRY] = UINT8_MAX, // special case
    [FRM_TOK] =
        sizeof(uint8_t) + sizeof(uint_t) + PTLS_MAX_DIGEST_SIZE + CID_LEN_MAX,
    [FRM_STR] = UINT8_MAX,    // special case
    [FRM_STR_09] = UINT8_MAX, // special case
    [FRM_STR_0a] = UINT8_MAX, // special case
    [FRM_STR_0b] = UINT8_MAX, // special case
    [FRM_STR_0c] = UINT8_MAX, // special case
    [FRM_STR_0d] = UINT8_MAX, // special case
    [FRM_STR_0e] = UINT8_MAX, // special case
    [FRM_STR_0f] = UINT8_MAX, // special case
    [FRM_MCD] = sizeof(uint8_t) + sizeof(uint_t),
    [FRM_MSD] = sizeof(uint8_t) + sizeof(uint_t) + sizeof(uint_t),
    [FRM_MSB] = sizeof(uint8_t) + sizeof(uint_t),
    [FRM_MSU] = sizeof(uint8_t) + sizeof(uint_t),
    [FRM_CDB] = sizeof(uint8_t) + sizeof(uint_t),
    [FRM_SDB] = sizeof(uint8_t) + sizeof(uint_t) + sizeof(uint_t),
    [FRM_SBB] = sizeof(uint8_t) + sizeof(uint_t),
    [FRM_SBU] = sizeof(uint8_t) + sizeof(uint_t),
    [FRM_CID] = sizeof(uint8_t) + 2 * sizeof(uint_t) + sizeof(uint8_t) +
                CID_LEN_MAX + SRT_LEN,
    [FRM_RTR] = sizeof(uint8_t) + sizeof(uint_t),
    [FRM_PCL] = sizeof(uint8_t) + sizeof(uint64_t),
    [FRM_PRP] = sizeof(uint8_t) + sizeof(uint64_t),
    [FRM_CLQ] = UINT8_MAX, // special case
    [FRM_CLA] = UINT8_MAX, // special case
    [FRM_HSD] = sizeof(uint8_t)};


#define F_STREAM_FIN 0x01
#define F_STREAM_LEN 0x02
#define F_STREAM_OFF 0x04

#define FRAM_IN BLD BLU
#define FRAM_OUT BLD GRN

#define has_frm(frames, type) bit_isset(FRM_MAX, (type), &(frames))


typedef enum { sdt_inv, sdt_seq, sdt_ooo, sdt_dup, sdt_ign } strm_data_type_t;

#ifdef NDEBUG
#define log_stream_or_crypto_frame(...)
#else
extern void __attribute__((nonnull(2)))
log_stream_or_crypto_frame(const bool is_rtx,
                           const struct pkt_meta * const m,
                           const uint8_t fl,
                           const dint_t sid,
                           const bool in,
                           const strm_data_type_t kind);
#endif

extern bool __attribute__((nonnull))
dec_frames(struct q_conn * const c, struct w_iov ** vv, struct pkt_meta ** mm);

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4)
#endif
                               ))
enc_padding_frame(struct q_conn_info * const ci,
                  uint8_t ** pos,
                  const uint8_t * const end,
                  struct pkt_meta * const m,
                  const uint16_t len);

extern bool __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4, 5, 6)
#endif
                               )) enc_ack_frame(struct q_conn_info * const ci,
                                                uint8_t ** pos,
                                                const uint8_t * const start,
                                                const uint8_t * const end,
                                                struct pkt_meta * const m,
                                                struct pn_space * const pn);

extern void __attribute__((nonnull))
calc_lens_of_stream_or_crypto_frame(struct pkt_meta * const m,
                                    const struct w_iov * const v,
                                    const struct q_stream * const s,
                                    const bool rtx);

extern void __attribute__((nonnull))
enc_stream_or_crypto_frame(uint8_t ** pos,
                           const uint8_t * const end,
                           struct pkt_meta * const m,
                           struct w_iov * const v,
                           struct q_stream * const s);

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4)
#endif
                               )) enc_close_frame(struct q_conn_info * const ci,
                                                  uint8_t ** pos,
                                                  const uint8_t * const end,
                                                  struct pkt_meta * const m);

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4)
#endif
                               ))
enc_path_response_frame(struct q_conn_info * const ci,
                        uint8_t ** pos,
                        const uint8_t * const end,
                        struct pkt_meta * const m);

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4, 5)
#endif
                               ))
enc_max_strm_data_frame(struct q_conn_info * const ci,
                        uint8_t ** pos,
                        const uint8_t * const end,
                        struct pkt_meta * const m,
                        struct q_stream * const s);

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4)
#endif
                               ))
enc_max_data_frame(struct q_conn_info * const ci,
                   uint8_t ** pos,
                   const uint8_t * const end,
                   struct pkt_meta * const m);

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4)
#endif
                               ))
enc_max_strms_frame(struct q_conn_info * const ci,
                    uint8_t ** pos,
                    const uint8_t * const end,
                    struct pkt_meta * const m,
                    const bool bidi);

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4, 5)
#endif
                               ))
enc_strm_data_blocked_frame(struct q_conn_info * const ci,
                            uint8_t ** pos,
                            const uint8_t * const end,
                            struct pkt_meta * const m,
                            struct q_stream * const s);

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4)
#endif
                               ))
enc_data_blocked_frame(struct q_conn_info * const ci,
                       uint8_t ** pos,
                       const uint8_t * const end,
                       struct pkt_meta * const m);

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4)
#endif
                               ))
enc_streams_blocked_frame(struct q_conn_info * const ci,
                          uint8_t ** pos,
                          const uint8_t * const end,
                          struct pkt_meta * const m,
                          const bool bidi);

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4)
#endif
                               ))
enc_path_challenge_frame(struct q_conn_info * const ci,
                         uint8_t ** pos,
                         const uint8_t * const end,
                         struct pkt_meta * const m);

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4)
#endif
                               ))
enc_new_cid_frame(struct q_conn_info * const ci,
                  uint8_t ** pos,
                  const uint8_t * const end,
                  struct pkt_meta * const m);

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4)
#endif
                               ))
enc_new_token_frame(struct q_conn_info * const ci,
                    uint8_t ** pos,
                    const uint8_t * const end,
                    struct pkt_meta * const m);

#ifndef NO_MIGRATION
extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4)
#endif
                               ))
enc_retire_cid_frame(struct q_conn_info * const ci,
                     uint8_t ** pos,
                     const uint8_t * const end,
                     struct pkt_meta * const m,
                     const uint_t seq);
#endif

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4)
#endif
                               )) enc_ping_frame(struct q_conn_info * const ci,
                                                 uint8_t ** pos,
                                                 const uint8_t * const end,
                                                 struct pkt_meta * const m);

extern void __attribute__((nonnull
#ifdef NO_QINFO
                           (2, 3, 4)
#endif
                               ))
enc_hshk_done_frame(struct q_conn_info * const ci,
                    uint8_t ** pos,
                    const uint8_t * const end,
                    struct pkt_meta * const m);


static inline bool __attribute__((nonnull))
is_ack_eliciting(const struct frames * const f)
{
    static const struct frames ack_or_pad = bitset_t_initializer(
        1 << FRM_ACK | 1 << FRM_PAD | 1 << FRM_CLQ | 1 << 1 << FRM_CLA);
    struct frames not_ack_or_pad = bitset_t_initializer(0);
    bit_nand2(FRM_MAX, &not_ack_or_pad, f, &ack_or_pad);
    return !bit_empty(FRM_MAX, &not_ack_or_pad);
}
