
# Quant for [RIOT-OS](https://www.riot-os.org/)

This directory has the build scaffolding to compile a simple, minimal Quant
client for [[RIOT-OS](https://www.riot-os.org/), using the [docker build
method](https://github.com/RIOT-OS/RIOT/wiki/Use-Docker-to-build-RIOT).

The source files are in `modules/quant/`, and the resulting binary will appear
in the `bin/` directory. Most of the minimal client functionality is shared with
the [Particle.io](https://docs.particle.io/) client, and resides in
`../test/minimal-transaction.c`. You will likely want to modify
`../test/minimal-transaction.c`, since by default it performs a `GET /5000` with
`quant.eggert.org` and nothing else.

## Building

To compile code, run `make BUILD_IN_DOCKER=1`. Note that I have only tested
Quant on the [ESP32](https://doc.riot-os.org/group__cpu__esp32.html) platform
and it will likely require modifications for other boards.

Quant should build with [RIOT-OS](https://github.com/RIOT-OS/RIOT) version
2020.01 or higher.

## Flashing

To compile and flash code, run `make BUILD_IN_DOCKER=1 flash`. Code is compiled
and then flashed to your device over USB.

To flash a project over USB without rebuilding, run `make BUILD_IN_DOCKER=1
flash-only`.

## Debug output

To connect to the serial console after flashing, run `make BUILD_IN_DOCKER=1
term`.

## Development and contributing

I'm happy to merge contributions that fix
[bugs](https://github.com/NTAP/quant/issues?q=is%3Aopen+is%3Aissue+label%3Abug)
or add
[features](https://github.com/NTAP/quant/issues?q=is%3Aopen+is%3Aissue+label%3Aenhancement).
Please send pull requests.

(Contributions to the underlying [warpcore](https://github.com/NTAP/warpcore)
stack are also very welcome.)
