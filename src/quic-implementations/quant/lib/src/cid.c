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

#include <stdio.h>
#include <sys/param.h>

#include <quant/quant.h>

#include "cid.h"
#include "quic.h"
#include "tls.h"

#ifndef NO_SRT_MATCHING
#include "conn.h"
#endif


char __cid_str[CID_STR_LEN];


void init_cids(struct cids * const ids)
{
    sl_init(&ids->ret);
    sl_init(&ids->act);
    sl_init(&ids->avl);
    ids->act_cnt = 0;
    for (uint8_t i = 0; i < CIDS_MAX; i++) {
        ids->cids[i].available = true;
        ids->cids[i].retired = false;
        sl_insert_head(&ids->avl, &ids->cids[i], next);
    }
}


struct cid * cid_by_seq(struct cid_sl * const sl, const uint_t seq)
{
    struct cid * id;
    sl_foreach (id, sl, next)
        if (id->seq == seq)
            return id;
    return 0;
}


struct cid * cid_by_id(struct cid_sl * const sl, const struct cid * const id)
{
    struct cid * i;
    sl_foreach (i, sl, next)
        if (cid_cmp(i, id) == 0)
            return i;
    return 0;
}


uint_t cid_cnt(const struct cids * const ids)
{
    return ids->act_cnt;
}


uint_t min_seq(const struct cids * const ids)
{
    uint_t min = UINT_T_MAX;
    struct cid * i;
    sl_foreach (i, &ids->act, next)
        min = MIN(min, i->seq);
    return min;
}


uint_t max_seq(const struct cids * const ids)
{
    uint_t max = 0;
    struct cid * i;
    sl_foreach (i, &ids->act, next)
        max = MAX(max, i->seq);
    return max;
}


void retire_prior_to(struct cids * const ids, const uint_t seq)
{
    struct cid * i;
    struct cid * tmp;
    sl_foreach_safe (i, &ids->act, next, tmp)
        if (i->seq < seq)
            cid_retire(ids, i);
}


struct cid * next_cid(struct cids * const ids, const uint_t seq)
{
    struct cid * next = 0;
    struct cid * i;
    sl_foreach (i, &ids->act, next)
        if (i->seq > seq && (next == 0 || next->seq > i->seq))
            next = i;
    return next;
}


bool need_more_cids(const struct cids * const ids, const uint_t act_cid_lim)
{
    return ids->act_cnt < MIN(4, MIN(act_cid_lim, CIDS_MAX));
}


struct cid * cid_ins(struct cids * const ids, const struct cid * const id)
{
    struct cid * i = sl_first(&ids->avl);
    if (i == 0) {
        // some stacks don't ACK RETIRE_CONNECTION_ID and just issue a new one
        i = sl_first(&ids->ret);
        if (likely(i)) {
            cid_del(ids, i);
#ifndef NO_SRT_MATCHING
            if (i->has_srt)
                conns_by_srt_del(i->srt);
#endif
            i = sl_first(&ids->avl);
            assure(i, "have cid");
        } else {
            warn(ERR, "cannot ins cid %s", cid_str(id));
            return 0;
        }
    }
    sl_remove_head(&ids->avl, next);
    cid_cpy(i, id);
    i->retired = i->available = false;
    sl_insert_head(&ids->act, i, next);
    ids->act_cnt++;
    return i;
}


void cid_del(struct cids * const ids, struct cid * const id)
{
    ensure(id->available == false, "cannot del available cid");
    if (id->retired) {
        sl_remove(&ids->ret, id, cid, next);
        id->retired = false;
    } else {
        sl_remove(&ids->act, id, cid, next);
        ids->act_cnt--;
    }
    id->available = true;
    sl_insert_head(&ids->avl, id, next);
}


void cid_retire(struct cids * const ids, struct cid * const id)
{
    ensure(id->available == false && id->retired == false,
           "can only retire active cid");
    sl_remove(&ids->act, id, cid, next);
    ids->act_cnt--;
    id->retired = true;
    sl_insert_head(&ids->ret, id, next);
}


const char *
cid2str(const struct cid * const id, char * const dst, const size_t len_dst)
{
    const int n = snprintf(dst, len_dst, "%" PRIu ":", id ? id->seq : 0);
    if (id)
        hex2str(id->id, id->len, &dst[n], len_dst - (size_t)n);
    return dst;
}


void mk_rand_cid(struct cid * const id,
                 const uint8_t len,
                 const bool srt
#ifdef NO_SRT_MATCHING
                 __attribute__((unused))
#endif
)
{
    // len==0 means zero-len cid
    if (len) {
        // illegal len means randomize
        id->len = len <= CID_LEN_MAX
                      ? len
                      : 8 + (uint8_t)w_rand_uniform32(CID_LEN_MAX - 7);
        rand_bytes(id->id, id->len);
    }

#ifndef NO_SRT_MATCHING
    id->has_srt = srt;
    if (srt)
        rand_bytes(id->srt, sizeof(id->srt));
#endif
}
