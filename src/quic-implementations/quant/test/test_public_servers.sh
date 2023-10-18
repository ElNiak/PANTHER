#! /usr/bin/env bash

# SPDX-License-Identifier: BSD-2-Clause
#
# Copyright (c) 2016-2020, NetApp, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


declare -A servers=(
    # [tag]="name|flags|port|retry-port|h3-port|URL"
    [aioquic]="quic.aiortc.org||443|4434|443|/40000"
    [akamai]="ietf.akaquic.com|-3|443|443|443|/100k"
    [apple]="[2a00:79e1:abc:301:18c7:dac8:b9c6:f91f]|-3|4433|4433|4433|/40000"
    [ats]="quic.ogre.com||4433|4434|4433|/en/latest/_static/jquery.js"
    [f5]="f5quic.com|-3|4433|4434|4433|/50000"
    [google]="quic.rocks|-3|4433|4434|4433|/40000"
    [haskell]="mew.org|-3|4433|4434|4433|/num/40000"
    [lsquic]="http3-test.litespeedtech.com|-3|4433|4434|4433|/40000"
    [msquic]="quic.westus.cloudapp.azure.com||4433|4434|443|/draft-ietf-quic-http-11.txt"
    [mvfst]="fb.mvfst.net|-3|443|4434|443|/40000"
    [nginx]="quic.nginx.org|-3|443|443|443|/static/fonts/RobotoRegular.woff"
    [ngtcp2]="nghttp2.org|-3|4433|4434|4433|/40000"
    [ngx_quic]="cloudflare-quic.com|-3|443|443|443|/index.html"
    [pandora]="pandora.cm.in.tum.de||4433|4434|4433|/index.html"
    [picoquic]="test.privateoctopus.com||4433|4434|4433|/40000"
    [pquic]="test.pquic.org||443|443|443|/40000"
    [quant]="quant.eggert.org||4433|4434|4433|/40000"
    [quic-go]="interop.seemann.io|-3|443|443|443|/script.js"
    [quiche]="quic.tech|-3|8443|8444|8443|/128KB.png"
    [quicker]="quicker.edm.uhasselt.be||4433|4434|4433|/index.html"
    [quicly]="quic.examp1e.net||4433|4434|443|/40000"
    [quinn]="h3.stammw.eu||4433|4434|443|/100K"
    # [local]="localhost||4433|4434|4433|/40000"
)

results=(live fail vneg hshk data clse rsmt zrtt rtry qrdy migr bind adrm kyph
         spin aecn zcid chch qbgr http)

if [ -n "$1" ]; then
    results+=(perf t_h2 t_hq)
    benchmarking=1
fi


iface=$(route get default | grep interface: | cut -f2 -d: | tr -d "[:space:]")

# use colordiff, if installed
if command -v colordiff > /dev/null; then
    colordiff=$(command -v colordiff)
else
    colordiff=$(command -v cat)
fi


pid=$$
script=$(basename -s .sh "$0")
rm -rf /tmp/"$script"*

# detect_leaks=1:
export ASAN_OPTIONS=strict_string_checks=1:strict_init_order=1:detect_stack_use_after_return=1:check_initialization_order=1:sleep_before_dying=30:alloc_dealloc_mismatch=1:detect_invalid_pointer_pairs=1:print_stacktrace=1:halt_on_error=1
export UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1:suppressions=../misc/gcc-ubsan-suppressions.txt

function test_server_initial {
    # run quant client and save a log for post-processing
    local opts="-c false -i $iface -t5 -v5 -g -b 1000 -l /dev/null"
    local log_base="/tmp/$script.$pid.$1.log"

    IFS='|' read -ra info <<< "${servers[$1]}"
    # 0=name, 1=flags, 2=port, 3=retry-port, 4=h3-port, 5=URL

    # initial 1rtt run that saves a 0-RTT ticket
    local cache="/tmp/$script.$pid.$1.cache"
    sem --jobs +0 --id $pid "bin/client $opts -s $cache ${info[1]} \
        https://${info[0]}:${info[2]}${info[5]} > $log_base.1rtt 2>&1"

    printf "%s " "$s"
}


function prep {
    local log="$1.log.$2"
    [ -s "$log" ] || return

    local sed_pattern='s,\x1B\[[0-9;]*[a-zA-Z],,g'
    local log_strip="$log.strip"
    gsed "$sed_pattern" "$log" > "$log_strip"

    if grep -q -E 'assertion failed|AddressSanitizer|runtime error|ABORT:' "$log_strip"; then
        ret="X"
    elif grep -q -E 'hexdump|STATELESS|_close_frame.*0x1c=quic err=0x[^0]' "$log_strip"; then
        ret="x"
    fi

    if [ -n "$ret" ]; then
        local ret_base="$1.ret"
        >&2 echo -n "($ret in $log) "
        if [ ! -e "$ret_base.fail" ] || [ "$(cat "$ret_base.fail")" = "x" ]; then
            echo $ret > "$ret_base.fail"
        fi
    fi

    echo "$log"
}


function vneg_ok {
    grep -E -q 'RX.*len=.*Initial' "$1"
    return $?
}


function test_server {
    # run quant client and save a log for post-processing
    local opts="-c false -i $iface -t5 -v5 -g -b 1000 -l /dev/null"
    local base="/tmp/$script.$pid.$1"

    IFS='|' read -ra info <<< "${servers[$1]}"
    # 0=name, 1=flags, 2=port, 3=retry-port, 4=h3-port, 5=URL

    if ! vneg_ok "$base.log.1rtt"; then
        return
    fi

    local cache="/tmp/$script.$pid.$1.cache"
    sem --jobs +0 --id $pid "bin/client $opts -s $cache ${info[1]} \
        https://${info[0]}:${info[2]}${info[5]} > $base.log.0rtt 2>&1"

    # rtry run
    sem --jobs +0 --id $pid "bin/client $opts ${info[1]} -s /dev/null \
        https://${info[0]}:${info[3]}${info[5]} > $base.log.rtry 2>&1"

    # key update run
    sem --jobs +0 --id $pid "bin/client $opts ${info[1]} -s /dev/null -u \
        https://${info[0]}:${info[2]}${info[5]} > $base.log.kyph 2>&1"

    # h3 run
    sem --jobs +0 --id $pid "bin/client $opts ${info[1]} -s /dev/null -3 \
        https://${info[0]}:${info[4]}${info[5]} > $base.log.h3 2>&1"

    # NAT rebinding run
    sem --jobs +0 --id $pid "bin/client $opts ${info[1]} -s /dev/null -n \
        https://${info[0]}:${info[2]}${info[5]} > $base.log.nat 2>&1"

    # quantum-readiness run
    sem --jobs +0 --id $pid "bin/client $opts ${info[1]} -s /dev/null -m \
        https://${info[0]}:${info[2]}${info[5]} > $base.log.qr 2>&1"

    # IP address mobility run
    sem --jobs +0 --id $pid "bin/client $opts ${info[1]} -s /dev/null -n -n \
        https://${info[0]}:${info[2]}${info[5]} > $base.log.adrm 2>&1"

    # zero-len CID run
    sem --jobs +0 --id $pid "bin/client $opts ${info[1]} -s /dev/null -z \
        https://${info[0]}:${info[2]}${info[5]} > $base.log.zcid 2>&1"

    # chacha20 run
    sem --jobs +0 --id $pid "bin/client $opts ${info[1]} -s /dev/null -a \
        https://${info[0]}:${info[2]}${info[5]} > $base.log.chch 2>&1"

    printf "%s " "$s"
}


function bench_server {
    local base="/tmp/$script.$pid.$1"

    IFS='|' read -ra info <<< "${servers[$1]}"
    # 0=name, 1=flags, 2=port, 3=retry-port, 4=h3-port, 5=URL

    if ! vneg_ok "$base.log.1rtt"; then
        return
    fi

    local size=5000000
    local obj=$size
    local log_base="$base.bench"
    local ret_base="$base.ret"
    local h2_out="$log_base.h2.out"
    local h2 ext prefix port host
    host=${info[0]}
    port=443

    # special cases for some servers
    [ "$s" = "winquic" ] && ext=.txt
    [ "$s" = "quic-go" ] && prefix=dynamic/
    [ "$s" = "quicly" ] && port=8443
    [ "$s" = "ngx_quic" ] && obj=5MB.png
    [ "$s" = "lsquic" ] && host=http3check.net && prefix=test/
    [ "$s" = "mvfst" ] && port=443

    h2=$({ time -p curl -k -s -o "$h2_out" --max-time 20 --connect-timeout 3 \
                 "https://$host:$port/$prefix$obj$ext"; } 2>&1)
    h2=$(echo "$h2" | fmt | cut -d' ' -f2)
    h2_size=$(stat -q "$h2_out" | cut -d' ' -f8)
    rm -f "$h2_out"
    if [ -n "$h2_size" ] && [ "$h2_size" -ge $size ]; then
        echo "$h2" > "$ret_base.t_h2"

        local cache="$base.cache"
        local opts="-c false -i $iface -t5 -v3 -l /dev/null"
        local hq_out="$log_base.hq.out"
        local wd hq
        ext=""
        prefix=""
        host=${info[0]}
        port=${info[2]}

        [ "$s" = "quicly" ] && ext=.txt
        [ "$s" = "lsquic" ] && port=4435

        mkdir "$hq_out"
        wd=$(pwd)
        pushd "$hq_out" > /dev/null || exit
        hq=$({ time -p $wd/bin/client $opts ${info[1]} -s "$cache" -w \
                     "https://$host:$port/$prefix$obj$ext" \
                     > "$log_base.log" 2>&1 ; } 2>&1)
        hq=$(echo "$hq" | fmt | cut -d' ' -f2)
        hq_size=$(stat -q "$obj$ext" | cut -d' ' -f8)
        popd > /dev/null || exit
        rm -rf "$hq_out" "$cache"

        if [ -n "$h2_size" ] && [ -n "$hq_size" ] && \
            [ "$hq_size" -ge "$size" ]; then
            echo "$hq" > "$ret_base.t_hq"
            perl -e "print 'T' if $h2 * 1.1 >= $hq" > "$ret_base.perf"
        fi
    fi

    printf "%s " "$s"
}


function analyze {
    local log
    local base="/tmp/$script.$pid.$1"
    local cache="$base.cache"
    rm -f "$cache"

    # analyze 1rtt
    log=$(prep "$base" "1rtt")
    if [ -s "$log.strip" ]; then
        grep -E -q 'RX.*len=' "$log.strip" && echo \* > "$base.ret.live"
        [ ! -s "$base.ret.live" ] && return

        perl -n -e 'BEGIN{$v=-1};
                    /0xbabababa, retrying with/ and $v=1;
                    /no vers in common/ and $v=0;
                    END{exit $v};' "$log.strip"
        local r=$?
        if [ $r -eq 1 ]; then
            echo V > "$base.ret.vneg"
        elif [ $r -eq 0 ]; then
            echo v > "$base.ret.vneg"
        fi

        perl -n -e '/TX.*Short kyph/ and $x=1;
            /RX.*len=.*Short/ && $x && exit 1;' "$log.strip"
        [ $? -eq 1 ] && echo H > "$base.ret.hshk"

        perl -n -e '/read (.*) bytes.*on conn/ and ($1 > 0 ? $x=1 : next);
            /dec_close.*err=0x([^ ]*)/ and ($1 ne "0" ? exit 0 : next);
            /enc_close.*err=0x0/ and $e=1;
            END{exit ($x + $e == 2)};' "$log.strip"
        [ $? -eq 1 ] && echo D > "$base.ret.data"

        perl -n -e 'BEGIN{$x=0};
            /dec_close.*err=0x([^ ]*)/ and ($1 eq "0000" ? $x++ : next);
            /enc_close.*err=0x0/ and $x++;
            END{exit $x};' "$log.strip"
        local r=$?
        if [ $r -ge 2 ]; then
            echo C > "$base.ret.clse"
        elif [ $r -eq 1 ]; then
            echo C > "$base.ret.clse" # c
        fi

        perl -n -e '/dec_new_cid_frame.*NEW_CONNECTION_ID|preferred_address.*cid=1:/ and $n=1;
            /migration to dcid/ && $n && exit 1;' "$log.strip"
        [ $? -eq 1 ] && echo M > "$base.ret.migr"

        # analyze spin
        perl -n -e '/TX.*spin=1/ and $n=1;
            $n && /RX.*spin=1/ && exit 1;' "$log.strip"
        [ $? -eq 1 ] && echo P > "$base.ret.spin"

        # analyze QUIC bit grease
        perl -n -e '/chk_tp.*grease_quic_bit/ && exit 1;' "$log.strip"
        [ $? -eq 1 ] && echo G > "$base.ret.qbgr"

        # analyze ECN
        perl -n -e '$n == 1 and /ECN verification failed/ and $n=2;
            $n == 0 and /dec_ack_frame.*ECN ect0=/ and $n=1;
            END{exit $n};' "$log.strip"
        local r=$?
        if [ $r -eq 2 ]; then
            echo e > "$base.ret.aecn"
        elif [ $r -eq 1 ]; then
            echo E > "$base.ret.aecn"
        fi

        [ ! -e "$base.ret.fail" ] && [ -s "$base.ret.hshk" ] && \
            [ -s "$base.ret.data" ] && [ -s "$base.ret.clse" ] && rm -f "$log"
        rm -f "$log.strip"
    fi

    # analyze rsmt and 0rtt
    log=$(prep "$base" "0rtt")
    if [ -s "$log.strip" ]; then
        perl -n -e '/new 0-RTT clnt conn/ and $x=1;
            /dec_close.*err=0x([^ ]*)/ and ($1 ne "0" ? exit 0 : next);
            /enc_close.*err=0x0/ and $e=1;
            END{exit ($x + $e == 2)};' "$log.strip"
        [ $? -eq 1 ] && echo R > "$base.ret.rsmt"

        perl -n -e '/connected after 0-RTT/ and $x=1;
            /dec_close.*err=0x([^ ]*)/ and ($1 ne "0" ? exit 0 : next);
            /enc_close.*err=0x0/ and $e=1;
            END{exit ($x + $e == 2)};' "$log.strip"
        [ $? -eq 1 ] && echo Z > "$base.ret.zrtt"
        [ ! -e "$base.ret.fail" ] && [ -s "$base.ret.rsmt" ] && \
            [ -s "$base.ret.zrtt" ] && rm -f "$log"
        rm -f "$log.strip"
    fi

    # analyze rtry
    log=$(prep "$base" "rtry")
    if [ -s "$log.strip" ]; then
        perl -n -e '/RX.*len=.*Retry/ and $x=1;
            /dec_close.*err=0x([^ ]*)/ and ($1 ne "0" ? exit 0 : next);
           /enc_close.*err=0x0/ and $e=1;
           END{exit ($x + $e == 2)};' "$log.strip"
        [ $? -eq 1 ] && echo S > "$base.ret.rtry"
        [ ! -e "$base.ret.fail" ] && [ -s "$base.ret.rtry" ] && rm -f "$log"
        rm -f "$log.strip"
    fi

    # analyze key update
    log=$(prep "$base" "kyph")
    if [ -s "$log.strip" ]; then
        perl -n -e '/TX.*Short kyph=1/ and $x=1;
            /dec_close.*err=0x([^ ]*)/ and ($1 ne "0" ? exit 0 : next);
           $x && /RX.*Short kyph=1/ && exit 1;' "$log.strip"
        [ $? -eq 1 ] && echo U > "$base.ret.kyph"
        [ ! -e "$base.ret.fail" ] && [ -s "$base.ret.kyph" ] && rm -f "$log"
        rm -f "$log.strip"
    fi

    # analyze h3
    log=$(prep "$base" "h3")
    if [ -s "$log.strip" ]; then
        perl -n -e '/read (.*) bytes.*on conn/ and ($1 > 0 ? $x=1 : next);
            /no h3 payload/ and $x=0;
            /dec_close.*err=0x([^ ]*)/ and ($1 ne "0" ? exit 0 : next);
            /enc_close.*err=0x0/ and $e=1;
            END{exit ($x + $e == 2)};' "$log.strip"
        [ $? -eq 1 ] && echo 3 > "$base.ret.http"
        [ ! -e "$base.ret.fail" ] && [ -s "$base.ret.http" ] && rm -f "$log"
        rm -f "$log.strip"
    fi

    # analyze NAT rebind
    log=$(prep "$base" "nat")
    if [ -s "$log.strip" ]; then
        perl -n -e '/NAT rebinding/ and $x=1;
            /dec_path.*PATH_CHALLENGE/ and $x==1 and $x=2;
            /enc_path.*PATH_RESPONSE/ and $x==2 and $x=3;
            /read (.*) bytes.*on conn/ and $x==3 and ($1 > 0 ? $x++ : next);
            /dec_close.*err=0x([^ ]*)/ and ($1 ne "0" ? exit 0 : $x++);
            /enc_close.*err=0x0/ and $x++;
            END{exit ($x >= 5)};' "$log.strip"
        # the >=5 should really be == 6, but haskell doesn't make me enc a CC frame
        [ $? -eq 1 ] && echo B > "$base.ret.bind"
        [ ! -e "$base.ret.fail" ] && [ -s "$base.ret.bind" ] && rm -f "$log"
        rm -f "$log.strip"
    fi

    # analyze quantum-readiness
    log=$(prep "$base" "qr")
    if [ -s "$log.strip" ]; then
        perl -n -e '/read (.*) bytes.*on conn/ and ($1 > 0 ? $x=1 : next);
            /no h3 payload/ and $x=0;
            /dec_close.*err=0x([^ ]*)/ and ($1 ne "0" ? exit 0 : next);
            /enc_close.*err=0x0/ and $e=1;
            END{exit ($x + $e == 2)};' "$log.strip"
        [ $? -eq 1 ] && echo Q > "$base.ret.qrdy"
        [ ! -e "$base.ret.fail" ] && [ -s "$base.ret.qrdy" ] && rm -f "$log"
        rm -f "$log.strip"
    fi

    # analyze IP address mobility
    log=$(prep "$base" "adrm")
    if [ -s "$log.strip" ]; then
        perl -n -e '/conn migration for/ and $x=1;
            /read (.*) bytes.*on conn/ and ($1 > 0 ? $x++ : next);
            /no h3 payload/ and $x=0;
            /dec_close.*err=0x([^ ]*)/ and ($1 ne "0" ? exit 0 : next);
            /enc_close.*err=0x0/ and $e=1;
            END{exit ($x + $e == 3)};' "$log.strip"
        [ $? -eq 1 ] && echo A > "$base.ret.adrm"
        [ ! -e "$base.ret.fail" ] && [ -s "$base.ret.adrm" ] && rm -f "$log"
        rm -f "$log.strip"
    fi

    # analyze zero-len source CIDs
    log=$(prep "$base" "zcid")
    if [ -s "$log.strip" ]; then
        perl -n -e '/read (.*) bytes.*on conn/ and ($1 > 0 ? $x=1 : next);
            /no h3 payload/ and $x=0;
            /dec_close.*err=0x([^ ]*)/ and ($1 ne "0" ? exit 0 : next);
            /enc_close.*err=0x0/ and $e=1;
            END{exit ($x + $e == 2)};' "$log.strip"
        [ $? -eq 1 ] && echo O > "$base.ret.zcid"
        [ ! -e "$base.ret.fail" ] && [ -s "$base.ret.zcid" ] && rm -f "$log"
        rm -f "$log.strip"
    fi

    # analyze chacha20
    log=$(prep "$base" "chch")
    if [ -s "$log.strip" ]; then
        perl -n -e '/read (.*) bytes.*on conn/ and ($1 > 0 ? $x=1 : next);
            /dec_close.*err=0x([^ ]*)/ and ($1 ne "0" ? exit 0 : next);
            /enc_close.*err=0x0/ and $e=1;
            END{exit ($x + $e == 2)};' "$log.strip"
        [ $? -eq 1 ] && echo 2 > "$base.ret.chch"
        [ ! -e "$base.ret.fail" ] && [ -s "$base.ret.chch" ] && rm -f "$log"
        rm -f "$log.strip"
    fi

    printf "%s " "$s"
}


printf "Initial: "
for s in $(shuf -e "${!servers[@]}"); do
    test_server_initial "$s"
done
sem --id $pid --wait

printf "\\nFeature: "
for s in $(shuf -e "${!servers[@]}"); do
    test_server "$s"
done
sem --id $pid --wait

if [ -n "$benchmarking" ]; then
    printf "\\nBenchmark: "
    for s in $(shuf -e "${!servers[@]}"); do
        bench_server "$s"
    done
fi

printf "\\nAnalyze: "
for s in "${!servers[@]}"; do
    analyze "$s" &
done
wait

printf "\\n\\n"

tmp=$(mktemp)
printf "%8s\\t" "" >> "$tmp"
for r in "${results[@]}"; do
    printf "%s\\t" "$r" >> "$tmp"
done
printf "\\n" >> "$tmp"

mapfile -d '' sorted < <(printf '%s\0' "${!servers[@]}" | sort -z)
ret_base="/tmp/$script.$pid"
for s in "${sorted[@]}"; do
    if [ ! -s "$ret_base.$s.ret.live" ] ||
       [ "$(cat "$ret_base.$s.ret.vneg")" = "v" ]; then
        continue
    fi
    printf "%-8s\\t" "$s" >> "$tmp"
    for r in "${results[@]}"; do
        ret=$ret_base.$s.ret.$r
        if [ -s "$ret" ]; then
            v=$(cat "$ret")
        else
            v=""
        fi
        rm -f "$ret" "$ret.fail"
        printf "%s\\t" "$v" >> "$tmp"
    done
    printf "\\n" >> "$tmp"
done

tmp2=$(mktemp)
expand -t 5 "$tmp" > "$tmp2"
mv "$tmp2" "$tmp"
if ! diff -wq "$(dirname $0)/$script.result" "$tmp" > /dev/null; then
    cat "$tmp"
fi
wdiff -n "$(dirname $0)/$script.result" "$tmp" | $colordiff
rm -f "$tmp"
