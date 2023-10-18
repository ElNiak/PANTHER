#! /usr/bin/env bash

if [ "$1" != particle ] && [ "$1" != riot ]; then
    echo particle or riot
    exit 1
fi

set -e

opts=('' NO_64BIT NO_SERVER MINIMAL_CIPHERS NO_MIGRATION NO_ERR_REASONS
      NO_ECN NO_SRT_MATCHING NO_OOO_0RTT NO_OOO_DATA NO_QINFO)

declare -A always=([particle]="-DNDEBUG -DRELEASE_BUILD"
                   [riot]="-DNDEBUG")

declare -A nm=([particle]=arm-none-eabi-nm
               [riot]=xtensa-esp32-elf-nm)

declare -A pref=([particle]=bin/particle-argon
                 [riot]=bin/esp32-wroom-32/quant-client)

i=0
for flag in "${opts[@]}"; do
        b=$((!i))
        ((i++)) || true
        data="$i-${flag:-NONE}"
        flags="${flag:+-D$flag} $flags"
        if [ ! -s "$data".elf ]; then
                echo -n "${flag:-NONE}"
                all="${always[$1]} -DHAVE_64BIT=$b $flags"
                case $1 in
                    particle)
                        out=$(env MODULAR=n COMPILE_LTO=n BUILD_FLAGS="$all" \
                                po argon build 2>/dev/null | \
                                    grep particle-argon.elf)
                        ;;
                    riot)
                        out=$(gmake LTO=0 BUILD_IN_DOCKER=1 DEVELHELP=0 \
                             BUILD_FLAGS=1 \
                             DOCKER_ENVIRONMENT_CMDLINE="-e BUILD_FLAGS=\"$all\"")
                        ;;
                esac

                echo "$out" | tail -n 1
                ${nm[$1]} -C -l -S --size-sort "${pref[$1]}".elf | \
                        gsed -e 's| |\t|' -e 's| |\t|' -e 's| |\t|' | \
                                cut -f2- > "$data".elf
                fpvgcc --sobj all "${pref[$1]}".map > "$data".map
        fi
done
