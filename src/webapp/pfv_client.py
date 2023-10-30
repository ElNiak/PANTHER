from flask import Flask, request, jsonify
import requests
import argparse
import configparser
import threading
import os
import socket

from pfv_utils.pfv_constant import *
from pfv import *

class PFVClient:
    app = Flask(__name__)
    app.debug = True
    thread = None
    
    def __init__(self,dir_path=None):
        PFVClient.dir_path         = dir_path
        PFVClient.ivy_include_path = dir_path + "/QUIC-Ivy-Attacker/ivy/include/1.7/"
                
        # Setup configuration
        PFVClient.config = configparser.ConfigParser(allow_no_value=True)
        PFVClient.config.read('configs/config.ini')

    #Parse the parameters received in the request and launch the SCDG
    @app.route('/run-exp', methods=['POST'])
    def run_scdg():
        #Modify config file with the args provided in web app
        user_data = request.json
        os.chdir(SOURCE_DIR)
        print(user_data)
        current_protocol = user_data['protocol']
        exp_args = user_data['args']
        net_args = ""
        for arg in exp_args:
            if arg in PFVClient.config['global_parameters']:
                PFVClient.config.set('global_parameters', arg, exp_args[arg])
            if arg in PFVClient.config['debug_parameters']:
                PFVClient.config.set('debug_parameters', arg, exp_args[arg])
            if arg == "net_parameters":
                net_args = exp_args[arg]
            if arg in PFVClient.config['shadow_parameters']:
                PFVClient.config.set('shadow_parameters', arg, exp_args[arg])
                
        for arg in PFVClient.config['net_parameters']:
            print(net_args)
            print(arg)
            if arg in net_args:
                PFVClient.config.set('net_parameters', arg, "true")
            else:
                PFVClient.config.set('net_parameters', arg, "false")
        
        for arg in PFVClient.config['verified_protocol']:
            if current_protocol == arg:
                PFVClient.config.set('verified_protocol', arg, "true")
            else:
                PFVClient.config.set('verified_protocol', arg, "false")
                
        with open('configs/config.ini', 'w') as configfile:
            PFVClient.config.write(configfile)
            
        current_tests = user_data['tests']
        prot_args = user_data['prot_args']
        protocol_conf = configparser.ConfigParser(allow_no_value=True)
        protocol_conf.read('configs/'+current_protocol+'/'+current_protocol+'_config.ini')
        for arg in prot_args:
            if arg in protocol_conf[current_protocol+'_parameters']:
                protocol_conf.set(current_protocol+'_parameters', arg, prot_args[arg])
        for test_type in protocol_conf.sections():
            for test in current_tests:
                if test_type in test:
                    protocol_conf.set(test_type, test, "true")
        with open('configs/'+current_protocol+'/'+current_protocol+'_config.ini', 'w') as configfile:
            protocol_conf.write(configfile)

        tool = PFV()
        try:
            PFVClient.thread = threading.Thread(target=tool.launch_experiments, args=([[user_data['implementation']]])) 
            PFVClient.thread.daemon = True
            PFVClient.thread.start()
            return "Request successful"
        except:
            return "Something went wrong"
        
    @app.after_request
    def add_header(r):
        """
        It sets the cache control headers to prevent caching
        
        :param r: The response object
        :return: the response object with the headers added.
        """
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        r.headers["Pragma"] = "no-cache"
        r.headers["Expires"] = "0"
        r.headers['Cache-Control'] = 'public, max-age=0'
        return r

    @app.route('/progress', methods = ['GET', 'POST'])
    def progress():
        #PFVClient.app.logger.info(PFVClient.experiments.count_1)
        return "0" #str(PFVClient.experiments.count_1)
        

    def run(self):
        PFVClient.app.run(host='0.0.0.0', port=80, use_reloader=True)