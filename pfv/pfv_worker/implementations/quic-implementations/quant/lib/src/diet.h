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

#include <quant/quant.h>

#include "tree.h"


/// This is a C adaptation of the "discrete interval encoding tree" (DIET) data
/// structure described in: Martin Erwig, "Diets for fat sets", Journal of
/// Functional Programming, Vol. 8, No. 6, pp. 627–632, 1998.
/// https://web.engr.oregonstate.edu/~erwig/papers/abstracts.html#JFP98
///
/// It also maintains a timestamp of the last insert operation into an @p ival,
/// for the purposes of calculating the ACK delay.


/// An interval [hi..lo] to be used with diet structures, of a given type.
///
struct ival {
    splay_entry(ival) node; ///< Splay tree node data.
    uint_t lo;              ///< Lower bound of the interval.
    uint_t hi;              ///< Upper bound of the interval.
    uint64_t t;             ///< Time stamp of last insert into this interval.
};


/// Compare two ival intervals.
///
/// @param[in]  a     Interval one.
/// @param[in]  b     Interval two.
///
/// @return     Zero if a is in b or b is in a. Negative if a's lower bound is
///             less than b's lower bound, positive otherwise.
///
static inline int __attribute__((nonnull, no_instrument_function))
ival_cmp(const struct ival * const a, const struct ival * const b)
{
    if ((a->lo >= b->lo && a->hi <= b->hi) ||
        (b->lo >= a->lo && b->hi <= a->hi))
        return 0;
    return (a->lo > b->lo) - (a->lo < b->lo);
}


splay_head(diet, ival);


#define diet_initializer splay_initializer
#define diet_init splay_init
#define diet_cnt splay_count
#define diet_foreach splay_foreach
#define diet_foreach_rev splay_foreach_rev
#define diet_next splay_next
#define diet_prev splay_prev


SPLAY_PROTOTYPE(diet, ival, node, ival_cmp)


extern struct ival * diet_find(struct diet * const d, const uint_t n);

extern struct ival * __attribute__((nonnull))
diet_insert(struct diet * const d, const uint_t n, const uint64_t t);

extern void __attribute__((nonnull))
diet_remove(struct diet * const d, const uint_t n);

extern void __attribute__((nonnull))
diet_remove_ival(struct diet * const d, const struct ival * const i);

extern void __attribute__((nonnull)) diet_free(struct diet * const d);

extern size_t __attribute__((nonnull)) diet_to_str(char * const str,
                                                   const size_t len,
                                                   struct diet * const d,
                                                   const bool print_t);

static inline struct ival * __attribute__((nonnull, no_instrument_function))
diet_max_ival(struct diet * const d)
{
    return splay_empty(d) ? 0 : splay_max(diet, d);
}


static inline struct ival * __attribute__((nonnull, no_instrument_function))
diet_min_ival(struct diet * const d)
{
    return splay_empty(d) ? 0 : splay_min(diet, d);
}


static inline uint_t __attribute__((nonnull, no_instrument_function))
diet_max(struct diet * const d)
{
    return splay_empty(d) ? 0 : splay_max(diet, d)->hi;
}


static inline uint_t __attribute__((nonnull, no_instrument_function))
diet_min(struct diet * const d)
{
    return splay_empty(d) ? 0 : splay_min(diet, d)->lo;
}


static inline bool __attribute__((nonnull, no_instrument_function))
diet_empty(const struct diet * const d)
{
    return splay_empty(d);
}


static inline uint64_t __attribute__((nonnull, no_instrument_function))
diet_timestamp(const struct ival * const i)
{
    return i->t;
}
