[![Built with
po-util](https://rawgit.com/nrobinson2000/po-util/master/images/built-with-po-util.svg)](https://po-util.com)

# Quant for [Particle.io](https://docs.particle.io/) boards

This directory has the build scaffolding to compile a simple, minimal Quant
client for [Particle.io](https://docs.particle.io/) boards, using
[po](https://po-util.com) as the build system. So you need to install `po`
first.

The source files are in `firmware/`, and the resulting binary will appear in the
`bin/` directory. Most of the minimal client functionality is shared with the
[RIOT-OS](https://www.riot-os.org/) client, and resides in
`../test/minimal-transaction.c`. You will likely want to modify
`../test/minimal-transaction.c`, since by default it performs a `GET /5000` with
`quant.eggert.org` and nothing else.

## Building

To compile code, run `po DEVICE_TYPE build`, substituting `DEVICE_TYPE` with the
desired device type, e.g., `photon`, `P1`, `electron`, `core`, `pi`, or `duo`.
Note that I have only tested Quant on the [Particle
Argon](https://docs.particle.io/argon/) (`argon`) and it will likely require
modifications for other boards.

To clean the project, run `po DEVICE_TYPE clean`.

Quant should build with [DeviceOS](https://github.com/particle-iot/device-os)
version 1.5.0 or higher. Note that `po` by default uses the `develop` branch of
[DeviceOS](https://github.com/particle-iot/device-os), which may or may not
work. Use `po config` to switch branches.

## Flashing

To compile and flash code, run `po DEVICE_TYPE flash`. Code is compiled and then
flashed to your device over USB.

To flash a project over USB without rebuilding, run `po DEVICE_TYPE dfu`.

## Debug output

To connect to the serial console after flashing, run `particle serial monitor`.

## Development and contributing

I'm happy to merge contributions that fix
[bugs](https://github.com/NTAP/quant/issues?q=is%3Aopen+is%3Aissue+label%3Abug)
or add
[features](https://github.com/NTAP/quant/issues?q=is%3Aopen+is%3Aissue+label%3Aenhancement).
Please send pull requests.

(Contributions to the underlying [warpcore](https://github.com/NTAP/warpcore)
stack are also very welcome.)
