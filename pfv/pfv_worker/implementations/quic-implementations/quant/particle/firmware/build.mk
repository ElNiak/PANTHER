INCLUDE_DIRS+=$(SOURCE_PATH) $(SOURCE_PATH)/test
CPPSRC+=main.cpp

DEPS=lib/deps
PICOTLS=$(DEPS)/picotls
TIMEOUT=$(DEPS)/timeout
WARPCORE=$(DEPS)/warpcore/lib

INCLUDE_DIRS+=\
	$(SOURCE_PATH)/$(PICOTLS)/deps/cifra/src \
	$(SOURCE_PATH)/$(PICOTLS)/deps/cifra/src/ext \
	$(SOURCE_PATH)/$(PICOTLS)/deps/micro-ecc \
	$(SOURCE_PATH)/$(PICOTLS)/include \
	$(SOURCE_PATH)/$(TIMEOUT) \
	$(SOURCE_PATH)/$(WARPCORE)/include \
	$(SOURCE_PATH)/lib/include

PICOTLS_SRC+=\
	$(PICOTLS)/deps/cifra/src/aes.c \
	$(PICOTLS)/deps/cifra/src/blockwise.c \
	$(PICOTLS)/deps/cifra/src/chacha20.c \
	$(PICOTLS)/deps/cifra/src/curve25519.c \
	$(PICOTLS)/deps/cifra/src/drbg.c \
	$(PICOTLS)/deps/cifra/src/gcm.c \
	$(PICOTLS)/deps/cifra/src/gf128.c \
	$(PICOTLS)/deps/cifra/src/modes.c \
	$(PICOTLS)/deps/cifra/src/poly1305.c \
	$(PICOTLS)/deps/cifra/src/sha256.c \
	$(PICOTLS)/deps/cifra/src/sha512.c \
	$(PICOTLS)/deps/micro-ecc/uECC.c \
	$(PICOTLS)/lib/cifra.c \
	$(PICOTLS)/lib/cifra/x25519.c \
	$(PICOTLS)/lib/cifra/aes128.c \
	$(PICOTLS)/lib/cifra/aes256.c \
	$(PICOTLS)/lib/cifra/chacha20.c \
	$(PICOTLS)/lib/picotls.c \
	$(PICOTLS)/lib/uecc.c

WARP_SRC+=\
	$(WARPCORE)/src/backend_sock.c \
	$(WARPCORE)/src/ifaddr.c \
	$(WARPCORE)/src/plat.c \
	$(WARPCORE)/src/util.c \
	$(WARPCORE)/src/warpcore.c \
	warpcore/config.c

QUANT_SRC+=\
	lib/src/cid.c \
	lib/src/conn.c \
	lib/src/diet.c \
	lib/src/frame.c \
	lib/src/loop.c \
	lib/src/marshall.c \
	lib/src/pkt.c \
	lib/src/pn.c \
	lib/src/quic.c \
	lib/src/recovery.c \
	lib/src/stream.c \
	lib/src/tls.c \
	test/minimal_transaction.c \
	quant/config.c


CSRC+=$(WARP_SRC) $(PICOTLS_SRC) $(QUANT_SRC)

ifdef BUILD_FLAGS
EXTRA_CFLAGS+=${BUILD_FLAGS}
else
EXTRA_CFLAGS+=-DMINIMAL_CIPHERS -DNO_QINFO -DNO_SERVER \
	-DNO_ERR_REASONS -DNO_OOO_0RTT \
	-DNO_MIGRATION -DNO_SRT_MATCHING
endif

# -DDSTACK -finstrument-functions -DNDEBUG -DRELEASE_BUILD
# -finstrument-functions-exclude-file-list=deps/micro-ecc,deps/cifra
EXTRA_CFLAGS+=-fstack-usage -foptimize-strlen -ffast-math \
	-Wno-error -Wno-parentheses -Wno-undef -Wno-unknown-pragmas \
	-Wno-unused-value -Wno-address -DNDEBUG -DRELEASE_BUILD \
	-DDLEVEL=DBG -DNO_TLS_LOG -DNO_QLOG -DNO_ECN \
	-D'ntoh16(x)=__builtin_bswap16(*(uint16_t*)(x))' \
	-D'ntoh32(x)=__builtin_bswap32(*(uint32_t*)(x))' \
	-D'ntoh64(x)=__builtin_bswap64(*(uint64_t*)(x))'

# TODO: figure out how to do this using make rules
$(shell	cd $(SOURCE_PATH) && ln -sf ../../lib)
$(shell	cd $(SOURCE_PATH) && ln -sf ../../test)

WARPCORE_VERSION:=$(shell grep 'warpcore.*VERSION' $(SOURCE_PATH)/../../$(WARPCORE)/../CMakeLists.txt | cut -d' ' -f3)
$(shell	mkdir -p $(SOURCE_PATH)/warpcore)
$(shell [ -s $(SOURCE_PATH)/warpcore/config.c ] || \
	sed -E -e 's|@PROJECT_NAME@|warpcore|g; s|@PROJECT_NAME_UC@|WARPCORE|g; s|@PROJECT_VERSION@|$(WARPCORE_VERSION)|g;' \
		$(SOURCE_PATH)/../../$(WARPCORE)/src/config.c.in > $(SOURCE_PATH)/warpcore/config.c)
$(shell [ -s $(SOURCE_PATH)/warpcore/config.h ] || \
	sed -E -e 's|@PROJECT_NAME@|warpcore|g; s|@PROJECT_NAME_UC@|WARPCORE|g; s|@PROJECT_VERSION@|$(WARPCORE_VERSION)|g; s|(#cmakedefine)|// \1|g; s|(@.*@)|0|g;' \
		$(SOURCE_PATH)/../../$(WARPCORE)/include/warpcore/config.h.in > $(SOURCE_PATH)/warpcore/config.h)

QUANT_VERSION:=$(shell grep 'quant.*VERSION' $(SOURCE_PATH)/../../CMakeLists.txt | cut -d' ' -f3)
DRAFT_VERSION:=$(shell grep 'quant.*VERSION' $(SOURCE_PATH)/../../CMakeLists.txt | cut -d' ' -f3 | cut -d. -f3)
$(shell	mkdir -p $(SOURCE_PATH)/quant)
$(shell [ -s $(SOURCE_PATH)/../lib/src/config.c ] || \
	sed -E -e 's|@PROJECT_NAME@|quant|g; s|@PROJECT_NAME_UC@|QUANT|g; s|@PROJECT_VERSION@|$(QUANT_VERSION)|g; s|@PROJECT_VERSION_PATCH@|$(DRAFT_VERSION)|g; s|(@.*@)|0|g;' \
		$(SOURCE_PATH)/../../lib/src/config.c.in > $(SOURCE_PATH)/quant/config.c)
$(shell [ -s $(SOURCE_PATH)/../lib/include/quant/config.h ] || \
	sed -E -e 's|@PROJECT_NAME@|quant|g; s|@PROJECT_NAME_UC@|QUANT|g; s|@PROJECT_VERSION@|$(QUANT_VERSION)|g; s|@PROJECT_VERSION_PATCH@|$(DRAFT_VERSION)|g; s|(#cmakedefine)|// \1|g; s|(@.*@)|0|g;' \
		$(SOURCE_PATH)/../../lib/include/quant/config.h.in > $(SOURCE_PATH)/quant/config.h)
