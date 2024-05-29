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

#include <quant/quant.h>

// needed for DEBUG_EXTRA:
#include "quic.h" // IWYU pragma: keep

struct q_conn;
struct q_stream;


typedef void (*func_ptr)(void);

extern func_ptr api_func;
extern void * api_conn;
extern void * api_strm;


extern void loop_init(void);

extern void loop_break(void);

extern void __attribute__((nonnull(1))) loop_run(struct w_engine * const w,
                                                 const func_ptr f,
                                                 struct q_conn * const c,
                                                 struct q_stream * const s);


// see https://stackoverflow.com/a/45600545/2240756
//
#define OVERLOADED_MACRO(M, ...) OVR(M, CNT_ARGS(__VA_ARGS__))(__VA_ARGS__)
#define OVR(macro_name, nargs) OVR_EXPAND(macro_name, nargs)
#define OVR_EXPAND(macro_name, nargs) macro_name##nargs
#define CNT_ARGS(...) ARG_MATCH(__VA_ARGS__, 9, 8, 7, 6, 5, 4, 3, 2, 1)
#define ARG_MATCH(_1, _2, _3, _4, _5, _6, _7, _8, _9, N, ...) N


#define maybe_api_return(...)                                                  \
    __extension__(OVERLOADED_MACRO(maybe_api_return, __VA_ARGS__))


#ifdef DEBUG_EXTRA
#define DEBUG_EXTRA_warn warn
#else
#define DEBUG_EXTRA_warn(...)
#endif


/// If current API function and argument match @p func and @p arg - and @p strm
/// if it is non-zero - exit the event loop.
///
/// @param      func  The API function to potentially return to.
/// @param      conn  The connection to check API activity on.
/// @param      strm  The stream to check API activity on.
///
/// @return     True if the event loop was exited.
///
#define maybe_api_return3(func, conn, strm)                                    \
    __extension__({                                                            \
        if (unlikely(api_func == (func_ptr)(&(func)) && api_conn == (conn) &&  \
                     ((strm) == 0 || api_strm == (strm)))) {                   \
            loop_break();                                                      \
            DEBUG_EXTRA_warn(DBG, #func "(" #conn ", " #strm                   \
                                        ") done, exiting event loop");         \
        }                                                                      \
        api_func == 0;                                                         \
    })


/// If current API argument matches @p arg - and @p strm if it is non-zero -
/// exit the event loop (for any active API function).
///
/// @param      conn  The connection to check API activity on.
/// @param      strm  The stream to check API activity on.
///
/// @return     True if the event loop was exited.
///
#define maybe_api_return2(conn, strm)                                          \
    __extension__({                                                            \
        if (unlikely(api_conn == (conn) &&                                     \
                     ((strm) == 0 || api_strm == (strm)))) {                   \
            loop_break();                                                      \
            DEBUG_EXTRA_warn(DBG, "<any>(" #conn ", " #strm                    \
                                  ") done, exiting event loop");               \
        }                                                                      \
        api_func == 0;                                                         \
    })
