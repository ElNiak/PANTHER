/*
 * ngtcp2
 *
 * Copyright (c) 2017 ngtcp2 contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
 * LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
 * WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */
#ifndef SHARED_H
#define SHARED_H

#ifdef HAVE_CONFIG_H
#  include <config.h>
#endif // HAVE_CONFIG_H

#include <ngtcp2/ngtcp2.h>

namespace ngtcp2 {

constexpr uint8_t HQ_ALPN[] = "\x05hq-29";

enum class QUICErrorType {
  Application,
  Transport,
  TransportVersionNegotiation,
  TransportIdleTimeout,
};

struct QUICError {
  QUICError(QUICErrorType type, uint64_t code) : type(type), code(code) {}

  QUICErrorType type;
  uint64_t code;
};

QUICError quic_err_transport(int liberr);

QUICError quic_err_idle_timeout();

QUICError quic_err_tls(int alert);

QUICError quic_err_app(int liberr);

// msghdr_get_ecn gets ECN bits from |msg|.  |family| is the address
// family from which packet is received.
unsigned int msghdr_get_ecn(msghdr *msg, int family);

// fd_set_ecn sets ECN bits |ecn| to |fd|.  |family| is the address
// family of |fd|.
void fd_set_ecn(int fd, int family, unsigned int ecn);

// fd_set_recv_ecn sets socket option to |fd| so that it can receive
// ECN bits.
void fd_set_recv_ecn(int fd, int family);

} // namespace ngtcp2

#endif // SHARED_H
