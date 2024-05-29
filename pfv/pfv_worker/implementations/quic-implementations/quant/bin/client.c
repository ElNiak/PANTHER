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

#include <errno.h>
#include <fcntl.h>
#include <libgen.h>
#include <limits.h>
#include <net/if.h>
#include <netdb.h>
#include <netinet/in.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/param.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/uio.h>
#include <time.h>
#include <unistd.h>

#define klib_unused

#include <http_parser.h>
#include <picohttp/h3zero.h>
#include <quant/quant.h>


#define bps(bytes, secs)                                                       \
    __extension__({                                                            \
        static char _str[32];                                                  \
        const double _bps = ((secs) > 1e-9) ? (double)(bytes)*8 / (secs) : 0;  \
        if (_bps > NS_PER_S)                                                   \
            snprintf(_str, sizeof(_str), "%.3f Gb/s", _bps / NS_PER_S);        \
        else if (_bps > US_PER_S)                                              \
            snprintf(_str, sizeof(_str), "%.3f Mb/s", _bps / US_PER_S);        \
        else if (_bps > MS_PER_S)                                              \
            snprintf(_str, sizeof(_str), "%.3f Kb/s", _bps / MS_PER_S);        \
        else                                                                   \
            snprintf(_str, sizeof(_str), "%.3f b/s", _bps);                    \
        _str;                                                                  \
    })


struct conn_cache_entry {
    struct q_conn * c;
    struct addrinfo * peerinfo;
#ifndef NO_MIGRATION
    struct addrinfo * migr_peer;
#endif
    bool migrated;
    uint8_t _unused[7];
};


KHASH_MAP_INIT_INT64(conn_cache, struct conn_cache_entry *)


static uint32_t vers = 0;
static uint32_t timeout = 10;
static uint32_t initial_rtt = 500;
static uint32_t num_bufs = 100000;
static uint32_t reps = 1;
static bool do_h3 = false;
static bool prefer_v6 = false;
static bool do_chacha = false;
static bool flip_keys = false;
static bool zlen_cids = false;
static bool write_files = false;
static bool test_qr = false;
static bool disable_pmtud = false;
static bool enable_grease = false;
#ifndef NO_MIGRATION
static bool rebind = false;
static bool switch_ip = false;
#endif


struct stream_entry {
    sl_entry(stream_entry) next;
    struct conn_cache_entry * cce;
    struct q_stream * s;
    char * url;
    uint64_t req_t;
    uint64_t rep_t;
    struct w_iov_sq req;
    struct w_iov_sq rep;
};


static sl_head(stream_list, stream_entry) sl = sl_head_initializer(sl);


static inline uint64_t __attribute__((nonnull))
conn_cache_key(const struct sockaddr * const sock)
{
    const struct sockaddr_in * const sock4 =
        (const struct sockaddr_in *)(const void *)sock;

    return ((uint64_t)sock4->sin_addr.s_addr
            << sizeof(sock4->sin_addr.s_addr) * 8) |
           (uint64_t)sock4->sin_port;
}


static void __attribute__((noreturn, nonnull))
usage(const char * const name,
      const char * const ifname,
      const char * const cache,
      const char * const tls_log,
      const char * const qlog_dir,
      const char * const tls_ca_store)
{
    printf("%s [options] URL [URL...]\n", name);
    printf("\t[-3]\t\tsend a static H3 request; default %s\n",
           do_h3 ? "true" : "false");
    printf("\t[-6]\t\tprefer IPv6; default %s\n", prefer_v6 ? "true" : "false");
    printf("\t[-a]\t\tforce Chacha20; default %s\n",
           do_chacha ? "true" : "false");
    printf("\t[-b bufs]\tnumber of network buffers to allocate; default %u\n",
           num_bufs);
    printf("\t[-c]\t\tverify TLS certs using this CA cert; default %s\n",
           *tls_ca_store ? tls_ca_store : "WebPKI");
    printf("\t[-e version]\tQUIC version to use; default 0x%08x\n",
           vers ? vers : DRAFT_VERSION);
    printf("\t[-g]\t\tenable greasing the QUIC bit; default %s\n",
           enable_grease ? "true" : "false");
    printf("\t[-i interface]\tinterface to run over; default %s\n", ifname);
    printf("\t[-l log]\tlog file for TLS keys; default %s\n",
           *tls_log ? tls_log : "false");
    printf("\t[-m]\t\ttest multi-pkt initial (\"quantum-readiness\"); default "
           "%s\n",
           test_qr ? "true" : "false");
#ifndef NO_MIGRATION
    printf("\t[-n]\t\tsimulate NAT rebind (use twice for \"real\" migration); "
           "default %s\n",
           rebind ? "true" : "false");
#endif
    printf("\t[-o]\t\tdisable PMTUD; default %s\n",
           disable_pmtud ? "true" : "false");
    printf("\t[-q log]\twrite qlog events to directory; default %s\n",
           *qlog_dir ? qlog_dir : "false");
    printf("\t[-r reps]\trepetitions for all URLs; default %u\n", reps);
    printf("\t[-s cache]\tTLS 0-RTT state cache; default %s\n", cache);
    printf("\t[-t timeout]\tidle timeout in seconds; default %u\n", timeout);
    printf("\t[-u]\t\tupdate TLS keys; default %s\n",
           flip_keys ? "true" : "false");
#ifndef NDEBUG
    printf("\t[-v verbosity]\tverbosity level (0-%d, default %d)\n", DLEVEL,
           util_dlevel);
#endif
    printf("\t[-w]\t\twrite retrieved objects to disk; default %s\n",
           write_files ? "true" : "false");
    printf("\t[-x rtt]\tinitial RTT in milliseconds (default %u)\n",
           initial_rtt);
    printf("\t[-z]\t\tuse zero-length source connection IDs; default %s\n",
           zlen_cids ? "true" : "false");
    exit(0);
}


static void __attribute__((nonnull))
set_from_url(char * const var,
             const size_t len,
             const char * const url,
             const struct http_parser_url * const u,
             const enum http_parser_url_fields f,
             const char * const def)
{
    if ((u->field_set & (1 << f)) == 0) {
        strncpy(var, def, len);
        var[len - 1] = 0;
    } else {
        const uint16_t l = f == UF_PATH
                               ? (uint16_t)strlen(url) - u->field_data[f].off
                               : u->field_data[f].len;
        strncpy(var, &url[u->field_data[f].off], l);
        var[l] = 0;
    }
}


#ifndef NO_MIGRATION
static void __attribute__((nonnull(1)))
try_migrate(struct conn_cache_entry * const cce)
{
    if (rebind && cce->migrated == false)
        cce->migrated = q_migrate(cce->c, switch_ip,
                                  cce->migr_peer ? cce->migr_peer->ai_addr : 0);
}
#else
#define try_migrate(...)
#endif


static struct addrinfo * __attribute__((nonnull))
get_addr(const char * const dest,
         const char * const port,
         struct addrinfo ** peer_v4,
         struct addrinfo ** peer_v6)
{
    *peer_v4 = *peer_v6 = 0;
    struct addrinfo * peer = 0;
    const int err = getaddrinfo(dest, port, 0, &peer);
    if (err != 0) {
        warn(ERR, "getaddrinfo: %s", gai_strerror(err));
        if (peer)
            freeaddrinfo(peer);
        return 0;
    }

    for (struct addrinfo * cand = peer; cand; cand = cand->ai_next) {
        if (*peer_v4 == 0 && cand->ai_family == AF_INET)
            *peer_v4 = cand;
        if (*peer_v6 == 0 && cand->ai_family == AF_INET6)
            *peer_v6 = cand;
    }

    return peer;
}


static struct q_conn * __attribute__((nonnull))
get(char * const url, struct w_engine * const w, khash_t(conn_cache) * cc)
{
    // parse and verify the URIs passed on the command line
    struct http_parser_url u = {0};
    if (http_parser_parse_url(url, strlen(url), 0, &u)) {
        warn(ERR, "URL \"%s\" is malformed (%s)", url,
             http_errno_description((enum http_errno)errno));
        return 0;
    }

    ensure((u.field_set & (1 << UF_USERINFO)) == 0,
           "userinfo unsupported in URL");

    // extract relevant info from URL
    char dest[1024];
    char port[64];
    char path[8192];
    set_from_url(dest, sizeof(dest), url, &u, UF_HOST, "localhost");
    set_from_url(port, sizeof(port), url, &u, UF_PORT, "4433");
    set_from_url(path, sizeof(path), url, &u, UF_PATH, "/index.html");

    struct addrinfo * peer_v4 = 0;
    struct addrinfo * peer_v6 = 0;
    struct addrinfo * const peerinfo = get_addr(dest, port, &peer_v4, &peer_v6);
    if (peerinfo == 0)
        goto fail;
    struct addrinfo * const peer =
        (prefer_v6 && peer_v6) ? peer_v6 : (peer_v4 ? peer_v4 : peer_v6);
    if (peer == 0)
        goto fail;
#ifndef NO_MIGRATION
    struct addrinfo * const migr_peer =
        peer->ai_family == AF_INET ? peer_v6 : peer_v4;
#endif

    // do we have a connection open to this peer?
    khiter_t k = kh_get(conn_cache, cc, conn_cache_key(peer->ai_addr));
    struct conn_cache_entry * cce = (k == kh_end(cc) ? 0 : kh_val(cc, k));

    // add to stream list
    struct stream_entry * se = calloc(1, sizeof(*se));
    ensure(se, "calloc failed");
    sq_init(&se->rep);
    sl_insert_head(&sl, se, next);

    sq_init(&se->req);
    if (do_h3) {
        q_alloc(w, &se->req, 0, peer->ai_family, 1024);
        struct w_iov * const v = sq_first(&se->req);
        const uint16_t len =
            (uint16_t)(h3zero_create_request_header_frame(
                           &v->buf[3], v->buf + v->len - 3, (uint8_t *)path,
                           strlen(path), dest) -
                       &v->buf[3]);

        v->buf[0] = h3zero_frame_header;
        if (len < 64) {
            v->buf[1] = (uint8_t)len;
            memmove(&v->buf[2], &v->buf[3], len);
            v->len = 2 + len;
        } else {
            v->buf[1] = (uint8_t)((len >> 8) | 0x40);
            v->buf[2] = (uint8_t)(len & 0xff);
            v->len = 3 + len;
        }

    } else {
        // assemble an HTTP/0.9 request
        char req_str[sizeof(path) + 6];
        const int req_str_len =
            snprintf(req_str, sizeof(req_str), "GET %s\r\n", path);
        q_chunk_str(w, cce ? cce->c : 0, peer->ai_family, req_str,
                    (uint32_t)req_str_len, &se->req);
    }

    const bool opened_new = cce == 0;
    if (opened_new) {
        se->req_t = w_now(CLOCK_MONOTONIC_RAW);
        // no, open a new connection
        char alpn[16];
        if (vers == 0x1)
            snprintf(alpn, sizeof(alpn), "h%c%s", do_h3 ? '3' : 'q',
                     do_h3 ? "" : "-interop");
        else
            snprintf(alpn, sizeof(alpn), "h%c-%02u", do_h3 ? '3' : 'q',
                     vers ? vers & 0x000000ff : DRAFT_VERSION);
        struct q_conn * const c =
            q_connect(w, peer->ai_addr, dest, &se->req, &se->s, true, alpn, 0);
        if (c == 0)
            goto fail;

        if (do_h3) {
            // we need to open a uni stream for an empty H/3 SETTINGS frame
            struct q_stream * const ss = q_rsv_stream(c, false);
            if (ss == 0)
                return 0;
            static const uint8_t h3_empty_settings[] = {
                0x00, h3zero_frame_settings, 0x00};
            // XXX lsquic doesn't like a FIN on this stream
            q_write_str(w, ss, (const char *)h3_empty_settings,
                        sizeof(h3_empty_settings), false);
        }

        cce = calloc(1, sizeof(*cce));
        ensure(cce, "calloc failed");
        cce->c = c;
        cce->peerinfo = peerinfo;
#ifndef NO_MIGRATION
        cce->migr_peer = migr_peer;
#endif

        // insert into connection cache
        int ret;
        k = kh_put(conn_cache, cc, conn_cache_key(peer->ai_addr), &ret);
        ensure(ret >= 1, "inserted returned %d", ret);
        kh_val(cc, k) = cce;

    } else {
        freeaddrinfo(peerinfo);
        se->s = q_rsv_stream(cce->c, true);
        if (se->s) {
            se->req_t = w_now(CLOCK_MONOTONIC_RAW);
            q_write(se->s, &se->req, true);
        }
    }
    try_migrate(cce);

    se->cce = cce;
    se->url = url;
    return cce->c;

fail:
    freeaddrinfo(peerinfo);
    return 0;
}


static void __attribute__((nonnull)) free_cc(khash_t(conn_cache) * cc)
{
    struct conn_cache_entry * cce;
    kh_foreach_value(cc, cce, {
        freeaddrinfo(cce->peerinfo);
        free(cce);
    });
    kh_release(conn_cache, cc);
}


static void free_se(struct stream_entry * const se)
{
    q_free(&se->req);
    q_free(&se->rep);
    free(se);
}


static void free_sl_head(void)
{
    struct stream_entry * const se = sl_first(&sl);
    sl_remove_head(&sl, next);
    free_se(se);
}


static void free_sl(void)
{
    while (sl_empty(&sl) == false)
        free_sl_head();
}


static void __attribute__((nonnull))
write_object(struct stream_entry * const se)
{
    char * const slash = strrchr(se->url, '/');
    if (slash && *(slash + 1) == 0)
        // this URL ends in a slash, so strip that to name the file
        *slash = 0;

    const int fd =
        open(*basename(se->url) == 0 ? "index.html" : basename(se->url),
             O_CREAT | O_WRONLY | O_CLOEXEC,
             S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH);
    ensure(fd != -1, "cannot open %s", basename(se->url));

    struct iovec vec[IOV_MAX];
    struct w_iov * v = sq_first(&se->rep);
    int i = 0;
    while (v) {
        vec[i].iov_base = v->buf;
        vec[i].iov_len = v->len;
        if (++i == IOV_MAX || sq_next(v, next) == 0) {
            ensure(writev(fd, vec, i) != -1, "cannot writev");
            i = 0;
        }
        v = sq_next(v, next);
    }
    close(fd);
}


int main(int argc, char * argv[])
{
#ifndef NDEBUG
    util_dlevel = DLEVEL; // default to maximum compiled-in verbosity
#endif
    char ifname[IFNAMSIZ] = "lo"
#ifndef __linux__
                            "0"
#endif
        ;
    int ch;
    char cache[MAXPATHLEN] = "/tmp/" QUANT "-session";
    char tls_log[MAXPATHLEN] = "";
    char qlog_dir[MAXPATHLEN] = "";
    char tls_ca_store[MAXPATHLEN] = "";
    int ret = -1;

    // set default TLS log file from environment
    const char * const keylog = getenv("SSLKEYLOGFILE");
    if (keylog) {
        strncpy(tls_log, keylog, MAXPATHLEN);
        tls_log[MAXPATHLEN - 1] = 0;
    }

    while ((ch = getopt(argc, argv,
                        "hi:v:s:t:l:c:u36azb:wr:q:me:x:og"
#ifndef NO_MIGRATION
                        "n"
#endif
                        )) != -1) {
        switch (ch) {
        case 'i':
            strncpy(ifname, optarg, sizeof(ifname) - 1);
            break;
        case 's':
            strncpy(cache, optarg, sizeof(cache) - 1);
            break;
        case 'q':
            strncpy(qlog_dir, optarg, sizeof(qlog_dir) - 1);
            break;
        case 't':
            timeout = (uint32_t)MIN(600, strtoul(optarg, 0, 10)); // 10 min
            break;
        case 'b':
            num_bufs = (uint32_t)MIN(strtoul(optarg, 0, 10), UINT32_MAX);
            break;
        case 'r':
            reps = (uint32_t)MAX(1, MIN(strtoul(optarg, 0, 10), UINT32_MAX));
            break;
        case 'e':
            vers = (uint32_t)MAX(1, MIN(strtoul(optarg, 0, 16), UINT32_MAX));
            break;
        case 'x':
            initial_rtt = MAX(1, (uint32_t)strtoul(optarg, 0, 10));
            break;
        case 'l':
            strncpy(tls_log, optarg, sizeof(tls_log) - 1);
            break;
        case 'c':
            strncpy(tls_ca_store, optarg, sizeof(tls_ca_store) - 1);
            break;
        case 'u':
            flip_keys = true;
            break;
        case '3':
            do_h3 = true;
            break;
        case '6':
            prefer_v6 = true;
            break;
        case 'a':
            do_chacha = true;
            break;
        case 'z':
            zlen_cids = true;
            break;
        case 'w':
            write_files = true;
            break;
        case 'm':
            test_qr = true;
            break;
        case 'o':
            disable_pmtud = true;
            break;
        case 'g':
            enable_grease = true;
            break;
#ifndef NO_MIGRATION
        case 'n':
            if (rebind)
                switch_ip = true;
            rebind = true;
            break;
#endif
        case 'v':
#ifndef NDEBUG
            util_dlevel = (short)MIN(DLEVEL, strtoul(optarg, 0, 10));
#endif
            break;
        case 'h':
        case '?':
        default:
            usage(basename(argv[0]), ifname, cache, tls_log, qlog_dir,
                  tls_ca_store);
        }
    }

    struct w_engine * const w = q_init(
        ifname,
        &(const struct q_conf){
            .conn_conf =
                &(struct q_conn_conf){.initial_rtt = initial_rtt,
                                      .enable_tls_key_updates = flip_keys,
                                      .enable_spinbit = true,
                                      .enable_udp_zero_checksums = true,
                                      .idle_timeout = timeout,
                                      .version = vers,
                                      .disable_pmtud = disable_pmtud,
                                      .enable_grease = enable_grease,
                                      .enable_quantum_readiness_test = test_qr},
            .qlog_dir = *qlog_dir ? qlog_dir : 0,
            .force_chacha20 = do_chacha,
            .num_bufs = num_bufs,
            .ticket_store = cache,
            .tls_log = *tls_log ? tls_log : 0,
            .client_cid_len = zlen_cids ? 0 : 4,
            .tls_ca_store = *tls_ca_store ? tls_ca_store : 0});
    khash_t(conn_cache) cc = {0};

    if (reps > 1)
        puts("size\ttime\t\tbps\t\turl");
    double sum_len = 0;
    double sum_elapsed = 0;
    for (uint64_t r = 1; r <= reps; r++) {
        int url_idx = optind;
        while (url_idx < argc) {
            // open a new connection, or get an open one
            warn(INF, "%s retrieving %s", basename(argv[0]), argv[url_idx]);
            get(argv[url_idx++], w, &cc);
        }

        // collect the replies
        bool all_closed;
        do {
            all_closed = true;
            bool rxed_new = false;
            struct stream_entry * se = 0;
            struct stream_entry * tmp = 0;
            sl_foreach_safe (se, &sl, next, tmp) {
                if (se->cce == 0 || se->cce->c == 0 || se->s == 0) {
                    sl_remove(&sl, se, stream_entry, next);
                    free_se(se);
                    continue;
                }
                try_migrate(se->cce);
                rxed_new |= q_read_stream(se->s, &se->rep, false);

                const bool is_closed = q_peer_closed_stream(se->s);
                all_closed &= is_closed;
                if (is_closed)
                    se->rep_t = w_now(CLOCK_MONOTONIC_RAW);
            }

            if (rxed_new == false && all_closed == false) {
                struct q_conn * c;
                q_ready(w, timeout * NS_PER_S, &c);
                if (c == 0)
                    break;
                if (q_is_conn_closed(c))
                    break;
            }

        } while (all_closed == false);

        // print/save the replies
        while (sl_empty(&sl) == false) {
            struct stream_entry * const se = sl_first(&sl);
            if (ret == -1)
                ret = w_iov_sq_cnt(&se->rep) == 0;
            else
                ret |= w_iov_sq_cnt(&se->rep) == 0;

            const double elapsed =
                se->rep_t >= se->req_t
                    ? (double)(se->rep_t - se->req_t) / NS_PER_S
                    : 0;
            const uint_t rep_len = w_iov_sq_len(&se->rep);
            sum_len += (double)rep_len;
            sum_elapsed += elapsed;
            if (reps > 1)
                printf("%" PRIu "\t%f\t\"%s\"\t%s\n", rep_len, elapsed,
                       bps(rep_len, elapsed), se->url);
#ifndef NDEBUG
            char cid_str[64];
            q_cid_str(se->cce->c, cid_str, sizeof(cid_str));
            warn(WRN,
                 "read %" PRIu
                 " byte%s in %.3f sec (%s) on conn %s strm %" PRIu,
                 rep_len, plural(rep_len), elapsed < 0 ? 0 : elapsed,
                 bps(rep_len, elapsed), cid_str, q_sid(se->s));
#endif

            // retrieve the TX'ed request
            q_stream_get_written(se->s, &se->req);

            if (write_files)
                write_object(se);

            // save the object, and print its first three packets to stdout
            struct w_iov * v;
            uint32_t n = 0;
            sq_foreach (v, &se->rep, next) {
                // cppcheck-suppress nullPointer
                const bool is_last = v == sq_last(&se->rep, w_iov, next);
                if (w_iov_sq_cnt(&se->rep) > 100 || reps > 1)
                    // don't print large responses, or repeated ones
                    continue;

                // XXX the strnlen() test is super-hacky
                if (do_h3 && n == 0 &&
                    (v->buf[0] != 0x01 && v->buf[0] != 0xff &&
                     strnlen((char *)v->buf, v->len) == v->len))
                    warn(WRN, "no h3 payload");
                if (n < 4 || is_last) {
                    if (do_h3) {
#ifndef NDEBUG
                        if (util_dlevel == DBG)
                            hexdump(v->buf, v->len);
#endif
                    } else {
                        // don't print newlines to console log
                        for (uint16_t p = 0; p < v->len; p++)
                            if (v->buf[p] == '\n' || v->buf[p] == '\r')
                                v->buf[p] = ' ';
                        printf("%.*s%s", v->len, v->buf, is_last ? "\n" : "");
                        if (is_last)
                            fflush(stdout);
                    }
                } else
                    printf(".");
                n++;
            }

            q_free_stream(se->s);
            free_sl_head();
        }
    }

    if (reps > 1)
        printf("TOTAL: %s\n", bps(sum_len, sum_elapsed));

    free_cc(&cc);
    free_sl();
    q_cleanup(w);
    warn(DBG, "%s exiting with %d", basename(argv[0]), ret);
    return ret;
}
