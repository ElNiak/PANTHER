#!/usr/bin/env python3.9
# -*- coding: utf-8 -*-


# TODO add logs
# TODO https://www.mongodb.com/docs/manual/core/geospatial-indexes/

from cgitb import html
import json
import os
import socket
import threading

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
import json
import datetime
from flask_cors import CORS
import pathlib
import pandas as pd

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
        IvyServer.ivy_model_path = dir_path + "/QUIC-Ivy/doc/examples/quic"
        IvyServer.ivy_test_path = dir_path  + "/QUIC-Ivy/doc/examples/quic/quic_tests/"
        IvyServer.ivy_temps_path = dir_path + "/QUIC-Ivy/doc/examples/quic/test/temp/"
        IvyServer.local_path = os.environ["ROOT_PATH"] + "/QUIC-Ivy/doc/examples/quic/test/temp/"
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
            res = requests.post('http://'+ IvyServer.current_implem+'-ivy:80/progress')
            IvyServer.app.logger.info(res.text)
            if res.text != "None":            
                if int(res.text) == IvyServer.experiments.args.iter:
                    if len(IvyServer.implems_used) > 0:
                        IvyServer.current_implem = IvyServer.implems_used.pop()
                        IvyServer.experiments.args.implementations = [IvyServer.current_implem]
                        print(IvyServer.experiments.args)
                        data = IvyServer.experiments.args.__dict__
                        from utils.constants import TESTS_CUSTOM
                        data["tests"] = TESTS_CUSTOM
                        res = requests.post('http://'+ IvyServer.current_implem+'-ivy:80/run-exp', json=data)
                        IvyServer.app.logger.info(res.text)
                        IvyServer.current_count += int(res.text)
                        
                    else:
                        IvyServer.current_count = 0
                        IvyServer.implems_used = None
                        IvyServer.current_implem = None
                        IvyServer.experiments.args.iter = 0
                        from utils.constants import TESTS_CUSTOM
                        TESTS_CUSTOM = []
            
            # for imple in IvyServer.implems_used: # One by one due to tshark with only one host
            #     res = requests.post('http://'+ imple+'-ivy:80/progress')
            #     IvyServer.app.logger.info(res.text)
            #     if res.text != "None":
            #         if count is None:
            #             count = int(res.text)
            #         else:
            #             count += int(res.text)
            IvyServer.app.logger.info(IvyServer.current_implem)
        else:
            return "None"
        return str(IvyServer.current_count+int(res.text))

    @app.route('/index.html', methods = ['GET', 'POST'])
    def serve_index():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        from utils.constants import TESTS_CUSTOM
        TESTS_CUSTOM = []
        if request.method == 'POST':
            print(request.form)
            
            for c in request.form:
                for elem in request.form.getlist(c):
                    print(elem)
            
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
            print(IvyServer.experiments.args)
            data = IvyServer.experiments.args.__dict__
            data["tests"] = TESTS_CUSTOM
            res = requests.post('http://'+ IvyServer.current_implem+'-ivy:80/run-exp', json=data)
            IvyServer.app.logger.info(res.text)
            # for imple in request.form.getlist("implem"):
            #     IvyServer.experiments.args.implementations = [imple]
            #     print(IvyServer.experiments.args)
            #     data = IvyServer.experiments.args.__dict__
            #     data["tests"] = TESTS_CUSTOM
            #     res = requests.post('http://'+ imple+'-ivy:80/run-exp', json=data)
            #     IvyServer.app.logger.info(res.text)
                # IvyServer.x = threading.Thread(target=IvyServer.experiments.launch_experiments, args=())
                # IvyServer.x.start()
        
            return render_template('index.html', 
                                server_tests=IvyServer.server_tests, 
                                client_tests=IvyServer.client_tests,
                                nb_exp=IvyServer.nb_exp, 
                                implems=IvyServer.implems,
                                progress=0,
                                iteration=int(IvyServer.experiments.args.iter) * len(IvyServer.implems) * len(TESTS_CUSTOM)) # TODO 0rtt
        else:
            # if IvyServer.x is not None:
            #     IvyServer.x.join()
            #     IvyServer.x = None
            #     IvyServer.implems_used = None
            
            return render_template('index.html', 
                                server_tests=IvyServer.server_tests, 
                                client_tests=IvyServer.client_tests,
                                nb_exp=IvyServer.nb_exp, 
                                implems=IvyServer.implems,
                                progress=IvyServer.experiments.count_1,
                                iteration=int(IvyServer.experiments.args.iter) * len(IvyServer.implems) * len(TESTS_CUSTOM))
            
    
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
        print(IvyServer.ivy_temps_path)
        print(os.listdir(IvyServer.ivy_temps_path))
        IvyServer.nb_exp = len(os.listdir(IvyServer.ivy_temps_path)) - 2
        
        
        default_page = 0
        page = request.args.get('page', default_page)
        try:
            page = page.number
        except:
            pass
        # Get queryset of items to paginate
        rge = range(IvyServer.nb_exp,0,-1)
        print([i for i in rge])
        print(page)
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
        result_row = df_csv.iloc[IvyServer.nb_exp-int(page)]
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
            print(file)
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
                print('Created on:', dt_c)
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
                data_pcap = {
                    "file": pcap_file,
                    "secrets": IvyServer.key_path + '/'+ summary["implementation"] +'_key.log' # TODO 
                }
                #res = requests.post('http://ivy-visualizer:80/#/', params=data_pcap)
                # IvyServer.app.logger.info(res)
                # #res = requests.get('http://ivy-visualizer:80/#/sequence')
                # IvyServer.app.logger.info(res.text)
                # IvyServer.app.logger.info(res)
          
            elif ".qlog" in file:
                # TODO modify ivy script and implem to generate qlog file in the same directory as pcap
                qlog_file = file
                data_qlog = {
                    "file": qlog_file, # TODO
                }
                #res = requests.post('http://ivy-visualizer:80/#/', params=data_qlog)
                #IvyServer.app.logger.info(res)
            
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
        print(items_page)
        print(paginator)
    
        
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
                           qlog_frame_link="http://ivy-visualizer:80/?file=http://ivy-standalone:80/directory/" +  str(IvyServer.nb_exp-int(page)) + "/file/" + qlog_file if qlog_file != '' else None,)

    @app.route('/results-global.html', methods = ['GET', 'POST'])
    def serve_results_global():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        IvyServer.nb_exp = len(os.listdir(IvyServer.ivy_temps_path)) - 2
        
        print(request.form)
        
        summary = {}
        df_csv = pd.read_csv(IvyServer.ivy_temps_path + 'data.csv',parse_dates=['date'])
        
        df_simplify_date = df_csv
        df_simplify_date['date'] = df_csv['date'].dt.strftime('%d/%m/%Y')
        df_date_min_max = df_simplify_date['date'].agg(['min', 'max'])
        df_nb_date = df_simplify_date['date'].nunique()
        df_dates = df_simplify_date['date'].unique()
        print(list(df_dates))
        print(df_date_min_max)
        print(df_nb_date)
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
                    print(i)
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
                           df_dates=list(df_dates))


    def get_attack_model(self, attack_model):
        """
        It returns the attack model
        :param attack_model: the attack model
        :return: the attack model
        """
        return attack_model
    
    def get_quic_model(self):
        """
        It returns the quic model
        :param quic_model: the quic model
        :return: the quic model
        """
        model = {}
        for dir in os.listdir(IvyServer.ivy_model_path):
            if os.isdir(dir) and ('quic_' in dir or 'tls_' in dir ) and dir != 'quic_tests' and dir != 'quic_fsm':
                model[dir] = {}
                for file in os.listdir(IvyServer.ivy_model_path + '/' + dir):
                    if '.ivy' in file:
                        model[dir][file] = {}
                        with open(IvyServer.ivy_model_path + '/' + dir + '/' + file, 'r') as f:
                            content = f.read()
                            for line in content.splitlines():
                                if 'include' in line:
                                    model[dir][file][line.split(' ')[1]] = line.split(' ')[2]
                            
        return model
    
    @app.route('/creator.html', methods = ['GET', 'POST'])
    def serve_attack():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        return render_template('creator.html')

    def run(self):
        IvyServer.app.run(host='0.0.0.0', port=80, use_reloader=True, threaded=True)  #, processes=4
        