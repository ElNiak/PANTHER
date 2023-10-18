// Copyright (c) 2014-2018, NetApp, Inc.
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

#include <arpa/inet.h>
#include <cinttypes>
#include <cstdint>
#include <fcntl.h>
#include <libgen.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <benchmark/benchmark.h>
#include <quant/quant.h>


static struct w_engine * w;
static struct q_conn *cc, *sc;


// static void log(const struct q_conn_info * const cci,
//                 const struct q_conn_info * const sci)
// {
//     static uint64_t c_ol_old = 0;
//     static uint64_t s_ol_old = 0;

//     if (cci->pkts_out_lost != c_ol_old || sci->pkts_out_lost != s_ol_old) {
//         std::cout << std::fixed << std::setprecision(4)
//                   << "C: i=" << cci->pkts_in_valid << " o=" << cci->pkts_out
//                   << " ol=" << cci->pkts_out_lost << " pto=" << cci->pto_cnt
//                   << " cwnd=" << cci->cwnd << "\t"
//                   << "S: i=" << sci->pkts_in_valid << " o=" << sci->pkts_out
//                   << " ol=" << sci->pkts_out_lost << " pto=" << sci->pto_cnt
//                   << " cwnd=" << sci->cwnd << std::endl;
//         c_ol_old = cci->pkts_out_lost;
//         s_ol_old = sci->pkts_out_lost;
//     }
// }


static inline uint64_t io(const uint64_t len)
{
    // reserve a new stream
    struct q_stream * const cs = q_rsv_stream(cc, true);
    if (unlikely(cs == nullptr))
        return 0;

    // allocate buffers to transmit a packet
    struct w_iov_sq o = w_iov_sq_initializer(o);
    q_alloc(w, &o, cc, q_conn_af(cc), len);

    // send the data
    q_write(cs, &o, true);

    // read the data
    while (true) {
        struct q_conn * ready;
        q_ready(w, 0, &ready);

        if (ready == sc) {
            struct w_iov_sq i = w_iov_sq_initializer(i);
            struct q_stream * const ss = q_read(sc, &i, true);
            if (ss == nullptr)
                continue;
            if (q_peer_closed_stream(ss))
                q_free_stream(ss);
            const uint64_t ilen = w_iov_sq_len(&i);
            ensure(ilen == len, "mismatch %" PRIu64 " %" PRIu64, len, ilen);
            q_free(&i);
            break;
        }
    }

    q_stream_get_written(cs, &o);
    q_free(&o);
    q_free_stream(cs);

#ifndef NO_QINFO
    struct q_conn_info cci = {0};
    struct q_conn_info sci = {0};
    q_info(cc, &cci);
    q_info(sc, &sci);
    // log(&cci, &sci);
#endif

    return len;
}


static void BM_conn(benchmark::State & state)
{
    const auto len = uint64_t(state.range(0));
    for (auto _ : state) {
        const uint64_t ilen = io(len);
        if (ilen != len) {
            state.SkipWithError("error");
            return;
        }
    }
    state.SetBytesProcessed(int64_t(state.iterations() * len)); // NOLINT
}


BENCHMARK(BM_conn)->RangeMultiplier(2)->Range(1024, 1024 * 1024 * 32)
    // ->Unit(benchmark::kMillisecond)
    ;


// BENCHMARK_MAIN()

int main(int argc __attribute__((unused)), char ** argv)
{
#ifndef NDEBUG
    util_dlevel = WRN; // default to maximum compiled-in verbosity
#endif

    // init
    const int cwd = open(".", O_CLOEXEC);
    ensure(cwd != -1, "cannot open");
    ensure(chdir(dirname(argv[0])) == 0, "cannot chdir");
    const struct q_conf conf = {nullptr, nullptr, "dummy.crt", "dummy.key",
                                nullptr, nullptr, 1000000};
    w = q_init("lo"
#ifndef __linux__
               "0"
#endif
               ,
               &conf);
    ensure(fchdir(cwd) == 0, "cannot fchdir");

    // bind server socket
    q_bind(w, 0, 55555);

    // connect to server
    struct sockaddr_in6 sip = {};
    sip.sin6_family = AF_INET6;
    sip.sin6_port = bswap16(55555);
    inet_pton(sip.sin6_family, "::1", &sip.sin6_addr);
    cc = q_connect(w, reinterpret_cast<struct sockaddr *>(&sip), // NOLINT
                   "localhost", nullptr, nullptr, true, nullptr, nullptr);
    ensure(cc, "is zero");

    // accept connection
    sc = q_accept(w, nullptr);
    ensure(sc, "is zero");

    benchmark::RunSpecifiedBenchmarks();

    // close connections
    q_close(cc, 0, nullptr);
    q_close(sc, 0, nullptr);
    q_cleanup(w);
}
