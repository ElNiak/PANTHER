#!/usr/bin/env python3.9
# -*- coding: utf-8 -*-


# TODO add logs
# TODO https://www.mongodb.com/docs/manual/core/geospatial-indexes/

from cgitb import html
import json
import os
import socket
import time
import uuid
import threading
import requests
from flask import Flask, flash, request, redirect, url_for, send_from_directory, Response, session, render_template, jsonify
from werkzeug.utils import secure_filename
from base64 import b64encode
from django.core.paginator import (Paginator,EmptyPage,PageNotAnInteger)
import datetime
from flask_cors import CORS
import pandas as pd
from npf_web_extension.app import export
import configparser
import argparse

from pfv_webapp.utils.cytoscape_generator import *
from pfv_utils.pfv_constant import *
from argument_parser.ArgumentParserRunner import ArgumentParserRunner
from pfv import *

DEBUG = True

class PFVServer:
    ROOTPATH = os.getcwd()
    app = Flask(__name__, static_folder=ROOTPATH + '/app/static/')
    app.secret_key = 'super secret key' # TODO
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['APPLICATION_ROOT'] = ROOTPATH + '/app/templates/'
    app.debug = True
    # enable CORS
    CORS(app, resources={r'/*': {'origins': '*'}})

    def __init__(self,dir_path=None):
        with open('configs/config.ini', 'w') as configfile:
            with open('configs/default_config.ini', "r") as default_config:
                default_settings = default_config.read()
                configfile.write(default_settings)
        PFVServer.dir_path         = dir_path
        PFVServer.ivy_include_path = dir_path + "/pfv-ivy/ivy/include/1.7/"
                
        # Setup configuration
        PFVServer.config = PFVServer.setup_config()
        PFVServer.enable_impems = {}
        PFVServer.protocol_conf = PFVServer.setup_protocol_parameters(PFVServer.current_protocol,dir_path)

        PFVServer.total_exp_in_dir = len(os.listdir(PFVServer.ivy_temps_path)) - 2
        PFVServer.current_exp_path = PFVServer.ivy_temps_path + str(PFVServer.total_exp_in_dir)
        PFVServer.local_exp_path   = PFVServer.local_path + str(PFVServer.total_exp_in_dir)
        
        PFVServer.current_tests = []
        PFVServer.implems_used = []
        
        PFVServer.total_exp = 0
        PFVServer.current_count = 0
        PFVServer.started_exp = False
        PFVServer.current_implem = None
        
        PFVServer.choices_args = {}
        
        # Get QUIC visualizer service (TODO move)
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            PFVServer.local_ip = local_ip
            vizualiser_ip = socket.gethostbyname("ivy-visualizer")
            PFVServer.vizualiser_ip = vizualiser_ip
        except:
            PFVServer.local_ip = ""
            PFVServer.vizualiser_ip = ""
            PFVServer.app.logger.info("No visualizer found")
                        
    def setup_config(init=True, protocol=None):
        config = configparser.ConfigParser(allow_no_value=True)
        if init:
            config.read('configs/default_config.ini')
        else:
            config.read('configs/config.ini')
        
        PFVServer.key_path = SOURCE_DIR + "/tls-keys/"
        PFVServer.implems = {}
        PFVServer.current_protocol =  ""
        PFVServer.supported_protocols = config["verified_protocol"].keys()
        if init:
            for p in config["verified_protocol"].keys():
                if config["verified_protocol"].getboolean(p):
                    PFVServer.current_protocol = p
                    break
        else:
            PFVServer.current_protocol = protocol
        return config
    
    def setup_protocol_parameters(protocol, dir_path, init=True):
        
        # TODO use client to get these information
        PFVServer.tests = {}
        PFVServer.implems = {}
        protocol_conf = configparser.ConfigParser(allow_no_value=True)
        for envar in P_ENV_VAR[protocol]:
            os.environ[envar] = P_ENV_VAR[protocol][envar]
            # os.environ['INITIAL_VERSION'] = str(self.args.initial_version)
            # ENV_VAR["INITIAL_VERSION"] = str(self.args.initial_version)
        if init:
            protocol_conf.read('configs/'+protocol+'/default_'+protocol+'_config.ini')
        else:
            protocol_conf.read('configs/'+protocol+'/'+protocol+'_config.ini')
        PFVServer.ivy_model_path = dir_path + "/pfv-ivy/protocol-testing/" + protocol
        PFVServer.ivy_test_path  = dir_path + "/pfv-ivy/protocol-testing/" + protocol +"/tests/"
        PFVServer.ivy_temps_path = dir_path + "/pfv-ivy/protocol-testing/ "+ protocol +"/test/temp/"
        PFVServer.local_path = os.environ["ROOT_PATH"] + "/pfv-ivy/protocol-testing/"+ protocol +"/test/temp/"
        for cate in protocol_conf.keys():
            if "test" in cate:
                PFVServer.tests[cate] = []
                for test in protocol_conf[cate]:
                    PFVServer.tests[cate].append(test)
        implem_config_path_server = 'configs/'+protocol+'/implem-server'
        implem_config_path_client = 'configs/'+protocol+'/implem-client'
        for file_path in os.listdir(implem_config_path_server):
            # check if current file_path is a file
            # TODO check if enable in global config
            if os.path.isfile(os.path.join(implem_config_path_server, file_path)):
                implem_name = file_path.replace(".ini","") 
                implem_conf_server = configparser.ConfigParser(allow_no_value=True)
                implem_conf_server.read(os.path.join(implem_config_path_server, file_path))
                implem_conf_client = configparser.ConfigParser(allow_no_value=True)
                implem_conf_client.read(os.path.join(implem_config_path_client, file_path))
                PFVServer.implems[implem_name] = [implem_conf_server, implem_conf_client]
        global_conf_file = "configs/global-conf.ini"
        global_config    = configparser.ConfigParser(allow_no_value=True)
        global_config.read(global_conf_file)
        for key in global_config:
            if "implementations" in key:
                implem = key.replace("-implementations","")
                for i in global_config[key]:
                    PFVServer.enable_impems[i] = global_config[key].getboolean(i)
        return protocol_conf
        
    
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
        r.headers.add("Access-Control-Allow-Headers", "authorization,content-type")
        r.headers.add("Access-Control-Allow-Methods", "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT")
        r.headers.add("Access-Control-Allow-Origin", "*")
        return r

    @app.route('/')
    def redirection():
        """
        It redirects the user to the index.html page
        :return: a redirect to the index.html page.
        """
        return redirect('index.html', code =302)
    
    @app.route('/progress', methods = ['GET'])
    def progress():
        return "None" if not PFVServer.started_exp else str(PFVServer.current_count)

    
    @app.route('/update-count', methods = ['GET'])
    def update_count():
        PFVServer.current_count += 1
        if PFVServer.started_exp:
            if PFVServer.current_count == PFVServer.total_exp:
                PFVServer.started_exp   = False
                PFVServer.current_count = 0
                PFVServer.total_exp     = 0
        return "ok"
    
    def get_args():
        # TODO refactor
        PFVServer.choices_args = {}
        args_parser = ArgumentParserRunner().parser
        args_list = [{}]
        is_mutually_exclusive = True
        for group_type in [args_parser._mutually_exclusive_groups, args_parser._action_groups]:
            for group in group_type:
                if group.title == "positional arguments":
                    continue
                if group.title == "optional arguments":
                    continue
                if group.title == "Usage type":
                    continue

                cont = False
                for p in PFVServer.supported_protocols:
                    if p in group.title.lower():
                        cont = True
                if cont:
                    continue
                        
                if len(args_list[-1]) == 3:
                    args_list.append({})
                
                for action in group._group_actions:
                    group_name = group.title
                    if group_name not in args_list[-1]:
                        args_list[-1][group_name] = []
                    if isinstance(action, argparse._StoreTrueAction):
                        args_list[-1][group_name].append({'name': action.dest, 'help': action.help, "type": "bool", "default": False, "is_mutually_exclusive": is_mutually_exclusive, "description": action.metavar})
                    elif isinstance(action, argparse._StoreFalseAction):
                        args_list[-1][group_name].append({'name': action.dest, 'help': action.help, "type": "bool", "default": True,  "is_mutually_exclusive": is_mutually_exclusive, "description": action.metavar})
                    elif not isinstance(action, argparse._HelpAction):
                        if hasattr(action, 'choices'):
                            if action.choices:
                                PFVServer.choices_args[action.dest] = action.choices
                            args_list[-1][group_name].append({'name': action.dest, 'help': action.help, "type": str(action.type), "default": action.default, "is_mutually_exclusive": is_mutually_exclusive, "choices": action.choices, "description": action.metavar})
                        else:
                            args_list[-1][group_name].append({'name': action.dest, 'help': action.help, "type": str(action.type), "default": action.default, "is_mutually_exclusive": is_mutually_exclusive, "description": action.metavar})
            is_mutually_exclusive = False
        
        json_arg = args_list
        
        args_list = [{}]
        is_mutually_exclusive = True
        for group_type in [args_parser._mutually_exclusive_groups, args_parser._action_groups]:
            for group in group_type:
                 for p in PFVServer.supported_protocols:
                    if p in group.title.lower():
                        if p in PFVServer.current_protocol:
                            if len(args_list[-1]) == 3:
                                args_list.append({})
                            
                            for action in group._group_actions:
                                group_name = group.title
                                if group_name not in args_list[-1]:
                                    args_list[-1][group_name] = []
                                if isinstance(action, argparse._StoreTrueAction):
                                    args_list[-1][group_name].append({'name': action.dest, 'help': action.help, "type": "bool", "default": False, "is_mutually_exclusive": is_mutually_exclusive, "description": action.metavar})
                                elif isinstance(action, argparse._StoreFalseAction):
                                    args_list[-1][group_name].append({'name': action.dest, 'help': action.help, "type": "bool", "default": True,  "is_mutually_exclusive": is_mutually_exclusive, "description": action.metavar})
                                elif not isinstance(action, argparse._HelpAction):
                                    if hasattr(action, 'choices'):
                                        if action.choices:
                                            PFVServer.choices_args[action.dest] = action.choices
                                        args_list[-1][group_name].append({'name': action.dest, 'help': action.help, "type": str(action.type), "default": action.default, "is_mutually_exclusive": is_mutually_exclusive, "choices": action.choices, "description": action.metavar})
                                    else:
                                        args_list[-1][group_name].append({'name': action.dest, 'help': action.help, "type": str(action.type), "default": action.default, "is_mutually_exclusive": is_mutually_exclusive, "description": action.metavar})
                        is_mutually_exclusive = False 
        prot_arg = args_list
        return json_arg, prot_arg
    
    def start_exp(exp_args, prot_args):
        for impl in PFVServer.implems_used:
            PFVServer.app.logger.info(impl)
            # TODO send directly parsed args of implem from here ?
            # for key,value in PFVServer.implems[impl].items():
            #     if key in exp_args:
            #         exp_args[key] = value
            #     else:
            #         exp_args[key] = value
            req = {
                "args": exp_args,
                "prot_args": prot_args,
                "protocol": PFVServer.current_protocol,
                "implementation": impl,
                "tests": PFVServer.current_tests,
            }
            response = requests.post('http://'+impl+'-ivy:80/run-exp', json=req)
            PFVServer.app.logger.info(str(response.content))
            
            while PFVServer.current_count < PFVServer.total_exp/len(PFVServer.implems_used):
                # wait
                time.sleep(10)
                print("wait")
                print(PFVServer.current_count)
                print(PFVServer.total_exp/len(PFVServer.implems_used))
            print("finish")
    
    
    @app.route('/index.html', methods = ['GET', 'POST'])
    def serve_index():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        print(PFVServer.current_protocol)
        json_arg, prot_arg = PFVServer.get_args()
        PFVServer.app.logger.info("JSON ARG")
        for elem in json_arg:
            PFVServer.app.logger.info(elem)
        PFVServer.app.logger.info("PROTOCOL ARG")
        for elem in prot_arg:
            PFVServer.app.logger.info(elem)
                
        if request.method == 'POST': 
            # TODO link json_arg and prot_arg to config so we can restore old config
            # TODO fix problem with alpn & initial version
            if request.args.get('prot', '') and request.args.get('prot', '') in PFVServer.supported_protocols:
                PFVServer.current_protocol = request.args.get('prot', '')
                json_arg, prot_arg = PFVServer.get_args()
                PFVServer.app.logger.info("JSON ARG")
                for elem in json_arg:
                    PFVServer.app.logger.info(elem)
                PFVServer.app.logger.info("PROTOCOL ARG")
                for elem in prot_arg:
                    PFVServer.app.logger.info(elem)
                PFVServer.config        = PFVServer.setup_config(False, PFVServer.current_protocol)
                PFVServer.protocol_conf = PFVServer.setup_protocol_parameters(PFVServer.current_protocol,PFVServer.dir_path,False)
            else:
                PFVServer.config        = PFVServer.setup_config(False,PFVServer.current_protocol)
                PFVServer.protocol_conf = PFVServer.setup_protocol_parameters(PFVServer.current_protocol,PFVServer.dir_path,False)
            # TODO implem progress, avoid to use post if experience already launched
            # TODO force to select at least one test and one implem
            PFVServer.app.logger.info(request.form)
            
            for c in request.form: 
                for elem in request.form.getlist(c):
                    PFVServer.app.logger.info(elem)
            
            PFVServer.implems_used = []
            exp_args = {}
            prot_args = {}
            PFVServer.current_tests = []
            arguments = dict(request.form)
            exp_number = 1
            for key,value in arguments.items():
                if (key,value) == ('boundary', 'experiment separation'):
                    exp_number += 1
                elif key in PFVServer.implems.keys() and value == 'true':
                    PFVServer.implems_used.append(key)
                elif 'test' in key and value == 'true':
                    PFVServer.current_tests.append(key)
                elif value != "": # value != "false" and 
                    if key in PFVServer.choices_args:
                        print(PFVServer.choices_args[key])
                        value = str(PFVServer.choices_args[key][int(value)-1])
                    if exp_number == 1:
                        exp_args[key] = value
                    elif exp_number == 2:
                        prot_args[key] = value
            
            PFVServer.app.logger.info(str(exp_args))
            PFVServer.app.logger.info(str(prot_args))
            PFVServer.app.logger.info(str(PFVServer.current_tests))
            PFVServer.started_exp = True
            PFVServer.total_exp = len(PFVServer.implems_used) * len(PFVServer.current_tests) * int(exp_args["iter"])
            
            thread = threading.Thread(target=PFVServer.start_exp, args=([exp_args, prot_args])) 
            thread.daemon = True
            thread.start()
            
            return render_template('index.html', 
                                json_arg=json_arg,
                                prot_arg=prot_arg,
                                enable_impems=PFVServer.enable_impems,
                                base_conf=PFVServer.config,
                                protocol_conf=PFVServer.protocol_conf,
                                supported_protocols=PFVServer.supported_protocols,
                                current_protocol= PFVServer.current_protocol,
                                tests=PFVServer.tests, 
                                nb_exp=PFVServer.total_exp_in_dir, 
                                implems=PFVServer.implems,
                                progress=PFVServer.current_count,
                                iteration=PFVServer.total_exp) # TODO 0rtt
        else:
            
            if request.args.get('prot', '') and request.args.get('prot', '') in PFVServer.supported_protocols:
                PFVServer.current_protocol = request.args.get('prot', '')
                json_arg, prot_arg = PFVServer.get_args()
                PFVServer.app.logger.info("JSON ARG")
                for elem in json_arg:
                    PFVServer.app.logger.info(elem)
                PFVServer.app.logger.info("PROTOCOL ARG")
                for elem in prot_arg:
                    PFVServer.app.logger.info(elem)
                PFVServer.config           = PFVServer.setup_config(False, PFVServer.current_protocol)
                PFVServer.protocol_conf    = PFVServer.setup_protocol_parameters(PFVServer.current_protocol,PFVServer.dir_path,False)
                
            if PFVServer.implems_used is not None:
                ln = len(PFVServer.implems_used)
            else:
                ln = 0 
                            
            return render_template('index.html', 
                                json_arg=json_arg,
                                prot_arg=prot_arg,
                                enable_impems=PFVServer.enable_impems,
                                base_conf=PFVServer.config,
                                supported_protocols=PFVServer.supported_protocols,
                                current_protocol= PFVServer.current_protocol,
                                protocol_conf=PFVServer.protocol_conf,
                                tests=PFVServer.tests, 
                                nb_exp=PFVServer.total_exp_in_dir, 
                                implems=PFVServer.implems,
                                progress=PFVServer.current_count, #PFVServer.experiments.count_1,
                                iteration=PFVServer.total_exp)
            
    @app.route('/directory/<int:directory>/file/<path:file>')
    def send_file(directory,file):
        return send_from_directory(PFVServer.ivy_temps_path + str(directory), file)
    
    @app.route('/key/<string:implem>')
    def send_key(implem):
        return send_from_directory(PFVServer.key_path, implem)
    
    # TODO redo 
    @app.route('/results.html', methods = ['GET', 'POST'])
    def serve_results():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        PFVServer.app.logger.info(PFVServer.ivy_temps_path)
        PFVServer.app.logger.info(os.listdir(PFVServer.ivy_temps_path))
        PFVServer.total_exp_in_dir = len(os.listdir(PFVServer.ivy_temps_path)) - 3 #2
        
        
        default_page = 0
        page = request.args.get('page', default_page)
        try:
            page = page.number
        except:
            pass
        # Get queryset of items to paginate
        rge = range(PFVServer.total_exp_in_dir,0,-1)
        PFVServer.app.logger.info([i for i in rge])
        PFVServer.app.logger.info(page)
        items = [i for i in rge]

        # Paginate items
        items_per_page = 1
        paginator = Paginator(items, per_page=items_per_page)

        try:
            items_page = paginator.page(page)
        except PageNotAnInteger:
            items_page = paginator.page(default_page)
        except EmptyPage:
            items_page = paginator.page(paginator.num_pages)
            
        df_csv = pd.read_csv(PFVServer.ivy_temps_path + 'data.csv').set_index('Run')
        PFVServer.app.logger.info(PFVServer.total_exp_in_dir-int(page))
        
        result_row = df_csv.iloc[-1]
        output = "df_csv_row.html"
            # TODO change the label
        #result_row.to_frame().T
        #subdf = df_csv.drop("ErrorIEV", axis=1).drop("OutputFile", axis=1).drop("date", axis=1).drop("date", axis=1).drop("date", axis=1) #.reset_index()
        subdf = df_csv[['Implementation', 'NbPktSend',"packet_event","recv_packet"]]
        subdf.fillna(0,inplace=True)
        #subdf["isPass"] = subdf["isPass"].astype(int)
        subdf["NbPktSend"] = subdf["NbPktSend"].astype(int)
        #PFVServer.app.logger.info(subdf)
        #PFVServer.app.logger.info(df_csv.columns)
        #PFVServer.app.logger.info(subdf.columns)
        #subdf.columns = df_csv.columns
        configurationData = [
                {
                "id": str(uuid.uuid4()), # Must be unique TODO df_csv_scdg['filename']
                "name": "Experiences coverage view",
                "parameters": ["Run"], # "Implementation",
                "measurements": ["NbPktSend"], # , "Total number of blocks",'Number Syscall found' , 'Number Address found', 'Number of blocks visited', "Total number of blocks","time"
                "data": subdf.to_csv()
                },
                {
                "id": str(uuid.uuid4()), # Must be unique TODO df_csv_scdg['filename']
                "name": "Experiences packet view",
                "parameters": ["Run"], # "Implementation"
                "measurements": ["packet_event", "recv_packet"], # , "Total number of blocks",'Number Syscall found' , 'Number Address found', 'Number of blocks visited', "Total number of blocks","time"
                "data": subdf.to_csv() # index=False -> need index
                },
            ]

        export(configurationData, output)
        
        #PFVServer.app.logger.info(configurationData)
        
        with open(output, 'r') as f:
            df_csv_content = f.read()
            
        summary = {}
        summary["nb_pkt"] = result_row["NbPktSend"]
        summary["initial_version"] = result_row["initial_version"]
    
        PFVServer.current_exp_path = PFVServer.ivy_temps_path + str(PFVServer.total_exp_in_dir-int(page))
        PFVServer.local_exp_path = PFVServer.local_path + str(PFVServer.total_exp_in_dir-int(page))
        exp_dir = os.listdir(PFVServer.current_exp_path)
        ivy_stderr = "No output"
        ivy_stdout = "No output"
        implem_err = "No output" 
        implem_out = "No output"
        iev_out = "No output"
        qlog_file=""
        pcap_file=""
        for file in exp_dir:
            PFVServer.app.logger.info(file)
            if 'ivy_stderr.txt' in file:
                with open(PFVServer.current_exp_path + '/' + file, 'r') as f:
                    content = f.read()
                    if content == '':
                        pass
                    else:
                        ivy_stderr = content
            elif 'ivy_stdout.txt' in file:
                with open(PFVServer.current_exp_path + '/' + file, 'r') as f:
                    content = f.read()
                    if content == '':
                        pass
                    else:
                        ivy_stdout = content
            elif '.err' in file:
                with open(PFVServer.current_exp_path + '/' + file, 'r') as f:
                    content = f.read()
                    if content == '':
                        pass
                    else:
                        implem_err =content
            elif '.out' in file:
                with open(PFVServer.current_exp_path + '/' + file, 'r') as f:
                    content = f.read()
                    if content == '':
                        pass
                    else:
                        implem_out = content
            elif '.iev' in file:
                # TODO use csv file
                # file creation timestamp in float
                c_time = os.path.getctime(PFVServer.current_exp_path + '/' + file)
                # convert creation timestamp into DateTime object
                dt_c = datetime.datetime.fromtimestamp(c_time)
                PFVServer.app.logger.info('Created on:' +  str(dt_c))
                summary["date"] = dt_c
                test_name = file.replace('.iev', '')[0:-1]
                summary["test_name"] = test_name
                with open(PFVServer.current_exp_path + '/' + file, 'r') as f:
                    content = f.read()
                    summary["test_result"] = "Pass" if "test_completed" in content else "Fail"
                    
                try:
                    plantuml_file = PFVServer.current_exp_path + "/plantuml.puml"
                    generate_graph_input(PFVServer.current_exp_path + '/' + file, plantuml_file)
                    plantuml_obj = PlantUML(url="http://www.plantuml.com/plantuml/img/",  basic_auth={}, form_auth={}, http_opts={}, request_opts={})

                    plantuml_file_png = plantuml_file.replace('.puml', '.png') #"media/" + str(nb_exp) + "_plantuml.png"
                    plantuml_obj.processes_file(plantuml_file,  plantuml_file_png)
                    
                    with open(PFVServer.current_exp_path + '/' + file, 'r') as f:
                        content = f.read()
                        if content == '':
                            pass
                        else:
                            iev_out = content
                except:
                    pass
            elif '.pcap' in file:
                pcap_file = file
                # Now we need qlogs and pcap informations
                summary["implementation"] = file.split('_')[0] 
                summary["test_type"] = file.split('_')[2]
          
            elif ".qlog" in file:
                qlog_file = file
            
        # Get page number from request, 
        # default to first page
        try:
            binary_fc       = open(plantuml_file_png, 'rb').read()  # fc aka file_content
            base64_utf8_str = b64encode(binary_fc).decode('utf-8')

            ext     = plantuml_file_png.split('.')[-1]
        except:
            base64_utf8_str = ''
            ext = 'png'
        dataurl = f'data:image/{ext};base64,{base64_utf8_str}'
        PFVServer.app.logger.info(items_page)
        PFVServer.app.logger.info(paginator)
    
        
        return render_template('results.html', 
                           items_page=items_page,
                           nb_exp=PFVServer.total_exp_in_dir,
                           page=int(page),
                           current_exp=PFVServer.current_exp_path,
                           ivy_stderr=ivy_stderr,
                           ivy_stdout=ivy_stdout,
                           implem_err=implem_err,
                           implem_out=implem_out,
                           iev_out=iev_out,
                           plantuml_file_png=dataurl,
                           summary=summary, # "http://"+PFVServer.vizualiser_ip+":80/?file=http://"
                           pcap_frame_link="http://ivy-visualizer:80/?file=http://ivy-standalone:80/directory/" +  str(PFVServer.total_exp_in_dir-int(page)) + "/file/" + pcap_file + "&secrets=http://ivy-standalone:80/key/" + summary["implementation"] +'_key.log' if pcap_file != '' else None,
                           qlog_frame_link="http://ivy-visualizer:80/?file=http://ivy-standalone:80/directory/" +  str(PFVServer.total_exp_in_dir-int(page)) + "/file/" + qlog_file if qlog_file != '' else None,
                           df_csv_content=df_csv_content)

    # TODO redo
    @app.route('/results-global.html', methods = ['GET', 'POST'])
    def serve_results_global():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        PFVServer.total_exp_in_dir = len(os.listdir(PFVServer.ivy_temps_path)) - 2
        
        PFVServer.app.logger.info(request.form)
        
        summary = {}
        df_csv = pd.read_csv(PFVServer.ivy_temps_path + 'data.csv',parse_dates=['date'])
        
        df_simplify_date = df_csv
        df_simplify_date['date'] = df_csv['date'].dt.strftime('%d/%m/%Y')
        df_date_min_max = df_simplify_date['date'].agg(['min', 'max'])
        df_nb_date = df_simplify_date['date'].nunique()
        df_dates = df_simplify_date['date'].unique()
        PFVServer.app.logger.info(list(df_dates))
        PFVServer.app.logger.info(df_date_min_max)
        PFVServer.app.logger.info(df_nb_date)
        minimum_date = df_date_min_max["min"]
        maximum_date = df_date_min_max["max"]
                
        subdf = None
        #if len(request.form) >= 0:
        for key in request.form:
            if key == "date_range":
                minimum = df_dates[int(request.form.get("date_range").split(',')[0])]
                maximum = df_dates[int(request.form.get("date_range").split(',')[1])]
                if subdf is None:
                    subdf = df_csv.query('date >= @minimum and date <= @maximum')
                else:
                    subdf = subdf.query('date >= @minimum and date <= @maximum')
            elif key == "iter_range":
                minimum = request.form.get("iter_range").split(',')[0]
                maximum = request.form.get("iter_range").split(',')[1]
                if subdf is None: # TOODO
                    subdf = df_csv.loc[df_csv['Run'] >= int(minimum)]
                    subdf = subdf.loc[subdf['Run'] <= int(maximum)]
                else:
                    subdf = subdf.loc[subdf['Run'] >= int(minimum)]
                    subdf = subdf.loc[subdf['Run'] <= int(maximum)]
            elif key == "version":
                if request.form.get("version") != "all":
                    if subdf is None: # TOODO
                        subdf = df_csv.loc[df_csv['initial_version'] == request.form.get("version")]
                    else: 
                        subdf = subdf.loc[subdf['initial_version'] == request.form.get("version")]
            elif key == "ALPN":
                if request.form.get("ALPN") != "all":
                    if subdf is None: # TOODO
                        subdf = df_csv.loc[df_csv['Mode'] == request.form.get("test_type")]
                    else: 
                        subdf = subdf.loc[subdf['Mode'] == request.form.get("test_type")]
            elif key == "test_type":
                if request.form.get("test_type") != "all":
                    if subdf is None:
                        subdf = df_csv.loc[df_csv['Mode'] == request.form.get("test_type")]
                    else: 
                        subdf = subdf.loc[subdf['Mode'] == request.form.get("test_type")]
            elif key == "isPass":
                ispass = True if "True" in request.form.get("isPass") else False
                if request.form.get("isPass") != "all":
                    if subdf is None:
                        subdf = df_csv.loc[df_csv['isPass'] == ispass]
                    else: 
                        subdf = subdf.loc[subdf['isPass'] == ispass]
            elif key == "implem":
                for i in request.form.getlist("implem"):
                    PFVServer.app.logger.info(i)
                    if subdf is None:
                        subdf = df_csv.loc[df_csv['Implementation'] == i]
                    else: 
                        subdf = subdf.loc[subdf['Implementation'] == i]
            elif key == "server_test":
                for i in request.form.getlist("server_test"):
                    if subdf is None:
                        subdf = df_csv.loc[df_csv['TestName'] == i]
                    else: 
                        subdf = subdf.loc[subdf['TestName'] == i]
            elif key == "client_test":
                for i in request.form.getlist("client_test"):
                    if subdf is None:
                        subdf = df_csv.loc[df_csv['TestName'] == i]
                    else: 
                        subdf = subdf.loc[subdf['TestName'] == i]
        
        if subdf is not None:
            df_csv = subdf
            
        csv_text = df_csv.to_csv()
        
        
        output = "df_csv.html"
            # TODO change the label
        configurationData = [
                {
                "id": str(uuid.uuid4()), # Must be unique TODO df_csv_scdg['filename']
                "name": "Experiences coverage view",
                "parameters": ["Implementation", "Mode", "TestName"],
                "measurements": ["isPass","ErrorIEV","packet_event","packet_event_retry","packet_event_vn","packet_event_0rtt","packet_event_coal_0rtt", "recv_packet","recv_packet_retry","handshake_done","tls.finished","recv_packet_vn","recv_packet_0rtt","undecryptable_packet_event","version_not_found_event","date","initial_version","NbPktSend","version_not_found"], # , "Total number of blocks",'Number Syscall found' , 'Number Address found', 'Number of blocks visited', "Total number of blocks","time"
                "data": df_csv.to_csv(index=False)
                },
                {
                "id": str(uuid.uuid4()), # Must be unique TODO df_csv_scdg['filename']
                "name": "Experiences coverage view",
                "parameters": ["Implementation", "Mode", "TestName"],
                "measurements": ["isPass","ErrorIEV","packet_event","packet_event_retry","packet_event_vn","packet_event_0rtt","packet_event_coal_0rtt", "recv_packet","recv_packet_retry","handshake_done","tls.finished","recv_packet_vn","recv_packet_0rtt","undecryptable_packet_event","version_not_found_event","date","initial_version","NbPktSend","version_not_found"], # , "Total number of blocks",'Number Syscall found' , 'Number Address found', 'Number of blocks visited', "Total number of blocks","time"
                "data": df_csv.to_csv(index=False)
                },
                {
                "id": str(uuid.uuid4()), # Must be unique TODO df_csv_scdg['filename']
                "name": "Experiences coverage view",
                "parameters": ["Implementation", "Mode", "TestName"],
                "measurements": ["isPass","ErrorIEV","packet_event","packet_event_retry","packet_event_vn","packet_event_0rtt","packet_event_coal_0rtt", "recv_packet","recv_packet_retry","handshake_done","tls.finished","recv_packet_vn","recv_packet_0rtt","undecryptable_packet_event","version_not_found_event","date","initial_version","NbPktSend","version_not_found"], # , "Total number of blocks",'Number Syscall found' , 'Number Address found', 'Number of blocks visited', "Total number of blocks","time"
                "data": df_csv.to_csv(index=False)
                },
            ]
        # The above code is not valid Python code. It appears to be the beginning of a comment or
        # documentation string, but it is missing the closing characters.
        
        export(configurationData, output)
        
        #PFVServer.app.logger.info(configurationData)
        
        with open(output, 'r') as f:
            df_csv_content = f.read()
             
            
        return render_template('result-global.html', 
                           nb_exp=PFVServer.total_exp_in_dir,
                           current_exp=PFVServer.current_exp_path,
                           summary=summary,
                           csv_text=csv_text,
                           tests=PFVServer.tests, 
                           client_tests=PFVServer.client_tests,
                           implems=PFVServer.implems,
                           min_date=None,
                           max_date=None,
                           df_nb_date=df_nb_date,
                           df_dates=list(df_dates),
                           df_csv_content=df_csv_content)

    def get_attack_model(self, attack_model):
        """
        It returns the attack model
        :param attack_model: the attack model
        :return: the attack model
        """
        return attack_model
    
    @app.route('/kg/graph/json', methods = ['GET'])
    def get_json_graph():
        """
        It returns the json graph of the knowledge graph
        :return: the json graph of the knowledge graph
        """ 
        with open("/tmp/cytoscape_config.json", 'r') as json_file:
            data = json.load(json_file)
           
        response = PFVServer.app.response_class(
            response=json.dumps(data),
            status=200,
            mimetype='application/json'
        )
        return response
    
    # TODO redo
    @app.route('/creator.html', methods = ['GET', 'POST'])
    def serve_attack():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        # PFVServer.experiments.update_includes_ptls()
        # PFVServer.experiments.update_includes()
        setup_quic_model(PFVServer.ivy_test_path)
        setup_cytoscape()
        return render_template('creator.html')

    def run(self):
        PFVServer.app.run(host='0.0.0.0', port=80, use_reloader=True, threaded=True)  #, processes=4
        