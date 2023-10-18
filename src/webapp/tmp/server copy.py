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
            IvyServer.experiments.args.iter = int(request.form["iteration"])
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
                
            #print("SWAG")
            
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
        IvyServer.nb_exp = len(os.listdir(IvyServer.ivy_temps_path)) - 2
        
        
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
        #print(subdf)
        #print(df_csv.columns)
        #print(subdf.columns)
        #subdf.columns = df_csv.columns
        configurationData = [
                {
                "id": str(uuid.uuid4()), # Must be unique TODO df_csv_scdg['filename']
                "name": "Experiences coverage view",
                "parameters": ["Implementation","Run"],
                "measurements": ["NbPktSend"], # , "Total number of blocks",'Number Syscall found' , 'Number Address found', 'Number of blocks visited', "Total number of blocks","time"
                "data": subdf.to_csv()
                },
                {
                "id": str(uuid.uuid4()), # Must be unique TODO df_csv_scdg['filename']
                "name": "Experiences packet view",
                "parameters": ["Implementation","Run"],
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
        configurationData = {
                "id": str(uuid.uuid4()), # Must be unique
                "name": "Quickstart example",
                "parameters": ["N", "algorithm", "num_cpus", "cpu_brand"],
                "measurements": ["efficiency"],
                "data": """algorithm,N,num_cpus,efficiency,cpu_brand
                Algorithm 1,10,1,0.75,Ryzen
                Algorithm 1,10,4,0.85,Ryzen
                Algorithm 1,10,8,0.90,Ryzen
                Algorithm 2,10,1,0.65,Ryzen
                Algorithm 2,10,4,0.80,Ryzen
                Algorithm 2,10,8,0.87,Ryzen
                """, # Raw data in csv format
            }
        export(configurationData, output)
        
        #print(configurationData)
        
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
        
        #print(configurationData)
        
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
    
    def construct_cytoscape_graph():
        elements  = []
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
        os.chdir(IvyServer.ivy_test_path + "server_tests/")
        ivy_file = "quic_server_test_stream.ivy" # TODO
        os.system("chown root:root /tmp/ivy_show_output.txt")
        os.system("ivy_check diagnose=true show_compiled=false pedantic=true trusted=false trace=false isolate_mode=test isolate=this "+ ivy_file +"> /tmp/ivy_show_output.txt")
        os.system("chown root:root /tmp/cytoscape_model.json")
        initializers = False
        in_action = False
        in_action_assumptions = False
        in_action_guarantees = False
        with open("/tmp/ivy_show_output.txt", 'r') as input_file:
            with open("/tmp/cytoscape_model.json", 'w') as output_file:
                input_file_content_lines = input_file.readlines()
                for line in input_file_content_lines:
                    if "/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/" in line:
                        line = line.replace("/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/", "")
                    if "in action" in line:
                        last_action = ""
                        called_from = ""
                        
                    if "implementation of" in line:
                        has_implem = True
                        is_init = False
                        is_frame = False
                        is_module_object = False
                        is_module_object_present = False
                        line = line.replace("implementation of", "")
                        splitted_line = line.split(":")
                        splitted_line[0] = splitted_line[0].replace(" ", "")
                        #print(splitted_line[0])
                        if splitted_line[0] in avoid:
                            #print("=========================================")
                            continue
                        
                        prefix = "/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/"
                        
                        if "server_test" in splitted_line[0]:
                            prefix =  "/tmp/QUIC-FormalVerification/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/server_tests/"
                        elif "client_test" in splitted_line[0]:
                            prefix =  "/tmp/QUIC-FormalVerification/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/client_tests/"
                        
                        if "quic_transport_parameters" in splitted_line[0]:
                            tp_name = splitted_line[2].replace(" ", "").replace(".set","").replace("\n", "")
                            if splitted_line[0] not in mapping:
                                mapping[splitted_line[0]] = {}
                            mapping[splitted_line[0]][tp_name] = []
                            #print(tp_name)
                            #print("**************************************")
                            with open("/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/quic_transport_parameters.ivy", 'r') as f:
                                content = f.read()
                                reached = False
                                for l in content.splitlines():
                                    if "object " + tp_name in l:
                                        reached = True
                                        
                                    if ":" in l and reached:
                                        attr = l.split(":")
                                        if "#" not in attr[0]:
                                            mapping[splitted_line[0]][tp_name].append({
                                                "name": attr[0].replace(" ", ""),
                                                "type": attr[1].replace(" ", "") if "#" not in attr[1] else attr[1].split("#")[0].replace(" ", "")
                                            })
                                        
                                    if reached and "}" in l:
                                        #reached = False
                                        break
                        else:
                            if not splitted_line[0] in mapping:
                                mapping[splitted_line[0]] = [ ]
                            
                            line = int(splitted_line[1].replace("line", "").replace(" ", ""))
                            action_name = splitted_line[2].replace(" ", "").replace("\n", "")
                            #print(action_name)
                            with open(prefix + splitted_line[0], 'r') as f:
                                    content = f.readlines()
                                    
                            #print(mapping[splitted_line[0]])
                            #print(line)
                            #print(len(content))
                            
                            if "." in action_name:
                                # action related to object or module (method)
                                if "frame." in action_name:
                                    is_frame = True
                                    mapping[splitted_line[0]].append({ 
                                        "frame_name" : action_name.replace("frame.", "").split(".")[0],  
                                        "frame_object" : [],                        
                                        "actions": {
                                            "line": line,
                                            "action_name": action_name,
                                            "implementation": [],
                                            "monitor":{
                                                "before": [],
                                                "after": [],
                                                "around": []
                                            },
                                            "action_return" : {
                                                "name": "",
                                                "type": "",
                                            },
                                            "action_parameters": [],
                                            "exported": False if not "export" in content[line-1] else True,
                                            "events": False,
                                            "assertions_as_guarantees": {
                                                "called_from": [],
                                                "assertions":[],
                                            },
                                            "assertions_as_assumption": {
                                                "called_from": [],
                                                "assertions":[],
                                            }
                                        }
                                    })
                                    with open("/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/" + splitted_line[0], 'r') as f:
                                        content = f.read()
                                        reached = False
                                        reached_struct = False
                                        for l in content.splitlines():
                                            if "object " + mapping[splitted_line[0]][-1]["frame_name"] in l:
                                                reached = True
                                                
                                            if reached and "variant" in l and "struct" in l:
                                                reached_struct = True
                                                
                                            if ":" in l and reached_struct: # and not "#" in line
                                                attr = l.split(":") #.replace(" ", "")
                                                if "#" not in attr[0]:
                                                    mapping[splitted_line[0]][-1]["frame_object"].append({
                                                        "name": attr[0].replace(" ", ""),
                                                        "type": attr[1].replace(" ", "") if "#" not in attr[1] else attr[1].split("#")[0].replace(" ", "")
                                                    })
                                                
                                            if reached and reached_struct and "}" in l:
                                                break
                                else:
                                    is_module_object = True
                                    object_name = action_name.split(".")[0]
                                    #print(object_name)
                                    #print(mapping[splitted_line[0]])
                                    if object_name in avoid_impl:
                                        continue
                                    
                                    if "endpoint" in splitted_line[0]:
                                        object_name = object_name+"_ep"
                                    
                                    for obj in mapping[splitted_line[0]]:
                                        #print("checking module present")
                                        #print(obj)
                                        if  object_name + "_name" in obj.keys():
                                            is_module_object_present = True
                                            current_elem = obj
                                            current_elem["actions"].append({
                                                "line": line,
                                                "action_name": action_name,
                                                "implementation": [],
                                                "monitor":{
                                                    "before": [],
                                                    "after": [],
                                                    "around": []
                                                },
                                                "action_return" : {
                                                    "name": "",
                                                    "type": "",
                                                },
                                                "action_parameters": [],
                                                "exported": False if not "export" in content[line-1] else True,
                                                "events": False,
                                                "assertions_as_guarantees": {
                                                    "called_from": [],
                                                    "assertions":[],
                                                },
                                                "assertions_as_assumption": {
                                                    "called_from": [],
                                                    "assertions":[],
                                                }
                                            })
                                            break
                                        
                                    if not is_module_object_present:
                                        mapping[splitted_line[0]].append({ 
                                            object_name + "_name" : action_name.replace("frame.", "").split(".")[0],  
                                            object_name + "_object" : [],    
                                            object_name + "_module" : {
                                                "module_parameters": [],
                                                "module_attributes": [], # Not used, we dont want user to modify it but we keep it in case
                                            },                      
                                            "actions": [{
                                                "line": line,
                                                "action_name": action_name,
                                                "implementation": [],
                                                "monitor":{
                                                    "before": [],
                                                    "after": [],
                                                    "around": []
                                                },
                                                "action_return" : {
                                                    "name": "",
                                                    "type": "",
                                                },
                                                "action_parameters": [],
                                                "exported": False if not "export" in content[line-1] else True,
                                                "events": False,
                                                "assertions_as_guarantees": {
                                                    "called_from": [],
                                                    "assertions":[],
                                                },
                                                "assertions_as_assumption": {
                                                    "called_from": [],
                                                    "assertions":[],
                                                }
                                            }]
                                        })
                                        with open("/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/" + splitted_line[0], 'r') as f:
                                            content = f.read()
                                            reached = False
                                            is_module = False
                                            for l in content.splitlines():
                                                if "object " + mapping[splitted_line[0]][-1][object_name + "_name"]  in l and not reached:
                                                    reached = True
                                                    mapping[splitted_line[0]][-1][object_name + "_module"] = None
                                                elif "module " + mapping[splitted_line[0]][-1][object_name + "_name"]  in l and not reached:
                                                    is_module = True
                                                    reached = True
                                                    bracket_count = 0
                                                    module_parameters = l.split("=")[0].split("(")[1].split(")")[0].split(",")
                                                    for param in module_parameters:
                                                        #print(param)
                                                        mapping[splitted_line[0]][-1][object_name + "_object"] = None
                                                        attr = param.split(":")
                                                        if "#" not in attr[0]:
                                                            mapping[splitted_line[0]][-1][object_name + "_module"]["module_parameters"].append({
                                                                "name": attr[0].replace(" ", ""),
                                                                "type": attr[1].replace(" ", "") if "#" not in attr[1] else attr[1].split("#")[0].replace(" ", "")
                                                            })
                                                
                                                if reached:
                                                    if not is_module:
                                                        if "}" in l or "action" in l:
                                                            break
                                                        if ":" in l: # and not "#" in l
                                                            attr = l.split(":")
                                                            if "#" not in attr[0]:
                                                                if "instance" in attr[0]:
                                                                    mapping[splitted_line[0]][-1][object_name + "_object"].append({
                                                                        "name": attr[0].replace("instance ", "").replace(" ", ""),
                                                                        "type": attr[1].replace(" ", "") if "#" not in attr[1] else attr[1].split("#")[0].replace(" ", ""),
                                                                        "instance": True
                                                                    })
                                                                else:
                                                                    mapping[splitted_line[0]][-1][object_name + "_object"].append({
                                                                        "name": attr[0].replace(" ", ""),
                                                                        "type": attr[1].replace(" ", "") if "#" not in attr[1] else attr[1].split("#")[0].replace(" ", "")
                                                                    })
                                                        
                                                    else:
                                                        # For attributes
                                                        if "after init" in l and bracket_count == 0:
                                                            break
                                                        if "{" in l:
                                                            bracket_count += 1
                            elif "init " in action_name or "init[" in action_name:
                                is_init = True
                                mapping[splitted_line[0]].append({ 
                                    "actions": {
                                        "action_name": "init",
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
                            elif "import " in content[line-1] and not "_finalize" in action_name:
                                has_implem = False
                                mapping[splitted_line[0]].append({ 
                                    "actions": {
                                        "line": line,
                                        "action_name": action_name,
                                        "action_return" : None,
                                        "exported": False if not "export" in content[line-1] else True,
                                        "action_parameters": [],
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
                                        "monitor":{
                                            "before": [],
                                            "after": [],
                                            "around": []
                                        },
                                        "action_return" : {
                                            "name": "",
                                            "type": "",
                                        },
                                        "action_parameters": [],
                                        "exported": False if not "export" in content[line-1] else True,
                                        "events": False,
                                        "assertions_as_guarantees": {
                                            "called_from": [],
                                            "assertions":[],
                                        },
                                        "assertions_as_assumption": {
                                            "called_from": [],
                                            "assertions":[],
                                        }
                                    }
                                })
                            
                            #print(mapping[splitted_line[0]])
                            #print(line)
                            
                            is_implement = False
                            
                            # get action content
                            with open(prefix + splitted_line[0], 'r') as f:
                                    content = f.readlines()
                                    # if line < len(content)-1:
                                    #     signature = content[line]
                                    # else:
                                    signature = content[line-1]
                                    #print(signature)
                                    #print(line)
                                    corrected_line = line
                                    corrected_signature = signature
                                    # Work around to get the right line due to error in ivy_show
                                    while not (action_name.split(".")[-1]  in corrected_signature and ("action" in corrected_signature or "implement" in corrected_signature)) and \
                                          corrected_line < len(content) and corrected_line >= 0:
                                        corrected_line += 1
                                        corrected_signature = content[corrected_line-1]
                                        if action_name.split(".")[-1] in corrected_signature and \
                                            ("action" in corrected_signature or "implement" in corrected_signature):
                                            line = corrected_line
                                            signature = corrected_signature
                                            
                                            if "implement" in corrected_signature:
                                                is_implement = True
                                            # TODO TypeError: list indices must be integers or slices, not str
                                            #mapping[splitted_line[0]][-1]["actions"]["line"] = corrected_line
                                            #print("FOUND 1")
                                            break
                                        
                                    
                                    corrected_line = line
                                    corrected_signature = signature
                                    #print(action_name.split(".")[-1])
                                    
                                    # TODO problem -> separate action and implement
                                    while not (action_name.split(".")[-1] in corrected_signature and ("action" in corrected_signature or "implement" in corrected_signature)) and \
                                          corrected_line < len(content) and corrected_line >= 0:
                                        corrected_line -= 1
                                        corrected_signature = content[corrected_line-1]
                                        if action_name.split(".")[-1] in corrected_signature and \
                                            ("action" in corrected_signature or "implement" in corrected_signature):
                                            line = corrected_line
                                            signature = corrected_signature
                                            #mapping[splitted_line[0]][-1]["actions"]["line"] = corrected_line
                                            #print("FOUND 2")
                                            
                                            if "implement" in corrected_signature:
                                                is_implement = True
                                                
                                            break
                                    
                                    #print(corrected_signature)
                                    #print(line)
                                    #print(signature) 
                                    
                                    if is_module_object:
                                        if not is_module_object_present:
                                            #print("not is_module_object_present")
                                            current_elem = mapping[splitted_line[0]][-1]["actions"][-1]
                                        else:
                                            #print("is_module_object_present")
                                            current_elem = mapping[splitted_line[0]][-1]["actions"][-1]
                                    else:
                                        current_elem = mapping[splitted_line[0]][-1]["actions"]
                                    #print(current_elem)
                                    
                                    if not is_init:
                                        signature = signature.replace("action ", "")
                                        signature = signature.replace(current_elem["action_name"], "")
                                        if not "{" in signature: #  and not is_frame
                                            has_implem = False
                                        if not "returns" in signature:
                                            current_elem["action_return"] = None
                                            if "(" in signature:
                                                action_parameters = signature.split("=")[0].split("(")[1].split(")")[0].split(",")
                                                #print(action_parameters)
                                                for param in action_parameters:
                                                    #print(param)
                                                    attr = param.split(":")
                                                    if "#" not in attr[0]:
                                                        current_elem["action_parameters"].append({
                                                            "name": attr[0].replace(" ", ""),
                                                            "type": attr[1].replace(" ", "") if "#" not in attr[1] else attr[1].split("#")[0].replace(" ", "")
                                                        })
                                            else:
                                                if not is_implement:
                                                    current_elem["action_parameters"] = None
                                                else:
                                                    for l in content:
                                                        if action_name.split(".")[-1] in l and \
                                                           "action" in l:
                                                            action_parameters = l.split("=")[0].split("(")[1].split(")")[0].split(",")
                                                            #print(action_parameters)
                                                            for param in action_parameters:
                                                                #print(param)
                                                                attr = param.split(":")
                                                                if "#" not in attr[0]:
                                                                    current_elem["action_parameters"].append({
                                                                        "name": attr[0].replace(" ", ""),
                                                                        "type": attr[1].replace(" ", "") if "#" not in attr[1] else attr[1].split("#")[0].replace(" ", "")
                                                                    })
                                                    
                                        else:
                                            action_return = signature.split("returns")[1].split("(")[1].split(")")[0].split(":")
                                            current_elem["action_return"]["name"] = action_return[0]
                                            current_elem["action_return"]["type"] = action_return[1]
                                            if "(" in signature.split("returns")[0]:
                                                action_parameters = signature.split("returns")[0].split("(")[1].split(")")[0].split(",")
                                                #print(action_parameters)
                                                for param in action_parameters:
                                                    #print(param)
                                                    attr = param.split(":")
                                                    if "#" not in attr[0]:
                                                        current_elem["action_parameters"].append({
                                                            "name": attr[0].replace(" ", ""),
                                                            "type": attr[1].replace(" ", "") if "#" not in attr[1] else attr[1].split("#")[0].replace(" ", "")
                                                        })
                                            else:
                                                if not is_implement:
                                                    current_elem["action_parameters"] = None
                                                else:
                                                    for l in content:
                                                        if action_name.split(".")[-1] in l and \
                                                           "action" in l:
                                                            action_return = l.split("returns")[1].split("(")[1].split(")")[0].split(":")
                                                            current_elem["action_return"]["name"] = action_return[0]
                                                            current_elem["action_return"]["type"] = action_return[1]
                                                            if "(" in l.split("returns")[0]:
                                                                action_parameters = l.split("returns")[0].split("(")[1].split(")")[0].split(",")
                                                                #print(action_parameters)
                                                                for param in action_parameters:
                                                                    #print(param)
                                                                    attr = param.split(":")
                                                                    if "#" not in attr[0]:
                                                                        current_elem["action_parameters"].append({
                                                                            "name": attr[0].replace(" ", ""),
                                                                            "type": attr[1].replace(" ", "") if "#" not in attr[1] else attr[1].split("#")[0].replace(" ", "")
                                                                        })
                                    else:
                                        current_elem["action_parameters"] = None
                                        current_elem["action_return"] = None
                                    if has_implem:
                                        bracket_count = 0
                                        c_line = line
                                        for l in content[line:]:
                                            if "}" in l:
                                                if bracket_count == 0:
                                                    break
                                                bracket_count -= 1
                                            if "{" in l:
                                                bracket_count += 1
                                            #if current_elem["implementation"].count(l) == 0: 
                                            if len(current_elem["implementation"]) > 0 and current_elem["implementation"][-1]["line"] < c_line: # Not sure it is always true
                                                current_elem["implementation"].append({"line":c_line, 
                                                                                       "file":splitted_line[0],
                                                                                       "instruction":l}) # TODO check doublons
                                            else:
                                                current_elem["implementation"].append({"line":c_line, 
                                                                                       "file":splitted_line[0],
                                                                                       "instruction":l})
                                            c_line += 1
                            #print(splitted_line[0])
                            #print(mapping[splitted_line[0]])
                            #print("============================================")
                    
                    elif "monitor of" in line:
                        line = line.replace("monitor of", "")
                        splitted_line = line.split(":")
                        splitted_line[0] = splitted_line[0].replace(" ", "")
                        #print(splitted_line[0])
                        
                        if splitted_line[0] in avoid:
                            #print("=========================================")
                            continue
                        
                        prefix = "/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/"
                        
                        if "server_test" in splitted_line[0]:
                            prefix =  "/tmp/QUIC-FormalVerification/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/server_tests/"
                        elif "client_test" in splitted_line[0]:
                            prefix =  "/tmp/QUIC-FormalVerification/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/client_tests/"
                        if not splitted_line[0] in mapping:
                            mapping[splitted_line[0]] = [ ]
                            
                        line = int(splitted_line[1].replace("line", "").replace(" ", ""))
                        action_name = splitted_line[2].replace(" ", "").replace("\n", "")
                        #print(action_name)
                        with open(prefix + splitted_line[0], 'r') as f:
                            content = f.readlines()
                                    
                        #print(mapping[splitted_line[0]])
                        #print(line)
                        #print(len(content))
                        
                        # Get monitor type
                        with open(prefix + splitted_line[0], 'r') as f:
                            content = f.readlines()
                            signature = content[line-1]
                            #print(signature)
                            #print(line)
                            corrected_line = line
                            corrected_signature = signature
                            signature_type = "around" if "around" in corrected_signature else "after" if "after" in corrected_signature else "before"
                            # Work around to get the right line due to error in ivy_show
                            while not (action_name.split(".")[-1]  in corrected_signature and ("around" in corrected_signature or "after" in corrected_signature or "before" in corrected_signature)) and \
                                    corrected_line < len(content) and corrected_line >= 0:
                                corrected_line += 1
                                corrected_signature = content[corrected_line-1]
                                if action_name.split(".")[-1] in corrected_signature and \
                                    ("around" in corrected_signature or "after" in corrected_signature or "before" in corrected_signature):
                                    line = corrected_line
                                    signature = corrected_signature
                                    # TODO TypeError: list indices must be integers or slices, not str
                                    #mapping[splitted_line[0]][-1]["actions"]["line"] = corrected_line
                                    signature_type = "around" if "around" in corrected_signature else "after" if "after" in corrected_signature else "before"
                                    #print("FOUND 1")
                                    break
                                               
                            corrected_line = line
                            corrected_signature = signature
                            #print(action_name.split(".")[-1])
                                    
                            # TODO problem
                            while not (action_name.split(".")[-1]  in corrected_signature and ("around" in corrected_signature or "after" in corrected_signature or "before" in corrected_signature)) and \
                                  corrected_line < len(content) and corrected_line >= 0:
                                corrected_line -= 1
                                corrected_signature = content[corrected_line-1]
                                if action_name.split(".")[-1] in corrected_signature and \
                                    ("around" in corrected_signature or "after" in corrected_signature or "before" in corrected_signature):
                                    line = corrected_line
                                    signature = corrected_signature
                                    #mapping[splitted_line[0]][-1]["actions"]["line"] = corrected_line
                                    signature_type = "around" if "around" in corrected_signature else "after" if "after" in corrected_signature else "before"
                                    #print("FOUND 2")
                                    break
                            
                            print("°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°")
                            print(corrected_signature)    
                            print(line)
                            print(signature) 
                            print(signature_type)
                            print(action_name)
                            print(splitted_line[0])
                            print("°°°°°")
                            is_module_object_present = False
                            current_action = None
                            another_file = False
                            if "." in action_name:
                                # TODO uniformize frame and module and object
                                if "frame" in action_name:
                                    object_name = action_name.split(".")[0]
                                    for obj in mapping[splitted_line[0]]:
                                        # print("checking module present")
                                        # print(obj)
                                        if  object_name + "_name" in obj.keys():
                                            is_module_object_present = True
                                            if obj["actions"]["action_name"] == action_name:
                                                current_action = obj["actions"]
                                                break
                                    if current_action == None: # is_module_object_present and 
                                        print("current_action == None")
                                        another_file = True
                                else:
                                    object_name = action_name.split(".")[0]
                                    print(object_name)
                                    for obj in mapping[splitted_line[0]]:
                                        # print("checking module present")
                                        # print(obj)
                                        if  object_name + "_name" in obj.keys():
                                            is_module_object_present = True
                                            for act in obj["actions"]:
                                                if act["action_name"] == action_name:
                                                    current_action = act
                                                    break
                                    if current_action == None: # is_module_object_present and 
                                        print("current_action == None")
                                        # mapping[splitted_line[0]][-1]["actions"].append({ 
                                        #     "line": line,
                                        #     "action_name": action_name,
                                        #     "implementation": [],
                                        #     "monitor":{
                                        #         "before": [],
                                        #         "after": [],
                                        #         "around": []
                                        #     },
                                        #     "action_return" : {
                                        #         "name": "",
                                        #         "type": "",
                                        #     },
                                        #     "action_parameters": [],
                                        #     "exported": False if not "export" in content[line-1] else True,
                                        #     "events": False
                                        # })
                                        # current_action = mapping[splitted_line[0]][-1]["actions"]
                                        another_file = True
                            else:
                                for obj in mapping[splitted_line[0]]:
                                    # print("checking action present")
                                    # print(obj)
                                    if not isinstance(obj["actions"], list): # else mean it is a module
                                        if obj["actions"]["action_name"] == action_name: 
                                            current_action = obj["actions"]
                                            break
                                if current_action == None:
                                    print("current_action == None")
                                    # mapping[splitted_line[0]].append({ 
                                    #                     "actions": {
                                    #                         "line": line,
                                    #                         "action_name": action_name,
                                    #                         "implementation": [],
                                    #                         "monitor":{
                                    #                             "before": [],
                                    #                             "after": [],
                                    #                             "around": []
                                    #                         },
                                    #                         "action_return" : {
                                    #                             "name": "",
                                    #                             "type": "",
                                    #                         },
                                    #                         "action_parameters": [],
                                    #                         "exported": False if not "export" in content[line-1] else True,
                                    #                         "events": False
                                    #                     }
                                    #                 })
                                    # current_action = mapping[splitted_line[0]][-1]["actions"]
                                    another_file = True
                            ##print(splitted_line[0])
                            
                            is_new_file = False
                            new_file = None
                            
                            # if current_action == None:
                            #     print(splitted_line[0])
                            #     print(action_name)
                            #     print(line)
                            #     print("++++++++++++++++++++++")
                            found = False
                            #if current_action == None:
                            if another_file:
                                is_new_file = True
                                # Maybe better to create new file ? 
                                # We choose to append to existing file containing action
                                for file in mapping.keys():
                                    if file != "quic_transport_parameters.ivy" and not found and file != splitted_line[0]:
                                        print(file)
                                        if "." in action_name:
                                            # TODO uniformize frame and module and object
                                            if "frame" in action_name:
                                                object_name = action_name.split(".")[0]
                                                for obj in mapping[file]:
                                                    #print("checking module present")
                                                    #print(obj)
                                                    if  object_name + "_name" in obj.keys():
                                                        is_module_object_present = True
                                                        if obj["actions"]["action_name"] == action_name:
                                                            print("Found")
                                                            current_action = obj["actions"]
                                                            # new_file = file
                                                            # current_action["action_return"] = obj["actions"]["action_return"]
                                                            # current_action["action_parameters"] = obj["actions"]["action_parameters"]
                                                            # with open(prefix + new_file, 'r') as f:
                                                            #     content = f.readlines()
                                                            found = True
                                                            break
                                            else:
                                                object_name = action_name.split(".")[0]
                                                for obj in mapping[file]:
                                                    #print("checking module present")
                                                    #print(obj)
                                                    if  object_name + "_name" in obj.keys():
                                                        is_module_object_present = True
                                                        for act in obj["actions"]:
                                                            if act["action_name"] == action_name:
                                                                print("Found 2")
                                                                current_action = act
                                                                # current_action["action_return"] = act["action_return"]
                                                                # current_action["action_parameters"] = act["action_parameters"]
                                                                # new_file = file
                                                                # with open(prefix + new_file, 'r') as f:
                                                                #     content = f.readlines()
                                                                found = True
                                                                break
                                        #         if is_module_object_present and current_action == None:
                                        #             mapping[file].append({ 
                                        #                 "actions": {
                                        #                     "line": line,
                                        #                     "action_name": action_name,
                                        #                     "implementation": [],
                                        #                     "monitor":{
                                        #                         "before": [],
                                        #                         "after": [],
                                        #                         "around": []
                                        #                     },
                                        #                     "action_return" : {
                                        #                         "name": "",
                                        #                         "type": "",
                                        #                     },
                                        #                     "action_parameters": [],
                                        #                     "exported": False if not "export" in content[line-1] else True,
                                        #                     "events": False
                                        #                 }
                                        #             })
                                        else:
                                            for obj in mapping[file]:
                                                # print("checking action present")
                                                # print(obj)
                                                if not isinstance(obj["actions"], list): # else mean it is a module
                                                    if obj["actions"]["action_name"] == action_name: 
                                                        print("Found 3")
                                                        current_action = obj["actions"]
                                                        # new_file = file
                                                        # print(prefix + new_file)
                                                        # current_action["action_return"] = obj["actions"]["action_return"]
                                                        # current_action["action_parameters"] = obj["actions"]["action_parameters"]
                                                        # with open(prefix + new_file, 'r') as f:
                                                        #     content = f.readlines()
                                                        #     print(content[-1])
                                                        found = True
                                                        break
                                            # if current_action == None:
                                            #     mapping[file][-1]["actions"] = { 
                                            #         "line": line,
                                            #         "action_name": action_name,
                                            #         "implementation": [],
                                            #         "monitor":{
                                            #             "before": [],
                                            #             "after": [],
                                            #             "around": []
                                            #         },
                                            #         "action_return" : {
                                            #             "name": "",
                                            #             "type": "",
                                            #         },
                                            #         "action_parameters": [],
                                            #         "exported": False if not "export" in content[line-1] else True,
                                            #         "events": False
                                            #     }
                                    if found:
                                        break
                            print("°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°")
                            
                            if another_file and not found:
                                print(action_name)
                                print(splitted_line[0])
                                continue

                            if current_action and signature_type in ["around", "after", "before"]: # current_action and
                                print("getting_monitor_content")
                                print(line)
                                print(content[line])
                                bracket_count = 0
                                c_line = line
                                for l in content[line:]:
                                    if "}" in l:
                                        if bracket_count == 0:
                                            break
                                        bracket_count -= 1
                                    if "{" in l:
                                        bracket_count += 1
                                    #if current_action["monitor"][signature_type].count(l) == 0:
                                    if len(current_action["monitor"][signature_type]) > 0 and current_action["monitor"][signature_type][-1]["line"] < c_line:
                                        current_action["monitor"][signature_type].append({"line":c_line, 
                                                                                          "file":splitted_line[0] if new_file == None else new_file,
                                                                                          "instruction":l})
                                    elif len(current_action["monitor"][signature_type]) == 0:
                                        current_action["monitor"][signature_type].append({"line":c_line, 
                                                                                          "file":splitted_line[0] if new_file == None else new_file,
                                                                                          "instruction":l})
                                    c_line += 1
                            else:
                                print("ERROR")
                                print(signature_type)
                                pass
                                #print("ERROR")
                                #exit(0) 
                    
                    elif "initializers are" in line:
                        initializers = True
                    elif "Initialization must establish the invariant" in line:
                        initializers = False
                    elif initializers:
                        print("------------- initializers -------------")
                        #line = line.replace("line ", "")
                        splitted_line = line.split(":")
                        splitted_line[0] = splitted_line[0].replace(" ", "")
                        #print(splitted_line[0])
                        
                        if len(splitted_line[0]) != 3:
                            continue
                        
                        if splitted_line[0] in avoid:
                            #print("=========================================")
                            continue
                        
                        prefix = "/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/"
                        
                        if "server_test" in splitted_line[0]:
                            prefix =  "/tmp/QUIC-FormalVerification/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/server_tests/"
                        elif "client_test" in splitted_line[0]:
                            prefix =  "/tmp/QUIC-FormalVerification/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/client_tests/"
                        if not splitted_line[0] in mapping:
                            mapping[splitted_line[0]] = [ ]
                        
                        print(splitted_line)
                        line = int(splitted_line[1].replace("line", "").replace(" ", ""))
                        action_name = splitted_line[2].replace(" ", "").replace("\n", "")
                        
                        if "." in action_name:
                            pass # we dont want initializer of module object, already parsed before
                        #print(action_name)
                        with open(prefix + splitted_line[0], 'r') as f:
                            content = f.readlines()
                                    
                        #print(mapping[splitted_line[0]])
                        #print(line)
                        #print(len(content))
                        
                        # Get monitor type
                        with open(prefix + splitted_line[0], 'r') as f:
                            content = f.readlines()   
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
                            bracket_count = 0
                            c_line = line
                            for l in content[line:]:
                                if "}" in l:
                                    if bracket_count == 0:
                                        break
                                        bracket_count -= 1
                                    if "{" in l:
                                        bracket_count += 1
                                    #if current_elem["implementation"].count(l) == 0: 
                                    if len(current_elem["implementation"]) > 0 and current_elem["implementation"][-1]["line"] < c_line: # Not sure it is always true
                                        current_elem["implementation"].append({"line":c_line, 
                                                                                "file":splitted_line[0],
                                                                               "instruction":l}) # TODO check doublons
                                    else:
                                        current_elem["implementation"].append({"line":c_line, 
                                                                               "file":splitted_line[0],
                                                                               "instruction":l})
                                    c_line += 1
                        
                    
                    elif "ext:" in line:
                        action_name = line.split("ext:")[-1].replace("\n","")
                        print(action_name)
                        found = False
                        for file in mapping.keys():
                            if file != "quic_transport_parameters.ivy" and not found:
                                print(file)
                                if "." in action_name:
                                    # TODO uniformize frame and module and object
                                    if "frame" in action_name:
                                        object_name = action_name.split(".")[0]
                                        print(object_name)
                                        for obj in mapping[file]:
                                            #print("checking module present")
                                            #print(obj)
                                            if  object_name + "_name" in obj.keys():
                                                is_module_object_present = True
                                                if obj["actions"]["action_name"] == action_name:
                                                    print("Found")
                                                    #current_action = obj["actions"]
                                                    obj["actions"]["exported"] = True
                                                    # new_file = file
                                                    # current_action["action_return"] = obj["actions"]["action_return"]
                                                    # current_action["action_parameters"] = obj["actions"]["action_parameters"]
                                                    # with open(prefix + new_file, 'r') as f:
                                                    #     content = f.readlines()
                                                    found = True
                                                    break
                                    else:
                                        object_name = action_name.split(".")[0]
                                        for obj in mapping[file]:
                                            #print("checking module present")
                                            #print(obj)
                                            if  object_name + "_name" in obj.keys():
                                                is_module_object_present = True
                                                for act in obj["actions"]:
                                                    if act["action_name"] == action_name:
                                                        print("Found 2")
                                                        #current_action = act
                                                        act["exported"] = True
                                                                # current_action["action_return"] = act["action_return"]
                                                                # current_action["action_parameters"] = act["action_parameters"]
                                                                # new_file = file
                                                                # with open(prefix + new_file, 'r') as f:
                                                                #     content = f.readlines()
                                                        found = True
                                                        break
                                        #         if is_module_object_present and current_action == None:
                                        #             mapping[file].append({ 
                                        #                 "actions": {
                                        #                     "line": line,
                                        #                     "action_name": action_name,
                                        #                     "implementation": [],
                                        #                     "monitor":{
                                        #                         "before": [],
                                        #                         "after": [],
                                        #                         "around": []
                                        #                     },
                                        #                     "action_return" : {
                                        #                         "name": "",
                                        #                         "type": "",
                                        #                     },
                                        #                     "action_parameters": [],
                                        #                     "exported": False if not "export" in content[line-1] else True,
                                        #                     "events": False
                                        #                 }
                                        #             })
                                else:
                                    for obj in mapping[file]:
                                        # print("checking action present")
                                        # print(obj)
                                        if not isinstance(obj["actions"], list): # else mean it is a module
                                            if obj["actions"]["action_name"] == action_name: 
                                                print("Found 3")
                                                #current_action = obj["actions"]
                                                obj["actions"]["exported"] = True
                                                        # new_file = file
                                                        # print(prefix + new_file)
                                                        # current_action["action_return"] = obj["actions"]["action_return"]
                                                        # current_action["action_parameters"] = obj["actions"]["action_parameters"]
                                                        # with open(prefix + new_file, 'r') as f:
                                                        #     content = f.readlines()
                                                        #     print(content[-1])
                                                found = True
                                                break
                                            # if current_action == None:
                                            #     mapping[file][-1]["actions"] = { 
                                            #         "line": line,
                                            #         "action_name": action_name,
                                            #         "implementation": [],
                                            #         "monitor":{
                                            #             "before": [],
                                            #             "after": [],
                                            #             "around": []
                                            #         },
                                            #         "action_return" : {
                                            #             "name": "",
                                            #             "type": "",
                                            #         },
                                            #         "action_parameters": [],
                                            #         "exported": False if not "export" in content[line-1] else True,
                                            #         "events": False
                                            #     }
                            # if found:
                            #     break
                    elif "guarantees" in line:
                        in_action_assumptions = False
                        in_action_guarantees = True
                        print("------- in_action_guarantees -------")
                    elif "assumptions" in line:
                        in_action_assumptions = True
                        in_action_guarantees = False
                        print("------- in_action_assumptions -------")
                    elif "in action" in line:
                        print("------------- in action -------------")
                        in_action_bool = True
                        found = False
                        line = line.replace("in action","")
                        line = line.replace(":\n","")
                        action_name = line.split(" when called from ")[0].replace(" ","")
                        print(action_name)
                        for file in mapping.keys():
                            if file != "quic_transport_parameters.ivy" and not found:
                                print(file)
                                if "." in action_name:
                                    # TODO uniformize frame and module and object
                                    if "frame" in action_name:
                                        object_name = action_name.split(".")[0]
                                        print(object_name)
                                        for obj in mapping[file]:
                                            #print("checking module present")
                                            #print(obj)
                                            if  object_name + "_name" in obj.keys():
                                                is_module_object_present = True
                                                if obj["actions"]["action_name"] == action_name:
                                                    print("Found")
                                                    #current_action = obj["actions"]
                                                    if in_action_assumptions:
                                                        for elem in line.split(" when called from ")[-1].split(","):
                                                            if elem not in obj["actions"]["assertions_as_assumption"]["called_from"]:
                                                                obj["actions"]["assertions_as_assumption"]["called_from"].append(elem)
                                                        in_action = obj["actions"]["assertions_as_assumption"]
                                                    elif in_action_guarantees:
                                                        for elem in line.split(" when called from ")[-1].split(","):
                                                            if elem not in obj["actions"]["assertions_as_guarantees"]["called_from"]:
                                                                obj["actions"]["assertions_as_guarantees"]["called_from"].append(elem)
                                                        in_action = obj["actions"]["assertions_as_guarantees"]
                                                    #in_action = obj['actions']
                                                    found = True
                                                    break
                                    else:
                                        object_name = action_name.split(".")[0]
                                        for obj in mapping[file]:
                                            #print("checking module present")
                                            #print(obj)
                                            if  object_name + "_name" in obj.keys():
                                                is_module_object_present = True
                                                for act in obj["actions"]:
                                                    if act["action_name"] == action_name:
                                                        print("Found 2")
                                                        #current_action = act
                                                        # act["exported"] = True
                                                        if in_action_assumptions:
                                                            for elem in line.split(" when called from ")[-1].split(","):
                                                                if elem not in act["assertions_as_assumption"]["called_from"]:
                                                                    act["assertions_as_assumption"]["called_from"].append(elem)
                                                            in_action = act["assertions_as_assumption"]
                                                        elif in_action_guarantees:
                                                            for elem in line.split(" when called from ")[-1].split(","):
                                                                if elem not in act["assertions_as_guarantees"]["called_from"]:
                                                                    act["assertions_as_guarantees"]["called_from"].append(elem)
                                                            in_action = act["assertions_as_guarantees"]
                                                        #in_action = act
                                                        found = True
                                                        break
   
                                else:
                                    for obj in mapping[file]:
                                        # print("checking action present")
                                        # print(obj)
                                        if not isinstance(obj["actions"], list): # else mean it is a module
                                            if obj["actions"]["action_name"] == action_name: 
                                                print("Found 3")
                                                if in_action_assumptions:
                                                    for elem in line.split(" when called from ")[-1].split(","):
                                                        if elem not in obj["actions"]["assertions_as_assumption"]["called_from"]:
                                                            obj["actions"]["assertions_as_assumption"]["called_from"].append(elem)
                                                    in_action = obj["actions"]["assertions_as_assumption"]
                                                elif in_action_guarantees:
                                                    for elem in line.split(" when called from ")[-1].split(","):
                                                        if elem not in obj["actions"]["assertions_as_guarantees"]["called_from"]:
                                                            obj["actions"]["assertions_as_guarantees"]["called_from"].append(elem)
                                                    in_action = obj["actions"]["assertions_as_guarantees"]
                                                found = True
                                                break
                            
                    elif in_action_assumptions and "assumption" in line:
                        print("in_action_assumptions and assumption in line")
                        splitted_line = line.split(":")
                        splitted_line[0] = splitted_line[0].replace(" ", "")
                        #print(splitted_line[0])
                        
                        # if len(splitted_line[0]) != 3:
                        #     continue
                        
                        if splitted_line[0] in avoid:
                            #print("=========================================")
                            continue
                        
                        prefix = "/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/"
                        
                        if "server_test" in splitted_line[0]:
                            prefix =  "/tmp/QUIC-FormalVerification/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/server_tests/"
                        elif "client_test" in splitted_line[0]:
                            prefix =  "/tmp/QUIC-FormalVerification/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/client_tests/"
                        if not splitted_line[0] in mapping:
                            mapping[splitted_line[0]] = [ ]
                        
                        print(splitted_line)
                        line = int(splitted_line[1].replace("line", "").replace(" ", ""))
                        print(line)
                        
                        with open(prefix + splitted_line[0], 'r') as f:
                            content = f.readlines()
                                    
                        #print(mapping[splitted_line[0]])
                        #print(line)
                        #print(len(content))
                        i = 2
                        assertion_line = content[line-1]
                        while "require" not in assertion_line:
                            assertion_line += content[line-i]
                            i += 1
                        
                        assertion_line = assertion_line.lstrip()
                            
                        print(assertion_line)
                        
                        # Get monitor type
                        with open(prefix + splitted_line[0], 'r') as f:
                            content = f.readlines() 
                            
                            in_action["assertions"].append({
                                "line":line,
                                "file":splitted_line[0],
                                "assertion":assertion_line,
                            })
                            
                             
                    elif in_action_guarantees and "guarantee" in line:
                        print("in_action_guarantees and guarantee in line")
                        splitted_line = line.split(":")
                        splitted_line[0] = splitted_line[0].replace(" ", "")
                        #print(splitted_line[0])
                        
                        print(splitted_line[0])
                        
                        # if len(splitted_line[0]) != 3:
                        #     continue
                        
                        if splitted_line[0] in avoid:
                            #print("=========================================")
                            continue
                        
                        prefix = "/usr/local/lib/python2.7/dist-packages/ms_ivy-1.8.24-py2.7.egg/ivy/include/1.7/"
                        
                        if "server_test" in splitted_line[0]:
                            prefix =  "/tmp/QUIC-FormalVerification/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/server_tests/"
                        elif "client_test" in splitted_line[0]:
                            prefix =  "/tmp/QUIC-FormalVerification/QUIC-Ivy-Attacker/doc/examples/quic/quic_tests/client_tests/"
                        if not splitted_line[0] in mapping:
                            mapping[splitted_line[0]] = [ ]
                        
                        print(splitted_line)
                        line = int(splitted_line[1].replace("line", "").replace(" ", ""))
                        
                        print(line)
                       
                        
                        with open(prefix + splitted_line[0], 'r') as f:
                            content = f.readlines()
                                    
                        print(content[line-1])
                        
                        i = 2
                        assertion_line = content[line-1]
                        while "require" not in assertion_line:
                            assertion_line += content[line-i]
                            i += 1
                            
                        assertion_line = assertion_line.lstrip()
                            
                        #print(mapping[splitted_line[0]])
                        #print(line)
                        #print(len(content))
                        
                        # Get monitor type
                        with open(prefix + splitted_line[0], 'r') as f:
                            content = f.readlines() 
                            
                            in_action["assertions"].append({
                                "line":line,
                                "file":splitted_line[0],
                                "assertion":assertion_line,
                            })
                    
                os.chdir(current_dir)
                json_object = json.dumps(mapping, indent=4)
                output_file.write(json_object)




    def get_quic_model():
        """
        It returns the quic model
        :param quic_model: the quic model
        :return: the quic model
        """
        base_path_test = os.path.join(IvyServer.ivy_model_path,"quic_tests/client_tests/quic_client_test.ivy")
        model = {}
        
        # TODO use ivy parser
        
        includes_to_add = []
        includes_to_done = []
        with open(base_path_test, 'r') as f:
            content = f.read()
            for line in content.splitlines():
                if line.startswith("include "):
                    IvyServer.app.logger.info(line)
                    includes_to_add.append(line.split(' ')[-1]+".ivy")
                    
        IvyServer.app.logger.info(includes_to_add)
        
        model["ivy_base"] = {}
        
        while len(includes_to_add) > 0:
            IvyServer.app.logger.info(includes_to_add)  
            for dir in os.listdir(IvyServer.ivy_model_path):
                IvyServer.app.logger.info(dir)      
                if os.path.isdir(os.path.join(IvyServer.ivy_model_path,dir)) and ('quic_' in dir or 'tls_' in dir ) and dir != 'quic_tests': #  and dir != 'quic_fsm'
                    if dir not in model:
                        model[dir] = {}
                    for file in os.listdir(IvyServer.ivy_model_path + '/' + dir):
                        IvyServer.app.logger.info(file) 
                        if '.ivy' in file and file in includes_to_add:
                            includes_to_add.remove(file)
                            includes_to_done.append(file)
                            if file not in model[dir]:
                                model[dir][file] = {}
                                model[dir][file]["include"] = []
                                model[dir][file]["function"] = []
                                model[dir][file]["relation"] = []
                                model[dir][file]["export"] = []
                                model[dir][file]["action"] = {}
                            with open(IvyServer.ivy_model_path + '/' + dir + '/' + file, 'r') as f:
                                content = f.read()
                                for line in content.splitlines():
                                    line = line.lstrip()
                                    if line.startswith("include "):
                                        IvyServer.app.logger.info(line)
                                        include_ivy = line.split("#")[0]
                                        include_ivy = include_ivy.split(' ')[-1]+".ivy"
                                        if include_ivy != ".ivy":
                                            if include_ivy not in includes_to_done and include_ivy not in includes_to_add:
                                                includes_to_add.append(include_ivy)
                                            model[dir][file]["include"].append(include_ivy)
                                    elif line.startswith("function "):
                                        IvyServer.app.logger.info(line)
                                        include_ivy = line.split("#")[0]
                                        include_ivy = include_ivy.replace("function ", '')
                                        if include_ivy != ".ivy":
                                            model[dir][file]["function"].append(include_ivy)
                                    elif line.startswith("relation "):
                                        IvyServer.app.logger.info(line)
                                        include_ivy = line.split("#")[0]
                                        include_ivy = include_ivy.replace("relation ", '')
                                        if include_ivy != ".ivy":
                                            model[dir][file]["relation"].append(include_ivy)
                                    elif line.startswith("export "):
                                        IvyServer.app.logger.info(line)
                                        include_ivy = line.split("#")[0]
                                        include_ivy = include_ivy.replace("export ", '')
                                        if include_ivy != ".ivy":
                                            model[dir][file]["export"].append(include_ivy)
                                    elif line.startswith("action "):
                                        IvyServer.app.logger.info(line)
                                        include_ivy = line.split("#")[0]
                                        include_ivy = include_ivy.replace("action ", '')
                                        if include_ivy != ".ivy":
                                            if include_ivy not in model[dir][file]["action"]:
                                                model[dir][file]["action"][include_ivy] = []
                                            
                            IvyServer.app.logger.info(model)  
            for file in os.listdir(IvyServer.ivy_include_path):
                IvyServer.app.logger.info(file) 
                if '.ivy' in file and file in includes_to_add:
                    includes_to_add.remove(file)
                    includes_to_done.append(file)
                    if file not in model["ivy_base"]:
                        model["ivy_base"][file] = {}
                    with open(IvyServer.ivy_include_path  + '/' + file, 'r') as f:
                        content = f.read()
                        for line in content.splitlines():
                            if line.startswith("include "):
                                IvyServer.app.logger.info(line)
                                include_ivy = line.split("#")[0]
                                include_ivy = include_ivy.split(' ')[-1]+".ivy"
                                if include_ivy != ".ivy":
                                    if include_ivy not in includes_to_done and include_ivy not in includes_to_add:
                                        includes_to_add.append(include_ivy)
                                    model["ivy_base"][file]["include"] = include_ivy
                    IvyServer.app.logger.info(model) 
        #IvyServer.app.logger.info(json.dumps(model, indent=4, sort_keys=True))                 
        return model
    
    
    @app.route('/kg/graph/json', methods = ['GET'])
    def get_json_graph():
        """
        It returns the json graph of the knowledge graph
        :return: the json graph of the knowledge graph
        """ 
        parents = []
        with open("/tmp/cytoscape_config.json", 'r') as json_file:
            data = json.load(json_file)
            ##print(len(data))
            i = 0
            to_remove = []
            for elem in data:
                if elem["group"] == "shapes":
                    #del data[elem]
                    ##print("swag")
                    #elem = None
                    to_remove.append(elem)
                data[i]["locked"] = False
                if data[i]["group"] == "nodes":
                    data[i]["position"] = None
                if data[i]["group"] == "edges":
                    data[i]["data"]["approxpoints"] = None
                    data[i]["data"]["bspline"] = None
                    data[i]["data"]["arrowend"] = None
                # if "cluster" in data[i]["data"]:
                #     data[i]["data"]["parent"] = data[i]["data"]["cluster"]
                if "\n" in data[i]["data"]["label"]: # probably a module
                    children = data[i]["data"]["label"].split("\n")[1:]
                    children_updated = []
                    for child in children:
                        child = child.split(".")[0]
                        children_updated.append(child)
                    for elem in data:
                        if elem["data"]["label"] in children_updated:
                            elem["data"]["parent"] = data[i]["data"]["id"]
                            data[i]["data"]["label"] = data[i]["data"]["label"].split("\n")[0] # TODO only one
                            parents.append(data[i]["data"]["id"])
                if "." in data[i]["data"]["label"]:
                    parent = data[i]["data"]["label"].split(".")[0]
                    #parent_id = data[i]["data"]["id"]
                    # TODO not greedy
                    for elem in data:
                        if elem["data"]["label"] == parent:
                            data[i]["data"]["parent"] = elem["data"]["id"]
                            parents.append(elem["data"]["id"])

                # else:
                #     data[i]["classes"] = data[i]["classes"] + " groupIcon" 
 
                if "client" in data[i]["data"]["label"] or "server" in data[i]["data"]["label"]: 
                    data[i]["data"]["kind"] = "TelcoCloudVirtualDevice"
                elif "frame" in data[i]["data"]["label"] or "packet" in data[i]["data"]["label"]:
                    data[i]["data"]["kind"] = "VNF"
                else:
                    data[i]["data"]["kind"] = "NetworkService"
                
                data[i]["data"]["displayName"] = data[i]["data"]["label"].split("\n")[0]
                
                if "frame" in data[i]["data"]["label"] or "packet" in data[i]["data"]["label"]:
                    data[i]["data"]["operationalState"] = "notWorking"
                else:
                    data[i]["data"]["operationalState"] = "Working"
                    
                data[i]["data"]["alarmSeverity"] = "cleared"
                
                # if data[i]["group"] == "nodes":
                #     data[i]["classes"] = data[i]["classes"] + " nodeIcon" 
                
                ##print(elem)
                i+=1
            for elem in to_remove:
                data.remove(elem)
            
            for i in range(len(data)):
                 if data[i]["group"] == "nodes":
                    if data[i]["data"]["id"] in parents:
                        data[i]["classes"] = data[i]["classes"] + " groupIcon" 
                    else:
                        data[i]["classes"] = data[i]["classes"] + " nodeIcon" 
            ##print(len(data))
            ##print(i)
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
                #print(res)
                channel.send(res)
            """ % (Module, Function))
            channel.send(ArgumentList) # 
            ##print(channel.receive())
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
        #     ##print(result) 
        #     json_object = json.dumps(result, indent=4)
        #     # Writing to sample.json
        #     with open("/tmp/sample.json", "w") as outfile:
        #         outfile.write(json_object)
        # except Exception as e:
        #     #print(e)
            
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
        # #print(analysis_graph)
        
        # model = IvyServer.get_quic_model()
        # json_object = json.dumps(model, indent=4)
        # # Writing to sample.json
        # os.system("chown root:root /tmp/sample_model.json")
        # with open("/tmp/sample_model.json", "w") as outfile:
        #     outfile.write(json_object)
            
        IvyServer.construct_cytoscape_graph()
        return render_template('creator.html')

    def run(self):
        IvyServer.app.run(host='0.0.0.0', port=80, use_reloader=True, threaded=True)  #, processes=4
        