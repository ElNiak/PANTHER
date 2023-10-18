configure_file(quant.service.in quant.service)
configure_file(quant-server.sh.in quant-server.sh @ONLY)
configure_file(gcc-ubsan-suppressions.txt gcc-ubsan-suppressions.txt COPYONLY)
