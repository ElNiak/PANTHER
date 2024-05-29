# Set the name of your application:
APPLICATION = quant-client

# If no BOARD is found in the environment, use this default:
BOARD ?= esp32-wroom-32

# This has to be the absolute path to the RIOT base directory:
RIOTBASE ?= $(CURDIR)/../../riot

# Uncomment this to enable code in RIOT that does safety checking
# which is not needed in a production environment but helps in the
# development process:
DEVELHELP ?= 1

# Change this to 0 to show compiler invocation lines by default:
QUIET ?= 1

# Modules to include:
EXTERNAL_MODULE_DIRS += modules
USEMODULE += quant

USEMODULE += esp_wifi

BAUD=115200
CFLAGS += -DTHREAD_STACKSIZE_MAIN=8192 -DSTDIO_UART_BAUDRATE=${BAUD}
PROGRAMMER_SPEED=1843200

-include Makefile.wifi-credentials

include $(RIOTBASE)/Makefile.include
