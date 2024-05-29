NO_AUTO_SRC = 1

PTLS_INC = lib/deps/picotls/include
PTLS_SRC = lib/deps/picotls

QUIC_INC = lib/include
QUIC_SRC = lib/src

TIMEOUT_INC = lib/deps/timeout

WARP_INC = lib/deps/warpcore/lib/include
WARP_SRC = lib/deps/warpcore/lib/src

SRC += \
	$(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src/aes.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src/blockwise.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src/chacha20.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src/curve25519.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src/drbg.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src/gcm.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src/gf128.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src/modes.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src/poly1305.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src/sha256.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src/sha512.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/deps/micro-ecc/uECC.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/lib/cifra.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/lib/cifra/x25519.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/lib/cifra/aes128.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/lib/cifra/aes256.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/lib/cifra/chacha20.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/lib/picotls.c \
	$(RIOTPROJECT)/$(PTLS_SRC)/lib/uecc.c \
	$(RIOTPROJECT)/$(QUIC_SRC)/cid.c \
	$(RIOTPROJECT)/$(QUIC_SRC)/conn.c \
	$(RIOTPROJECT)/$(QUIC_SRC)/diet.c \
	$(RIOTPROJECT)/$(QUIC_SRC)/frame.c \
	$(RIOTPROJECT)/$(QUIC_SRC)/loop.c \
	$(RIOTPROJECT)/$(QUIC_SRC)/marshall.c \
	$(RIOTPROJECT)/$(QUIC_SRC)/pkt.c \
	$(RIOTPROJECT)/$(QUIC_SRC)/pn.c \
	$(RIOTPROJECT)/$(QUIC_SRC)/quic.c \
	$(RIOTPROJECT)/$(QUIC_SRC)/recovery.c \
	$(RIOTPROJECT)/$(QUIC_SRC)/stream.c \
	$(RIOTPROJECT)/$(QUIC_SRC)/tls.c \
	$(RIOTPROJECT)/$(WARP_SRC)/backend_riot.c \
	$(RIOTPROJECT)/$(WARP_SRC)/plat.c \
	$(RIOTPROJECT)/$(WARP_SRC)/util.c \
	$(RIOTPROJECT)/$(WARP_SRC)/warpcore.c \
	$(RIOTPROJECT)/test/minimal_transaction.c \
	quant/config.c \
	warpcore/config.c

.PHONY: dirs

all: quant/config.c warpcore/config.c

INCLUDES += \
	-isystem $(CURDIR) \
	-isystem $(RIOTPROJECT)/$(PTLS_INC) \
	-isystem $(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src \
	-isystem $(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src/ext \
	-isystem $(RIOTPROJECT)/$(PTLS_SRC)/deps/micro-ecc \
	-isystem $(RIOTPROJECT)/$(QUIC_INC) \
	-isystem $(RIOTPROJECT)/$(TIMEOUT_INC) \
	-isystem $(RIOTPROJECT)/$(WARP_INC)

ifndef BUILD_FLAGS
BUILD_FLAGS=-DMINIMAL_CIPHERS -DNO_ERR_REASONS -DNO_OOO_0RTT \
	-DNO_MIGRATION -DNO_SRT_MATCHING -DNO_QINFO -DNO_SERVER -DNO_ECN
endif

# -DDSTACK -finstrument-functions -DNDEBUG
# -finstrument-functions-exclude-file-list=deps/micro-ecc,deps/cifra
DEVELHELP=
CFLAGS +=-fstack-usage -foptimize-strlen -ffast-math \
	-Wno-unknown-pragmas -Wno-missing-field-initializers -Wno-cast-align \
	-Wno-strict-prototypes -Wno-sign-compare -Wno-maybe-uninitialized \
	-Wno-unused-variable -Wno-unused-but-set-variable \
	-DDLEVEL=DBG -DNO_TLS_LOG -DNO_QLOG ${BUILD_FLAGS} \
	-D'ntoh16(x)=__builtin_bswap16(*(uint16_t*)(x))' \
	-D'ntoh32(x)=__builtin_bswap32(*(uint32_t*)(x))' \
	-D'ntoh64(x)=__builtin_bswap64(*(uint64_t*)(x))' \
	-D'alloca(x)=(void*)&x'
# NOTE: alloca definition is obviously garbage, but it's never called anyway

include $(RIOTBASE)/Makefile.base

dirs:
	@# make a bunch of unusual directories for the out-of-tree dependencies
	@mkdir -p quant warpcore \
		$(BINDIR)/$(MODULE)/$(RIOTPROJECT)/$(PTLS_SRC)/deps/cifra/src \
		$(BINDIR)/$(MODULE)/$(RIOTPROJECT)/$(PTLS_SRC)/deps/micro-ecc \
		$(BINDIR)/$(MODULE)/$(RIOTPROJECT)/$(PTLS_SRC)/lib/cifra \
		$(BINDIR)/$(MODULE)/$(RIOTPROJECT)/$(QUIC_SRC) \
		$(BINDIR)/$(MODULE)/$(RIOTPROJECT)/$(WARP_SRC) \
		$(BINDIR)/$(MODULE)/$(RIOTPROJECT)/test \
		$(BINDIR)/$(MODULE)/quant/quant \
		$(BINDIR)/$(MODULE)/warpcore

QUANT_VERSION=$(shell grep 'quant.*VERSION' $(RIOTPROJECT)/CMakeLists.txt | cut -d' ' -f3)
DRAFT_VERSION=$(shell grep 'quant.*VERSION' $(RIOTPROJECT)/CMakeLists.txt | cut -d' ' -f3 | cut -d. -f3)

quant/config.c: $(RIOTPROJECT)/lib/src/config.c.in quant/config.h
	@sed -E -e 's|@PROJECT_NAME@|quant|g; s|@PROJECT_NAME_UC@|QUANT|g; s|@PROJECT_VERSION@|$(QUANT_VERSION)|g; s|@PROJECT_VERSION_PATCH@|$(DRAFT_VERSION)|g; s|(@.*@)|0|g;' \
		$< > $@

quant/config.h: $(RIOTPROJECT)/lib/include/quant/config.h.in dirs
	@sed -E -e 's|@PROJECT_NAME@|quant|g; s|@PROJECT_NAME_UC@|QUANT|g; s|@PROJECT_VERSION@|$(QUANT_VERSION)|g; s|@PROJECT_VERSION_PATCH@|$(DRAFT_VERSION)|g; s|(#cmakedefine)|// \1|g; s|(@.*@)|0|g;' \
		$< > $@

WARPCORE_VERSION:=$(shell grep 'warpcore.*VERSION' $(RIOTPROJECT)/lib/deps/warpcore/CMakeLists.txt | cut -d' ' -f3)

warpcore/config.c: $(RIOTPROJECT)/$(WARP_SRC)/config.c.in warpcore/config.h
	@sed -E -e 's|@PROJECT_NAME@|warpcore|g; s|@PROJECT_NAME_UC@|WARPCORE|g; s|@PROJECT_VERSION@|$(WARPCORE_VERSION)|g;' \
		$< > $@

warpcore/config.h: $(RIOTPROJECT)/$(WARP_INC)/warpcore/config.h.in dirs
	@sed -E -e 's|@PROJECT_NAME@|warpcore|g; s|@PROJECT_NAME_UC@|WARPCORE|g; s|@PROJECT_VERSION@|$(WARPCORE_VERSION)|g; s|(#cmakedefine)|// \1|g; s|(@.*@)|0|g;' \
		$< > $@

