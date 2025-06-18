# TODOs

!!! note "Development Roadmap"
    This document tracks planned improvements and known issues. Contributions are welcome for any of these items.

* detached mode for experiences

* Analysis plugins (perf report, qvis etc)

* add docker consumption for "network_sent_mb_total": 11.09375,
      "network_recv_mb_total": 14.197265625,

* Command behavioral design pattern
  * <https://refactoring.guru/design-patterns/command/python/example#example-0>

* <https://refactoring.guru/design-patterns/state>

* Create a template module with helper functions linked to command generation module

* Enable execution environment at service level

* docker push cyberelniak/panther_net:tagname

## Service Plugin Refactoring (HIGH PRIORITY)

!!! danger "Critical Code Duplication Issue"
    Service plugins have 155-283% code duplication. This is a critical technical debt that needs immediate attention.

* **Phase 1**: Analysis and test coverage
  * Map all duplicated code blocks
  * Establish baseline metrics
  * Create comprehensive test suite
  
* **Phase 2**: Create base infrastructure
  * Implement BaseQUICServiceManager class
  * Create BaseServiceConfig for shared schemas
  * Build ServiceCommandBuilder utility
  
* **Phase 3**: Pilot refactoring with picoquic
  * Target: Reduce from 205% to <30% duplication
  * Validate approach before mass migration
  
* **Phase 4**: Mass migration
  * Refactor lsquic & mvfst (283% duplication)
  * Refactor quiche & quinn (226% duplication)
  * Refactor remaining implementations
  
* **Phase 5**: Optimization and documentation
  * Further abstractions for Docker patterns
  * Update development guides
  * Performance optimization

**See**: `SERVICE_DUPLICATION_REFACTORING_PLAN.md` and `SERVICE_REFACTORING_EXAMPLE.md` for detailed implementation plan.

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
