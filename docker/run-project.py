#!/usr/bin/env python

from distutils.dir_util import copy_tree
from shutil import copyfile
import getopt
import sys
import os
from os import listdir
from os.path import isfile, join

# sudo python run-project.py -b true -m server -p /home/user/Documents/QUIC-FormalVerification -i 100

def usage():
    message = "Usage: ./run-project -b[uild] <true/false> -m[ode] <client/server/all> -p <path/> -i <iteration>"
    print(message)

def main(argv):     
    build = False
    delete = False
    mode  = "all" 
    path = ""
    it = 1
    
    try:                                
        opts, args = getopt.getopt(argv, "hg:b:m:p:i:f:d", ["help", "build=","mode=","path=","iteration=","final=","delete="])
    except getopt.GetoptError:          
        usage()                         
        sys.exit(2)                    
    for opt, arg in opts:                
        if opt in ("-h", "--help"):      
            usage()                     
            sys.exit()                       
        elif opt == '-b' and arg.lower() == "true":                
            build = True    
        elif opt == '-m':
            if not arg == "all" and not arg == "client" and not arg == "server":
                usage()                     
                sys.exit()            
            mode = arg  
        elif opt == '-i':
            #TODO check if int           
            it = int(arg)  
        elif opt == '-p':
            if arg == "" :
                usage()                     
                sys.exit()            
            path = arg  
            if not path[-1] == "/" and not path[-1] == "\\":
                path += "/"
        elif opt == '-d': 
            delete = True

    if delete: 
        os.system('docker rm $(docker ps -aq)')
        os.system('docker rmi $(docker images -aq)')

    if build:
        os.system('docker build -t quic-ivy-uclouvain .')

    if mode == "all":
        os.system('docker run --privileged -it -v '+ path + 'results:/results quic-ivy-uclouvain bash test_all.sh ' + str(it))
    elif mode == "client":
        os.system('docker run --privileged -it -v '+ path + 'results:/results quic-ivy-uclouvain bash test_client.sh ' + str(it))
    elif mode == "server":
        os.system('docker run --privileged -it -v '+ path + 'results:/results quic-ivy-uclouvain bash test_server.sh ' + str(it)) # test_server.sh ' + str(it)

    os.system('chmod -R 777 results/')

if __name__ == "__main__":
    main(sys.argv[1:])
