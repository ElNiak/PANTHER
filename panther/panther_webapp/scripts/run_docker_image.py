#!/usr/bin/env python

from distutils.dir_util import copy_tree
from shutil import copyfile
import getopt
import sys
import os
from os import listdir
from os.path import isfile, join
from utils.ArgumentParser import ArgumentParser
from utils.constants import *
from utils.CustomFormatter import CustomFormatter
import os


# TODO redo aioquic
# screen -dm bash -c 'python3.10 run_docker_image.py --mode client --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations aioquic --iter 1 --compile --delete --build --remove --docker_output_path docker-output-100-client-aioquic/ >> 100_client_0rtt_aioquic;'


# screen -dm bash -c 'python3.10 run_docker_image.py --mode client --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations picoquic --iter 100 --compile --remove --docker_output_path docker-output-100-client-picoquic/ >> 100_client_0rtt_picoquic; \
#                     python3.10 run_docker_image.py --mode client --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations mvfst --iter 100 --compile --remove --docker_output_path docker-output-100-client-mvfst/ >> 100_client_0rtt_mvfst; \
#                     python3.10 run_docker_image.py --mode client --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations quant --iter 100 --compile --remove  --docker_output_path docker-output-100-client-quant/ >> 100_client_0rtt_quant; \
#                     python3.10 run_docker_image.py --mode client --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations quiche --iter 100 --compile --remove --docker_output_path docker-output-100-client-quiche/ >> 100_client_0rtt_quiche; \
#                     python3.10 run_docker_image.py --mode client --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations quinn --iter 100 --compile --remove  --docker_output_path docker-output-100-client-quinn/ >> 100_client_0rtt_quinn; \
#                     python3.10 run_docker_image.py --mode client --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations lsquic --iter 100 --compile --remove  --docker_output_path docker-output-100-client-lsquic/ >> 100_client_0rtt_lsquic; \
#                     python3.10 run_docker_image.py --mode client --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations quic-go --iter 100 --compile --remove --docker_output_path docker-output-100-client-quic-go/ >> 100_client_0rtt_quic-go; \
#                     python3.10 run_docker_image.py --mode client --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations aioquic --iter 100 --compile --remove  --docker_output_path docker-output-100-client-aioquic/ >> 100_client_0rtt_aioquic;'

# screen -dm bash -c 'python3.10 run_docker_image.py --mode server --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations picoquic --iter 100 --compile --remove --docker_output_path docker-output-100-server-picoquic/ >> 100_server_0rtt_picoquic; \
#                     python3.10 run_docker_image.py --mode server --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations mvfst --iter 100 --compile --remove --docker_output_path docker-output-100-server-mvfst/ >> 100_server_0rtt_mvfst; \
#                     python3.10 run_docker_image.py --mode server --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations quant --iter 100 --compile --remove  --docker_output_path docker-output-100-server-quant/ >> 100_server_0rtt_quant; \
#                     python3.10 run_docker_image.py --mode server --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations quiche --iter 100 --compile --remove --docker_output_path docker-output-100-server-quiche/ >> 100_server_0rtt_quiche; \
#                     python3.10 run_docker_image.py --mode server --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations quinn --iter 100 --compile --remove  --docker_output_path docker-output-100-server-quinn/ >> 100_server_0rtt_quinn; \
#                     python3.10 run_docker_image.py --mode server --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations lsquic --iter 100 --compile --remove  --docker_output_path docker-output-100-server-lsquic/ >> 100_server_0rtt_lsquic; \
#                     python3.10 run_docker_image.py --mode server --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations quic-go --iter 100 --compile --remove --docker_output_path docker-output-100-server-quic-go/ >> 100_server_0rtt_quic-go; \
#                     python3.10 run_docker_image.py --mode server --categories 0rtt_test --update_include_tls  --timeout 30 --getstats --implementations aioquic --iter 100 --compile --remove  --docker_output_path docker-output-100-server-aioquic/ >> 100_server_0rtt_aioquic;'


SOURCE_DIR = os.getenv("PWD")
IMPLEM_DIR = SOURCE_DIR + "/quic-implementations"


def main(argv):
    args_parser = ArgumentParser()
    args = args_parser.parse_arguments()
    print(args)
    if args.remove:
        os.system("sudo docker rm $(sudo docker ps -aq)")

    if args.delete:
        os.system("sudo docker rmi $(sudo docker images -aq)")

    if args.build:  # TODO add no_cache option
        print("build")
        command = "sudo docker build" + " -t quic-ivy-uclouvain " + " ."
        print(command)
        os.system(command)

    if not os.path.isdir(SOURCE_DIR + "/" + args.docker_output_path):
        os.mkdir(SOURCE_DIR + "/" + args.docker_output_path)

    command = (
        'sudo docker run --cpus="4.0" --memory="10g" --memory-reservation="9.5g" '
        + " --privileged -it -v "
        + SOURCE_DIR
        + "/"
        + args.docker_output_path
        + ":/QUIC-FormalVerification/panther-ivy/protocol-testing/quic/test/temp "
        + " --name quic-ivy-uclouvain quic-ivy-uclouvain "
        + "python3.10 panther.py --docker --mode "
        + str(args.mode)
        + " --categories "
        + str(args.categories)
        + " --implementations "
        + " ".join([str(elem) for elem in args.implementations])
        + " --update_include_tls  --timeout "
        + str(args.timeout)
        + " --getstats  --iter "
        + str(args.iter)
        + " --compile"
    )
    print(command)
    os.system(command)


if __name__ == "__main__":
    main(sys.argv[1:])
