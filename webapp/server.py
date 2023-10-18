#!/usr/bin/env python3.9
# -*- coding: utf-8 -*-


# TODO add logs
# TODO https://www.mongodb.com/docs/manual/core/geospatial-indexes/

from cgitb import html
import json
import os
import socket
import threading
import uuid
import requests
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
import datetime
from flask_cors import CORS
import pathlib
import pandas as pd
from npf_web_extension.app import export
import execnet

DEBUG = True

class IvyServer:
    ROOTPATH = os.getcwd()
    app = Flask(__name__, static_folder=ROOTPATH + '/webapp/static/')
    app.secret_key = 'super secret key' # TODO
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['APPLICATION_ROOT'] = ROOTPATH + '/webapp/templates/'
    app.debug = True
    
    # enable CORS
    CORS(app, resources={r'/*': {'origins': '*'}})
    
    
    def __init__(self,dir_path=None,experiments=None):
        IvyServer.dir_path = dir_path
        IvyServer.ivy_model_path = dir_path + "/QUIC-Ivy-Attacker/doc/examples/quic"
        IvyServer.ivy_test_path = dir_path  + "/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/"
        IvyServer.ivy_temps_path = dir_path + "/QUIC-Ivy-Attacker/doc/examples/quic/test/temp/"
        IvyServer.ivy_include_path = dir_path + "/QUIC-Ivy-Attacker/ivy/include/1.7/"
        IvyServer.local_path = os.environ["ROOT_PATH"] + "/QUIC-Ivy-Attacker/doc/examples/quic/test/temp/"
        IvyServer.key_path = SOURCE_DIR + "/tls-keys/"
        IvyServer.server_tests = []
        IvyServer.server_tests_checkbox = []
        for cate in TESTS_SERVER:
            for test in TESTS_SERVER[cate]:
                IvyServer.server_tests.append(test)
        IvyServer.client_tests = []
        IvyServer.client_tests_checkbox = []
        for cate in TESTS_CLIENT:
            for test in TESTS_CLIENT[cate]:
                IvyServer.client_tests.append(test)
                
        IvyServer.implems = []
        for i in IMPLEMENTATIONS.keys():
            IvyServer.implems.append(i)

        IvyServer.implem_tests_checkbox = []

        IvyServer.experiments = experiments
        IvyServer.nb_exp = len(os.listdir(IvyServer.ivy_temps_path)) - 2
        IvyServer.current_exp = IvyServer.ivy_temps_path + str(IvyServer.nb_exp)
        IvyServer.local_exp = IvyServer.local_path + str(IvyServer.nb_exp)
        
        IvyServer.x = None
        
        IvyServer.implems_used = None
        IvyServer.current_count = 0
        
        IvyServer.current_implem = None
        
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        IvyServer.local_ip = local_ip
        vizualiser_ip = socket.gethostbyname("ivy-visualizer")
        IvyServer.vizualiser_ip = vizualiser_ip


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
    
    @app.route('/progress', methods = ['GET', 'POST'])
    def progress():
        if IvyServer.implems_used is not None:
            from utils.constants import TESTS_CUSTOM
            res = requests.post('http://'+ IvyServer.current_implem+'-ivy:80/progress')
            IvyServer.app.logger.info(res.text)
            if res.text != "None":            
                if int(res.text) == IvyServer.experiments.args.iter:
                    if IvyServer.current_count + int(res.text) < len(TESTS_CUSTOM) * IvyServer.experiments.args.iter : # TODO some bugs
                        IvyServer.current_count += int(res.text)
                    else:
                        if len(IvyServer.implems_used) > 0:
                            IvyServer.current_implem = IvyServer.implems_used.pop()
                            IvyServer.experiments.args.implementations = [IvyServer.current_implem]
                            IvyServer.app.logger.info(IvyServer.experiments.args)
                            data = IvyServer.experiments.args.__dict__
                            data["tests"] = TESTS_CUSTOM
                            ress = requests.post('http://'+ IvyServer.current_implem+'-ivy:80/run-exp', json=data)
                            IvyServer.app.logger.info(res.text)
                            IvyServer.current_count += int(res.text)
                            
                        else:
                            IvyServer.current_count = 0
                            IvyServer.implems_used = None
                            IvyServer.current_implem = None
                            IvyServer.experiments.args.iter = 0
                            TESTS_CUSTOM = []
                return str(IvyServer.current_count+int(res.text))
            else: 
                return str(IvyServer.current_count)
        else:
            return "None"

    @app.route('/index.html', methods = ['GET', 'POST'])
    def serve_index():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        from utils.constants import TESTS_CUSTOM
        
        if request.method == 'POST':
            TESTS_CUSTOM = []
            IvyServer.app.logger.info(request.form)
            
            # if IvyServer.implems_used is not None:
            #     return render_template('index.html', 
            #                     server_tests=IvyServer.server_tests, 
            #                     client_tests=IvyServer.client_tests,
            #                     nb_exp=IvyServer.nb_exp, 
            #                     implems=IvyServer.implems,
            #                     progress=0,
            #                     iteration=int(IvyServer.experiments.args.iter) * (len(IvyServer.implems_used)+1) * len(TESTS_CUSTOM)) # TODO 0rtt
            
            for c in request.form: 
                for elem in request.form.getlist(c):
                    IvyServer.app.logger.info(elem)
            
            IvyServer.experiments.args.mode = "custom"
            IvyServer.experiments.args.initial_version = 1 if request.form["version"] == "rfc9000" else (29 if request.form["version"] == "draft29" else 28)
            IvyServer.experiments.args.alpn = request.form["ALPN"]
            IvyServer.experiments.args.vnet = True if request.form["net_mode"] == "vnet" else False
            IvyServer.experiments.args.shadow = True if request.form["net_mode"] == "shadow" else False
            IvyServer.experiments.args.iter = int(request.form["iteration"])
            IvyServer.experiments.args.internal_iteration = int(request.form["internal_iteration"])
            IvyServer.experiments.args.loss = float(request.form["loss"])/100
            IvyServer.experiments.args.jitter = int(request.form["Jitter"])
            IvyServer.experiments.args.latency = int(request.form["Latency"])
            IvyServer.experiments.args.timeout = int(request.form["timeout"])
            # TODO docker
            
            for elem in request.form.getlist("server_test"):
                TESTS_CUSTOM.append(elem)
            
            for elem in request.form.getlist("client_test"):
                TESTS_CUSTOM.append(elem)
            
            IvyServer.implems_used = request.form.getlist("implem")
            
            IvyServer.current_implem = IvyServer.implems_used.pop()
            IvyServer.experiments.args.implementations = [IvyServer.current_implem]
            IvyServer.app.logger.info(IvyServer.experiments.args)
            data = IvyServer.experiments.args.__dict__
            IvyServer.experiments.args.ivy_ui = True if "ivy_ui" in request.form.keys() else False
            data["tests"] = TESTS_CUSTOM
            res = requests.post('http://'+ IvyServer.current_implem+'-ivy:80/run-exp', json=data)
            IvyServer.app.logger.info(res.text)
        
            return render_template('index.html', 
                                server_tests=IvyServer.server_tests, 
                                client_tests=IvyServer.client_tests,
                                nb_exp=IvyServer.nb_exp, 
                                implems=IvyServer.implems,
                                progress=0,
                                iteration=int(IvyServer.experiments.args.iter) * (len(IvyServer.implems_used)+1) * len(TESTS_CUSTOM)) # TODO 0rtt
        else:
            if IvyServer.implems_used is not None:
                ln = len(IvyServer.implems_used)
            else:
                ln = 0 
                
            #IvyServer.app.logger.info("SWAG")
            
            return render_template('index.html', 
                                server_tests=IvyServer.server_tests, 
                                client_tests=IvyServer.client_tests,
                                nb_exp=IvyServer.nb_exp, 
                                implems=IvyServer.implems,
                                progress=IvyServer.experiments.count_1,
                                iteration=int(IvyServer.experiments.args.iter) * ln * len(TESTS_CUSTOM))
            
    
    @app.route('/directory/<int:directory>/file/<path:file>')
    def send_file(directory,file):
        return send_from_directory(IvyServer.ivy_temps_path + str(directory), file)
    
    @app.route('/key/<string:implem>')
    def send_key(implem):
        return send_from_directory(IvyServer.key_path, implem)
    
    @app.route('/results.html', methods = ['GET', 'POST'])
    def serve_results():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        IvyServer.app.logger.info(IvyServer.ivy_temps_path)
        IvyServer.app.logger.info(os.listdir(IvyServer.ivy_temps_path))
        IvyServer.nb_exp = len(os.listdir(IvyServer.ivy_temps_path)) - 3 #2
        
        
        default_page = 0
        page = request.args.get('page', default_page)
        try:
            page = page.number
        except:
            pass
        # Get queryset of items to paginate
        rge = range(IvyServer.nb_exp,0,-1)
        IvyServer.app.logger.info([i for i in rge])
        IvyServer.app.logger.info(page)
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
            
        df_csv = pd.read_csv(IvyServer.ivy_temps_path + 'data.csv').set_index('Run')
        IvyServer.app.logger.info(IvyServer.nb_exp-int(page))
        
        result_row = df_csv.iloc[-1]
        output = "df_csv_row.html"
            # TODO change the label
        #result_row.to_frame().T
        #subdf = df_csv.drop("ErrorIEV", axis=1).drop("OutputFile", axis=1).drop("date", axis=1).drop("date", axis=1).drop("date", axis=1) #.reset_index()
        subdf = df_csv[['Implementation', 'NbPktSend',"packet_event","recv_packet"]]
        subdf.fillna(0,inplace=True)
        #subdf["isPass"] = subdf["isPass"].astype(int)
        subdf["NbPktSend"] = subdf["NbPktSend"].astype(int)
        #IvyServer.app.logger.info(subdf)
        #IvyServer.app.logger.info(df_csv.columns)
        #IvyServer.app.logger.info(subdf.columns)
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
                # {
                # "id": str(uuid.uuid4()), # Must be unique TODO df_csv_scdg['filename']
                # "name": "Experiences coverage view",
                # "parameters": ["Implementation", "Mode", "TestName"],
                # "measurements": ["packet_event","packet_event_retry","packet_event_vn","packet_event_0rtt","packet_event_coal_0rtt", "recv_packet","recv_packet_retry","handshake_done","tls.finished","recv_packet_vn","recv_packet_0rtt","undecryptable_packet_event","version_not_found_event","date","initial_version","NbPktSend","version_not_found"], # , "Total number of blocks",'Number Syscall found' , 'Number Address found', 'Number of blocks visited', "Total number of blocks","time"
                # "data": subdf.to_csv(index=False)
                # },
            ]
        # configurationData = {
        #         "id": str(uuid.uuid4()), # Must be unique
        #         "name": "Quickstart example",
        #         "parameters": ["N", "algorithm", "num_cpus", "cpu_brand"],
        #         "measurements": ["efficiency"],
        #         "data": """algorithm,N,num_cpus,efficiency,cpu_brand
        #         Algorithm 1,10,1,0.75,Ryzen
        #         Algorithm 1,10,4,0.85,Ryzen
        #         Algorithm 1,10,8,0.90,Ryzen
        #         Algorithm 2,10,1,0.65,Ryzen
        #         Algorithm 2,10,4,0.80,Ryzen
        #         Algorithm 2,10,8,0.87,Ryzen
        #         """, # Raw data in csv format
        #     }
        export(configurationData, output)
        
        #IvyServer.app.logger.info(configurationData)
        
        with open(output, 'r') as f:
            df_csv_content = f.read()
            
        summary = {}
        summary["nb_pkt"] = result_row["NbPktSend"]
        summary["initial_version"] = result_row["initial_version"]
    
        IvyServer.current_exp = IvyServer.ivy_temps_path + str(IvyServer.nb_exp-int(page))
        IvyServer.local_exp = IvyServer.local_path + str(IvyServer.nb_exp-int(page))
        exp_dir = os.listdir(IvyServer.current_exp)
        ivy_stderr = "No output"
        ivy_stdout = "No output"
        implem_err = "No output" 
        implem_out = "No output"
        iev_out = "No output"
        qlog_file=""
        pcap_file=""
        for file in exp_dir:
            IvyServer.app.logger.info(file)
            if 'ivy_stderr.txt' in file:
                with open(IvyServer.current_exp + '/' + file, 'r') as f:
                    content = f.read()
                    if content == '':
                        pass
                    else:
                        ivy_stderr = content
            elif 'ivy_stdout.txt' in file:
                with open(IvyServer.current_exp + '/' + file, 'r') as f:
                    content = f.read()
                    if content == '':
                        pass
                    else:
                        ivy_stdout = content
            elif '.err' in file:
                with open(IvyServer.current_exp + '/' + file, 'r') as f:
                    content = f.read()
                    if content == '':
                        pass
                    else:
                        implem_err =content
            elif '.out' in file:
                with open(IvyServer.current_exp + '/' + file, 'r') as f:
                    content = f.read()
                    if content == '':
                        pass
                    else:
                        implem_out = content
            elif '.iev' in file:
                # TODO use csv file
                # file creation timestamp in float
                c_time = os.path.getctime(IvyServer.current_exp + '/' + file)
                # convert creation timestamp into DateTime object
                dt_c = datetime.datetime.fromtimestamp(c_time)
                IvyServer.app.logger.info('Created on:' +  str(dt_c))
                summary["date"] = dt_c
                test_name = file.replace('.iev', '')[0:-1]
                summary["test_name"] = test_name
                with open(IvyServer.current_exp + '/' + file, 'r') as f:
                    content = f.read()
                    summary["test_result"] = "Pass" if "test_completed" in content else "Fail"
                    
                try:
                    plantuml_file = IvyServer.current_exp + "/plantuml.puml"
                    generate_graph_input(IvyServer.current_exp + '/' + file, plantuml_file)
                    plantuml_obj = PlantUML(url="http://www.plantuml.com/plantuml/img/",  basic_auth={}, form_auth={}, http_opts={}, request_opts={})

                    plantuml_file_png = plantuml_file.replace('.puml', '.png') #"media/" + str(nb_exp) + "_plantuml.png"
                    plantuml_obj.processes_file(plantuml_file,  plantuml_file_png)
                    
                    with open(IvyServer.current_exp + '/' + file, 'r') as f:
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
        IvyServer.app.logger.info(items_page)
        IvyServer.app.logger.info(paginator)
    
        
        return render_template('results.html', 
                           items_page=items_page,
                           nb_exp=IvyServer.nb_exp,
                           page=int(page),
                           current_exp=IvyServer.current_exp,
                           ivy_stderr=ivy_stderr,
                           ivy_stdout=ivy_stdout,
                           implem_err=implem_err,
                           implem_out=implem_out,
                           iev_out=iev_out,
                           plantuml_file_png=dataurl,
                           summary=summary, # "http://"+IvyServer.vizualiser_ip+":80/?file=http://"
                           pcap_frame_link="http://ivy-visualizer:80/?file=http://ivy-standalone:80/directory/" +  str(IvyServer.nb_exp-int(page)) + "/file/" + pcap_file + "&secrets=http://ivy-standalone:80/key/" + summary["implementation"] +'_key.log' if pcap_file != '' else None,
                           qlog_frame_link="http://ivy-visualizer:80/?file=http://ivy-standalone:80/directory/" +  str(IvyServer.nb_exp-int(page)) + "/file/" + qlog_file if qlog_file != '' else None,
                           df_csv_content=df_csv_content)

    @app.route('/results-global.html', methods = ['GET', 'POST'])
    def serve_results_global():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        IvyServer.nb_exp = len(os.listdir(IvyServer.ivy_temps_path)) - 2
        
        IvyServer.app.logger.info(request.form)
        
        summary = {}
        df_csv = pd.read_csv(IvyServer.ivy_temps_path + 'data.csv',parse_dates=['date'])
        
        df_simplify_date = df_csv
        df_simplify_date['date'] = df_csv['date'].dt.strftime('%d/%m/%Y')
        df_date_min_max = df_simplify_date['date'].agg(['min', 'max'])
        df_nb_date = df_simplify_date['date'].nunique()
        df_dates = df_simplify_date['date'].unique()
        IvyServer.app.logger.info(list(df_dates))
        IvyServer.app.logger.info(df_date_min_max)
        IvyServer.app.logger.info(df_nb_date)
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
                    IvyServer.app.logger.info(i)
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
            # configurationData = {
                # "id": "1234567-1234567894567878241-12456", # Must be unique
                # "name": "Quickstart example",
                # "parameters": ["N", "algorithm", "num_cpus", "cpu_brand"],
                # "measurements": ["efficiency"],
                # "data": """algorithm,N,num_cpus,efficiency,cpu_brand
                # Algorithm 1,10,1,0.75,Ryzen
                # Algorithm 1,10,4,0.85,Ryzen
                # Algorithm 1,10,8,0.90,Ryzen
                # Algorithm 2,10,1,0.65,Ryzen
                # Algorithm 2,10,4,0.80,Ryzen
                # Algorithm 2,10,8,0.87,Ryzen
                # """, # Raw data in csv format
            # }
        # The above code is not valid Python code. It appears to be the beginning of a comment or
        # documentation string, but it is missing the closing characters.
        
        export(configurationData, output)
        
        #IvyServer.app.logger.info(configurationData)
        
        with open(output, 'r') as f:
            df_csv_content = f.read()
             
            
        return render_template('result-global.html', 
                           nb_exp=IvyServer.nb_exp,
                           current_exp=IvyServer.current_exp,
                           summary=summary,
                           csv_text=csv_text,
                           server_tests=IvyServer.server_tests, 
                           client_tests=IvyServer.client_tests,
                           implems=IvyServer.implems,
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
    
    def setup_cytoscape():
        output = []
        id = 1
        output.append({
            "data": {
                "displayName": "Environment",
                "label": "Environment",
                "long_info": "Environment",
                "actions": [], 
                "height": 0, 
                "cluster": "", 
                "shape": "", 
                "id": "Environment", 
                "obj": "", 
                "weight": 10,
                "width": 0, 
                "short_info": "Environment", 
                "events": [],
                "relations": None,
                "functions": None,
                "operationalState":"Working",
                "alarmSeverity":"critical",
                "kind":"TelcoCloudPhysicalDevice"
            }, 
            "classes": "nodeIcon", 
            "group": "nodes", 
            "locked": False, 
            "position": None
        })
        
        # TODO componentIcon
        
        output.append({
            "data": {
                "displayName": "ShimGroup",
                "label": "ShimGroup",
                "long_info": "ShimGroup",
                "actions": [], 
                "height": 0, 
                "weight": 9,
                "cluster": "", 
                "shape": "", 
                "id": "ShimGroup", 
                "obj": "", 
                "width": 0, 
                "short_info": "ShimGroup", 
                #"parent": "Environment",
                "events": [],
                "relations": None,
                "functions": None,
                "operationalState":"Working",
                "alarmSeverity":"critical",
            }, 
            "classes": "groupIcon", 
            "group": "nodes", 
            "locked": False, 
            "position": None
        })
        
        output.append({
            "data": {
                "displayName": "EntitiesGroup",
                "label": "EntitiesGroup",
                "long_info": "EntitiesGroup",
                "actions": [], 
                "height": 0, 
                "cluster": "", 
                "shape": "", 
                "weight": 8,
                "id": "EntitiesGroup", 
                "obj": "", 
                "width": 0, 
                "short_info": "EntitiesGroup", 
                #"parent": "ShimGroup",
                "events": [],
                "relations": None,
                "functions": None,
                "operationalState":"Working",
                "alarmSeverity":"critical",
            }, 
            "classes": "groupIcon", 
            "group": "nodes", 
            "locked": False, 
            "position": None
        })
        
        output.append({
            "data": {
                "displayName": "SecurityGroup",
                "label": "SecurityGroup",
                "long_info": "SecurityGroup",
                "actions": [], 
                "height": 0, 
                "cluster": "", 
                "shape": "", 
                "weight": 7,
                "id": "SecurityGroup", 
                "obj": "", 
                "width": 0, 
                "short_info": "SecurityGroup", 
                #"parent": "ShimGroup",
                "events": [],
                "relations": None,
                "functions": None,
                "operationalState":"Working",
                "alarmSeverity":"critical",
            }, 
            "classes": "groupIcon", 
            "group": "nodes", 
            "locked": False, 
            "position": None
        })
        
        
        output.append({
            "data": {
                "displayName": "ProtectionGroup",
                "label": "ProtectionGroup",
                "long_info": "ProtectionGroup",
                "actions": [], 
                "height": 0, 
                "cluster": "", 
                "weight": 6,
                "shape": "", 
                "id": "ProtectionGroup", 
                "obj": "", 
                "width": 0, 
                "short_info": "ProtectionGroup", 
                #"parent": "SecurityGroup",
                "events": [],
                "relations": None,
                "functions": None,
                "operationalState":"Working",
                "alarmSeverity":"critical",
            }, 
            "classes": "groupIcon", 
            "group": "nodes", 
            "locked": False, 
            "position": None
        })
        
        output.append({
            "data": {
                "displayName": "PacketGroup",
                "label": "PacketGroup",
                "long_info": "PacketGroup",
                "actions": [], 
                "height": 0, 
                "cluster": "", 
                "shape": "", 
                "id": "PacketGroup", 
                "obj": "", 
                "width": 0, 
                "weight": 5,
                "short_info": "PacketGroup", 
                #"parent": "ProtectionGroup",
                "events": [],
                "relations": None,
                "functions": None,
                "operationalState":"Working",
                "alarmSeverity":"critical",
            }, 
            "classes": "groupIcon", 
            "group": "nodes", 
            "locked": False, 
            "position": None
        })
        
        # Frame group already done after 
        
        components_ids = []
        
        edges = []
        
        # TODO add groups per network layers
        # TODO add edges between groups
        
        with open("/tmp/cytoscape_model.json", 'r') as input_file:
            with open("/tmp/cytoscape_config.json", 'w') as output_file:
                data = json.load(input_file)
                components_ids = data.keys()
                for component in data.keys():
                    if DEBUG: 
                        print("--------------------------")
                        print(component)
                    relations = []
                    functions = []
                    if len(component) > 1:
                        for elem in data[component]:
                            if "relations" in elem.keys():
                                relations.append(elem["relations"])
                            if "functions" in elem.keys():
                                functions.append(elem["functions"])
                    title = component.replace(".ivy", "").replace("quic_","").replace("ivy_","").replace("_", " ").title()
                    
                    obj_present = False
                    for elem in data[component]:
                        if component == "quic_shim.ivy":
                            if DEBUG:
                                print("SWAGGGGGGGGGGGGGGGGGGGGG")
                            
                        for key in elem.keys():
                            if "name" in key: 
                                obj_present = True
                               
                    #classes = "groupIcon" if obj_present else "nodeIcon"
                    classes = "groupIcon" if component == "quic_frame.ivy" else "nodeIcon"
                    
                    if "shim" in component:
                        if DEBUG:
                            print(classes)
                        parent = "ShimGroup"
                        weight = 2
                    elif component == "quic_frame.ivy":
                        #parent = "PacketGroup"
                        weight = 4
                        pass
                    elif component == "quic_transport_parameters.ivy":
                        parent = ""
                        weight = 2
                        pass
                    elif ("client" in component or "server" in component or "endpoint" in component or "attacker" in component or "victim" in component) and \
                        not "frame" in component:
                        parent = "EntitiesGroup"
                        weight = 2
                    elif "packet" in component:
                        parent = "PacketGroup"
                        weight = 2
                    elif "security" in component:
                        parent = "SecurityGroup"
                        weight = 2
                    elif "protection" in component:
                        parent = "ProtectionGroup"
                        weight = 2
                    else:
                        weight = 2
                        
                    output.append({
                        "data": {
                            "displayName": title,
                            "label": title,
                            "weight": weight,
                            "long_info": title,
                            "actions": [json.dumps({
                                "data": {
                                    "displayName": title,
                                    "label": title,
                                    "long_info": title,
                                    "actions": [], 
                                    "height": 0, 
                                    "cluster": "", 
                                    "shape": "", 
                                    "id": component, 
                                    "obj": "", 
                                    "width": 0, 
                                    "short_info": title, 
                                    "events": [],
                                    "parent": parent,
                                    "relations": relations,
                                    "functions": functions,
                                    "alarmSeverity":"major",
                                    "operationalState": "Working",
                                    "kind": "NetworkService" if classes == "nodeIcon" else "",
                                }, 
                                "classes": classes, 
                                "group": "nodes", 
                                "locked": False, 
                                "position": None
                            })], 
                            "height": 0, 
                            "cluster": "", 
                            "shape": "", 
                            "id": component, 
                            "obj": "", 
                            "width": 0, 
                            "short_info": title, 
                            "events": [],
                            "parent": parent,
                            "relations": relations,
                            "functions": functions,
                            "alarmSeverity":"major",
                            "operationalState": "Working",
                            "kind": "NetworkService" if classes == "nodeIcon" else "",
                        }, 
                        "classes": classes, 
                        "group": "nodes", 
                        "locked": False, 
                        "position": None
                    })
                    
                    for elem in data[component]:
                        if DEBUG: 
                            print("°°°°°°°°°°°°°°°°°°°")
                            print(elem)
                        is_obj = False
                        for key in elem.keys():  
                            if DEBUG:
                                print(key)
                            if "name" in key:
                                if DEBUG: 
                                    print("**** IN ****")
                                is_obj = True
                                title = key.replace("_name", "").replace("_", " ").title()
                                parent = ""
                                for output_elem in output: # TODO
                                    if output_elem["data"]["label"] in title:
                                        parent = output_elem["data"]["id"]
                                        break
                                if "shim" in component:
                                    if DEBUG:
                                        print(classes)
                                    parent = "ShimGroup"
                                elif component == "quic_frame.ivy":
                                    #parent = "PacketGroup"
                                    pass
                                elif component == "quic_transport_parameters.ivy":
                                    parent = ""
                                    pass
                                elif ("client" in component or "server" in component or "endpoint" in component or "attacker" in component or "victim" in component) and \
                                    not "frame" in component:
                                    parent = "EntitiesGroup"
                                elif "packet" in component:
                                    parent = "PacketGroup"
                                elif "security" in component:
                                    parent = "SecurityGroup"
                                elif "protection" in component:
                                    parent = "ProtectionGroup"
                                if DEBUG: 
                                    print(type(elem))
                                    print(type(elem["actions"]))
                                edges_actions = []
                                if isinstance(elem["actions"],list):
                                    for action in elem["actions"]:
                                        for instr in action["monitor"]["around"]:
                                            if instr["file"] in components_ids:
                                                if action["action_name"]+instr["file"] not in edges_actions:
                                                    if "." in action["action_name"]:
                                                        if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame -> not always, e.g tls_api
                                                            source_id = action["action_name"].split(".")[1]
                                                        else:
                                                            source_id = action["action_name"].split(".")[0]
                                                    else:
                                                        source_id = component
                                                    edges.append({
                                                        "data": {
                                                            "source_obj": component, 
                                                            "target_obj": instr["file"], 
                                                            "long_info": [
                                                                action["action_name"], 
                                                            ], 
                                                            "approxpoints": None, 
                                                            "actions": [], 
                                                            "bspline": None, 
                                                            "id": action["action_name"]+component+instr["file"], 
                                                            "arrowend":None, 
                                                            "transitive": True, 
                                                            "obj": "", 
                                                            "target": instr["file"], 
                                                            "label": action["action_name"], 
                                                            "source": source_id, 
                                                            "short_info": instr["file"], 
                                                            "events": []
                                                        }, 
                                                        "classes": "around", # TODO change type of edge
                                                        "group": "edges"
                                                    })
                                                    
                                                    edges_actions.append(action["action_name"]+instr["file"])
                                              
                                        for instr in action["monitor"]["after"]:
                                            if instr["file"] in components_ids:
                                                if action["action_name"]+instr["file"] not in edges_actions:
                                                    if "." in action["action_name"]:
                                                        if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                            source_id = action["action_name"].split(".")[1]
                                                        else:
                                                            source_id = action["action_name"].split(".")[0]
                                                    else:
                                                        source_id = component
                                                    edges.append({
                                                        "data": {
                                                            "source_obj": component, 
                                                            "target_obj": instr["file"], 
                                                            "long_info": [
                                                                action["action_name"]
                                                            ], 
                                                            "approxpoints": None, 
                                                            "actions": [], 
                                                            "bspline": None, 
                                                            "id": action["action_name"]+component+instr["file"], 
                                                            "arrowend":None, 
                                                            "transitive": True, 
                                                            "obj": "", 
                                                            "target": instr["file"], 
                                                            "label": action["action_name"], 
                                                            "source": source_id, 
                                                            "short_info": instr["file"], 
                                                            "events": []
                                                        }, 
                                                        "classes": "after",  # TODO change type of edge
                                                        "group": "edges"
                                                    })
                                                    edges_actions.append(action["action_name"]+instr["file"])
                                              
                                        for instr in action["monitor"]["before"]:
                                            if instr["file"] in components_ids:
                                                if action["action_name"]+instr["file"] not in edges_actions:
                                                    if "." in action["action_name"]:
                                                        if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                            source_id = action["action_name"].split(".")[1]
                                                        else:
                                                            source_id = action["action_name"].split(".")[0]
                                                    else:
                                                        source_id = component
                                                    edges.append({
                                                        "data": {
                                                            "source_obj": component, 
                                                            "target_obj": instr["file"], 
                                                            "long_info": [
                                                                action["action_name"]
                                                            ], 
                                                            "approxpoints": None, 
                                                            "actions": [], 
                                                            "bspline": None, 
                                                            "id": action["action_name"]+component+instr["file"], 
                                                            "arrowend":None, 
                                                            "transitive": True, 
                                                            "obj": "", 
                                                            "target": instr["file"], 
                                                            "label": action["action_name"], 
                                                            "source": source_id, 
                                                            "short_info": instr["file"], 
                                                            "events": []
                                                        }, 
                                                        "classes": "before",  # TODO change type of edge
                                                        "group": "edges"
                                                    })
                                                    edges_actions.append(action["action_name"]+instr["file"])
                                              
                                        for instr in action["implementation"]:
                                            if instr["file"] in components_ids:
                                                if action["action_name"]+instr["file"] not in edges_actions:
                                                    if "." in action["action_name"]:
                                                        if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                            source_id = action["action_name"].split(".")[1]
                                                        else:
                                                            source_id = action["action_name"].split(".")[0]
                                                    else:
                                                        source_id = component
                                                    edges.append({
                                                        "data": {
                                                            "source_obj": component, 
                                                            "target_obj": instr["file"], 
                                                            "long_info": [
                                                                action["action_name"]
                                                            ], 
                                                            "approxpoints": None, 
                                                            "actions": [], 
                                                            "bspline": None, 
                                                            "id": action["action_name"]+component+instr["file"], 
                                                            "arrowend":None, 
                                                            "transitive": True, 
                                                            "obj": "", 
                                                            "target": instr["file"], 
                                                            "label": action["action_name"], 
                                                            "source": source_id, 
                                                            "short_info": instr["file"], 
                                                            "events": []
                                                        }, 
                                                        "classes": "implementation",  # TODO change type of edge
                                                        "group": "edges"
                                                    })
                                                    edges_actions.append(action["action_name"]+instr["file"])
                                        
                                        if "assertions_as_guarantees" in action.keys():
                                            for instr in action["assertions_as_guarantees"]["assertions"]: # TODO
                                                if instr["file"] in components_ids:
                                                    if action["action_name"]+instr["file"] not in edges_actions:
                                                        if "." in action["action_name"]:
                                                            if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                                source_id = action["action_name"].split(".")[1]
                                                            else:
                                                                source_id = action["action_name"].split(".")[0]
                                                        else:
                                                            source_id = component
                                                        edges.append({
                                                        "data": {
                                                            "source_obj": component, 
                                                            "target_obj": instr["file"], 
                                                            "long_info": [
                                                                instr["assertion"]
                                                            ], 
                                                            "approxpoints": None, 
                                                            "actions": [], 
                                                            "bspline": None, 
                                                            "id": instr["assertion"]+component+instr["file"], 
                                                            "arrowend":None, 
                                                            "transitive": True, 
                                                            "obj": "", 
                                                            "target": instr["file"], 
                                                            "label": instr["assertion"], 
                                                            "source": source_id, # TODO change with key
                                                            "short_info": instr["file"], 
                                                            "events": []
                                                        }, 
                                                        "classes": "assertions", 
                                                        "group": "edges"
                                                    })
                                                    edges_actions.append(action["action_name"]+instr["file"])
                                            for instr in action["assertions_as_guarantees"]["called_from"]: # TODO
                                                if instr["component"] in components_ids:
                                                    if action["action_name"]+instr["component"] not in edges_actions:
                                                        if "." in action["action_name"]:
                                                            if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                                source_id = action["action_name"].split(".")[1]
                                                            else:
                                                                source_id = action["action_name"].split(".")[0]
                                                        else:
                                                            source_id = component
                                                        edges.append({
                                                        "data": {
                                                            "source_obj": component, 
                                                            "target_obj": instr["component"], 
                                                            "long_info": [
                                                                instr["caller_func"]
                                                            ], 
                                                            "approxpoints": None, 
                                                            "actions": [], 
                                                            "bspline": None, 
                                                            "id": instr["caller_func"]+component+instr["component"], 
                                                            "arrowend":None, 
                                                            "transitive": True, 
                                                            "obj": "", 
                                                            "target": instr["component"], 
                                                            "label": instr["caller_func"], 
                                                            "source": source_id, 
                                                            "short_info": instr["component"], 
                                                            "events": []
                                                        }, 
                                                        "classes": "call", 
                                                        "group": "edges"
                                                    })
                                                    edges_actions.append(action["action_name"]+instr["component"])
                                         
                                        if "called_from" in action.keys():
                                            for instr in action["called_from"]: # TODO
                                                if instr["component"] in components_ids:
                                                    if action["action_name"]+instr["component"] not in edges_actions:
                                                        if "." in action["action_name"]:
                                                            if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                                source_id = action["action_name"].split(".")[1]
                                                            else:
                                                                source_id = action["action_name"].split(".")[0]
                                                        else:
                                                            source_id = component
                                                        edges.append({
                                                        "data": {
                                                            "source_obj": component, 
                                                            "target_obj": instr["component"], 
                                                            "long_info": [
                                                                instr["caller_func"]
                                                            ], 
                                                            "approxpoints": None, 
                                                            "actions": [], 
                                                            "bspline": None, 
                                                            "id": instr["caller_func"]+component+instr["component"], 
                                                            "arrowend":None, 
                                                            "transitive": True, 
                                                            "obj": "", 
                                                            "target": instr["component"], 
                                                            "label": instr["caller_func"], 
                                                            "source": source_id, 
                                                            "short_info": instr["component"], 
                                                            "events": []
                                                        }, 
                                                        "classes": "call", 
                                                        "group": "edges"
                                                    })
                                                    edges_actions.append(instr["caller_func"]+instr["component"])
                                                    
                                        if "assertions_as_assumption" in action.keys():
                                            for instr in action["assertions_as_assumption"]["assertions"]: # TODO
                                                if instr["file"] in components_ids:
                                                    if action["action_name"]+instr["file"] not in edges_actions:
                                                        if "." in action["action_name"]:
                                                            if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                                source_id = action["action_name"].split(".")[1]
                                                            else:
                                                                source_id = action["action_name"].split(".")[0]
                                                        else:
                                                            source_id = component
                                                        edges.append({
                                                        "data": {
                                                            "source_obj": component, 
                                                            "target_obj": instr["file"], 
                                                            "long_info": [
                                                                instr["assertion"]
                                                            ], 
                                                            "approxpoints": None, 
                                                            "actions": [], 
                                                            "bspline": None, 
                                                            "id": instr["assertion"]+component+instr["file"], 
                                                            "arrowend":None, 
                                                            "transitive": True, 
                                                            "obj": "", 
                                                            "target": instr["file"], 
                                                            "label": instr["assertion"], 
                                                            "source": source_id, #action["action_name"]+component, 
                                                            "short_info": instr["file"], 
                                                            "events": []
                                                        }, 
                                                        "classes": "assertions", 
                                                        "group": "edges"
                                                    })
                                                    edges_actions.append(action["action_name"]+instr["file"])
                                            for instr in action["assertions_as_assumption"]["called_from"]: # TODO
                                                if instr["component"] in components_ids:
                                                    if action["action_name"]+instr["component"] not in edges_actions:
                                                        if "." in action["action_name"]:
                                                            if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                                source_id = action["action_name"].split(".")[1]
                                                            else:
                                                                source_id = action["action_name"].split(".")[0]
                                                        else:
                                                            source_id = component
                                                        edges.append({
                                                        "data": {
                                                            "source_obj": component, 
                                                            "target_obj": instr["component"], 
                                                            "long_info": [
                                                                instr["caller_func"]
                                                            ], 
                                                            "approxpoints": None, 
                                                            "actions": [], 
                                                            "bspline": None, 
                                                            "id": instr["caller_func"]+component+instr["component"], 
                                                            "arrowend":None, 
                                                            "transitive": True, 
                                                            "obj": "", 
                                                            "target": instr["component"], 
                                                            "label": instr["caller_func"], 
                                                            "source": source_id, 
                                                            "short_info": instr["component"], 
                                                            "events": []
                                                        }, 
                                                        "classes": "edge_unknown", 
                                                        "group": "edges"
                                                    })
                                                    edges_actions.append(action["action_name"]+instr["component"])
                                        
                                    operationalState = "Working"
                                    # pass
                                    # operationalState = "Working" if elem["actions"]["exported"] else "notWorking"
                                    # kind = "VNF" if ("frame" in title.lower() or "packet" in title.lower()) else ("server" if ("client" in title.lower() or "server" in title.lower())  else "NetworkService")
                                elif isinstance(elem,list):
                                    operationalState = "Working"
                                    # pass
                                else:
                                    operationalState = "Working" if elem["actions"]["exported"] else "notWorking"
                                kind = "VNF" if ("frame" in title.lower() or "packet" in title.lower()) else ("server" if ("client" in title.lower() or "server" in title.lower() or "attacker" in title.lower())  else "NetworkService")
                                output.append({
                                    "data": {
                                        "displayName": title,
                                        "label": title,
                                        "weight": 1,
                                        "long_info": title + "\n" + component,
                                        "actions": [
                                            json.dumps({
                                            "data": {
                                                "displayName": title,
                                                "label": title,
                                                "long_info": title + "\n" + component,
                                                "actions": [
                                                ], 
                                                "height": 0, 
                                                "cluster": "", 
                                                "shape": "", 
                                                "id": key.replace("_name","").replace("frame_","").replace("_ep",""), #"n" + str(id), 
                                                "obj": "", 
                                                "width": 0, 
                                                "short_info": title, 
                                                "events": [],
                                                "parent": parent,
                                                "operationalState": operationalState,
                                                "kind": kind,
                                                "alarmSeverity":"cleared",
                                                # "relations": component[-1]["relations"],
                                                # "functions": component[-1]["functions"]
                                            }, 
                                            "classes": "nodeIcon", 
                                            "group": "nodes", 
                                            "locked": False, 
                                            "position": None
                                        })], 
                                        "height": 0, 
                                        "cluster": "", 
                                        "shape": "", 
                                        "id": key.replace("_name","").replace("frame_","").replace("_ep",""), #"n" + str(id), 
                                        "obj": "", 
                                        "width": 0, 
                                        "short_info": title, 
                                        "events": [],
                                        "parent": parent,
                                        "operationalState": operationalState,
                                        "kind": kind,
                                        "alarmSeverity":"cleared",
                                        # "relations": component[-1]["relations"],
                                        # "functions": component[-1]["functions"]
                                    }, 
                                    "classes": "nodeIcon", 
                                    "group": "nodes", 
                                    "locked": False, 
                                    "position": None
                                })
                                id += 1
                            
                            elif "actions" in key and not is_obj:
                                edges_actions = []
                                action = elem["actions"]
                                if DEBUG:
                                    print(action)
                                if "monitor" in action.keys():
                                    for instr in action["monitor"]["around"]:
                                        if instr["file"] in components_ids:
                                            if action["action_name"]+instr["file"] not in edges_actions:
                                                if "." in action["action_name"]:
                                                    if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                        source_id = action["action_name"].split(".")[1]
                                                    else:
                                                        source_id = action["action_name"].split(".")[0]
                                                else:
                                                    source_id = component
                                                edges.append({
                                                    "data": {
                                                        "source_obj": component, 
                                                        "target_obj": instr["file"], 
                                                        "long_info": [
                                                            action["action_name"], 
                                                        ], 
                                                        "approxpoints": None, 
                                                        "actions": [], 
                                                        "bspline": None, 
                                                        "id": action["action_name"]+component+instr["file"], 
                                                        "arrowend":None, 
                                                        "transitive": True, 
                                                        "obj": "", 
                                                        "target": instr["file"], 
                                                        "label": action["action_name"], 
                                                        "source": source_id, 
                                                        "short_info": instr["file"], 
                                                        "events": []
                                                    }, 
                                                    "classes": "around", # TODO change type of edge
                                                    "group": "edges"
                                                })
                                                edges_actions.append(action["action_name"]+instr["file"])
                                                
                                    for instr in action["monitor"]["after"]:
                                        if instr["file"] in components_ids:
                                            if action["action_name"]+instr["file"] not in edges_actions:
                                                if "." in action["action_name"]:
                                                    if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                        source_id = action["action_name"].split(".")[1]
                                                    else:
                                                        source_id = action["action_name"].split(".")[0]
                                                else:
                                                    source_id = component
                                                edges.append({
                                                    "data": {
                                                        "source_obj": component, 
                                                        "target_obj": instr["file"], 
                                                        "long_info": [
                                                            action["action_name"]
                                                        ], 
                                                        "approxpoints": None, 
                                                        "actions": [], 
                                                        "bspline": None, 
                                                        "id": action["action_name"]+component+instr["file"], 
                                                        "arrowend":None, 
                                                        "transitive": True, 
                                                        "obj": "", 
                                                        "target": instr["file"], 
                                                        "label": action["action_name"], 
                                                        "source": source_id, 
                                                        "short_info": instr["file"], 
                                                        "events": []
                                                    }, 
                                                    "classes": "after",  # TODO change type of edge
                                                    "group": "edges"
                                                })
                                                edges_actions.append(action["action_name"]+instr["file"])
                                                
                                    for instr in action["monitor"]["before"]:
                                        if instr["file"] in components_ids:
                                            if action["action_name"]+instr["file"] not in edges_actions:
                                                if "." in action["action_name"]:
                                                    if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                        source_id = action["action_name"].split(".")[1]
                                                    else:
                                                        source_id = action["action_name"].split(".")[0]
                                                else:
                                                    source_id = component
                                                edges.append({
                                                    "data": {
                                                        "source_obj": component, 
                                                        "target_obj": instr["file"], 
                                                        "long_info": [
                                                            action["action_name"]
                                                        ], 
                                                        "approxpoints": None, 
                                                        "actions": [], 
                                                        "bspline": None, 
                                                        "id": action["action_name"]+component+instr["file"], 
                                                        "arrowend":None, 
                                                        "transitive": True, 
                                                        "obj": "", 
                                                        "target": instr["file"], 
                                                        "label": action["action_name"], 
                                                        "source": source_id, 
                                                        "short_info": instr["file"], 
                                                        "events": []
                                                    }, 
                                                    "classes": "before",  # TODO change type of edge
                                                    "group": "edges"
                                                })
                                                edges_actions.append(action["action_name"]+instr["file"])
                                                
                                if "implementation" in action.keys():
                                    for instr in action["implementation"]:
                                        if instr["file"] in components_ids:
                                            if action["action_name"]+instr["file"] not in edges_actions:
                                                if "." in action["action_name"]:
                                                    if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                        source_id = action["action_name"].split(".")[1]
                                                    else:
                                                        source_id = action["action_name"].split(".")[0]
                                                else:
                                                    source_id = component
                                                edges.append({
                                                    "data": {
                                                        "source_obj": component, 
                                                        "target_obj": instr["file"], 
                                                        "long_info": [
                                                            action["action_name"]
                                                        ], 
                                                        "approxpoints": None, 
                                                        "actions": [], 
                                                        "bspline": None, 
                                                        "id": action["action_name"]+component+instr["file"], 
                                                        "arrowend":None, 
                                                        "transitive": True, 
                                                        "obj": "", 
                                                        "target": instr["file"], 
                                                        "label": action["action_name"], 
                                                        "source": source_id, 
                                                        "short_info": instr["file"], 
                                                        "events": []
                                                    }, 
                                                    "classes": "implementation", 
                                                    "group": "edges"
                                                })
                                                edges_actions.append(action["action_name"]+instr["file"])
                                    
                                if "assertions_as_guarantees" in action.keys():
                                    for instr in action["assertions_as_guarantees"]["assertions"]: # TODO
                                        if instr["file"] in components_ids:
                                            if action["action_name"]+instr["file"] not in edges_actions:
                                                if "." in action["action_name"]:
                                                    if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                        source_id = action["action_name"].split(".")[1]
                                                    else:
                                                        source_id = action["action_name"].split(".")[0]
                                                else:
                                                    source_id = component
                                                edges.append({
                                                    "data": {
                                                    "source_obj": component, 
                                                    "target_obj": instr["file"], 
                                                    "long_info": [
                                                        instr["assertion"]
                                                    ], 
                                                    "approxpoints": None, 
                                                    "actions": [], 
                                                    "bspline": None, 
                                                    "id": instr["assertion"]+component+instr["file"], 
                                                    "arrowend":None, 
                                                    "transitive": True, 
                                                    "obj": "", 
                                                    "target": instr["file"], 
                                                    "label": instr["assertion"], 
                                                    "source": source_id, # TODO change with key
                                                    "short_info": instr["file"], 
                                                    "events": []
                                                }, 
                                                "classes": "assertions", 
                                                "group": "edges"
                                            })
                                            edges_actions.append(action["action_name"]+instr["file"])
                                            
                                    for instr in action["assertions_as_guarantees"]["called_from"]: # TODO
                                        if instr["component"] in components_ids:
                                            if action["action_name"]+instr["component"] not in edges_actions:
                                                if "." in action["action_name"]:
                                                    if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                        source_id = action["action_name"].split(".")[1]
                                                    else:
                                                        source_id = action["action_name"].split(".")[0]
                                                else:
                                                    source_id = component
                                                edges.append({
                                                    "data": {
                                                    "source_obj": component, 
                                                    "target_obj": instr["component"], 
                                                    "long_info": [
                                                        instr["caller_func"]
                                                    ], 
                                                    "approxpoints": None, 
                                                    "actions": [], 
                                                    "bspline": None, 
                                                    "id": instr["caller_func"]+component+instr["component"], 
                                                    "arrowend":None, 
                                                    "transitive": True, 
                                                    "obj": "", 
                                                    "target": instr["component"], 
                                                    "label": instr["caller_func"], 
                                                    "source": source_id, 
                                                    "short_info": instr["component"], 
                                                    "events": []
                                                }, 
                                                "classes": "call", 
                                                "group": "edges"
                                            })
                                            edges_actions.append(action["action_name"]+instr["component"])
                                
                                if "called_from" in action.keys():
                                    for instr in action["called_from"]: # TODO
                                        if instr["component"] in components_ids:
                                            if action["action_name"]+instr["component"] not in edges_actions:
                                                if "." in action["action_name"]:
                                                    if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                        source_id = action["action_name"].split(".")[1]
                                                    else:
                                                        source_id = action["action_name"].split(".")[0]
                                                else:
                                                    source_id = component
                                                edges.append({
                                                "data": {
                                                    "source_obj": component, 
                                                    "target_obj": instr["component"], 
                                                    "long_info": [
                                                        instr["caller_func"]
                                                    ], 
                                                    "approxpoints": None, 
                                                    "actions": [], 
                                                    "bspline": None, 
                                                    "id": instr["caller_func"]+component+instr["component"], 
                                                    "arrowend":None, 
                                                    "transitive": True, 
                                                    "obj": "", 
                                                    "target": instr["component"], 
                                                    "label": instr["caller_func"], 
                                                    "source": source_id, 
                                                    "short_info": instr["component"], 
                                                    "events": []
                                                }, 
                                                "classes": "call", 
                                                "group": "edges"
                                            })
                                            edges_actions.append(action["action_name"]+instr["component"])
                                                    
                                if "assertions_as_assumption" in action.keys():
                                    for instr in action["assertions_as_assumption"]["assertions"]: # TODO
                                        if instr["file"] in components_ids:
                                            if action["action_name"]+instr["file"] not in edges_actions:
                                                if "." in action["action_name"]:
                                                    if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                        source_id = action["action_name"].split(".")[1]
                                                    else:
                                                        source_id = action["action_name"].split(".")[0]
                                                else:
                                                    source_id = component
                                                edges.append({
                                                    "data": {
                                                        "source_obj": component, 
                                                        "target_obj": instr["file"], 
                                                        "long_info": [
                                                            instr["assertion"]
                                                        ], 
                                                        "approxpoints": None, 
                                                        "actions": [], 
                                                        "bspline": None, 
                                                        "id": instr["assertion"]+component+instr["file"], 
                                                        "arrowend":None, 
                                                        "transitive": True, 
                                                        "obj": "", 
                                                        "target": instr["file"], 
                                                        "label": instr["assertion"], 
                                                        "source": source_id,  # action["action_name"]+
                                                        "short_info": instr["file"], 
                                                        "events": []
                                                        }, 
                                                        "classes": "assertion", 
                                                        "group": "edges"
                                                    })
                                                edges_actions.append(action["action_name"]+instr["file"])
                                                    
                                    for instr in action["assertions_as_assumption"]["called_from"]: # TODO
                                        if instr["component"] in components_ids:
                                            if action["action_name"]+instr["component"] not in edges_actions:
                                                if "." in action["action_name"]:
                                                    if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                                        source_id = action["action_name"].split(".")[1]
                                                    else:
                                                        source_id = action["action_name"].split(".")[0]
                                                else:
                                                    source_id = component
                                                edges.append({
                                                        "data": {
                                                        "source_obj": component, 
                                                        "target_obj": instr["component"], 
                                                        "long_info": [
                                                            instr["caller_func"]
                                                        ], 
                                                        "approxpoints": None, 
                                                        "actions": [], 
                                                        "bspline": None, 
                                                        "id": instr["caller_func"]+component+instr["component"], 
                                                        "arrowend":None, 
                                                        "transitive": True, 
                                                        "obj": "", 
                                                        "target": instr["component"], 
                                                        "label": instr["caller_func"], 
                                                        "source": source_id, 
                                                        "short_info": instr["component"], 
                                                        "events": []
                                                    }, 
                                                    "classes": "call", 
                                                    "group": "edges"
                                                })
                                                edges_actions.append(action["action_name"]+instr["component"])
                            
                            elif "quic_transport_parameters.ivy" in component:
                                output.append({
                                    "data": {
                                        "displayName": key.replace("_", " ").title(),
                                        "label": key.replace("_", " ").title(),
                                        "long_info": key.replace("_", " ").title(),
                                        "actions": [], 
                                        "height": 0, 
                                        "cluster": "", 
                                        "shape": "", 
                                        "id": key, 
                                        "obj": "", 
                                        "width": 0, 
                                        "short_info": title, 
                                        "events": [],
                                        "weight": 1,
                                        "parent":"quic_transport_parameters.ivy",
                                        "relations": None,
                                        "functions": None,
                                        "alarmSeverity":"major",
                                        "operationalState": "Working",
                                        "kind": "NetworkService", # TODO
                                    }, 
                                    "classes": "nodeIcon", 
                                    "group": "nodes", 
                                    "locked": False, 
                                    "position": None
                                })
                                # if "." in action["action_name"]:
                                #     if action["action_name"].count(".") == 2 and "frame" in action["action_name"]: # frame 
                                #         source_id = action["action_name"].split(".")[1]
                                #     else:
                                #         source_id = action["action_name"].split(".")[0]
                                # else:
                                #     source_id = component
                                edges.append({ # TODO
                                    "data": {
                                        "source_obj": key, 
                                        "target_obj": "quic_transport_parameters.ivy", 
                                        "long_info": [
                                            key
                                        ], 
                                        "approxpoints": None, 
                                        "actions": [], 
                                        "bspline": None, 
                                        "id": key, 
                                        "arrowend":None, 
                                        "transitive": True, 
                                        "obj": "", 
                                        "target": "quic_transport_parameters.ivy", 
                                        "label": key.replace("_", " ").title(), 
                                        "source": key, 
                                        "short_info":key.replace("_", " ").title(),
                                        "events": []
                                    }, 
                                    "classes": "implementation", 
                                    "group": "edges"
                                })
                                               
                            else:
                                if DEBUG:
                                    print(key)
                    id += 1
                    
                edges.append({
                    "data": {
                            "source_obj": "net", 
                            "target_obj": "Environment", 
                            "long_info": [
                               
                            ], 
                            "approxpoints": None, 
                            "actions": [], 
                            "bspline": None, 
                            "id": "netEnvironment", 
                            "arrowend":None, 
                            "transitive": True, 
                            "obj": "", 
                            "target": "Environment", 
                            "label": "", 
                            "source": "net", 
                            "short_info": "", 
                            "events": []
                        }, 
                        "classes": "comp", # TODO change type of edge
                        "group": "edges"
                    })
                
                edges.append({
                    "data": {
                            "source_obj": "ShimGroup", 
                            "target_obj": "Environment", 
                            "long_info": [
                               
                            ], 
                            "approxpoints": None, 
                            "actions": [], 
                            "bspline": None, 
                            "id": "ShimGroupEnvironment", 
                            "arrowend":None, 
                            "transitive": True, 
                            "obj": "", 
                            "target": "Environment", 
                            "label": "", 
                            "source": "ShimGroup", 
                            "short_info": "", 
                            "events": []
                        }, 
                        "classes": "comp", # TODO change type of edge
                        "group": "edges"
                    })
                
                edges.append({
                    "data": {
                            "source_obj": "EntitiesGroup", 
                            "target_obj": "ShimGroup", 
                            "long_info": [
                               
                            ], 
                            "approxpoints": None, 
                            "actions": [], 
                            "bspline": None, 
                            "id": "EntitiesGroupShimGroup", 
                            "arrowend":None, 
                            "transitive": True, 
                            "obj": "", 
                            "source": "EntitiesGroup", 
                            "label": "", 
                            "target": "ShimGroup", 
                            "short_info": "", 
                            "events": []
                        }, 
                        "classes": "comp", # TODO change type of edge
                        "group": "edges"
                    })
                
                edges.append({
                    "data": {
                            "source_obj": "SecurityGroup", 
                            "target_obj": "ShimGroup", 
                            "long_info": [
                               
                            ], 
                            "approxpoints": None, 
                            "actions": [], 
                            "bspline": None, 
                            "id": "SecurityGroupShimGroup", 
                            "arrowend":None, 
                            "transitive": True, 
                            "obj": "", 
                            "source": "SecurityGroup", 
                            "label": "", 
                            "target": "ShimGroup", 
                            "short_info": "", 
                            "events": []
                        }, 
                        "classes": "comp", # TODO change type of edge
                        "group": "edges"
                    })
                
                edges.append({
                    "data": {
                            "source_obj": "ProtectionGroup", 
                            "target_obj": "SecurityGroup", 
                            "long_info": [
                               
                            ], 
                            "approxpoints": None, 
                            "actions": [], 
                            "bspline": None, 
                            "id": "ProtectionGroupSecurityGroup", 
                            "arrowend":None, 
                            "transitive": True, 
                            "obj": "", 
                            "target": "SecurityGroup", 
                            "label": "", 
                            "source": "ProtectionGroup", 
                            "short_info": "", 
                            "events": []
                        }, 
                        "classes": "comp", # TODO change type of edge
                        "group": "edges"
                    })
                
                edges.append({
                    "data": {
                            "source_obj": "PacketGroup", 
                            "target_obj": "ProtectionGroup", 
                            "long_info": [
                               
                            ], 
                            "approxpoints": None, 
                            "actions": [], 
                            "bspline": None, 
                            "id": "PacketGroupProtectionGroup", 
                            "arrowend":None, 
                            "transitive": True, 
                            "obj": "", 
                            "target": "ProtectionGroup", 
                            "label": "", 
                            "source": "PacketGroup", 
                            "short_info": "", 
                            "events": []
                        }, 
                        "classes": "comp", # TODO change type of edge
                        "group": "edges"
                    })
                
                edges.append({
                    "data": {
                            "source_obj": "quic_frame.ivy", 
                            "target_obj": "PacketGroup", 
                            "long_info": [
                               
                            ], 
                            "approxpoints": None, 
                            "actions": [], 
                            "bspline": None, 
                            "id": "PacketGroupquic_frame.ivy", 
                            "arrowend":None, 
                            "transitive": True, 
                            "obj": "", 
                            "target": "PacketGroup", 
                            "label": "", 
                            "source": "quic_frame.ivy", 
                            "short_info": "", 
                            "events": []
                        }, 
                        "classes": "comp", # TODO change type of edge
                        "group": "edges"
                    })
                    
                components_links = {}
                for component in data.keys():
                    components_links[component] = 0
                
                #for edge in edges:
                    # if edge["data"]["source"] in components_links.keys() and edge["data"]["source"] != edge["data"]["target"]:
                    #     components_links[edge["data"]["source"]] += 1
                    # if edge["data"]["target"] in components_links.keys() and edge["data"]["source"] != edge["data"]["target"]:
                    #     components_links[edge["data"]["target"]] += 1
                
                #if 
                
                for node in output:
                    if "parent" in node["data"].keys() and node["data"]["parent"] in components_links.keys():
                        components_links[node["data"]["parent"]] += 1
                
                for component_link in components_links.keys():
                    if components_links[component_link] == 0:
                        for component in output:
                            if component["data"]["id"] == component_link:
                                component["classes"] = "nodeIcon"
                                component["data"]["kind"] = "NetworkService"
                            if component["classes"] ==  "groupIcon":
                                component["data"]["parent"] = ""
                for edge in edges:
                     output.append(edge)
                     
                json_object = json.dumps(output, indent=4)
                #print(json_object)
                output_file.write(json_object)
        
    def setup_quic_model():
        mapping = {}
        avoid = [
            "collections_impl.ivy",
            "order.ivy",
            "quic_fsm_sending.ivy",
            "quic_fsm_receiving.ivy",
            "deserializer.ivy",
            "udp_impl.ivy",
            "random_value.ivy",
            "file.ivy", # TODO
            "serdes.ivy",
            "tls_msg.ivy"
            #"quic_transport_parameters.ivy", # TODO parse before
        ]
        
        avoid_impl = [
            "fake_client",
            "mim_server_target",
            "mim_client_target",
            "mim_agent",
            "http_request_file", # TODO
            "http_response_file"
        ]

        current_dir = os.getcwd()

        IvyServer.change_permission()

        initializers = False
        in_action = False
        in_action_assumptions = False
        in_action_guarantees = False
        
        actions = []

        with open("/tmp/ivy_show_output.txt", 'r') as input_file:
            with open("/tmp/cytoscape_model.json", 'w') as output_file:
                input_file_content_lines = input_file.readlines()
                for line in input_file_content_lines:

                    # TODO
                    if "/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/" in line:
                        line = line.replace("/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/", "")

                    if "implementation of" in line:
                        has_implem = True
                        is_init = False
                        is_module_object = False
                        is_module_object_present = False

                        line = line.replace("implementation of", "")

                        splitted_line = IvyServer.split_line(line)

                        if splitted_line[0] in avoid:
                            continue

                        prefix = IvyServer.get_prefix(splitted_line)

                        with open(prefix + splitted_line[0], 'r') as f:
                            content = f.readlines()

                        line = int(splitted_line[1].replace("line", "").replace(" ", ""))
                        action_name = splitted_line[2].replace(" ", "").replace("\n", "")
                        
                        actions.append({
                            "action_name":action_name,
                            "file":splitted_line[0]
                        })

                        object_name = ""
                        if "." in action_name:
                            s = action_name.split(".")
                            object_name = s[0]
                            if object_name in avoid_impl:
                                continue
                            elif "frame" in object_name and len(s) > 2:
                                object_name = object_name + "_" + s[1]
                            elif "endpoint" in splitted_line[0]:
                                object_name = object_name + "_ep"

                        if "quic_transport_parameters" in splitted_line[0]:
                            IvyServer.init_tp_mapping(content, mapping, splitted_line)
                        else:
                            has_implem, is_init, is_module_object, is_module_object_present = IvyServer.init_mapping(
                                action_name, content, has_implem, is_init, is_module_object,
                                is_module_object_present, line, mapping, object_name, splitted_line)

                            is_implement = False

                            # Get action content
                            signature = content[line-1]
                            corrected_line = line
                            corrected_signature = signature
                            
                            # if DEBUG and "client.set_tls_id" in action_name: 
                            #     IvyServer.app.logger.info("°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°")
                            #     IvyServer.app.logger.info("line: " + str(line))
                            #     IvyServer.app.logger.info("signature: " + signature)
                            #     IvyServer.app.logger.info("action_name: " + action_name)
                            #     IvyServer.app.logger.info("°°°°°")
                            #     import time
                            #     time.sleep(10)
                                    
                            # Should check if action define in same file (tls_api.lower.send vs attacker.behavior e.g)
                            checked_action_name = action_name.split(".")[-1] if action_name.count(".") == 1  else action_name

                            # Work around to get the right line due to error in ivy_show of modification in output
                            # not sure necessary now -> Still needed for quic_endpoint for example !
                            
                            # TODO problem -> separate action and implement .split(".")[-1] -> TODO use to find module/object
                            while not (checked_action_name in corrected_signature and ("action" in corrected_signature or "implement" in corrected_signature)) and \
                                    len(content) > corrected_line >= 0:
                                corrected_line -= 1
                                corrected_signature = content[corrected_line-1]
                                if checked_action_name in corrected_signature and \
                                    ("action" in corrected_signature or "implement" in corrected_signature):
                                    line = corrected_line
                                    signature = corrected_signature
                                    if "implement" in corrected_signature:
                                        is_implement = True
                                    break
                                
                            corrected_line = line
                            corrected_signature = signature

                            while not (checked_action_name in corrected_signature and ("action" in corrected_signature or "implement" in corrected_signature)) and \
                                    len(content) > corrected_line >= 0:
                                corrected_line += 1
                                corrected_signature = content[corrected_line-1]
                                if checked_action_name in corrected_signature and \
                                    ("action" in corrected_signature or "implement" in corrected_signature):
                                    line = corrected_line
                                    signature = corrected_signature
                                    if "implement" in corrected_signature:
                                        is_implement = True
                                    break

                            if DEBUG : 
                                IvyServer.app.logger.info("°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°")
                                IvyServer.app.logger.info("corrected_signature: " + corrected_signature)
                                IvyServer.app.logger.info("line: " + str(line))
                                IvyServer.app.logger.info("signature: " + signature)
                                IvyServer.app.logger.info("action_name: " + action_name)
                                IvyServer.app.logger.info("splitted_line[0]: " + splitted_line[0])
                                IvyServer.app.logger.info("°°°°°")
                                # if "client.set_tls_id" in action_name:
                                #     import time
                                #     time.sleep(10)


                            if is_module_object:
                                current_elem = mapping[splitted_line[0]][-1]["actions"][-1]
                            else:
                                current_elem = mapping[splitted_line[0]][-1]["actions"]

                            if not is_init:
                                signature = signature.replace("action ", "")
                                signature = signature.replace(current_elem["action_name"], "")
                                if not "{" in signature:
                                    has_implem = False
                                if not "returns" in signature:
                                    current_elem["action_return"] = None
                                    if "(" in signature:
                                        action_parameters = signature.split("=")[0].split("(")[1].split(")")[0].split(",")
                                        IvyServer.get_action_parameters(action_parameters, current_elem)
                                    else:
                                        if not is_implement:
                                            current_elem["action_parameters"] = None
                                        else:
                                            for l in content:
                                                if action_name.split(".")[-1] in l and "action" in l:
                                                    action_parameters = l.split("=")[0].split("(")[1].split(")")[0].split(",")
                                                    IvyServer.get_action_parameters(action_parameters, current_elem)

                                else:
                                    IvyServer.get_action_return(current_elem, signature)
                                    if "(" in signature.split("returns")[0]:
                                        action_parameters = signature.split("returns")[0].split("(")[1].split(")")[0].split(",")
                                        IvyServer.get_action_parameters(action_parameters, current_elem)
                                    else:
                                        if not is_implement:
                                            current_elem["action_parameters"] = None
                                        else:
                                            for l in content:
                                                if action_name.split(".")[-1] in l and \
                                                   "action" in l:
                                                    IvyServer.get_action_return(current_elem, l)
                                                    if "(" in l.split("returns")[0]:
                                                        action_parameters = l.split("returns")[0].split("(")[1].split(")")[0].split(",")
                                                        IvyServer.get_action_parameters(action_parameters, current_elem)
                            else:
                                current_elem["action_parameters"] = None
                                current_elem["action_return"] = None
                            if has_implem:
                                implem_elem = current_elem["implementation"]
                                called_actions = IvyServer.get_action_implementation(content, implem_elem, line, None, splitted_line)
                                if len(called_actions) > 0:
                                    for called_action in called_actions:
                                        found = False
                                        for file in mapping.keys():
                                            if file != "quic_transport_parameters.ivy":
                                                if "." in called_action:
                                                    # TODO uniformize frame and module and object
                                                    current_action, found = IvyServer.find_external_object_action(called_action,
                                                                                                                  current_elem, file,
                                                                                                                  found, mapping)
                                                else:
                                                    current_action, found = IvyServer.find_external_action(called_action,
                                                                                                           current_elem,
                                                                                                           file, found, mapping)
                                                    if called_action == "app_server_open_event_0rtt":
                                                        if DEBUG:
                                                            print("app_server_open_event_0rtt")
                                                            print(current_action)
                                                        # import time
                                                        #time.sleep(100)
                                                if found: # TODO mananage := called_action
                                                    # if "server.behavior" in called_action:
                                                    #     print(splitted_line[0] if not new_file else new_file)
                                                    #     import time
                                                    #     time.sleep(10)
                                                    current_action["called_from"].append({
                                                        "caller_func": called_action,
                                                        "component": splitted_line[0] 
                                                    })
                                                    break


                    elif "monitor of" in line:
                        line = line.replace("monitor of", "")
                        splitted_line = IvyServer.split_line(line)

                        if splitted_line[0] in avoid:
                            continue

                        prefix = IvyServer.get_prefix(splitted_line)

                        if not splitted_line[0] in mapping:
                            mapping[splitted_line[0]] = []
                            
                        line = int(splitted_line[1].replace("line", "").replace(" ", ""))
                        action_name = splitted_line[2].replace(" ", "").replace("\n", "")

                        with open(prefix + splitted_line[0], 'r') as f:
                            content = f.readlines()

                        # Get monitor type
                        signature = content[line-1]
                        corrected_line = line
                        corrected_signature = signature
                        signature_type = "around" if "around" in corrected_signature else "after" if "after" in corrected_signature else "before"

                        # Work around to get the right line due to error in ivy_show
                        while not (action_name.split(".")[-1] in corrected_signature and ("around" in corrected_signature or "after" in corrected_signature or "before" in corrected_signature)) and \
                                len(content) > corrected_line >= 0:
                            corrected_line -= 1
                            corrected_signature = content[corrected_line-1]
                            if action_name.split(".")[-1] in corrected_signature and \
                                ("around" in corrected_signature or "after" in corrected_signature or "before" in corrected_signature):
                                line = corrected_line
                                signature = corrected_signature
                                signature_type = "around" if "around" in corrected_signature else "after" if "after" in corrected_signature else "before"
                                break

                        corrected_line = line
                        corrected_signature = signature

                        while not (action_name.split(".")[-1] in corrected_signature and ("around" in corrected_signature or "after" in corrected_signature or "before" in corrected_signature)) and \
                                len(content) > corrected_line >= 0:
                            corrected_line += 1
                            corrected_signature = content[corrected_line-1]
                            if action_name.split(".")[-1] in corrected_signature and \
                                ("around" in corrected_signature or "after" in corrected_signature or "before" in corrected_signature):
                                line = corrected_line
                                signature = corrected_signature
                                signature_type = "around" if "around" in corrected_signature else "after" if "after" in corrected_signature else "before"
                                break

                        if DEBUG:
                            IvyServer.app.logger.info("°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°")
                            IvyServer.app.logger.info(corrected_signature)
                            IvyServer.app.logger.info(line)
                            IvyServer.app.logger.info(signature)
                            IvyServer.app.logger.info(signature_type)
                            IvyServer.app.logger.info(action_name)
                            IvyServer.app.logger.info(splitted_line[0])
                            IvyServer.app.logger.info("°°°°°")
                            # if "ivy_quic_shim_client" in splitted_line[0]:
                            #     import time
                            #     time.sleep(10)

                        current_action = None
                        another_file = False
                        if "." in action_name:
                            # TODO uniformize frame and module and object
                            s = action_name.split(".")
                            object_name = s[0]
                            if "frame" in object_name and len(s) > 2:
                                object_name = object_name + "_" + s[1]
                            elif "endpoint" in splitted_line[0]:
                                object_name = object_name + "_ep"
                            if DEBUG:
                                IvyServer.app.logger.info(object_name)
                            for obj in mapping[splitted_line[0]]:
                                if  object_name + "_name" in obj.keys():
                                    for act in obj["actions"]:
                                        if act["action_name"] == action_name:
                                            if DEBUG:
                                                IvyServer.app.logger.info("Found 2")
                                            current_action = act
                                            break
                            if current_action is None:
                                if DEBUG:
                                    IvyServer.app.logger.info("current_action == None")
                                another_file = True
                        else:
                            for obj in mapping[splitted_line[0]]:
                                if not isinstance(obj["actions"], list): # else mean it is a module
                                    if obj["actions"]["action_name"] == action_name:
                                        if DEBUG:
                                            IvyServer.app.logger.info("Found 3")
                                        current_action = obj["actions"]
                                        break
                            if current_action is None:
                                if DEBUG:
                                    IvyServer.app.logger.info("current_action == None")
                                another_file = True

                        new_file = None
                        found = False
                        if another_file:
                            # Maybe better to create new file ?
                            # We choose to append to existing file containing action
                            for file in mapping.keys():
                                if DEBUG:
                                    IvyServer.app.logger.info(file)
                                if file != "quic_transport_parameters.ivy" and not found and file != splitted_line[0]:
                                    if "." in action_name:
                                        # TODO uniformize frame and module and object
                                        current_action, found = IvyServer.find_external_object_action(action_name,
                                                                                                 current_action, file,
                                                                                                 found, mapping)
                                    else:
                                        current_action, found = IvyServer.find_external_action(action_name, current_action,
                                                                                          file, found, mapping)
                                if found:
                                    break
                        if DEBUG:
                            IvyServer.app.logger.info("°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°")

                        if another_file and not found:
                            if DEBUG:
                                IvyServer.app.logger.info(action_name)
                                IvyServer.app.logger.info(splitted_line[0])
                            continue

                        if current_action and signature_type in ["around", "after", "before"]:
                            if DEBUG:
                                IvyServer.app.logger.info("getting_monitor_content")
                                IvyServer.app.logger.info(line)
                                IvyServer.app.logger.info(content[line])
                            implem_elem = current_action["monitor"][signature_type]
                            called_actions = IvyServer.get_action_implementation(content, implem_elem, line, new_file, splitted_line)
                            if len(called_actions) > 0:
                                for called_action in called_actions:
                                    for file in mapping.keys():
                                        if file != "quic_transport_parameters.ivy":
                                            if "." in called_action:
                                                # TODO uniformize frame and module and object
                                                current_action, found = IvyServer.find_external_object_action(called_action,
                                                                                                        current_action, file,
                                                                                                        found, mapping)
                                            else:
                                                current_action, found = IvyServer.find_external_action(called_action,
                                                                                                    current_action,
                                                                                                    file, found, mapping)
                                            if called_action == "app_server_open_event_0rtt":
                                                if DEBUG:
                                                    print("app_server_open_event_0rtt")
                                                    print(current_action)
                                                # import time
                                                #time.sleep(100)
                                            if found:
                                                # if "server.behavior" in called_action:
                                                #     print(splitted_line[0] if not new_file else new_file)
                                                #     import time
                                                #     time.sleep(10)
                                                current_action["called_from"].append({
                                                    "caller_func": called_action.replace("\n", ""),
                                                    "component": splitted_line[0] if not new_file else new_file
                                                })
                                                break
                        else:
                            if DEBUG:
                                IvyServer.app.logger.info("ERROR")
                                IvyServer.app.logger.info(signature_type)
                            pass
                    
                    elif "initializers are" in line:
                        initializers = True
                    elif "Initialization must establish the invariant" in line:
                        initializers = False
                    elif initializers:
                        if DEBUG:
                            IvyServer.app.logger.info("------------- initializers -------------")
                        splitted_line = IvyServer.split_line(line)

                        if len(splitted_line[0]) != 3:
                            continue
                        
                        if splitted_line[0] in avoid:
                            continue

                        prefix = IvyServer.get_prefix(splitted_line)
                        if not splitted_line[0] in mapping:
                            mapping[splitted_line[0]] = [ ]

                        if DEBUG:
                            IvyServer.app.logger.info(splitted_line)
                        line = int(splitted_line[1].replace("line", "").replace(" ", ""))
                        action_name = splitted_line[2].replace(" ", "").replace("\n", "")
                        
                        if "." in action_name:
                            pass # we dont want initializer of module object, already parsed before
                        with open(prefix + splitted_line[0], 'r') as f:
                            content = f.readlines()

                        # Get init content
                        mapping[splitted_line[0]].append({
                                "actions": {
                                    "action_name": action_name,
                                    "action_return" : None,
                                    "implementation": [],
                                    "monitor":{
                                        "before": [],
                                        "after": [],
                                        "around": []
                                    },
                                    "exported": False if not "export" in content[line-1] else True,
                                    "events": False,
                                    "init": True
                                }
                        })
                        implem_elem = current_elem["implementation"]
                        called_actions = IvyServer.get_action_implementation(content, implem_elem, line, None, splitted_line)
                        if len(called_actions) > 0:
                            for called_action in called_actions:
                                for file in mapping.keys():
                                    if file != "quic_transport_parameters.ivy":
                                        if "." in called_action:
                                            # TODO uniformize frame and module and object
                                            current_action, found = IvyServer.find_external_object_action(called_action,
                                                                                                    current_action, file,
                                                                                                    found, mapping)
                                        else:
                                            current_action, found = IvyServer.find_external_action(called_action,
                                                                                                current_action,
                                                                                                file, found, mapping)
                                        if called_action == "app_server_open_event_0rtt":
                                            if DEBUG:
                                                print("app_server_open_event_0rtt")
                                                print(current_action)
                                            # import time
                                            #time.sleep(100)
                                        if found:
                                            # if "server.behavior" in called_action:
                                            #     print(splitted_line[0] if not new_file else new_file)
                                            #     import time
                                            #     time.sleep(10)
                                            current_action["called_from"].append({
                                                "caller_func": called_action,
                                                "component": splitted_line[0]
                                            })
                                            break

                    
                    elif "ext:" in line:
                        if DEBUG:
                            IvyServer.app.logger.info("------------- exported -------------")
                        action_name = line.split("ext:")[-1].replace("\n","")
                        if DEBUG:
                            IvyServer.app.logger.info(action_name)
                        found = False
                        for file in mapping.keys():
                            if file != "quic_transport_parameters.ivy" and not found:
                                if DEBUG:
                                    IvyServer.app.logger.info(file)
                                if "." in action_name:
                                    # TODO uniformize frame and module and object
                                    #object_name = action_name.split(".")[0]
                                    s = action_name.split(".")
                                    object_name = s[0]
                                    if object_name in avoid_impl:
                                        continue
                                    elif "frame" in object_name and len(s) > 2:
                                        object_name = object_name + "_" + s[1]
                                    elif "endpoint" in splitted_line[0]:
                                        object_name = object_name + "_ep"
                                        
                                    for obj in mapping[file]:
                                        if  object_name + "_name" in obj.keys():
                                            for act in obj["actions"]:
                                                if act["action_name"] == action_name:
                                                    if DEBUG:
                                                        IvyServer.app.logger.info("Found 2")
                                                    act["exported"] = True
                                                    found = True
                                                    break
                                else:
                                    for obj in mapping[file]:
                                        if not isinstance(obj["actions"], list): # else mean it is a module
                                            if obj["actions"]["action_name"] == action_name:
                                                if DEBUG:
                                                    IvyServer.app.logger.info("Found 3")
                                                obj["actions"]["exported"] = True
                                                found = True
                                                break
                            if found:
                                break
                    elif "guarantees" in line:
                        in_action_assumptions = False
                        in_action_guarantees = True
                        if DEBUG:
                            IvyServer.app.logger.info("------- in_action_guarantees -------")
                    elif "assumptions" in line:
                        in_action_assumptions = True
                        in_action_guarantees = False
                        if DEBUG:
                            IvyServer.app.logger.info("------- in_action_assumptions -------")
                    elif "in action" in line:
                        if DEBUG:
                            IvyServer.app.logger.info("------------- in action -------------")
                        found = False
                        line = line.replace("in action","")
                        line = line.replace(":\n","")
                        action_name = line.split(" when called from ")[0].replace(" ","")
                        if DEBUG:
                            IvyServer.app.logger.info(action_name)
                        for file in mapping.keys():
                            if file != "quic_transport_parameters.ivy" and not found:
                                if DEBUG:
                                    IvyServer.app.logger.info(file)
                                if "." in action_name:
                                    # TODO uniformize frame and module and object
                                    object_name = action_name.split(".")[0]
                                    for obj in mapping[file]:
                                        if  object_name + "_name" in obj.keys():
                                            for act in obj["actions"]:
                                                if act["action_name"] == action_name:
                                                    if DEBUG:
                                                        IvyServer.app.logger.info("Found 2")
                                                    in_action = IvyServer.setup_assertions(act, in_action,
                                                                                      in_action_assumptions,
                                                                                      in_action_guarantees, line, mapping)
                                                    found = True
                                                    break
   
                                else:
                                    for obj in mapping[file]:
                                        if not isinstance(obj["actions"], list): # else mean it is a module
                                            if obj["actions"]["action_name"] == action_name:
                                                if DEBUG: 
                                                    IvyServer.app.logger.info("Found 3")
                                                in_action = IvyServer.setup_assertions(obj["actions"], in_action,
                                                                                  in_action_assumptions,
                                                                                  in_action_guarantees, line, mapping)
                                                found = True
                                                break
                            if found:
                                break
                            
                    elif in_action_assumptions and "assumption" in line:
                        if DEBUG:
                            IvyServer.app.logger.info("in_action_assumptions and assumption in line")

                        splitted_line = IvyServer.split_line(line)

                        if splitted_line[0] in avoid:
                            continue

                        IvyServer.add_assertion(in_action, mapping, splitted_line)


                    elif in_action_guarantees and "guarantee" in line:
                        if DEBUG:
                            IvyServer.app.logger.info("in_action_guarantees and guarantee in line")
                        splitted_line = IvyServer.split_line(line)

                        if splitted_line[0] in avoid:
                            continue

                        IvyServer.add_assertion(in_action, mapping, splitted_line)
                        
                # Last check to get all called actions
                
                for action_name_val in actions:
                    found = False
                    action_name = action_name_val["action_name"]
                    file_origin = action_name_val["file"]
                    print("------------------------")
                    print("action_name: " + action_name)
                    print("file_origin: " + file_origin)
                    for file in mapping.keys():
                        if file != "quic_transport_parameters.ivy" and file != file_origin:
                            if DEBUG:
                                print("file: " + file)
                            # print("°°°°°°°")
                            for obj in mapping[file]:
                                if "actions" in obj.keys():
                                    current_elem = obj["actions"] # ERROR SOMEWHERE HERE
                                    if not isinstance(obj["actions"], list):
                                        if "implementation" in obj["actions"].keys():
                                            for l in obj["actions"]["implementation"]:
                                                stripped_line = l["instruction"].lstrip()
                                                if not stripped_line.startswith("#"):
                                                    if stripped_line.split(".")[-1].startswith(action_name.split(".")[-1]):
                                                        if DEBUG:
                                                            print("present in l: " + str(stripped_line))
                                                            print("file: " + file)
                                                            print("action_name: " + action_name)
                                                            print("file_origin: " + file_origin)
                                                        found = False
                                                        for file_i in mapping.keys():
                                                            if file_i != "quic_transport_parameters.ivy":
                                                                if "." in action_name:
                                                                    # TODO uniformize frame and module and object
                                                                    current_action, found = IvyServer.find_external_object_action(action_name,
                                                                                                                                    current_elem, file_i,
                                                                                                                                    found, mapping)
                                                                else:
                                                                    current_action, found = IvyServer.find_external_action(action_name,
                                                                                                                           current_elem,
                                                                                                                           file_i, found, mapping)
                                        
                                                                if found: # TODO mananage := action_name
                                                                    if DEBUG:
                                                                        print("found 1",{
                                                                            "caller_func": action_name,
                                                                            "component": file
                                                                        })
                                                                        print("file_i: " + file_i)
                                                                    not_present = True
                                                                    for elem in current_action["called_from"]:
                                                                        if elem["caller_func"] == action_name:
                                                                            not_present = False
                                                                            break
                                                                    if not_present:
                                                                        # if "server.behavior" in action_name:
                                                                        #     print(splitted_line[0] if not new_file else new_file)
                                                                        #     import time
                                                                        #     time.sleep(10)
                                                                        current_action["called_from"].append({
                                                                            "caller_func": action_name,
                                                                            "component": file
                                                                        })
                                                                    break
                                                                
                                                    elif action_name.split(".")[-1] in stripped_line: # TODO 
                                                        if action_name.split(".")[-1] in stripped_line:
                                                            if DEBUG:
                                                                print(stripped_line)
                                                                print("Char after:")
                                                                print(stripped_line.split(action_name.split(".")[-1])[0][-1])
                                                                print("Char before:")
                                                                print(stripped_line.split(action_name.split(".")[-1])[1][0])
                                                            if stripped_line.split(action_name.split(".")[-1])[0][-1] in [".", " ","", "(",","] and \
                                                                stripped_line.split(action_name.split(".")[-1])[1][0] in [".", " ","", "(",","]:
                                                                if DEBUG:
                                                                    print("2 present in l: " + str(stripped_line))    
                                                                    print("file: " + file)
                                                                    print("action_name: " + action_name)
                                                                    print("file_origin: " + file_origin) 
                                                                found = False
                                                                for file_i in mapping.keys():
                                                                    if file_i != "quic_transport_parameters.ivy"  and file != file_origin:
                                                                        if "." in action_name:
                                                                            # TODO uniformize frame and module and object
                                                                            current_action, found = IvyServer.find_external_object_action(action_name,
                                                                                                                                            current_elem, file_i,
                                                                                                                                            found, mapping)
                                                                        else:
                                                                            current_action, found = IvyServer.find_external_action(action_name,
                                                                                                                                current_elem,
                                                                                                                                file_i, found, mapping)
                                                
                                                                        if found: # TODO mananage := action_name
                                                                            if DEBUG:
                                                                                print("found 2",{
                                                                                    "caller_func": action_name,
                                                                                    "component": file
                                                                                })
                                                                                print("file_i: " + file_i)
                                                                            not_present = True
                                                                            for elem in current_action["called_from"]:
                                                                                if elem["caller_func"] == action_name:
                                                                                    not_present = False
                                                                                    break
                                                                            if not_present:
                                                                                # if "server.behavior" in action_name:
                                                                                #     print(file)
                                                                                #     import time
                                                                                #     time.sleep(10)
                                                                                current_action["called_from"].append({
                                                                                    "caller_func": action_name,
                                                                                    "component": file
                                                                                })
                                                                                                                                   
                                                    else:
                                                        pass
                                                        #print("not in l: " + str(stripped_line))
                        elif file == "quic_transport_parameters.ivy":
                            # Get transport parameters references    [1]  
                            print("file: " + file)
                            for obj in mapping[file]:
                                print(obj)
                                for file_i in mapping.keys():
                                    if file_i != "quic_transport_parameters.ivy":
                                        for obj_i in mapping[file_i]:
                                            if "actions" in obj_i.keys():
                                                current_elem = obj_i["actions"] # ERROR SOMEWHERE HERE
                                                if not isinstance(obj_i["actions"], list):
                                                    if "implementation" in obj_i["actions"].keys():
                                                        for l in obj_i["actions"]["implementation"]:
                                                            stripped_line = l["instruction"].lstrip()
                                                            if str(obj) in stripped_line: # TODO
                                                                pass
                                                                # obj["called_from"].append({
                                                                #     "caller_func": obj_i["actions"]["action_name"],
                                                                #     "component": file_i
                                                                # })
                                                                            
                                                                        
                                            
                 
                
                # Get relation and functions
                IvyServer.get_relations(mapping)
                
                os.chdir(current_dir)
                json_object = json.dumps(mapping, indent=4)
                output_file.write(json_object)

    def get_relations(mapping):
        for file in mapping.keys():
            functions = []
            relations = []
            prefix = IvyServer.get_prefix([file])
            with open(prefix + file, 'r') as f:
                if DEBUG:
                    IvyServer.app.logger.info(file)
                content = f.readlines()
                line = 1
                for l in content:
                    stripped_line = l.lstrip()
                    if stripped_line.startswith("function "):
                        if DEBUG:
                            IvyServer.app.logger.info(stripped_line)
                        include_ivy = stripped_line.split("#")[0]
                        include_ivy = include_ivy.replace("function ", '')
                        if include_ivy != ".ivy":
                            functions.append({
                                "name": include_ivy,
                                "comment": stripped_line.split("#")[1].replace("\n","") if "#" in stripped_line else "",
                                "line": line,
                                "file": file
                            })
                    elif stripped_line.startswith("relation "):
                        if DEBUG:
                            IvyServer.app.logger.info(stripped_line)
                        include_ivy = stripped_line.split("#")[0]
                        include_ivy = include_ivy.replace("relation ", '')
                        if include_ivy != ".ivy":
                            relations.append({
                                "name": include_ivy,
                                "comment": stripped_line.split("#")[1].replace("\n","") if "#" in stripped_line else "",
                                "line": line,
                                "file": file
                            })
                    line += 1
                if DEBUG:
                    IvyServer.app.logger.info(json.dumps(mapping[file]))
                mapping[file].append({
                    "functions": functions,
                    "relations": relations
                })
                    
    
    def add_assertion(in_action, mapping, splitted_line):
        prefix = IvyServer.get_prefix(splitted_line)
        if not splitted_line[0] in mapping:
            mapping[splitted_line[0]] = []
        line = int(splitted_line[1].replace("line", "").replace(" ", ""))
        if DEBUG:
            IvyServer.app.logger.info(splitted_line)
            IvyServer.app.logger.info(line)
        with open(prefix + splitted_line[0], 'r') as f:
            content = f.readlines()
        i = 2
        assertion_line = content[line - 1]
        while "require" not in assertion_line:
            assertion_line += content[line - i]
            i += 1
        assertion_line = assertion_line.lstrip()
        if DEBUG:
            IvyServer.app.logger.info(assertion_line)
        # Get monitor type
        in_action["assertions"].append({
            "line": line,
            "file": splitted_line[0],
            "assertion": assertion_line,
        })

    def setup_assertions(act, in_action, in_action_assumptions, in_action_guarantees, line, mapping):
        if in_action_assumptions:
            for elem in line.split(" when called from ")[-1].split(","):
                if elem not in act["assertions_as_assumption"]["called_from"]:
                    if elem == "the environment":
                        appended = {
                            "caller_func": "Environment",
                            "component": "Environment"
                        }
                    else:
                        component = ""
                        if "." in elem:
                            # TODO uniformize frame and module and object
                            s = elem.split(".")
                            object_name = s[0]
                            if "frame" in object_name and len(s) > 2:
                                object_name = object_name + "_" + s[1]
                            elif object_name in ["attacker","client","server","victim"]:
                                object_name = object_name + "_ep"
                            for file in mapping.keys():
                                for obj in mapping[file]:
                                    if  object_name + "_name" in obj.keys():
                                        for act in obj["actions"]:
                                            if act["action_name"] == elem:
                                                component = file
                                                break
                        else:
                            for file in mapping.keys():
                                for obj in mapping[file]:
                                    if DEBUG:
                                        print(obj)
                                    if "actions" in obj.keys() and not isinstance(obj["actions"], list):
                                        if obj["actions"]["action_name"] == elem:
                                            component = file
                                            break
                        # if "server.behavior" in elem:
                        #     print(component)
                        #     import time
                        #     time.sleep(10)
                        appended = {
                            "caller_func": elem,
                            "component": component
                        }
                    act["assertions_as_assumption"]["called_from"].append(appended)
            in_action = act["assertions_as_assumption"]
        elif in_action_guarantees:
            for elem in line.split(" when called from ")[-1].split(","):
                if elem not in act["assertions_as_guarantees"]["called_from"]:
                    if elem == "the environment":
                        appended = {
                            "caller_func": "Environment",
                            "component": "Environment"
                        }
                    else:
                        component = ""
                        if "." in elem:
                            # TODO uniformize frame and module and object
                            s = elem.split(".")
                            object_name = s[0]
                            if "frame" in object_name and len(s) > 2:
                                object_name = object_name + "_" + s[1]
                            elif object_name in ["attacker","client","server","victim"]:
                                object_name = object_name + "_ep"
                            for file in mapping.keys():
                                for obj in mapping[file]:
                                    if  object_name + "_name" in obj.keys():
                                        for act in obj["actions"]:
                                            if act["action_name"] == elem:
                                                component = file
                                                break
                        else:
                            for file in mapping.keys():
                                for obj in mapping[file]:
                                    if DEBUG:
                                        print(obj)
                                    if "actions" in obj.keys() and not isinstance(obj["actions"], list):
                                        if obj["actions"]["action_name"] == elem:
                                            component = file
                                            break
                        # if "server.behavior" in elem:
                        #     print(component)
                        #     import time
                        #     time.sleep(10)
                        appended = {
                            "caller_func": elem,
                            "component": component
                        } 
                    act["assertions_as_guarantees"]["called_from"].append(appended)
            in_action = act["assertions_as_guarantees"]
        return in_action

    def find_external_action(action_name, current_action, file, found, mapping):
        for obj in mapping[file]:
            if not isinstance(obj["actions"], list):  # else mean it is a module
                if obj["actions"]["action_name"] == action_name:
                    if DEBUG:
                        IvyServer.app.logger.info("Found 3")
                    current_action = obj["actions"]
                    found = True
                    break
        return current_action, found

    def find_external_object_action(action_name, current_action, file, found, mapping):
        s = action_name.split(".")
        object_name = s[0]
        if "frame" in object_name and len(s) > 2:
            object_name = object_name + "_" + s[1]
        elif "endpoint" in file:
            object_name = object_name + "_ep"
        for obj in mapping[file]:
            if object_name + "_name" in obj.keys():
                for act in obj["actions"]:
                    if act["action_name"] == action_name:
                        if DEBUG:
                            IvyServer.app.logger.info("Found 2")
                        current_action = act
                        found = True
                        break
        return current_action, found

    def get_action_implementation(content, implem_elem, line, new_file, splitted_line):
        bracket_count = 0
        c_line = line
        called_action = []
        for l in content[line:]:
            if "}" in l:
                if bracket_count == 0:
                    break
                bracket_count -= 1
            if "{" in l:
                bracket_count += 1
            
            if l.lstrip().startswith("call "): 
                called_action.append(l.split("call ")[1].split("(")[0])
                 
            
            if len(implem_elem) > 0 and implem_elem[-1]["line"] < c_line:
                implem_elem.append({"line": c_line,
                                    "file": splitted_line[0] if new_file is None else new_file,
                                    "instruction": l})
            elif len(implem_elem) == 0:
                implem_elem.append({"line": c_line,
                                    "file": splitted_line[0] if new_file is None else new_file,
                                    "instruction": l})
            c_line += 1
        if DEBUG:
            print(called_action)
        return called_action
    
    def get_called_action_implementation(content, line, new_file, splitted_line):
        bracket_count = 0
        called_action = []
        for l in content[line:]:
            if "}" in l:
                if bracket_count == 0:
                    break
                bracket_count -= 1
            if "{" in l:
                bracket_count += 1
            
        print(called_action)
        return called_action

    def get_action_return(current_elem, signature):
        action_return = signature.split("returns")[1].split("(")[1].split(")")[0].split(":")
        current_elem["action_return"]["name"] = action_return[0]
        current_elem["action_return"]["type"] = action_return[1]

    def get_action_parameters(action_parameters, current_elem):
        for param in action_parameters:
            attr = param.split(":")
            if "#" not in attr[0]:
                current_elem["action_parameters"].append({
                    "name": attr[0].replace(" ", ""),
                    "type": attr[1].replace(" ", "") if "#" not in attr[1] else attr[1].split("#")[0].replace(" ", "")
                })

    def init_mapping(action_name, content, has_implem, is_init, is_module_object,
                     is_module_object_present, line, mapping, object_name, splitted_line):
        if not splitted_line[0] in mapping:
            mapping[splitted_line[0]] = []
        if "." in action_name:
            # action related to object or module (method)
            is_module_object = True

            # if "endpoint" in splitted_line[0]:
            #     object_name = object_name + "_ep"

            is_module_object_present = IvyServer.check_object_present(action_name, content,
                                                            is_module_object_present, line,
                                                            mapping, object_name,
                                                            splitted_line)

            if not is_module_object_present:
                IvyServer.get_module_object_attributes(action_name, content, line,
                                             mapping, object_name, splitted_line)

        elif "init " in action_name or "init[" in action_name:
            is_init = True
            mapping[splitted_line[0]].append({
                "actions": {
                    "action_name": "init",
                    "action_return": None,
                    "implementation": [],
                    "monitor": {
                        "before": [],
                        "after": [],
                        "around": []
                    },
                    "exported": False if not "export" in content[line - 1] else True,
                    "events": False,
                    "called_from": [],
                    "init": True
                }
            })
        elif "import " in content[line - 1] and not "_finalize" in action_name:
            has_implem = False
            mapping[splitted_line[0]].append({
                "actions": {
                    "line": line,
                    "action_name": action_name,
                    "action_return": None,
                    "exported": False if not "export" in content[line - 1] else True,
                    "action_parameters": [],
                    "called_from": [],
                    "events": True
                }
            })
        else:
            # isolate action
            mapping[splitted_line[0]].append({
                "actions": {
                    "line": line,
                    "action_name": action_name,
                    "implementation": [],
                    "monitor": {
                        "before": [],
                        "after": [],
                        "around": []
                    },
                    "action_return": {
                        "name": "",
                        "type": "",
                    },
                    "action_parameters": [],
                    "exported": False if not "export" in content[line - 1] else True,
                    "events": False,
                    "called_from": [],
                    "assertions_as_guarantees": {
                        "called_from": [],
                        "assertions": [],
                    },
                    "assertions_as_assumption": {
                        "called_from": [],
                        "assertions": [],
                    }
                }
            })
        return has_implem, is_init, is_module_object, is_module_object_present

    def get_module_object_attributes(action_name, content, line, mapping, object_name,
                                     splitted_line):
        mapping[splitted_line[0]].append({
            object_name + "_name": object_name if "frame" not in action_name else object_name.replace("frame_",""),
            object_name + "_object": [],
            object_name + "_module": {
                "module_parameters": [],
                "module_attributes": [],  # Not used, we dont want user to modify it but we keep it in case
            },
            "actions": [{
                "line": line,
                "action_name": action_name,
                "implementation": [],
                "monitor": {
                    "before": [],
                    "after": [],
                    "around": []
                },
                "action_return": {
                    "name": "",
                    "type": "",
                },
                "action_parameters": [],
                "exported": False if not "export" in content[line - 1] else True,
                "events": False,
                "called_from": [],
                "assertions_as_guarantees": {
                    "called_from": [],
                    "assertions": [],
                },
                "assertions_as_assumption": {
                    "called_from": [],
                    "assertions": [],
                }
            }]
        })
        reached = False
        is_module = False
        for l in content:
            if "object " + mapping[splitted_line[0]][-1][object_name + "_name"] in l and not reached:
                reached = True
                mapping[splitted_line[0]][-1][object_name + "_module"] = None
            elif "module " + mapping[splitted_line[0]][-1][object_name + "_name"] in l and not reached:
                is_module = True
                reached = True
                bracket_count = 0 # TODO
                module_parameters = l.split("=")[0].split("(")[1].split(")")[0].split(",")
                for param in module_parameters:
                    mapping[splitted_line[0]][-1][object_name + "_object"] = None
                    attr = param.split(":")
                    if "#" not in attr[0]:
                        mapping[splitted_line[0]][-1][object_name + "_module"]["module_parameters"].append({
                            "name": attr[0].replace(" ", ""),
                            "type": attr[1].replace(" ", "") if "#" not in attr[1] else attr[1].split("#")[0].replace(
                                " ", "")
                        })

            if reached:
                if not is_module:
                    if "}" in l or "action" in l:
                        break
                    if ":" in l:  # and not "#" in l
                        attr = l.split(":")
                        if "#" not in attr[0]:
                            if "instance" in attr[0]:
                                mapping[splitted_line[0]][-1][object_name + "_object"].append({
                                    "name": attr[0].replace("instance ", "").replace(" ", ""),
                                    "type": attr[1].replace(" ", "") if "#" not in attr[1] else attr[1].split("#")[
                                        0].replace(" ", ""),
                                    "instance": True
                                })
                            else:
                                mapping[splitted_line[0]][-1][object_name + "_object"].append({
                                    "name": attr[0].replace(" ", ""),
                                    "type": attr[1].replace(" ", "") if "#" not in attr[1] else attr[1].split("#")[
                                        0].replace(" ", "")
                                })

                else:
                    # For attributes
                    if "after init" in l and bracket_count == 0:
                        break
                    if "{" in l:
                        bracket_count += 1

    def check_object_present(action_name, content, is_module_object_present, line, mapping, object_name,
                             splitted_line):
        for obj in mapping[splitted_line[0]]:
            if object_name + "_name" in obj.keys():
                is_module_object_present = True
                current_elem = obj
                current_elem["actions"].append({
                    "line": line,
                    "action_name": action_name,
                    "implementation": [],
                    "monitor": {
                        "before": [],
                        "after": [],
                        "around": []
                    },
                    "action_return": {
                        "name": "",
                        "type": "",
                    },
                    "action_parameters": [],
                    "exported": False if not "export" in content[line - 1] else True,
                    "events": False,
                    "called_from": [],
                    "assertions_as_guarantees": {
                        "called_from": [],
                        "assertions": [],
                    },
                    "assertions_as_assumption": {
                        "called_from": [],
                        "assertions": [],
                    }
                })
                break
        return is_module_object_present

    def init_tp_mapping(content, mapping, splitted_line):
        tp_name = splitted_line[2].replace(" ", "").replace(".set", "").replace("\n", "")
        if splitted_line[0] not in mapping:
            mapping[splitted_line[0]] = []
            mapping[splitted_line[0]].append({})
        mapping[splitted_line[0]][0][tp_name] = {
            "called_from": [],
            "attributes": []
        }
        reached = False
        reached_struct = False
        for l in content:
            if "object " + tp_name in l:
                reached = True

            if reached and "variant" in l and "struct" in l:
                reached_struct = True

            if ":" in l and reached:
                attr = l.split(":")
                if "#" not in attr[0]:
                    mapping[splitted_line[0]][0][tp_name]["attributes"].append({
                        "name": attr[0].lstrip().rstrip(),
                        "type": attr[1].lstrip().rstrip() if "#" not in attr[1] else attr[1].split("#")[0].lstrip().rstrip()
                    })

            if reached and reached_struct and "}" in l:
                break

    def get_prefix(splitted_line):
        prefix = "/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/"
        if "server_test" in splitted_line[0]:
            prefix = "/tmp/QUIC-FormalVerification/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/server_tests/"
        elif "client_test" in splitted_line[0]:
            prefix = "/tmp/QUIC-FormalVerification/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/client_tests/"
        return prefix

    def change_permission():
        os.chdir(IvyServer.ivy_test_path + "server_tests/")
        ivy_file = "quic_server_test_stream.ivy"  # TODO
        os.system("chown root:root /tmp/ivy_show_output.txt")
        os.system("ivy_check diagnose=true show_compiled=false pedantic=true trusted=false trace=false isolate_mode=test isolate=this " + ivy_file + "> /tmp/ivy_show_output.txt")
        os.system("chown root:root /tmp/cytoscape_model.json")
        os.system("chown root:root /tmp/cytoscape_config.json")

    def split_line(line):
        splitted_line = line.split(":")
        splitted_line[0] = splitted_line[0].replace(" ", "")
        return splitted_line


    @app.route('/kg/graph/json', methods = ['GET'])
    def get_json_graph():
        """
        It returns the json graph of the knowledge graph
        :return: the json graph of the knowledge graph
        """ 
        parents = []
        with open("/tmp/cytoscape_config.json", 'r') as json_file:
            data = json.load(json_file)
            # ##IvyServer.app.logger.info(len(data))
            # i = 0
            # to_remove = []
            # for elem in data:
            #     if elem["group"] == "shapes":
            #         #del data[elem]
            #         ##IvyServer.app.logger.info("swag")
            #         #elem = None
            #         to_remove.append(elem)
            #     data[i]["locked"] = False
            #     if data[i]["group"] == "nodes":
            #         data[i]["position"] = None
            #     if data[i]["group"] == "edges":
            #         data[i]["data"]["approxpoints"] = None
            #         data[i]["data"]["bspline"] = None
            #         data[i]["data"]["arrowend"] = None
            #     # if "cluster" in data[i]["data"]:
            #     #     data[i]["data"]["parent"] = data[i]["data"]["cluster"]
            #     if "\n" in data[i]["data"]["label"]: # probably a module
            #         children = data[i]["data"]["label"].split("\n")[1:]
            #         children_updated = []
            #         for child in children:
            #             child = child.split(".")[0]
            #             children_updated.append(child)
            #         for elem in data:
            #             if elem["data"]["label"] in children_updated:
            #                 elem["data"]["parent"] = data[i]["data"]["id"]
            #                 data[i]["data"]["label"] = data[i]["data"]["label"].split("\n")[0] # TODO only one
            #                 parents.append(data[i]["data"]["id"])
            #     if "." in data[i]["data"]["label"]:
            #         parent = data[i]["data"]["label"].split(".")[0]
            #         #parent_id = data[i]["data"]["id"]
            #         # TODO not greedy
            #         for elem in data:
            #             if elem["data"]["label"] == parent:
            #                 data[i]["data"]["parent"] = elem["data"]["id"]
            #                 parents.append(elem["data"]["id"])

            #     # else:
            #     #     data[i]["classes"] = data[i]["classes"] + " groupIcon" 
 
            #     if "client" in data[i]["data"]["label"] or "server" in data[i]["data"]["label"]: 
            #         data[i]["data"]["kind"] = "TelcoCloudVirtualDevice"
            #     elif "frame" in data[i]["data"]["label"] or "packet" in data[i]["data"]["label"]:
            #         data[i]["data"]["kind"] = "VNF"
            #     else:
            #         data[i]["data"]["kind"] = "NetworkService"
                
            #     data[i]["data"]["displayName"] = data[i]["data"]["label"].split("\n")[0]
                
            #     if "frame" in data[i]["data"]["label"] or "packet" in data[i]["data"]["label"]:
            #         data[i]["data"]["operationalState"] = "notWorking"
            #     else:
            #         data[i]["data"]["operationalState"] = "Working"
                    
            #     data[i]["data"]["alarmSeverity"] = "cleared"
                
            #     # if data[i]["group"] == "nodes":
            #     #     data[i]["classes"] = data[i]["classes"] + " nodeIcon" 
                
            #     ##IvyServer.app.logger.info(elem)
            #     i+=1
            # for elem in to_remove:
            #     data.remove(elem)
            
            # for i in range(len(data)):
            #      if data[i]["group"] == "nodes":
            #         if data[i]["data"]["id"] in parents:
            #             data[i]["classes"] = data[i]["classes"] + " groupIcon" 
            #         else:
            #             data[i]["classes"] = data[i]["classes"] + " nodeIcon" 
            ##IvyServer.app.logger.info(len(data))
            ##IvyServer.app.logger.info(i)
        
        response = IvyServer.app.response_class(
            response=json.dumps(data),
            status=200,
            mimetype='application/json'
        )
        return response
    
    @app.route('/creator.html', methods = ['GET', 'POST'])
    def serve_attack():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        IvyServer.experiments.update_includes_ptls()
        IvyServer.experiments.update_includes()
        def call_python_version(Version, Module, Function, ArgumentList):
            folder = ExperimentRunner.SOURCE_DIR + "/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/server_tests/"
            IvyServer.experiments.update_includes_ptls()
            IvyServer.experiments.update_includes()
            # //env:PATH=%s//env:PYTHONPATH=%s , os.getenv('PATH'), os.getenv('PYTHONPATH'))
            gw      = execnet.makegateway("popen//python=python%s//chdir=%s" % (Version, folder))
            # os.chdir(folder)
            channel = gw.remote_exec("""
                from %s import %s as the_function
                import ivy.ivy_module
                import sys
                import os
                import json
                sys.argv = ['ivy_init.py', 'quic_server_test_stream.ivy']
                #channel.send(os.getcwd())
                with ivy.ivy_module.Module():
                    tree = the_function(**channel.receive())
                
                def is_jsonable(x):
                    try:
                        json.dumps(x)
                        return True
                    except (TypeError, OverflowError):
                        return False

                def my_dict(obj):
                    if not  hasattr(obj,"__dict__"):
                        if is_jsonable(obj):
                            return obj
                        else:
                            element = []
                            if isinstance(obj, list):
                                for item in obj:
                                    element.append(my_dict(item))
                                return element
                            elif isinstance(obj, set):
                                return my_dict(list(obj))
                            else:
                                return str(obj)
                    result = {}
                    for key, val in obj.__dict__.items():
                        if key.startswith("_"):
                            continue
                        element = []
                        if isinstance(val, list):
                            for item in val:
                                element.append(my_dict(item))
                        elif isinstance(val, set):
                            element = my_dict(list(val))
                        elif isinstance(val, dict):
                            for keyi, vali in val.items():
                                if is_jsonable(vali):
                                    element.append(my_dict(vali))
                                else:
                                    element.append(str(vali))
                        else:
                            element = my_dict(val)
                        result[key] = element
                    return result
                # json.loads(json.dumps(tree, default=lambda o: o.__dict__ if hasattr(o, '__dict__') else o))
                res = my_dict(tree)
                #IvyServer.app.logger.info(res)
                channel.send(res)
            """ % (Module, Function))
            channel.send(ArgumentList) # 
            ##IvyServer.app.logger.info(channel.receive())
            return channel.receive()

        # try:
        #     # pedantic=true isolate_mode=test isolate=this
        #     result = call_python_version("2.7", "ivy.ivy_init", "ivy_init",  
        #                                  {"show_compiled":"true", 
        #                                   "pedantic":"true", 
        #                                   "isolate_mode":"test", 
        #                                   "isolate":"this",
        #                                   "ui":"cti",
        #                                   "create_isolate":False}) 
        #     ##IvyServer.app.logger.info(result) 
        #     json_object = json.dumps(result, indent=4)
        #     # Writing to sample.json
        #     with open("/tmp/sample.json", "w") as outfile:
        #         outfile.write(json_object)
        # except Exception as e:
        #     #IvyServer.app.logger.info(e)
            
        def buildNodes(nodeRecord):
            data = {"id": str(nodeRecord.n._id), "label": next(iter(nodeRecord.n.labels))}
            data.update(nodeRecord.n.properties)

            return {"data": data}

        def buildEdges(relationRecord):
            data = {"source": str(relationRecord.r.start_node._id),
                    "target": str(relationRecord.r.end_node._id),
                    "relationship": relationRecord.r.rel.type}

            return {"data": data}
            
        # IvyServer.experiments.remove_includes()
        # IvyServer.experiments.included_files = list()

        # analysis_graph = ivy_init()
        # #IvyServer.app.logger.info(analysis_graph)
        
        # model = IvyServer.get_quic_model()
        # json_object = json.dumps(model, indent=4)
        # # Writing to sample.json
        # os.system("chown root:root /tmp/sample_model.json")
        # with open("/tmp/sample_model.json", "w") as outfile:
        #     outfile.write(json_object)
            
        IvyServer.setup_quic_model()
        IvyServer.setup_cytoscape()
        return render_template('creator.html')

    def run(self):
        IvyServer.app.run(host='0.0.0.0', port=80, use_reloader=True, threaded=True)  #, processes=4
        