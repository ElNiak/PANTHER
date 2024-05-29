# ivy

IVy is a research tool intended to allow interactive development of
protocols and their proofs of correctness and to provide a platform
for developing and experimenting with automated proof techniques. In
particular, IVy provides interactive visualization of automated
proofs, and supports a use model in which the human protocol designer
and the automated tool interact to expose errors and prove
correctness.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.10819552.svg)](https://doi.org/10.5281/zenodo.10819552)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white) ![C++](https://img.shields.io/badge/c++-%2300599C.svg?style=for-the-badge&logo=c%2B%2B&logoColor=white) ![Debian](https://img.shields.io/badge/Debian-D70A53?style=for-the-badge&logo=debian&logoColor=white)

# Installation
## Linux
On Debian-based Linux ditributions such as Ubuntu, download and install the file `ms-ivy_X.X_YYYY.deb` where `X.X` is the IVy version and `YYYY` is the machine architecture. Use your system’s package manager to install this package, or the following commands:
```
$ sudo dpkg -i ms-ivy_X.X_YYYY.deb
$ sudo apt-get install -f
```
The first command will report missing dependencies, which will be installed by the second command.

## Windows
The Windows binary distribution is in the form of a zip archive. Download the file `ivy.X.Y-.Windows-z86.zip`, where `X.X` is the IVy version (this will work on both 32-bit and 64 bit Intel Windows). Use Windows Explorer to extract this archive in the directory `C:\`. This should give you a directory `C:\ivy`. To use IVy in a command window, first execute this command:
```
> C:\ivy\scripts\activate
```

## Further Reading

For further information on IVy, see [the IVy web site](http://kenmcmil.github.io/ivy/).
