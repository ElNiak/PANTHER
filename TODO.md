# TODOs

* Rename gits ?

* Add loading bar

* detached mode

* Analysis plugins (perf report, qvis etc)

## PANTHER Ivy

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
