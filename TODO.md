# TODOs

!!! note "Development Roadmap"
    This document tracks planned improvements and known issues. Contributions are welcome for any of these items.


* detached mode for experiences

* Analysis plugins (perf report, qvis etc)

* add docker consumption for "network_sent_mb_total": 11.09375,
      "network_recv_mb_total": 14.197265625,

* Command behavioral design pattern
  * https://refactoring.guru/design-patterns/command/python/example#example-0

* https://refactoring.guru/design-patterns/state

## PANTHER Ivy

!!! warning "Ivy Integration Status"
    The Ivy integration is currently under active development. Some features may be unstable.

* Use Jinja template for ivy_to_cpp

* Improve Lexer + Parser code quality/readibility

* Improve documentations ?

* Result Handler

## PANTHER

* Create single container for IUT -> less disk used
  * Still ok ?
  * Create new docker-compose/swarm per experience ?
    * with docker network ? we need to create route
  * What about when using shddow ? We send binary to shadow container ?

* Improving config files
  * removing duplicate
  * Add classes to save the states

* documentation + comments

* Refactor the python code itself

* Better outputs managements

* Redo the readmes

* Enable better cli and webapp usage

* Add some tests

## PANTHER webapp

* refactor /creator with accordingly -> to allow and adapt multiple protocol
  * <https://github.com/Kanaries/pygwalker>

* refactor /result with accordingly -> to allow and adapt multiple protocol

* Allow to add new implementation configuration

* <https://peak.telecommunity.com/DevCenter/PkgResources#entrypoint-objects>

## PVF architecture

* Make docker internal system match to current system ?

* build.py to replace makefile

* update docker compose file
