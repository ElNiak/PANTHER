#!/usr/bin/env python3.9
# -*- coding: utf-8 -*-


# TODO add logs
# TODO https://www.mongodb.com/docs/manual/core/geospatial-indexes/

from cgitb import html
import json
import os
import threading

# from tkinter import N
from flask import Flask, flash, request, redirect, url_for, send_from_directory, Response, session, render_template
from werkzeug.utils import secure_filename
from run_experiments import *
from gui.graph_visualizer import *
from base64 import b64encode
from django.core.paginator import (
    Paginator,
    EmptyPage,
    PageNotAnInteger,
)

# import logging
# log = logging.getLogger('api')

class IvyWorker:
    ROOTPATH = os.getcwd()
    app = Flask(__name__, static_folder=ROOTPATH + '/webapp/static/')
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['APPLICATION_ROOT'] = ROOTPATH + '/webapp/templates/'
    app.debug = True
    
    
    def __init__(self,dir_path=None,experiments=None):
        IvyWorker.dir_path = dir_path
        IvyWorker.ivy_temps_path = dir_path + "/QUIC-Ivy-Attacker/doc/examples/quic/test/temp/"
        IvyWorker.server_tests = []
        IvyWorker.server_tests_checkbox = []
        for cate in TESTS_SERVER:
            for test in TESTS_SERVER[cate]:
                IvyWorker.server_tests.append(test)
        IvyWorker.client_tests = []
        IvyWorker.client_tests_checkbox = []
        for cate in TESTS_CLIENT:
            for test in TESTS_CLIENT[cate]:
                IvyWorker.client_tests.append(test)
                
        IvyWorker.implems = []
        for i in IMPLEMENTATIONS.keys():
            IvyWorker.implems.append(i)

        IvyWorker.implem_tests_checkbox = []

        IvyWorker.experiments = experiments
        IvyWorker.nb_exp = len(os.listdir(IvyWorker.ivy_temps_path)) - 1
        IvyWorker.current_exp = IvyWorker.ivy_temps_path + str(IvyWorker.nb_exp)
        
        IvyWorker.x = None


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
        IvyWorker.app.logger.info(IvyWorker.experiments.count_1)
        return str(IvyWorker.experiments.count_1)

    @app.route('/run-exp', methods = ['GET', 'POST'])
    def run_exp():
        if IvyWorker.x is not None:
            IvyWorker.x.join()
            IvyWorker.x = None
            #return "ko" # cancel ?
        IvyWorker.app.logger.info(request.get_json())
        # {'mode': 'custom', 'implementations': ['picoquic'], 'nb_request': 10, 'initial_version': 1, 'dir': None, 'iter': 1, 'nclient': 1, 'getstats': False, 'compile': True, 'run': True, 'timeout': 30, 'gdb': False, 'keep_alive': False, 'update_include_tls': True, 'docker': True, 'vnet': False, 'alpn': 'hq-interop', 'categories': 'all', 'gui': False, 'webapp': True, 'api': False, 'gperf': False}
        #exit(0)
        #IvyWorker.experiments.args = request.get_json()
        req = request.get_json()
        from utils.constants import TESTS_CUSTOM
        TESTS_CUSTOM = req["tests"]
        IvyWorker.app.logger.info(req["tests"])
        IvyWorker.app.logger.info(type(req["tests"]))
        IvyWorker.experiments.set_custom(req["tests"])
        for key in req:
            if key != "tests":
                setattr(IvyWorker.experiments.args, key, req[key])
        IvyWorker.x = threading.Thread(target=IvyWorker.experiments.launch_experiments, args=([req["tests"]])) 
        IvyWorker.x.start()
        return "ok"

    #TODO cancel button
    
    def run(self):
        IvyWorker.app.run(host='0.0.0.0', port=80, use_reloader=True, threaded=True)  
        