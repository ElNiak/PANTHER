import configparser
import logging
import os

log = logging.getLogger("PFV builder")

config = configparser.ConfigParser(allow_no_value=True)
config.read('src/pfv/configs/global-config.ini')

# TODO parse config file

# update config file

# update docker-compose file