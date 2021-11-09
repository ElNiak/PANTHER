LIBSDIRS=-L/ngtcp2/third-party/.libs/ -L/ngtcp2/lib/.libs/ -L/openssl/ -L/openssl/ -L/nghttp3/lib/.libs/
LIBS=-l:libngtcp2.a -l:libhttp-parser.a -l:libssl.a -l:libcrypto.a -l:libnghttp3.a -lev -ldl -lpthread
EXTERN_OBJECTS=/ngtcp2/crypto/.libs/shared.o /ngtcp2/crypto/openssl/openssl.o
INCLUDES=-include arpa/inet.h -I/ngtcp2/third-party -I/ngtcp2/lib/includes -I/ngtcp2/crypto/includes
CFLAGS=-std=c++17
CC=g++
DEPS=debug.cc keylog.cc http.cc util.cc shared.cc

%.o: %.cc
	$(CC) $(CFLAGS) $(INCLUDES) $(LIBSDIRS) -c $? $(LIBS)

all: generic-client generic-server

generic-client: generic-client.cc $(DEPS)
	$(CC) -o $@ $(CFLAGS) $(INCLUDES) $(LIBSDIRS) $? $(LIBS) $(EXTERN_OBJECTS)

generic-server: generic-server.cc $(DEPS)
	$(CC) -o $@ $(CFLAGS) $(INCLUDES) $(LIBSDIRS) $? $(LIBS) $(EXTERN_OBJECTS)

