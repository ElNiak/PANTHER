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

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include <quant/quant.h>

#include "marshall.h"

// #define VARINT1_MAX 0x3f
// #define VARINT2_MAX UINT16_C(0x3FFF)
// #define VARINT4_MAX UINT32_C(0x3fffffff)
// #define VARINT8_MAX UINT64_C(0x3fffffffffffffff)
// #define VARINT_MAX VARINT8_MAX

#ifndef NDEBUG
#define VARINT_MASK UINT64_C(0xc000000000000000)
#endif
#define VARINT_MASK8 UINT64_C(0x3fffffffc0000000)
#define VARINT_MASK4 UINT64_C(0x000000003fffc000)
#define VARINT_MASK2 UINT64_C(0x0000000000003fc0)


/// Computes number of bytes need to enccode @p v in QUIC varint encoding.
///
/// @param[in]  val   Value to check.
///
/// @return     Number of bytes needed in varint encoding (1, 2, 4 or 8).
///
uint8_t varint_size(const uint64_t val)
{
    assure((val & VARINT_MASK) == 0, "value overflow: %" PRIu, (uint_t)val);

    if ((val & VARINT_MASK8) != 0)
        return 8;
    if ((val & VARINT_MASK4) != 0)
        return 4;
    if ((val & VARINT_MASK2) != 0)
        return 2;
    return 1;
}


void enc1(uint8_t ** pos,
          const uint8_t * const end
#ifdef NDEBUG
          __attribute__((unused))
#endif
          ,
          const uint8_t val)
{
    assure(*pos + sizeof(val) <= end, "buffer overflow: %lu",
           (unsigned long)(end - *pos));
    **pos = val;
    *pos += sizeof(val);
}


void enc2(uint8_t ** pos,
          const uint8_t * const end
#ifdef NDEBUG
          __attribute__((unused))
#endif
          ,
          const uint16_t val)
{
    assure(*pos + sizeof(val) <= end, "buffer overflow: %lu",
           (unsigned long)(end - *pos));
    const uint16_t v = bswap16(val);
    memcpy(*pos, &v, sizeof(v));
    *pos += sizeof(val);
}


void enc3(uint8_t ** pos,
          const uint8_t * const end
#ifdef NDEBUG
          __attribute__((unused))
#endif
          ,
          const uint32_t val)
{
    assure(*pos + 3 <= end, "buffer overflow: %lu",
           (unsigned long)(end - *pos));
    const uint32_t v = bswap32(val << 8);
    memcpy(*pos, &v, 3);
    *pos += 3;
}


void enc4(uint8_t ** pos,
          const uint8_t * const end
#ifdef NDEBUG
          __attribute__((unused))
#endif
          ,
          const uint32_t val)
{
    assure(*pos + sizeof(val) <= end, "buffer overflow: %lu",
           (unsigned long)(end - *pos));
    const uint32_t v = bswap32(val);
    memcpy(*pos, &v, sizeof(v));
    *pos += sizeof(val);
}


void enc8(uint8_t ** pos,
          const uint8_t * const end
#ifdef NDEBUG
          __attribute__((unused))
#endif
          ,
          const uint64_t val)
{
    assure(*pos + sizeof(val) <= end, "buffer overflow: %lu",
           (unsigned long)(end - *pos));
    const uint64_t v = bswap64(val);
    memcpy(*pos, &v, sizeof(v));
    *pos += sizeof(val);
}


void encv(uint8_t ** pos,
          const uint8_t * const end
#ifdef NDEBUG
          __attribute__((unused))
#endif
          ,
          const uint64_t val)
{
    assure((val & VARINT_MASK) == 0, "value overflow: %" PRIu, (uint_t)val);

    if ((val & VARINT_MASK8) != 0) {
        assure(*pos + 8 <= end, "buffer overflow: %lu",
               (unsigned long)(end - *pos));
        *(*pos + 0) = ((val >> 56) & 0x3f) + 0xc0;
        *(*pos + 1) = (val >> 48) & 0xff;
        *(*pos + 2) = (val >> 40) & 0xff;
        *(*pos + 3) = (val >> 32) & 0xff;
        *(*pos + 4) = (val >> 24) & 0xff;
        *(*pos + 5) = (val >> 16) & 0xff;
        *(*pos + 6) = (val >> 8) & 0xff;
        *(*pos + 7) = val & 0xff;
        *pos += 8;
        return;
    }

    if ((val & VARINT_MASK4) != 0) {
        assure(*pos + 4 <= end, "buffer overflow: %lu",
               (unsigned long)(end - *pos));
        *(*pos + 0) = ((val >> 24) & 0x3f) + 0x80;
        *(*pos + 1) = (val >> 16) & 0xff;
        *(*pos + 2) = (val >> 8) & 0xff;
        *(*pos + 3) = val & 0xff;
        *pos += 4;
        return;
    }

    if ((val & VARINT_MASK2) != 0) {
        assure(*pos + 2 <= end, "buffer overflow: %lu",
               (unsigned long)(end - *pos));
        *(*pos + 0) = ((val >> 8) & 0x3f) + 0x40;
        *(*pos + 1) = val & 0xff;
        *pos += 2;
        return;
    }

    assure(*pos + 1 <= end, "buffer overflow: %lu",
           (unsigned long)(end - *pos));
    **pos = val & 0x3f;
    *pos += 1;
}


void encvl(uint8_t ** pos,
           const uint8_t * const end,
           const uint64_t val,
           const uint8_t len)
{
    const uint8_t len_needed = varint_size(val);
    assure(len_needed <= len, "value/len mismatch");

    if (len_needed == len) {
        encv(pos, end, val);
        return;
    }

    if (len == 2) {
        enc1(pos, end, 0x40);
        enc1(pos, end, (uint8_t)val);
        return;
    }

    if (len == 4) {
        enc1(pos, end, 0x80);
        enc1(pos, end, 0x00);
        enc2(pos, end, (uint16_t)val);
        return;
    }

    if (len == 8) {
        enc1(pos, end, 0xC0);
        enc1(pos, end, 0x00);
        enc2(pos, end, 0x00);
        enc4(pos, end, (uint32_t)val);
        return;
    }
}


void encb(uint8_t ** pos,
          const uint8_t * const end
#ifdef NDEBUG
          __attribute__((unused))
#endif
          ,
          const uint8_t * const val,
          const uint16_t len)
{
    assure(*pos + len <= end, "buffer overflow: %lu",
           (unsigned long)(end - *pos));
    memcpy(*pos, val, len);
    *pos += len;
}


bool dec1(uint8_t * const val,
          const uint8_t ** const pos,
          const uint8_t * const end)
{
    if (unlikely(*pos + sizeof(*val) > end))
        return false;
    *val = **pos;
    *pos += sizeof(*val);
    return true;
}


bool dec2(uint16_t * const val,
          const uint8_t ** const pos,
          const uint8_t * const end)
{
    if (unlikely(*pos + sizeof(*val) > end))
        return false;
    memcpy(val, *pos, sizeof(*val));
    *val = bswap16(*val);
    *pos += sizeof(*val);
    return true;
}


bool dec3(uint32_t * const val,
          const uint8_t ** const pos,
          const uint8_t * const end)
{
    if (unlikely(*pos + 3 > end))
        return false;
    memcpy(val, *pos, 3);
    *val = bswap32(*val << 8);
    *pos += 3;
    return true;
}


bool dec4(uint32_t * const val,
          const uint8_t ** const pos,
          const uint8_t * const end)
{
    if (unlikely(*pos + sizeof(*val) > end))
        return false;
    memcpy(val, *pos, sizeof(*val));
    *val = bswap32(*val);
    *pos += sizeof(*val);
    return true;
}


bool dec8(uint64_t * const val,
          const uint8_t ** const pos,
          const uint8_t * const end)
{
    if (unlikely(*pos + sizeof(*val) > end))
        return false;
    memcpy(val, *pos, sizeof(*val));
    *val = bswap64(*val);
    *pos += sizeof(*val);
    return true;
}


bool decv(uint64_t * const val,
          const uint8_t ** const pos,
          const uint8_t * const end)
{
    switch (**pos & 0xc0) {
    case 0xc0:
        if (unlikely(*pos + 8 > end))
            return false;
        *val =
            ((uint64_t)(*(*pos + 0) & 0x3f) << 56) +
            ((uint64_t)(*(*pos + 1)) << 48) + ((uint64_t)(*(*pos + 1)) << 48) +
            ((uint64_t)(*(*pos + 2)) << 40) + ((uint64_t)(*(*pos + 3)) << 32) +
            ((uint64_t)(*(*pos + 4)) << 24) + ((uint64_t)(*(*pos + 5)) << 16) +
            ((uint64_t)(*(*pos + 6)) << 8) + ((uint64_t)(*(*pos + 7)) << 0);
        *pos += 8;
        return true;

    case 0x80:
        if (unlikely(*pos + 4 > end))
            return false;
        *val = ((uint64_t)(*(*pos + 0) & 0x3f) << 24) +
               ((uint64_t)(*(*pos + 1)) << 16) +
               ((uint64_t)(*(*pos + 2)) << 8) + ((uint64_t)(*(*pos + 3)) << 0);
        *pos += 4;
        return true;

    case 0x40:
        if (unlikely(*pos + 2 > end))
            return false;
        *val = ((uint64_t)(*(*pos + 0) & 0x3f) << 8) + (uint64_t)(*(*pos + 1));
        *pos += 2;
        return true;

    case 0x00:
        if (unlikely(*pos + 1 > end))
            return false;
        *val = (**pos) & 0x3f;
        *pos += 1;
        return true;
    }

    return false;
}


bool decb(uint8_t * const val,
          const uint8_t ** const pos,
          const uint8_t * const end,
          const uint16_t len)
{
    if (unlikely(*pos + len > end))
        return false;
    memcpy(val, *pos, len);
    *pos += len;
    return true;
}
