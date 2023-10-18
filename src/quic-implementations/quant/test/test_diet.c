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

#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>

#include <quant/quant.h>

#include "bitset.h"
#include "diet.h"
#include "tree.h"

static uint64_t t = 0;


static void trace(struct diet * const d,
                  const uint_t lo
#ifdef NDEBUG
                  __attribute__((unused))
#endif
                  ,
                  const uint_t hi
#ifdef NDEBUG
                  __attribute__((unused))
#endif
                  ,
                  const char * const op
#ifdef NDEBUG
                  __attribute__((unused))
#endif
)
{
    char str[8192];
    diet_to_str(str, sizeof(str), d, true);
#ifndef NDEBUG
    if (lo == hi)
        warn(DBG, "t %" PRIu64 ", cnt %" PRIu ", %s %" PRIu ": %s", t,
             diet_cnt(d), op, lo, str);
    else
        warn(DBG, "t %" PRIu64 ", cnt %" PRIu ", %s %" PRIu "-%" PRIu ": %s", t,
             diet_cnt(d), op, lo, hi, str);
#endif

    uint_t c = 0;
    char * s = str;
    while (*s)
        c += *(s++) == ',';
    ensure(str[0] == 0 || c + 1 == diet_cnt(d), "%" PRIu " %" PRIu "", c + 1,
           diet_cnt(d));
}


static void chk(struct diet * const d)
{
    struct ival * i;
    struct ival * next;
    for (i = splay_min(diet, d); i != 0; i = next) {
        next = splay_next(diet, d, i);
        ensure(next == 0 || i->hi + 1 < next->lo,
               "%" PRIu "-%" PRIu " %" PRIu "-%" PRIu, i->lo, i->hi, next->lo,
               next->hi);
    }
}


#define N 300
bitset_define(values, N);

int main()
{
    w_init_rand();
#ifndef NDEBUG
    util_dlevel = DLEVEL; // default to maximum compiled-in verbosity
#endif
    struct diet d = diet_initializer(diet);
    struct values v = bitset_t_initializer(0);

    // insert some items
    while (N != bit_count(N, &v)) {
        const uint_t x = w_rand_uniform32(N);
        if (bit_isset(N, x, &v) == 0) {
            bit_set(N, x, &v);
            diet_insert(&d, x, ++t);
            trace(&d, x, x, "ins");
            chk(&d);
        }
    }

    // remove all items
    while (!splay_empty(&d)) {
        const uint_t x = w_rand_uniform32(N);
        struct ival * const i = diet_find(&d, x);
        if (i) {
            if (w_rand_uniform32(2)) {
                const uint_t lodiff = w_rand_uniform32(3);
                const uint_t lo = x - (x > lodiff ? lodiff : 0);
                const uint_t hi = x + w_rand_uniform32(3);
                diet_remove_ival(&d, &(struct ival){.lo = lo, .hi = hi});
                trace(&d, lo, hi, "rem_ival");
            } else {
                diet_remove(&d, x);
                trace(&d, x, x, "rem");
            }
            chk(&d);
        }
    }
    ensure(diet_cnt(&d) == 0, "incorrect node count %" PRIu " != 0",
           diet_cnt(&d));

    return 0;
}
