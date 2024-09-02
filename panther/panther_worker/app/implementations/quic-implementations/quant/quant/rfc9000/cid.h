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

#include <quant/quant.h>

#ifndef NO_MIGRATION
#define CIDS_MAX 8
#else
#define CIDS_MAX 1
#endif

#define CID_LEN_MAX 16         ///< Maximum CID length allowed by spec.
#define CID_LEN_MIN_INI_DCID 8 ///< Minimum DCID length required in an Initial.

#define SRT_LEN 16 ///< Stateless reset token length allowed by spec.


struct cid {
    sl_entry(cid) next;

    uint_t seq; ///< Connection ID sequence number
    /// XXX len must precede id for cid_cmp() over both to work
    uint8_t len; ///< Connection ID length
    /// XXX id must precede srt for rand_bytes() over both to work
    uint8_t id[CID_LEN_MAX]; ///< Connection ID
#ifndef NO_SRT_MATCHING
    uint8_t srt[SRT_LEN]; ///< Stateless Reset Token
    uint8_t has_srt : 1;  ///< Is the SRT field valid?
#endif
    uint8_t in_cbi : 1;       ///< Is the CID in conns_by_id?
    uint8_t retired : 1;      ///< Did we retire this CID?
    uint8_t available : 1;    ///< Is this CID available?
    uint8_t local_choice : 1; ///< Was this CID chosen by this end or the peer?
#ifndef NO_SRT_MATCHING
    uint8_t : 3;
#else
    uint8_t : 4;
#endif
#if HAVE_64BIT
    uint8_t _unused[2];
#else
    uint8_t _unused[6];
#endif
};


sl_head(cid_sl, cid);

struct cids {
    struct cid cids[CIDS_MAX];
    struct cid_sl ret;
    struct cid_sl act;
    struct cid_sl avl;
    uint_t act_cnt;
#if !HAVE_64BIT
    uint8_t unused[4];
#endif
};


#define hex_str_len(x) ((x)*2 + 1)

#define CID_STR_LEN hex_str_len(2 * sizeof(uint_t) + CID_LEN_MAX + 1)

extern char __cid_str[CID_STR_LEN];

#define cid_str(cid) cid2str((cid), __cid_str, sizeof(__cid_str))

#define mk_cid_str(lvl, cid, str)                                              \
    char str[DLEVEL >= (lvl) ? CID_STR_LEN : 1] = "";                          \
    if (DLEVEL >= (lvl) && likely(cid))                                        \
        cid2str((cid), str, sizeof(str));


extern void __attribute__((nonnull)) init_cids(struct cids * const ids);

extern struct cid * __attribute__((nonnull))
cid_by_seq(struct cid_sl * const sl, const uint_t seq);

extern struct cid * __attribute__((nonnull))
cid_by_id(struct cid_sl * const sl, const struct cid * const id);

extern uint_t __attribute__((nonnull)) cid_cnt(const struct cids * const ids);

extern uint_t __attribute__((nonnull)) min_seq(const struct cids * const ids);

extern uint_t __attribute__((nonnull)) max_seq(const struct cids * const ids);

extern void __attribute__((nonnull))
retire_prior_to(struct cids * const ids, const uint_t seq);

extern struct cid * __attribute__((nonnull))
next_cid(struct cids * const ids, const uint_t seq);

extern bool __attribute__((nonnull))
need_more_cids(const struct cids * const ids, const uint_t act_cid_lim);

extern struct cid * __attribute__((nonnull))
cid_ins(struct cids * const ids, const struct cid * const id);

extern void __attribute__((nonnull))
cid_del(struct cids * const ids, struct cid * const id);

extern void __attribute__((nonnull))
cid_retire(struct cids * const ids, struct cid * const id);

extern void __attribute__((nonnull))
mk_rand_cid(struct cid * const id, const uint8_t len, const bool srt);

extern const char * __attribute__((nonnull(2)))
cid2str(const struct cid * const id, char * const dst, const size_t len_dst);


static inline int __attribute__((nonnull, no_instrument_function))
cid_cmp(const struct cid * const a, const struct cid * const b)
{
    // if the lengths are different, memcmp will fail on the first byte
    return memcmp(&a->len, &b->len, a->len + sizeof(a->len));
}


static inline void __attribute__((nonnull))
cid_cpy(struct cid * const dst, const struct cid * const src)
{
    memcpy((uint8_t *)dst + offsetof(struct cid, seq),
           (const uint8_t *)src + offsetof(struct cid, seq),
           sizeof(struct cid) - offsetof(struct cid, seq) -
               sizeof(src->_unused));
}
