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

/*-
 * SPDX-License-Identifier: BSD-2-Clause-FreeBSD
 *
 * Copyright (c) 2008, Jeffrey Roberson <jeff@freebsd.org>
 * All rights reserved.
 *
 * Copyright (c) 2008 Nokia Corporation
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice unmodified, this list of conditions, and the following
 *    disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
 * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 * IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 * THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * $FreeBSD$
 */

#pragma once


/*
 * Macros addressing word and bit within it, tuned to make compiler
 * optimize cases when SETSIZE fits into single machine word.
 */
#define _bitset_bits (sizeof(long) * 8)

#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wreserved-id-macro"
#define __howmany(x, y) (((x) + ((y)-1)) / (y))

#define __bitset_words(_s) (__howmany(_s, _bitset_bits))

#define __bitcountl(x) __builtin_popcountl((unsigned long)(x))
#pragma clang diagnostic pop

#define bitset_define(t, _s)                                                   \
    struct t {                                                                 \
        long __bits[__bitset_words((_s))];                                     \
    }

/*
 * Helper to declare a bitset without it's size being a constant.
 *
 * Sadly we cannot declare a bitset struct with '__bits[]', because it's
 * the only member of the struct and the compiler complains.
 */
#define bitset_define_var(t) bitset_define(t, 1)


/*
 * Define a default type that can be used while manually specifying size
 * to every call.
 */
bitset_define(bitset, 1);


#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wreserved-id-macro"
#define __bitset_mask(_s, n)                                                   \
    (1L << ((__bitset_words((_s)) == 1) ? (size_t)(n) : ((n) % _bitset_bits)))

#define __bitset_word(_s, n)                                                   \
    ((__bitset_words((_s)) == 1) ? 0 : ((n) / _bitset_bits))
#pragma clang diagnostic pop

#define bit_clr(_s, n, p)                                                      \
    ((p)->__bits[__bitset_word(_s, n)] &= ~__bitset_mask((_s), (n)))

#define bit_copy(_s, f, t) (void)(*(t) = *(f))

#define bit_isset(_s, n, p)                                                    \
    ((((p)->__bits[__bitset_word(_s, n)] & __bitset_mask((_s), (n))) != 0))

#define bit_set(_s, n, p)                                                      \
    ((p)->__bits[__bitset_word(_s, n)] |= __bitset_mask((_s), (n)))

#define bit_zero(_s, p)                                                        \
    do {                                                                       \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            (p)->__bits[__i] = 0L;                                             \
    } while (0)

#define bit_fill(_s, p)                                                        \
    do {                                                                       \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            (p)->__bits[__i] = -1L;                                            \
    } while (0)

#define bit_setof(_s, n, p)                                                    \
    do {                                                                       \
        bit_zero(_s, p);                                                       \
        (p)->__bits[__bitset_word(_s, n)] = __bitset_mask((_s), (n));          \
    } while (0)

/* Is p empty. */
#define bit_empty(_s, p)                                                       \
    __extension__({                                                            \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            if ((p)->__bits[__i])                                              \
                break;                                                         \
        __i == __bitset_words((_s));                                           \
    })

/* Is p full set. */
#define bit_isfullset(_s, p)                                                   \
    __extension__({                                                            \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            if ((p)->__bits[__i] != (long)-1)                                  \
                break;                                                         \
        __i == __bitset_words((_s));                                           \
    })

/* Is c a subset of p. */
#define bit_subset(_s, p, c)                                                   \
    __extension__({                                                            \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            if (((c)->__bits[__i] & (p)->__bits[__i]) != (c)->__bits[__i])     \
                break;                                                         \
        __i == __bitset_words((_s));                                           \
    })

/* Are there any common bits between b & c? */
#define bit_overlap(_s, p, c)                                                  \
    __extension__({                                                            \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            if (((c)->__bits[__i] & (p)->__bits[__i]) != 0)                    \
                break;                                                         \
        __i != __bitset_words((_s));                                           \
    })

/* Compare two sets, returns 0 if equal 1 otherwise. */
#define bit_cmp(_s, p, c)                                                      \
    __extension__({                                                            \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            if (((c)->__bits[__i] != (p)->__bits[__i]))                        \
                break;                                                         \
        __i != __bitset_words((_s));                                           \
    })

#define bit_or(_s, d, s)                                                       \
    do {                                                                       \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            (d)->__bits[__i] |= (s)->__bits[__i];                              \
    } while (0)

#define bit_or2(_s, d, s1, s2)                                                 \
    do {                                                                       \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            (d)->__bits[__i] = (s1)->__bits[__i] | (s2)->__bits[__i];          \
    } while (0)

#define bit_and(_s, d, s)                                                      \
    do {                                                                       \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            (d)->__bits[__i] &= (s)->__bits[__i];                              \
    } while (0)

#define bit_and2(_s, d, s1, s2)                                                \
    do {                                                                       \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            (d)->__bits[__i] = (s1)->__bits[__i] & (s2)->__bits[__i];          \
    } while (0)

#define bit_nand(_s, d, s)                                                     \
    do {                                                                       \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            (d)->__bits[__i] &= ~(s)->__bits[__i];                             \
    } while (0)

#define bit_nand2(_s, d, s1, s2)                                               \
    do {                                                                       \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            (d)->__bits[__i] = (s1)->__bits[__i] & ~(s2)->__bits[__i];         \
    } while (0)

#define bit_xor(_s, d, s)                                                      \
    do {                                                                       \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            (d)->__bits[__i] ^= (s)->__bits[__i];                              \
    } while (0)

#define bit_xor2(_s, d, s1, s2)                                                \
    do {                                                                       \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            (d)->__bits[__i] = (s1)->__bits[__i] ^ (s2)->__bits[__i];          \
    } while (0)

#define bit_clr_atomic(_s, n, p)                                               \
    atomic_clear_long(&(p)->__bits[__bitset_word(_s, n)],                      \
                      __bitset_mask((_s), n))

#define bit_set_atomic(_s, n, p)                                               \
    atomic_set_long(&(p)->__bits[__bitset_word(_s, n)], __bitset_mask((_s), n))

#define bit_set_atomic_acq(_s, n, p)                                           \
    atomic_set_acq_long(&(p)->__bits[__bitset_word(_s, n)],                    \
                        __bitset_mask((_s), n))

/* Convenience functions catering special cases. */
#define bit_and_atomic(_s, d, s)                                               \
    do {                                                                       \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            atomic_clear_long(&(d)->__bits[__i], ~(s)->__bits[__i]);           \
    } while (0)

#define bit_or_atomic(_s, d, s)                                                \
    do {                                                                       \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            atomic_set_long(&(d)->__bits[__i], (s)->__bits[__i]);              \
    } while (0)

#define bit_copy_store_rel(_s, f, t)                                           \
    do {                                                                       \
        size_t __i;                                                            \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            atomic_store_rel_long(&(t)->__bits[__i], (f)->__bits[__i]);        \
    } while (0)

#define bit_ffs(_s, p)                                                         \
    __extension__({                                                            \
        size_t __i;                                                            \
        int __bit;                                                             \
                                                                               \
        __bit = 0;                                                             \
        for (__i = 0; __i < __bitset_words((_s)); __i++) {                     \
            if ((p)->__bits[__i] != 0) {                                       \
                __bit = __builtin_ffsl((p)->__bits[__i]);                      \
                __bit += __i * _bitset_bits;                                   \
                break;                                                         \
            }                                                                  \
        }                                                                      \
        __bit;                                                                 \
    })

#define bit_fls(_s, p)                                                         \
    __extension__({                                                            \
        size_t __i;                                                            \
        int __bit;                                                             \
                                                                               \
        __bit = 0;                                                             \
        for (__i = __bitset_words((_s)); __i > 0; __i--) {                     \
            if ((p)->__bits[__i - 1] != 0) {                                   \
                __bit = (int)(sizeof((p)->__bits[__i - 1]) << 3) -             \
                        __builtin_clzl((size_t)(p)->__bits[__i - 1]);          \
                __bit += (__i - 1) * _bitset_bits;                             \
                break;                                                         \
            }                                                                  \
        }                                                                      \
        __bit;                                                                 \
    })

#define bit_count(_s, p)                                                       \
    __extension__({                                                            \
        size_t __i;                                                            \
        int __count;                                                           \
                                                                               \
        __count = 0;                                                           \
        for (__i = 0; __i < __bitset_words((_s)); __i++)                       \
            __count += __bitcountl((p)->__bits[__i]);                          \
        __count;                                                               \
    })

#define bitset_t_initializer(x)                                                \
    {                                                                          \
        .__bits = { x }                                                        \
    }

#define bitset_fset(n) [0 ...((n)-1)] = (-1L)

/*
 * Dynamically allocate a bitset.
 */
#define bitset_alloc(_s, mt, mf)                                               \
    malloc(__bitset_words(_s) * sizeof(long), mt, (mf))
