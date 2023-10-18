include(ExternalProject)

find_package(OpenSSL)

set(GOPATH ${CMAKE_CURRENT_BINARY_DIR}/go)

# Use quic-go for testing against, rather than proto-quic monster
set(QUICGO github.com/lucas-clemente/quic-go)
externalproject_add(quic-go
  DOWNLOAD_COMMAND env GOPATH=${GOPATH} go get ${QUICGO}
  # UPDATE_COMMAND env GOPATH=${GOPATH} go get -u ${QUICGO}
  CONFIGURE_COMMAND cd ${GOPATH}/src/${QUICGO} && git checkout http09
  BUILD_COMMAND
    cd ${GOPATH}/src/${QUICGO} && env GOPATH=${GOPATH} go get -t -u ./...
  INSTALL_COMMAND ""
  EXCLUDE_FROM_ALL 1
)


# Use quicly for testing against
externalproject_add(quicly
  # UPDATE_COMMAND ""
  GIT_REPOSITORY https://github.com/h2o/quicly.git
  GIT_SHALLOW 1
  CMAKE_ARGS
    -DOPENSSL_ROOT_DIR=${OPENSSL_ROOT_DIR}
    -DCMAKE_C_COMPILER=${CMAKE_C_COMPILER}
    -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
  INSTALL_COMMAND ""
  EXCLUDE_FROM_ALL 1
)


# Use ngtcp2 for testing against
externalproject_add(openssl
  UPDATE_COMMAND ""
  # GIT_REPOSITORY https://github.com/openssl/openssl.git
  GIT_REPOSITORY https://github.com/tatsuhiro-t/openssl
  GIT_TAG quic-draft-22
  GIT_SHALLOW 1
  CONFIGURE_COMMAND ./config --prefix=${CMAKE_CURRENT_BINARY_DIR} enable-tls1_3
  BUILD_IN_SOURCE 1
  BUILD_COMMAND make -j8
  INSTALL_COMMAND make install_sw
  EXCLUDE_FROM_ALL 1
)

externalproject_add(nghttp3
  UPDATE_COMMAND ""
  GIT_REPOSITORY https://github.com/ngtcp2/nghttp3
  GIT_SHALLOW 1
  PATCH_COMMAND autoreconf -i
  CONFIGURE_COMMAND ./configure --prefix=${CMAKE_CURRENT_BINARY_DIR} --enable-lib-only
  BUILD_IN_SOURCE 1
  BUILD_COMMAND make -j8
  INSTALL_COMMAND make install
  EXCLUDE_FROM_ALL 1
)

externalproject_add(ngtcp2
  DEPENDS openssl nghttp3
  UPDATE_COMMAND ""
  GIT_REPOSITORY https://github.com/ngtcp2/ngtcp2.git
  GIT_SHALLOW 1
  GIT_TAG draft-22
  CMAKE_ARGS
    -DCMAKE_C_COMPILER=${CMAKE_C_COMPILER}
    -DOPENSSL_ROOT_DIR=${CMAKE_CURRENT_BINARY_DIR}
    -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
    -DCMAKE_PREFIX_PATH=${CMAKE_CURRENT_BINARY_DIR}
    -DENABLE_DEBUG=ON -DENABLE_ASAN=ON
  BUILD_IN_SOURCE 1
  INSTALL_COMMAND ""
  EXCLUDE_FROM_ALL 1
)


# Use picoquic for testing against
externalproject_add(picoquic
  UPDATE_COMMAND ""
  GIT_REPOSITORY https://github.com/private-octopus/picoquic.git
  GIT_SHALLOW 1
  # GIT_TAG draft-21
  BUILD_IN_SOURCE 1
  CMAKE_ARGS
    -DCMAKE_C_COMPILER=${CMAKE_C_COMPILER}
    -DOPENSSL_ROOT_DIR=${OPENSSL_ROOT_DIR}
    -DPTLS_INCLUDE_DIR=${PROJECT_SOURCE_DIR}/lib/deps/picotls/include
    -DPTLS_CORE_LIBRARY=${CMAKE_BINARY_DIR}/lib/deps/picotls/libpicotls-core.a
    -DPTLS_MINICRYPTO_LIBRARY=${CMAKE_BINARY_DIR}/lib/deps/picotls/libpicotls-minicrypto.a
    -DPTLS_OPENSSL_LIBRARY=${CMAKE_BINARY_DIR}/lib/deps/picotls/libpicotls-openssl.a
    -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
    -DCMAKE_C_FLAGS=-Wno-error
  INSTALL_COMMAND ""
  EXCLUDE_FROM_ALL 1
)


# Use ats for testing against
externalproject_add(ats
  DEPENDS openssl
  UPDATE_COMMAND ""
  GIT_REPOSITORY https://github.com/apache/trafficserver.git
  GIT_SHALLOW 1
  GIT_TAG quic-latest
  PATCH_COMMAND autoreconf -i
  CONFIGURE_COMMAND
    ./configure PKG_CONFIG_PATH=${CMAKE_CURRENT_BINARY_DIR}/lib/pkgconfig
      --enable-debug --prefix=${CMAKE_CURRENT_BINARY_DIR}
  BUILD_IN_SOURCE 1
  BUILD_COMMAND make -j8
  INSTALL_COMMAND
    make install &&
    echo "CONFIG proxy.config.udp.threads INT 1" >> ${CMAKE_CURRENT_BINARY_DIR}/etc/trafficserver/records.config &&
    echo "CONFIG proxy.config.quic.no_activity_timeout_in INT 10" >> ${CMAKE_CURRENT_BINARY_DIR}/etc/trafficserver/records.config &&
    sed -i "" -E
      -e "s/.*proxy.config.diags.debug.enabled.*/CONFIG proxy.config.diags.debug.enabled INT 1/g"
      -e "s/.*proxy.config.diags.debug.tags.*/CONFIG proxy.config.diags.debug.tags STRING quic|udp/g"
      -e "s/.*proxy.config.http.server_ports.*/CONFIG proxy.config.http.server_ports STRING 4433:quic/g"
      -e "s/.*proxy.config.ssl.server.cipher_suite.*/CONFIG proxy.config.ssl.server.cipher_suite STRING TLS13-AES-128-GCM-SHA256:TLS13-AES-128-GCM-SHA256:TLS13-CHACHA20-POLY1305-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:DHE-DSS-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA256:DHE-RSA-AES128-SHA256:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA:DHE-DSS-AES256-SHA:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA:AES256-GCM-SHA384:AES128-GCM-SHA256:AES256-SHA256:AES128-SHA256:AES256-SHA:AES128-SHA:DES-CBC3-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA/g"
      ${CMAKE_CURRENT_BINARY_DIR}/etc/trafficserver/records.config
  EXCLUDE_FROM_ALL 1
)


# Use quicker for testing against
externalproject_add(node
  UPDATE_COMMAND ""
  GIT_REPOSITORY https://github.com/kevin-kp/node
  GIT_SHALLOW 1
  GIT_TAG add_quicker_support-tls-d28
  BUILD_IN_SOURCE 1
  PATCH_COMMAND sed -i "" -e "s/.*g.*-7.*//g" configure
  CONFIGURE_COMMAND
    ./configure --openssl-no-asm --prefix=${CMAKE_CURRENT_BINARY_DIR}
  BUILD_COMMAND make -j8
  EXCLUDE_FROM_ALL 1
)

externalproject_add(quicker
  DEPENDS node
  UPDATE_COMMAND ""
  GIT_REPOSITORY https://github.com/rmarx/quicker
  GIT_SHALLOW 1
  PATCH_COMMAND
    npm install &&
    npm install typescript &&
    node_modules/typescript/bin/tsc -p .
  CONFIGURE_COMMAND ""
  BUILD_IN_SOURCE 1
  BUILD_COMMAND ""
  INSTALL_COMMAND ""
  EXCLUDE_FROM_ALL 1
)


# Use quinn for testing against
externalproject_add(quinn
  UPDATE_COMMAND ""
  GIT_REPOSITORY https://github.com/djc/quinn.git
  GIT_SHALLOW 1
  # GIT_TAG add_quicker_support-tls-d28
  CONFIGURE_COMMAND ""
  BUILD_COMMAND ""
  INSTALL_COMMAND ""
  BUILD_IN_SOURCE 1
  EXCLUDE_FROM_ALL 1
)


# Use msquic for testing against
externalproject_add(lttng-ust
  UPDATE_COMMAND ""
  GIT_REPOSITORY git://git.lttng.org/lttng-ust.git
  GIT_SHALLOW 1
  PATCH_COMMAND ./bootstrap
  CONFIGURE_COMMAND ./configure CC=gcc-9 CXX=g++-9
  BUILD_COMMAND make
  INSTALL_COMMAND ""
  BUILD_IN_SOURCE 1
  EXCLUDE_FROM_ALL 1
)

externalproject_add(msquic
  # DEPENDS lttng-ust
  UPDATE_COMMAND ""
  GIT_REPOSITORY git@github.com:microsoft/msquic.git
  GIT_SHALLOW 1
  # GIT_TAG add_quicker_support-tls-d28
  CONFIGURE_COMMAND
    cmake -DCMAKE_C_COMPILER=gcc-9
      -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
      -DQUIC_ENABLE_LOGGING=OFF
      .
  BUILD_COMMAND make VERBOSE=1
  INSTALL_COMMAND ""
  BUILD_IN_SOURCE 1
  EXCLUDE_FROM_ALL 1
)


# Use quic-scanner for testing against
externalproject_add(quic-scanner
  UPDATE_COMMAND ""
  GIT_REPOSITORY https://github.com/Lekensteyn/quic-scanner.git
  GIT_SHALLOW 1
  CONFIGURE_COMMAND ""
  BUILD_COMMAND ""
  INSTALL_COMMAND ""
  EXCLUDE_FROM_ALL 1
)

set(TRACKER github.com/QUIC-Tracker/quic-tracker)
externalproject_add(quic-tracker
  DOWNLOAD_COMMAND
    env GOPATH=${GOPATH}
      CGO_CFLAGS=-I${OPENSSL_ROOT_DIR}/include
      CGO_LDFLAGS=-L${OPENSSL_ROOT_DIR}/lib go get ${TRACKER} || true
  UPDATE_COMMAND ""
  CONFIGURE_COMMAND
    sed -i "" -e "s|go build|GOPATH=${GOPATH} CGO_CFLAGS=-I${OPENSSL_ROOT_DIR}/include CGO_LDFLAGS=-L${OPENSSL_ROOT_DIR}/lib go build|g $<SEMICOLON> s|make check|make|g" ${GOPATH}/src/${TRACKER}/../../mpiraux/pigotls/Makefile
  BUILD_COMMAND
    cd ${GOPATH}/src/${TRACKER}/../../mpiraux/pigotls &&
    env GOPATH=${GOPATH} OPENSSL_ROOT_DIR=${OPENSSL_ROOT_DIR} make &&
    cd ${GOPATH}/src/${TRACKER}/../../mpiraux/ls-qpack-go &&
    env GOPATH=${GOPATH} OPENSSL_ROOT_DIR=${OPENSSL_ROOT_DIR} make
  INSTALL_COMMAND ""
  EXCLUDE_FROM_ALL 1
)


# grep '^[^#]*_add' ../external/CMakeLists.txt | cut -f2 -d\( | sort | fmt -w 60
add_custom_target(ext-all DEPENDS
  ats minq mozquic ngtcp2 node nspr nss openssl picoquic
  quic-go quic-tracker quicker quicly
)
