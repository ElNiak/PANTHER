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

SOURCE_DIR =  os.getenv('PWD')
IMPLEM_DIR =  SOURCE_DIR + '/quic-implementations'

def main(argv):     
    args_parser = ArgumentParser()
    args = args_parser.parse_arguments()
    print(args)
    if args.delete: 
        os.system('sudo docker rm $(sudo docker ps -aq)')
        os.system('sudo docker rmi $(sudo docker images -aq)')

    if args.build: # TODO add no_cache option
        print("build")
        os.system('sudo docker build '+\
            ' --build-arg MODE='+ str(args.mode) +' --build-arg CATE='+ str(args.categories) +' --build-arg TIME='+ str(args.timeout) +' --build-arg IMPL='+ ' '.join([str(elem) for elem in args.implementations]) +' ' +\
            '--build-arg ITER='+ str(args.iter) +' ' +\
            ' -t quic-ivy-uclouvain .')

    command = 'sudo docker run --cpus="4.0" --memory="10g" --memory-reservation="9.5g" ' +\
        ' --privileged -it -v '+ args.docker_output_path + 'results:/QUIC-FormalVerification/QUIC-Ivy/doc/examples/quic/test/temp ' +\
        ' --name quic-ivy-uclouvain quic-ivy-uclouvain'
    print(command)
    os.system(command)

if __name__ == "__main__":
    main(sys.argv[1:])
