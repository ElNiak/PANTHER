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

#include <stdio.h>
#include <stdlib.h>
#include <sys/param.h>

#include <quant/quant.h>

#include "diet.h"


SPLAY_GENERATE(diet, ival, node, ival_cmp)


/// Return maximum interval underneath @p i.
///
/// @param      i     Interval inside diet tree.
///
/// @return     Largest interval underneath @p i.
///
static inline struct ival * find_max(struct ival * const i)
{
    if (i == 0)
        return 0;
    struct ival * n = i;
    while (splay_right(n, node))
        n = splay_right(n, node);
    return n;
}


/// Return minimum interval underneath @p i.
///
/// @param      i     Interval inside diet tree.
///
/// @return     Smallest interval underneath @p i.
///
static inline struct ival * find_min(struct ival * const i)
{
    if (i == 0)
        return 0;
    struct ival * n = i;
    while (splay_left(n, node))
        n = splay_left(n, node);
    return n;
}


/// Pointer to the interval containing @p n in diet tree @p d. Also has the side
/// effect of splaying the closest interval to @p n to the root of @p d.
///
/// @param      d     Diet tree.
/// @param[in]  n     Integer.
///
/// @return     Pointer to the ival structure containing @p i; zero otherwise.
///
struct ival * diet_find(struct diet * const d, const uint_t n)
{
    if (splay_empty(d))
        return 0;
    diet_splay(d, &(const struct ival){.lo = n, .hi = n});
    if (n < splay_root(d)->lo || n > splay_root(d)->hi)
        return 0;
    return splay_root(d);
}


/// Helper function to allocate an interval [n..n] containing only @p n.
///
/// @param[in]  n     Integer.
/// @param[in]  t     Timestamp.
///
/// @return     Newly allocated ival struct [n..n].
///
static inline struct ival * mk_ival(const uint_t n, const uint64_t t)
{
    struct ival * const i = calloc(1, sizeof(*i));
    ensure(i, "could not calloc");
    i->lo = i->hi = n;
    i->t = t;
    return i;
}


/// Inserts integer @p n of type into the diet tree @p d.
///
/// @param      d     Diet tree.
/// @param[in]  n     Integer.
/// @param[in]  t     Timestamp.
///
/// @return     Pointer to ival containing @p n.
///
struct ival *
diet_insert(struct diet * const d, const uint_t n, const uint64_t t)
{
    if (splay_empty(d))
        goto new_ival;

    // rotate the interval that contains n or is closest to it to the top
    diet_find(d, n);

    if (n >= splay_root(d)->lo && n <= splay_root(d)->hi) {
        splay_root(d)->t = MAX(splay_root(d)->t, t);
        return splay_root(d);
    }

    if (n < splay_root(d)->lo) {
        struct ival * const max = find_max(splay_left(splay_root(d), node));

        if (n + 1 == splay_root(d)->lo) {
            // we can expand the root to include n
            splay_root(d)->lo--;
            splay_root(d)->t = MAX(splay_root(d)->t, t);
        } else if (max && max->hi + 1 == n) {
            // we can expand the max child to include n
            max->hi++;
            max->t = MAX(max->t, t);
        } else
            goto new_ival;

        // check if we can merge the new root with its max left child
        if (max && max->hi == splay_root(d)->lo - 1) {
            splay_right(max, node) = splay_right(splay_root(d), node);
            max->hi = splay_root(d)->hi;
            max->t = MAX(max->t, t);
            struct ival * const old_root = splay_root(d);
            splay_root(d) = splay_left(splay_root(d), node);
            free(old_root);
            splay_count(d)--;
        }
        return splay_root(d);
    }

    if (n > splay_root(d)->hi) {
        struct ival * const min = find_min(splay_right(splay_root(d), node));

        if (n == splay_root(d)->hi + 1) {
            // we can expand the root to include n
            splay_root(d)->hi++;
            splay_root(d)->t = MAX(splay_root(d)->t, t);
        } else if (min && min->lo - 1 == n) {
            // we can expand the min child to include n
            min->lo--;
            min->t = MAX(min->t, t);
        } else
            goto new_ival;

        // check if we can merge the new root with its min right child
        if (min && min->lo == splay_root(d)->hi + 1) {
            splay_left(min, node) = splay_left(splay_root(d), node);
            min->lo = splay_root(d)->lo;
            min->t = MAX(min->t, t);
            struct ival * const old_root = splay_root(d);
            splay_root(d) = splay_right(splay_root(d), node);
            free(old_root);
            splay_count(d)--;
        }
        return splay_root(d);
    }

new_ival:;
    struct ival * const i = mk_ival(n, t);
    splay_insert(diet, d, i);
    return i;
}


/// Splits the root of the diet tree @p d, removing the interval [lo..hi] from
/// it.
///
/// @param      d     Diet tree.
/// @param[in]  lo    The lower value of the interval to be removed.
/// @param[in]  hi    The upper value of the interface to be remove.
///
static void __attribute__((nonnull))
split_root(struct diet * const d, const uint_t lo, const uint_t hi)
{
    struct ival * const i = mk_ival(splay_root(d)->lo, splay_root(d)->t);
    splay_count(d)++;
    i->hi = lo - 1;
    splay_root(d)->lo = hi + 1;
    splay_left(i, node) = splay_left(splay_root(d), node);
    splay_left(splay_root(d), node) = 0;
    splay_right(i, node) = splay_root(d);
    splay_root(d) = i;
}


/// Remove integer @p n from the intervals stored in diet tree @p d.
///
/// @param      d     Diet tree.
/// @param[in]  n     Integer.
///
void diet_remove(struct diet * const d, const uint_t n)
{
    if (splay_empty(d))
        return;

    // rotate the interval that contains n or is closest to it to the top
    diet_find(d, n);

    if (n < splay_root(d)->lo || n > splay_root(d)->hi)
        return;

    if (n == splay_root(d)->lo) {
        if (n == splay_root(d)->hi)
            free(splay_remove(diet, d, splay_root(d)));
        else
            // adjust lo bound
            splay_root(d)->lo++;
    } else if (n == splay_root(d)->hi) {
        // adjust hi bound
        splay_root(d)->hi--;
    } else
        split_root(d, n, n);
}


/// Remove interval @p i from diet tree @p d.
///
/// @param      d     Diet tree.
/// @param[in]  i     Interval.
///
void diet_remove_ival(struct diet * const d, const struct ival * const i)
{
    uint_t lo = i->lo;
    uint_t hi = i->hi;

again:
    if (splay_empty(d))
        return;

    // rotate the interval that contains n or is closest to it to the top
    diet_splay(d, i);

    if (hi < splay_root(d)->lo || lo > splay_root(d)->hi)
        return;

    if (lo > splay_root(d)->lo) {
        if (hi < splay_root(d)->hi) {
            split_root(d, lo, hi);
            return;
        }

        if (hi > splay_root(d)->hi) {
            const uint_t root_hi = splay_root(d)->hi;
            splay_root(d)->hi = lo - 1;
            lo = root_hi + 1;
            goto again;
        }

        splay_root(d)->hi = lo - 1;
        return;
    }

    if (lo < splay_root(d)->lo) {
        if (hi < splay_root(d)->hi) {
            const uint_t root_lo = splay_root(d)->lo;
            splay_root(d)->lo = hi + 1;
            hi = root_lo - 1;
            goto again;
        }

        if (hi <= splay_root(d)->hi)
            hi = splay_root(d)->lo - 1;
        goto free_root;
    }

    if (hi < splay_root(d)->hi) {
        splay_root(d)->lo = hi + 1;
        return;
    }
    hi = splay_root(d)->hi + 1;

free_root:;
    struct ival * const old_root = splay_root(d);
    splay_remove(diet, d, old_root);
    free(old_root);
    goto again;
}


/// Free the diet tree @p d and all its intervals.
///
/// @param      d     Diet tree.
///
void diet_free(struct diet * const d)
{
    while (!splay_empty(d)) {
        struct ival * const i = splay_min(diet, d);
        splay_remove(diet, d, i);
        free(i);
    }
}


size_t diet_to_str(char * const str,
                   const size_t len,
                   struct diet * const d,
                   const bool print_t)
{
    struct ival * i = 0;
    size_t pos = 0;
    str[0] = 0;
    diet_foreach (i, diet, d) {
        pos += (size_t)snprintf(&str[pos], len - pos, "%" PRIu, i->lo);
        if (i->lo != i->hi)
            pos += (size_t)snprintf(&str[pos], len - pos, "-%" PRIu, i->hi);
        if (print_t)
            pos += (size_t)snprintf(&str[pos], len - pos, "(%" PRIu ")",
                                    (uint_t)i->t);
        pos += (size_t)snprintf(&str[pos], len - pos, ", ");
        if (pos >= len)
            break;
    }
    if (pos > 2) {
        pos -= 2;
        str[pos] = 0; // strip final comma and space
    }
    return pos;
}
