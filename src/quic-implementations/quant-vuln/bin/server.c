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

#include <errno.h>
#include <fcntl.h>
#include <libgen.h>
#include <net/if.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/param.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef __linux__
#include <sys/types.h>
#endif

#include <http_parser.h>

#include <quant/quant.h>

struct q_conn;
struct q_stream;


#ifndef NDEBUG
static bool __attribute__((const)) is_bench_obj(const uint_t len)
{
    return len == 5000000 || len == 10000000;
}
#endif


static void __attribute__((noreturn)) usage(const char * const name,
                                            const char * const ifname,
                                            const char * const qlog_dir,
                                            const uint16_t port,
                                            const char * const dir,
                                            const char * const cert,
                                            const char * const key,
                                            const char * const tls_log,
                                            const uint32_t timeout,
                                            const uint32_t initial_rtt,
                                            const bool retry,
                                            const uint32_t num_bufs)
{
    printf("%s [options]\n", name);
    printf("\t[-b bufs]\tnumber of network buffers to allocate; default %u\n ",
           num_bufs);
    printf("\t[-c cert]\tTLS certificate; default %s\n", cert);
    printf("\t[-d dir]\tserver root directory; default %s\n", dir);
    printf("\t[-i interface]\tinterface to run over; default %s\n", ifname);
    printf("\t[-k key]\tTLS key; default %s\n", key);
    printf("\t[-l log]\tlog file for TLS keys; default %s\n",
           *tls_log ? tls_log : "false");
    printf("\t[-p port]\tdestination port; default %d\n", port);
    printf("\t[-q log]\twrite qlog events to directory; default %s\n",
           *qlog_dir ? qlog_dir : "false");
    printf("\t[-r]\t\tforce a Retry; default %s\n", retry ? "true" : "false");
    printf("\t[-t timeout]\tidle timeout in seconds; default %u\n", timeout);
#ifndef NDEBUG
    printf("\t[-v verbosity]\tverbosity level (0-%d, default %d)\n", DLEVEL,
           util_dlevel);
#endif
    printf("\t[-x rtt]\tinitial RTT in milliseconds (default %u)\n",
           initial_rtt);
    exit(0);
}


struct cb_data {
    struct q_stream * s;
    struct q_conn * c;
    struct w_engine * w;
    int dir;
    int af;
};


KHASH_MAP_INIT_INT(strm_cache, struct w_iov_sq *)


static bool send_err(struct cb_data * const d, const uint16_t code)
{
    const char * msg;
    bool close = false;

    switch (code) {
    case 400:
        msg = "400 Bad Request";
        close = true;
        break;
    case 403:
        msg = "403 Forbidden";
        break;
    case 404:
        msg = "404 Not Found";
        break;
    case 505:
        msg = "505 HTTP Version Not Supported";
        close = true;
        break;
    default:
        msg = "500 Internal Server Error";
    }

    if (close && d->c) {
        q_close(d->c, 0x0003, msg);
        d->c = 0;
    } else
        q_write_str(d->w, d->s, msg, strlen(msg), true);
    return close;
}


#ifndef NDEBUG
static uint32_t bench_cnt = 0;
#endif


static int serve_cb(http_parser * parser, const char * at, size_t len)
{
    (void)parser;
    struct cb_data * const d = parser->data;
    char cid_str[64];
    q_cid_str(d->c, cid_str, sizeof(cid_str));
    warn(INF, "conn %s strm %" PRId " serving URL %.*s", cid_str, q_sid(d->s),
         (int)len, at);

    struct http_parser_url u = {0};
    if (http_parser_parse_url(at, len, 0, &u)) {
        warn(ERR, "http_parser_parse_url: %s",
             http_errno_description((enum http_errno)errno));
        return send_err(d, 400);
    }

    char path[8192] = ".";
    if ((u.field_set & (1 << UF_PATH)) == 0)
        return send_err(d, 400);

    strncpy(&path[at[u.field_data[UF_PATH].off] == '/' ? 1 : 0],
            &at[u.field_data[UF_PATH].off], u.field_data[UF_PATH].len);

    if ((u.field_set & (1 << UF_QUERY)))
        warn(ERR, "ignoring query: %.*s", u.field_data[UF_QUERY].len,
             &at[u.field_data[UF_QUERY].off]);

    if ((u.field_set & (1 << UF_FRAGMENT)))
        warn(ERR, "ignoring fragment: %.*s", u.field_data[UF_FRAGMENT].len,
             &at[u.field_data[UF_FRAGMENT].off]);

    // hacky way to prevent directory traversals
    if (strstr(path, "..") || strstr(path, "//"))
        return send_err(d, 403);

    // check if this is a "GET /n" request for random data
    const uint32_t n = (uint32_t)strtoul(&path[2], 0, 10);
    if (n) {
        struct w_iov_sq out = w_iov_sq_initializer(out);
        q_alloc(d->w, &out, d->c, d->af, n);
        // check whether we managed to allow enough buffers
        if (w_iov_sq_len(&out) != n) {
            warn(ERR, "could only allocate %" PRIu "/%u bytes of buffer",
                 w_iov_sq_len(&out), n);
            q_free(&out);
            return send_err(d, 500);
        }

#ifndef NDEBUG
        // randomize data
        struct w_iov * v;
        uint8_t c = 'A' + (uint8_t)w_rand_uniform32(26);
        sq_foreach (v, &out, next) {
            memset(v->buf, c, v->len);
            c = unlikely(c == 'Z') ? 'A' : c + 1;
        }

        // for the two "benchmark objects", reduce logging
        if (is_bench_obj(n)) {
            warn(NTE, "reducing log level for benchmark object transfer");
            util_dlevel = WRN;
            bench_cnt++;
        }
#endif

        q_write(d->s, &out, true);

        return 0;
    }

    struct stat info;
    if (fstatat(d->dir, path, &info, 0) == -1)
        return send_err(d, 404);

    // if this a directory, look up its index
    if (info.st_mode & S_IFDIR) {
        strncat(path, "/index.html", sizeof(path) - len - 1);
        if (fstatat(d->dir, path, &info, 0) == -1)
            return send_err(d, 404);
    }

    if ((info.st_mode & S_IFREG) == 0 || (info.st_mode & S_IFLNK) == 0)
        return send_err(d, 403);

    if (info.st_size >= UINT32_MAX)
        return send_err(d, 500);

    const int f = openat(d->dir, path, O_RDONLY | O_CLOEXEC);
    ensure(f != -1, "could not open %s", path);

    q_write_file(d->w, d->s, f, (uint32_t)info.st_size, true);

    return 0;
}


static uint32_t __attribute__((nonnull))
strm_key(struct q_conn * const c, const struct q_stream * const s)
{
    uint8_t buf[sizeof(uint_t) + 32];
    const uint_t sid = q_sid(s);
    memcpy(buf, &sid, sizeof(uint_t));
    size_t len = sizeof(buf) - sizeof(uint_t);
    q_cid(c, &buf[sizeof(uint_t)], &len);
    return fnv1a_32(buf, len + sizeof(uint_t));
}


#define MAXPORTS 16

int main(int argc, char * argv[])
{
    uint32_t timeout = 10;
#ifndef NDEBUG
    short ini_dlevel = util_dlevel =
        DLEVEL; // default to maximum compiled-in verbosity
#endif
    char ifname[IFNAMSIZ] = "lo"
#ifndef __linux__
                            "0"
#endif
        ;
    char dir[MAXPATHLEN] = ".";
    char cert[MAXPATHLEN] = "test/dummy.crt";
    char key[MAXPATHLEN] = "test/dummy.key";
    char tls_log[MAXPATHLEN] = "";
    char qlog_dir[MAXPATHLEN] = "";
    uint16_t port[MAXPORTS] = {4433, 4434};
    size_t num_ports = 0;
    uint32_t num_bufs = 100000;
    uint32_t initial_rtt = 500;
    int ch;
    int ret = 0;
    bool retry = false;

    // set default TLS log file from environment
    const char * const keylog = getenv("SSLKEYLOGFILE");
    if (keylog) {
        strncpy(tls_log, keylog, MAXPATHLEN);
        tls_log[MAXPATHLEN - 1] = 0;
    }

    while ((ch = getopt(argc, argv, "hi:p:d:v:c:k:t:b:q:rl:x:")) != -1) {
        switch (ch) {
        case 'q':
            strncpy(qlog_dir, optarg, sizeof(qlog_dir) - 1);
            break;
        case 'i':
            strncpy(ifname, optarg, sizeof(ifname) - 1);
            break;
        case 'd':
            strncpy(dir, optarg, sizeof(dir) - 1);
            break;
        case 'c':
            strncpy(cert, optarg, sizeof(cert) - 1);
            break;
        case 'k':
            strncpy(key, optarg, sizeof(key) - 1);
            break;
        case 'p':
            port[num_ports++] =
                (uint16_t)MIN(UINT16_MAX, strtoul(optarg, 0, 10));
            ensure(num_ports < MAXPORTS, "can only listen on at most %u ports",
                   MAXPORTS);
            break;
        case 't':
            timeout =
                MIN(600, (uint32_t)strtoul(optarg, 0, 10)); // 10 min = 600 sec
            break;
        case 'x':
            initial_rtt = MAX(1, (uint32_t)strtoul(optarg, 0, 10));
            break;
        case 'b':
            num_bufs = (uint32_t)strtoul(optarg, 0, 10);
            break;
        case 'r':
            retry = true;
            break;
        case 'l':
            strncpy(tls_log, optarg, sizeof(tls_log) - 1);
            break;
        case 'v':
#ifndef NDEBUG
            ini_dlevel = util_dlevel =
                (short)MIN(DLEVEL, strtoul(optarg, 0, 10));
#endif
            break;
        case 'h':
        case '?':
        default:
            usage(basename(argv[0]), ifname, qlog_dir, port[0], dir, cert, key,
                  tls_log, timeout, initial_rtt, retry, num_bufs);
        }
    }

    if (num_ports == 0)
        // if no -p args were given, we listen on two ports by default
        num_ports = 2;

    const int dir_fd = open(dir, O_RDONLY | O_CLOEXEC);
    ensure(dir_fd != -1, "%s does not exist", dir);

    struct w_engine * const w =
        q_init(ifname,
               &(const struct q_conf){
                   .conn_conf =
                       &(struct q_conn_conf){.initial_rtt = initial_rtt,
                                             .idle_timeout = timeout,
                                             .enable_spinbit = true,
                                             .enable_udp_zero_checksums = true},
                   .qlog_dir = *qlog_dir ? qlog_dir : 0,
                   .tls_log = *tls_log ? tls_log : 0,
                   .force_retry = retry,
                   .num_bufs = num_bufs,
                   .tls_cert = cert,
                   .tls_key = key});
    for (size_t i = 0; i < num_ports; i++) {
        for (uint16_t idx = 0; idx < w->addr_cnt; idx++) {
#ifndef NDEBUG
            const struct q_conn * const c =
#endif
                q_bind(w, idx, port[i]);
            warn(DBG, "%s %s %s %s%s%s:%d", basename(argv[0]),
                 c ? "listening on" : "failed to bind to", ifname,
                 w->ifaddr[idx].addr.af == AF_INET6 ? "[" : "",
                 w_ntop(&w->ifaddr[idx].addr, ip_tmp),
                 w->ifaddr[idx].addr.af == AF_INET6 ? "]" : "", port[i]);
        }
    }

    khash_t(strm_cache) sc = {0};
    bool first_conn = true;
    http_parser_settings settings = {.on_url = serve_cb};

    while (1) {
        struct q_conn * c;
        const bool have_active =
            q_ready(w, first_conn ? 0 : timeout * NS_PER_S, &c);
        // warn(ERR, "%u %u", first_conn, have_active);
        if (c == 0) {
            if (have_active == false && timeout)
                break;
            continue;
        }
        first_conn = false;

        // do we need to q_accept?
        if (q_is_new_serv_conn(c)) {
            q_accept(w, 0);
            continue;
        }

        if (q_is_conn_closed(c)) {
            q_close(c, 0, 0);
            continue;
        }

    again:;
        struct w_iov_sq q = w_iov_sq_initializer(q);
        struct q_stream * s = q_read(c, &q, false);

        if (s == 0)
            continue;

        if (q_is_uni_stream(s)) {
            warn(NTE, "can't serve request on uni stream: %.*s",
                 sq_first(&q)->len, sq_first(&q)->buf);
            goto next;
        }

        if (q_is_stream_closed(s))
            goto next;

        khiter_t k = kh_get(strm_cache, &sc, strm_key(c, s));
        struct w_iov_sq * sq =
            (kh_size(&sc) == 0 || k == kh_end(&sc) ? 0 : kh_val(&sc, k));

        if (sq == 0) {
            // this is a new stream, insert into stream cache
            sq = calloc(1, sizeof(*sq));
            ensure(sq, "calloc failed");
            sq_init(sq);
            int err;
            k = kh_put(strm_cache, &sc, strm_key(c, s), &err);
            ensure(err >= 1, "inserted returned %d", err);
            kh_val(&sc, k) = sq;
        }
        sq_concat(sq, &q);

        if (q_peer_closed_stream(s) && !sq_empty(sq)) {
            // do we need to handle a request?
            char url[8192];
            size_t url_len = 0;
            struct w_iov * v;
            sq_foreach (v, sq, next) {
                memcpy(&url[url_len], v->buf, v->len);
                url_len += v->len;
            }

            http_parser parser = {
                .data = &(struct cb_data){.c = c,
                                          .w = w,
                                          .dir = dir_fd,
                                          .s = s,
                                          .af = sq_first(sq)->wv_af}};
            http_parser_init(&parser, HTTP_REQUEST);

            const size_t parsed =
                http_parser_execute(&parser, &settings, url, url_len);
            if (parsed != url_len) {
                warn(ERR, "HTTP parser error: %.*s", (int)(url_len - parsed),
                     &url[parsed]);
                // XXX the strnlen() test is super-hacky
                if (strnlen(url, url_len) == url_len)
                    send_err(parser.data, 400);
                else
                    send_err(parser.data, 505);
                ret = 1;
                continue;
            }
        }

    next:
        if (q_is_stream_closed(s)) {
            // retrieve the TX'ed request
            q_stream_get_written(s, &q);
#ifndef NDEBUG
            // if we wrote a "benchmark objects", increase logging
            const uint_t len = w_iov_sq_len(&q);
            if (is_bench_obj(len) && --bench_cnt == 0) {
                util_dlevel = ini_dlevel;
                warn(NTE, "increasing log level after benchmark object "
                          "transfer");
            }
#endif
            k = kh_get(strm_cache, &sc, strm_key(c, s));
            ensure(kh_size(&sc) && k != kh_end(&sc), "found");
            sq = kh_val(&sc, k);
            q_free(sq);
            free(sq);
            kh_del(strm_cache, &sc, k);
            q_free_stream(s);
            q_free(&q);
        }
        goto again;
    }

    q_cleanup(w);
    struct w_iov_sq * sq;
    kh_foreach_value(&sc, sq, { free(sq); });
    kh_release(strm_cache, &sc);
    warn(DBG, "%s exiting with %d", basename(argv[0]), ret);
    return ret;
}
