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
from flask import (
    Flask,
    flash,
    request,
    redirect,
    url_for,
    send_from_directory,
    Response,
    session,
    render_template,
    jsonify,
)
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from base64 import b64encode
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import datetime
from flask_cors import CORS
import pandas as pd
from npf_web_extension.app import export
import configparser
import argparse
import sys
from termcolor import colored, cprint
import terminal_banner

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from utils.cytoscape_generator import *
from panther_utils.panther_constant import *
from panther_config.panther_config import get_experiment_config, restore_config

from argument_parser.ArgumentParserRunner import ArgumentParserRunner

SOURCE_DIR = os.getcwd()
DEBUG = True


class PFVServer:
    ROOTPATH = os.getcwd()
    app = Flask(__name__, static_folder="/app/static/")
    app.secret_key = "super secret key"  # TODO
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    app.config["APPLICATION_ROOT"] = ROOTPATH + "/app/templates/"
    app.debug = True
    CORS(app, resources={r"/*": {"origins": "*"}})

    def __init__(self, dir_path=None):
        restore_config()

        # Initialize SocketIO
        PFVServer.socketio = SocketIO(PFVServer.app)

        # Setup configuration
        PFVServer.app.logger.info("Setup configuration ...")
        (
            PFVServer.supported_protocols,
            PFVServer.current_protocol,
            PFVServer.tests_enabled,
            PFVServer.conf_implementation_enable,
            PFVServer.implementation_enable,
            PFVServer.protocol_model_path,
            PFVServer.protocol_results_path,
            PFVServer.protocol_test_path,
            PFVServer.config,
            PFVServer.protocol_conf,
        ) = get_experiment_config(None, True, True)

        # Count number of directories in PFVServer.protocol_results_path
        PFVServer.total_exp_in_dir = 0
        with os.scandir(PFVServer.protocol_results_path) as entries:
            PFVServer.total_exp_in_dir = sum(1 for entry in entries if entry.is_dir())

        PFVServer.current_exp_path = os.path.join(
            PFVServer.protocol_results_path, str(PFVServer.total_exp_in_dir)
        )

        # Experiment parameters
        PFVServer.tests_requested = []
        PFVServer.implementation_requested = []
        PFVServer.experiment_iteration = 0
        PFVServer.experiment_current_iteration = 0
        PFVServer.is_experiment_started = False

        # Automatic GUI
        PFVServer.choices_args = {}

        PFVServer.get_quic_vizualier()

    def get_quic_vizualier():
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
        r.headers["Cache-Control"] = "public, max-age=0"
        r.headers.add("Access-Control-Allow-Headers", "authorization,content-type")
        r.headers.add(
            "Access-Control-Allow-Methods",
            "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT",
        )
        r.headers.add("Access-Control-Allow-Origin", "*")
        return r

    @app.route("/")
    def redirection():
        """
        It redirects the user to the index.html page
        :return: a redirect to the index.html page.
        """
        return redirect("index.html", code=302)

    def reset_experiment_state():
        PFVServer.is_experiment_started = False
        PFVServer.experiment_current_iteration = 0
        PFVServer.experiment_iteration = 0
        restore_config()

    @app.route("/update-count", methods=["GET"])
    def update_count():
        if PFVServer.is_experiment_started:
            PFVServer.experiment_current_iteration += 1
            if PFVServer.experiment_current_iteration >= PFVServer.experiment_iteration:
                PFVServer.emit_progress_update()
                PFVServer.reset_experiment_state()
            else:
                PFVServer.emit_progress_update()
        return jsonify({"status": "success"}), 200

    def emit_progress_update():
        progress = PFVServer.experiment_current_iteration
        PFVServer.socketio.emit("progress_update", {"progress": progress})

    @app.route("/errored-experiment", methods=["GET"])
    def errored_experiment():
        if PFVServer.is_experiment_started:
            PFVServer.emit_progress_update()
            PFVServer.reset_experiment_state()
        return jsonify({"status": "success"}), 200

    @app.route("/finish-experiment", methods=["GET"])
    def finish_experiment():
        if PFVServer.is_experiment_started:
            PFVServer.emit_progress_update()
            PFVServer.reset_experiment_state()
        return jsonify({"status": "success"}), 200

    def get_args():
        """_summary_
        Get list of argument for automatic GUI generation
        Returns:
            _type_: _description_
        """
        # TODO refactor -> From configfile
        PFVServer.choices_args = {}
        args_parser = ArgumentParserRunner().parser
        args_list = [{}]
        is_mutually_exclusive = True
        for group_type in [
            args_parser._mutually_exclusive_groups,
            args_parser._action_groups,
        ]:
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
                        args_list[-1][group_name].append(
                            {
                                "name": action.dest,
                                "help": action.help,
                                "type": "bool",
                                "default": False,
                                "is_mutually_exclusive": is_mutually_exclusive,
                                "description": action.metavar,
                            }
                        )
                    elif isinstance(action, argparse._StoreFalseAction):
                        args_list[-1][group_name].append(
                            {
                                "name": action.dest,
                                "help": action.help,
                                "type": "bool",
                                "default": True,
                                "is_mutually_exclusive": is_mutually_exclusive,
                                "description": action.metavar,
                            }
                        )
                    elif not isinstance(action, argparse._HelpAction):
                        if hasattr(action, "choices"):
                            if action.choices:
                                PFVServer.choices_args[action.dest] = action.choices
                            args_list[-1][group_name].append(
                                {
                                    "name": action.dest,
                                    "help": action.help,
                                    "type": str(action.type),
                                    "default": action.default,
                                    "is_mutually_exclusive": is_mutually_exclusive,
                                    "choices": action.choices,
                                    "description": action.metavar,
                                }
                            )
                        else:
                            args_list[-1][group_name].append(
                                {
                                    "name": action.dest,
                                    "help": action.help,
                                    "type": str(action.type),
                                    "default": action.default,
                                    "is_mutually_exclusive": is_mutually_exclusive,
                                    "description": action.metavar,
                                }
                            )
            is_mutually_exclusive = False

        json_arg = args_list

        args_list = [{}]
        is_mutually_exclusive = True
        for group_type in [
            args_parser._mutually_exclusive_groups,
            args_parser._action_groups,
        ]:
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
                                    args_list[-1][group_name].append(
                                        {
                                            "name": action.dest,
                                            "help": action.help,
                                            "type": "bool",
                                            "default": False,
                                            "is_mutually_exclusive": is_mutually_exclusive,
                                            "description": action.metavar,
                                        }
                                    )
                                elif isinstance(action, argparse._StoreFalseAction):
                                    args_list[-1][group_name].append(
                                        {
                                            "name": action.dest,
                                            "help": action.help,
                                            "type": "bool",
                                            "default": True,
                                            "is_mutually_exclusive": is_mutually_exclusive,
                                            "description": action.metavar,
                                        }
                                    )
                                elif not isinstance(action, argparse._HelpAction):
                                    if hasattr(action, "choices"):
                                        if action.choices:
                                            PFVServer.choices_args[
                                                action.dest
                                            ] = action.choices
                                        args_list[-1][group_name].append(
                                            {
                                                "name": action.dest,
                                                "help": action.help,
                                                "type": str(action.type),
                                                "default": action.default,
                                                "is_mutually_exclusive": is_mutually_exclusive,
                                                "choices": action.choices,
                                                "description": action.metavar,
                                            }
                                        )
                                    else:
                                        args_list[-1][group_name].append(
                                            {
                                                "name": action.dest,
                                                "help": action.help,
                                                "type": str(action.type),
                                                "default": action.default,
                                                "is_mutually_exclusive": is_mutually_exclusive,
                                                "description": action.metavar,
                                            }
                                        )
                        is_mutually_exclusive = False
        prot_arg = args_list
        return json_arg, prot_arg

    def start_exp(experiment_arguments, protocol_arguments, sequencial_test=True):
        # TODO add paramater to ask if we keep previous config for next run

        if sequencial_test:
            for impl in PFVServer.implementation_requested:
                PFVServer.app.logger.info(
                    "Starting experiment for implementation " + impl
                )
                req = {
                    "args": experiment_arguments,
                    "protocol_arguments": protocol_arguments,
                    "protocol": PFVServer.current_protocol,
                    "implementation": impl,
                    "tests_requested": PFVServer.tests_requested,
                }
                PFVServer.app.logger.info("with parameters: " + str(req))
                response = None
                try:
                    response = requests.get(f"http://{impl}-ivy:80/run-exp", json=req)
                    response.raise_for_status()
                    PFVServer.app.logger.info(f"Experiment status: {response.content}")
                except requests.RequestException as e:
                    PFVServer.app.logger.error(
                        f"Request failed for {impl}: {e} - {response}"
                    )
                    continue

                while (
                    PFVServer.experiment_current_iteration
                    < PFVServer.experiment_iteration
                    / len(PFVServer.implementation_requested)
                ):
                    time.sleep(10)
                    PFVServer.app.logger.info("Waiting")
                    PFVServer.app.logger.info("Waiting")
                    PFVServer.app.logger.info(
                        f"Current iteration: {PFVServer.experiment_current_iteration}"
                    )
                    PFVServer.app.logger.info(
                        f"Target iteration: {PFVServer.experiment_iteration / len(PFVServer.implementation_requested)}"
                    )
                PFVServer.app.logger.info(
                    "Ending experiment for implementation " + impl
                )
        else:
            # TODO multi test
            # Need to avoid shared configuration file
            pass

    # To start the experiment in a thread
    def start_experiment_thread(experiment_arguments, protocol_arguments):
        thread = threading.Thread(
            target=PFVServer.start_exp, args=(experiment_arguments, protocol_arguments)
        )
        thread.daemon = True
        thread.start()

    def change_current_protocol(protocol):
        PFVServer.app.logger.info(
            f"Selected Protocol change ({protocol}) -> change GUI"
        )

        PFVServer.current_protocol = protocol

        json_arg, prot_arg = PFVServer.get_args()

        if DEBUG:
            PFVServer.app.logger.info("JSON arguments availables:")
            for elem in json_arg:
                PFVServer.app.logger.info(elem)
            PFVServer.app.logger.info("PROTOCOL arguments availables:")
            for elem in prot_arg:
                PFVServer.app.logger.info(elem)

        return json_arg, prot_arg

    @app.route("/index.html", methods=["GET", "POST"])
    def serve_index():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        PFVServer.app.logger.info("Protocols under test: " + PFVServer.current_protocol)

        if DEBUG:
            json_arg, prot_arg = PFVServer.get_args()
            PFVServer.app.logger.info("JSON arguments availables:")
            for elem in json_arg:
                PFVServer.app.logger.info(elem)
            PFVServer.app.logger.info("PROTOCOL arguments availables:")
            for elem in prot_arg:
                PFVServer.app.logger.info(elem)

        if request.method == "POST":
            # TODO link json_arg and prot_arg to config so we can restore old config
            # TODO fix problem with alpn & initial version
            if (
                request.args.get("prot", "")
                and request.args.get("prot", "") in PFVServer.supported_protocols
            ):
                PFVServer.app.logger.info(
                    f"POST request with protocol change: {request.args.get('prot', '')}"
                )
                # The Selected Protocol change -> change GUI
                json_arg, prot_arg = PFVServer.change_current_protocol(
                    request.args.get("prot", "")
                )

                (
                    PFVServer.supported_protocols,
                    PFVServer.current_protocol,
                    PFVServer.tests_enabled,
                    PFVServer.conf_implementation_enable,
                    PFVServer.implementation_enable,
                    PFVServer.protocol_model_path,
                    PFVServer.protocol_results_path,
                    PFVServer.protocol_test_path,
                    PFVServer.config,
                    PFVServer.protocol_conf,
                ) = get_experiment_config(PFVServer.current_protocol, True, False)

            # TODO implem progress, avoid to use post if experience already launched
            # TODO force to select at least one test and one implem
            PFVServer.app.logger.info("Form in POST request:")
            PFVServer.app.logger.info(request.form)
            if DEBUG:
                for c in request.form:
                    for elem in request.form.getlist(c):
                        PFVServer.app.logger.info(elem)

            PFVServer.implementation_requested = []
            experiment_arguments = {}
            protocol_arguments = {}
            PFVServer.tests_requested = []

            arguments = dict(request.form)
            exp_number = 1
            for key, value in arguments.items():
                if (key, value) == ("boundary", "experiment separation"):
                    exp_number += 1
                elif key in PFVServer.implementation_enable.keys() and value == "true":
                    PFVServer.implementation_requested.append(key)
                elif "test" in key and value == "true":
                    PFVServer.tests_requested.append(key)
                elif value != "":
                    if key in PFVServer.choices_args:
                        print(PFVServer.choices_args[key])
                        value = str(PFVServer.choices_args[key][int(value) - 1])
                    if exp_number == 1:
                        experiment_arguments[key] = value
                    elif exp_number == 2:
                        protocol_arguments[key] = value

            PFVServer.app.logger.info(
                "Experiment arguments: " + str(experiment_arguments)
            )
            PFVServer.app.logger.info("Protocol arguments: " + str(protocol_arguments))
            PFVServer.app.logger.info(
                "Experiment tests requested: " + str(PFVServer.tests_requested)
            )

            PFVServer.is_experiment_started = True
            PFVServer.experiment_iteration = (
                len(PFVServer.implementation_requested)
                * len(PFVServer.tests_requested)
                * int(experiment_arguments["iter"])
            )

            PFVServer.start_experiment_thread(experiment_arguments, protocol_arguments)
        else:
            if (
                request.args.get("prot", "")
                and request.args.get("prot", "") in PFVServer.supported_protocols
            ):
                json_arg, prot_arg = PFVServer.change_current_protocol(
                    request.args.get("prot", "")
                )
                (
                    PFVServer.supported_protocols,
                    PFVServer.current_protocol,
                    PFVServer.tests_enabled,
                    PFVServer.conf_implementation_enable,
                    PFVServer.implementation_enable,
                    PFVServer.protocol_model_path,
                    PFVServer.protocol_results_path,
                    PFVServer.protocol_test_path,
                    PFVServer.config,
                    PFVServer.protocol_conf,
                ) = get_experiment_config(PFVServer.current_protocol, True, False)

        return render_template(
            "index.html",
            json_arg=json_arg,
            prot_arg=prot_arg,
            base_conf=PFVServer.config,
            protocol_conf=PFVServer.protocol_conf,
            supported_protocols=PFVServer.supported_protocols,
            current_protocol=PFVServer.current_protocol,
            nb_exp=PFVServer.total_exp_in_dir,
            tests_enable=PFVServer.tests_enabled,
            implementation_enable=PFVServer.implementation_enable,
            implementation_requested=PFVServer.implementation_requested,
            progress=PFVServer.experiment_current_iteration,  # PFVServer.experiments.count_1,
            iteration=PFVServer.experiment_iteration,
        )

    @app.route("/directory/<int:directory>/file/<path:file>")
    def send_file(directory, file):
        return send_from_directory(
            PFVServer.protocol_results_path + str(directory), file
        )

    @app.route("/key/<string:implem>")
    def send_key(implem):
        return send_from_directory(PFVServer.key_path, implem)

    # TODO redo
    @app.route("/results.html", methods=["GET", "POST"])
    def serve_results():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        PFVServer.app.logger.info(
            "Current Protocol Tests output folder: " + PFVServer.protocol_results_path
        )
        PFVServer.app.logger.info(os.listdir(PFVServer.protocol_results_path))

        with os.scandir(PFVServer.protocol_results_path) as entries:
            PFVServer.total_exp_in_dir = sum(1 for entry in entries if entry.is_dir())

        default_page = 0
        page = request.args.get("page", default_page)
        try:
            page = page.number
        except:
            pass
        # Get queryset of items to paginate
        rge = range(PFVServer.total_exp_in_dir, 0, -1)
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

        df_csv = pd.read_csv(PFVServer.protocol_results_path + "data.csv").set_index(
            "Run"
        )
        PFVServer.app.logger.info(PFVServer.total_exp_in_dir - int(page))

        result_row = df_csv.iloc[-1]
        output = "df_csv_row.html"
        # TODO change the label
        # result_row.to_frame().T
        # subdf = df_csv.drop("ErrorIEV", axis=1).drop("OutputFile", axis=1).drop("date", axis=1).drop("date", axis=1).drop("date", axis=1) #.reset_index()
        subdf = df_csv[["Implementation", "NbPktSend", "packet_event", "recv_packet"]]
        subdf.fillna(0, inplace=True)
        # subdf["isPass"] = subdf["isPass"].astype(int)
        subdf["NbPktSend"] = subdf["NbPktSend"].astype(int)
        # PFVServer.app.logger.info(subdf)
        # PFVServer.app.logger.info(df_csv.columns)
        # PFVServer.app.logger.info(subdf.columns)
        # subdf.columns = df_csv.columns
        configurationData = [
            {
                "id": str(uuid.uuid4()),  # Must be unique TODO df_csv_scdg['filename']
                "name": "Experiences coverage view",
                "parameters": ["Run"],  # "Implementation",
                "measurements": [
                    "NbPktSend"
                ],  # , "Total number of blocks",'Number Syscall found' , 'Number Address found', 'Number of blocks visited', "Total number of blocks","time"
                "data": subdf.to_csv(),
            },
            {
                "id": str(uuid.uuid4()),  # Must be unique TODO df_csv_scdg['filename']
                "name": "Experiences packet view",
                "parameters": ["Run"],  # "Implementation"
                "measurements": [
                    "packet_event",
                    "recv_packet",
                ],  # , "Total number of blocks",'Number Syscall found' , 'Number Address found', 'Number of blocks visited', "Total number of blocks","time"
                "data": subdf.to_csv(),  # index=False -> need index
            },
        ]

        export(configurationData, output)

        # PFVServer.app.logger.info(configurationData)

        with open(output, "r") as f:
            df_csv_content = f.read()

        summary = {}
        summary["nb_pkt"] = result_row["NbPktSend"]
        summary["initial_version"] = result_row["initial_version"]

        PFVServer.current_exp_path = PFVServer.protocol_results_path + str(
            PFVServer.total_exp_in_dir - int(page)
        )
        exp_dir = os.listdir(PFVServer.current_exp_path)
        ivy_stderr = "No output"
        ivy_stdout = "No output"
        implem_err = "No output"
        implem_out = "No output"
        iev_out = "No output"
        qlog_file = ""
        pcap_file = ""
        for file in exp_dir:
            PFVServer.app.logger.info(file)
            if "ivy_stderr.txt" in file:
                with open(PFVServer.current_exp_path + "/" + file, "r") as f:
                    content = f.read()
                    if content == "":
                        pass
                    else:
                        ivy_stderr = content
            elif "ivy_stdout.txt" in file:
                with open(PFVServer.current_exp_path + "/" + file, "r") as f:
                    content = f.read()
                    if content == "":
                        pass
                    else:
                        ivy_stdout = content
            elif ".err" in file:
                with open(PFVServer.current_exp_path + "/" + file, "r") as f:
                    content = f.read()
                    if content == "":
                        pass
                    else:
                        implem_err = content
            elif ".out" in file:
                with open(PFVServer.current_exp_path + "/" + file, "r") as f:
                    content = f.read()
                    if content == "":
                        pass
                    else:
                        implem_out = content
            elif ".iev" in file:
                # TODO use csv file
                # file creation timestamp in float
                c_time = os.path.getctime(PFVServer.current_exp_path + "/" + file)
                # convert creation timestamp into DateTime object
                dt_c = datetime.datetime.fromtimestamp(c_time)
                PFVServer.app.logger.info("Created on:" + str(dt_c))
                summary["date"] = dt_c
                test_name = file.replace(".iev", "")[0:-1]
                summary["test_name"] = test_name
                with open(PFVServer.current_exp_path + "/" + file, "r") as f:
                    content = f.read()
                    summary["test_result"] = (
                        "Pass" if "test_completed" in content else "Fail"
                    )

                try:
                    plantuml_file = PFVServer.current_exp_path + "/plantuml.puml"
                    generate_graph_input(
                        PFVServer.current_exp_path + "/" + file, plantuml_file
                    )
                    plantuml_obj = PlantUML(
                        url="http://www.plantuml.com/plantuml/img/",
                        basic_auth={},
                        form_auth={},
                        http_opts={},
                        request_opts={},
                    )

                    plantuml_file_png = plantuml_file.replace(
                        ".puml", ".png"
                    )  # "media/" + str(nb_exp) + "_plantuml.png"
                    plantuml_obj.processes_file(plantuml_file, plantuml_file_png)

                    with open(PFVServer.current_exp_path + "/" + file, "r") as f:
                        content = f.read()
                        if content == "":
                            pass
                        else:
                            iev_out = content
                except:
                    pass
            elif ".pcap" in file:
                pcap_file = file
                # Now we need qlogs and pcap informations
                summary["implementation"] = file.split("_")[0]
                summary["test_type"] = file.split("_")[2]

            elif ".qlog" in file:
                qlog_file = file

        # Get page number from request,
        # default to first page
        try:
            binary_fc = open(plantuml_file_png, "rb").read()  # fc aka file_content
            base64_utf8_str = b64encode(binary_fc).decode("utf-8")

            ext = plantuml_file_png.split(".")[-1]
        except:
            base64_utf8_str = ""
            ext = "png"
        dataurl = f"data:image/{ext};base64,{base64_utf8_str}"
        PFVServer.app.logger.info(items_page)
        PFVServer.app.logger.info(paginator)

        return render_template(
            "results.html",
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
            summary=summary,  # "http://"+PFVServer.vizualiser_ip+":80/?file=http://"
            pcap_frame_link=(
                "http://ivy-visualizer:80/?file=http://ivy-standalone:80/directory/"
                + str(PFVServer.total_exp_in_dir - int(page))
                + "/file/"
                + pcap_file
                + "&secrets=http://ivy-standalone:80/key/"
                + summary["implementation"]
                + "_key.log"
                if pcap_file != ""
                else None
            ),
            qlog_frame_link=(
                "http://ivy-visualizer:80/?file=http://ivy-standalone:80/directory/"
                + str(PFVServer.total_exp_in_dir - int(page))
                + "/file/"
                + qlog_file
                if qlog_file != ""
                else None
            ),
            df_csv_content=df_csv_content,
        )

    # TODO redo
    @app.route("/results-global.html", methods=["GET", "POST"])
    def serve_results_global():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        PFVServer.total_exp_in_dir = (
            len(os.listdir(PFVServer.protocol_results_path)) - 2
        )

        PFVServer.app.logger.info(request.form)

        summary = {}
        df_csv = pd.read_csv(
            PFVServer.protocol_results_path + "data.csv", parse_dates=["date"]
        )

        df_simplify_date = df_csv
        df_simplify_date["date"] = df_csv["date"].dt.strftime("%d/%m/%Y")
        df_date_min_max = df_simplify_date["date"].agg(["min", "max"])
        df_nb_date = df_simplify_date["date"].nunique()
        df_dates = df_simplify_date["date"].unique()
        PFVServer.app.logger.info(list(df_dates))
        PFVServer.app.logger.info(df_date_min_max)
        PFVServer.app.logger.info(df_nb_date)
        minimum_date = df_date_min_max["min"]
        maximum_date = df_date_min_max["max"]

        subdf = None
        # if len(request.form) >= 0:
        for key in request.form:
            if key == "date_range":
                minimum = df_dates[int(request.form.get("date_range").split(",")[0])]
                maximum = df_dates[int(request.form.get("date_range").split(",")[1])]
                if subdf is None:
                    subdf = df_csv.query("date >= @minimum and date <= @maximum")
                else:
                    subdf = subdf.query("date >= @minimum and date <= @maximum")
            elif key == "iter_range":
                minimum = request.form.get("iter_range").split(",")[0]
                maximum = request.form.get("iter_range").split(",")[1]
                if subdf is None:  # TOODO
                    subdf = df_csv.loc[df_csv["Run"] >= int(minimum)]
                    subdf = subdf.loc[subdf["Run"] <= int(maximum)]
                else:
                    subdf = subdf.loc[subdf["Run"] >= int(minimum)]
                    subdf = subdf.loc[subdf["Run"] <= int(maximum)]
            elif key == "version":
                if request.form.get("version") != "all":
                    if subdf is None:  # TOODO
                        subdf = df_csv.loc[
                            df_csv["initial_version"] == request.form.get("version")
                        ]
                    else:
                        subdf = subdf.loc[
                            subdf["initial_version"] == request.form.get("version")
                        ]
            elif key == "ALPN":
                if request.form.get("ALPN") != "all":
                    if subdf is None:  # TOODO
                        subdf = df_csv.loc[
                            df_csv["Mode"] == request.form.get("test_type")
                        ]
                    else:
                        subdf = subdf.loc[
                            subdf["Mode"] == request.form.get("test_type")
                        ]
            elif key == "test_type":
                if request.form.get("test_type") != "all":
                    if subdf is None:
                        subdf = df_csv.loc[
                            df_csv["Mode"] == request.form.get("test_type")
                        ]
                    else:
                        subdf = subdf.loc[
                            subdf["Mode"] == request.form.get("test_type")
                        ]
            elif key == "isPass":
                ispass = True if "True" in request.form.get("isPass") else False
                if request.form.get("isPass") != "all":
                    if subdf is None:
                        subdf = df_csv.loc[df_csv["isPass"] == ispass]
                    else:
                        subdf = subdf.loc[subdf["isPass"] == ispass]
            elif key == "implem":
                for i in request.form.getlist("implem"):
                    PFVServer.app.logger.info(i)
                    if subdf is None:
                        subdf = df_csv.loc[df_csv["Implementation"] == i]
                    else:
                        subdf = subdf.loc[subdf["Implementation"] == i]
            elif key == "server_test":
                for i in request.form.getlist("server_test"):
                    if subdf is None:
                        subdf = df_csv.loc[df_csv["TestName"] == i]
                    else:
                        subdf = subdf.loc[subdf["TestName"] == i]
            elif key == "client_test":
                for i in request.form.getlist("client_test"):
                    if subdf is None:
                        subdf = df_csv.loc[df_csv["TestName"] == i]
                    else:
                        subdf = subdf.loc[subdf["TestName"] == i]

        if subdf is not None:
            df_csv = subdf

        csv_text = df_csv.to_csv()

        output = "df_csv.html"
        # TODO change the label
        configurationData = [
            {
                "id": str(uuid.uuid4()),  # Must be unique TODO df_csv_scdg['filename']
                "name": "Experiences coverage view",
                "parameters": ["Implementation", "Mode", "TestName"],
                "measurements": [
                    "isPass",
                    "ErrorIEV",
                    "packet_event",
                    "packet_event_retry",
                    "packet_event_vn",
                    "packet_event_0rtt",
                    "packet_event_coal_0rtt",
                    "recv_packet",
                    "recv_packet_retry",
                    "handshake_done",
                    "tls.finished",
                    "recv_packet_vn",
                    "recv_packet_0rtt",
                    "undecryptable_packet_event",
                    "version_not_found_event",
                    "date",
                    "initial_version",
                    "NbPktSend",
                    "version_not_found",
                ],  # , "Total number of blocks",'Number Syscall found' , 'Number Address found', 'Number of blocks visited', "Total number of blocks","time"
                "data": df_csv.to_csv(index=False),
            },
            {
                "id": str(uuid.uuid4()),  # Must be unique TODO df_csv_scdg['filename']
                "name": "Experiences coverage view",
                "parameters": ["Implementation", "Mode", "TestName"],
                "measurements": [
                    "isPass",
                    "ErrorIEV",
                    "packet_event",
                    "packet_event_retry",
                    "packet_event_vn",
                    "packet_event_0rtt",
                    "packet_event_coal_0rtt",
                    "recv_packet",
                    "recv_packet_retry",
                    "handshake_done",
                    "tls.finished",
                    "recv_packet_vn",
                    "recv_packet_0rtt",
                    "undecryptable_packet_event",
                    "version_not_found_event",
                    "date",
                    "initial_version",
                    "NbPktSend",
                    "version_not_found",
                ],  # , "Total number of blocks",'Number Syscall found' , 'Number Address found', 'Number of blocks visited', "Total number of blocks","time"
                "data": df_csv.to_csv(index=False),
            },
            {
                "id": str(uuid.uuid4()),  # Must be unique TODO df_csv_scdg['filename']
                "name": "Experiences coverage view",
                "parameters": ["Implementation", "Mode", "TestName"],
                "measurements": [
                    "isPass",
                    "ErrorIEV",
                    "packet_event",
                    "packet_event_retry",
                    "packet_event_vn",
                    "packet_event_0rtt",
                    "packet_event_coal_0rtt",
                    "recv_packet",
                    "recv_packet_retry",
                    "handshake_done",
                    "tls.finished",
                    "recv_packet_vn",
                    "recv_packet_0rtt",
                    "undecryptable_packet_event",
                    "version_not_found_event",
                    "date",
                    "initial_version",
                    "NbPktSend",
                    "version_not_found",
                ],  # , "Total number of blocks",'Number Syscall found' , 'Number Address found', 'Number of blocks visited', "Total number of blocks","time"
                "data": df_csv.to_csv(index=False),
            },
        ]
        # The above code is not valid Python code. It appears to be the beginning of a comment or
        # documentation string, but it is missing the closing characters.

        export(configurationData, output)

        # PFVServer.app.logger.info(configurationData)

        with open(output, "r") as f:
            df_csv_content = f.read()

        return render_template(
            "result-global.html",
            nb_exp=PFVServer.total_exp_in_dir,
            current_exp=PFVServer.current_exp_path,
            summary=summary,
            csv_text=csv_text,
            tests_requested=PFVServer.tests_requested,
            client_tests=PFVServer.client_tests,
            implementation_requested=PFVServer.implementation_requested,
            min_date=None,
            max_date=None,
            df_nb_date=df_nb_date,
            df_dates=list(df_dates),
            df_csv_content=df_csv_content,
        )

    def get_attack_model(self, attack_model):
        """
        It returns the attack model
        :param attack_model: the attack model
        :return: the attack model
        """
        return attack_model

    @app.route("/kg/graph/json", methods=["GET"])
    def get_json_graph():
        """
        It returns the json graph of the knowledge graph
        :return: the json graph of the knowledge graph
        """
        with open("/tmp/cytoscape_config.json", "r") as json_file:
            data = json.load(json_file)

        response = PFVServer.app.response_class(
            response=json.dumps(data), status=200, mimetype="application/json"
        )
        return response

    # TODO redo
    @app.route("/creator.html", methods=["GET", "POST"])
    def serve_attack():
        """
        It creates a folder for the project, and then calls the upload function
        :return: the upload function.
        """
        # PFVServer.experiments.update_includes_ptls()
        # PFVServer.experiments.update_includes()
        setup_quic_model(PFVServer.protocol_test_path)
        setup_cytoscape()
        return render_template("creator.html")

    def run(self):
        PFVServer.app.run(
            host="0.0.0.0", port=80, use_reloader=True, threaded=True
        )  # , processes=4


banner = """
@@@@@@@@@@@@@@@@&&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@: .~JG#&@@@@@@@@@@@@@@@@@@@@@@@@@@&BJ~. .&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@G   .::: :?5G57~:.........:^!YG5J^.:^:.   5@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@G :.  :~                           ^:  .: Y@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@& .:  ^    .                   .    ^  :. #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@7   .:  .     .^.        ~:     .  ..   ~@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@7      ~~^.  ^7^::~ ~::^7^  .^~~.     !&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@7     :!~??~. :?!: .!?^ .~??~~^     :@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@J       .Y5~7J7..^   ^..7J?^YY.       ^&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@^   .   . !P7!^. .~. .^.  ~7!5~ .   :  ..B@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@:.  :~   !^  .:^^  .^.^.  ^^:.  ^J.  ^^  :.#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@P.^  ?^    ..:: :^.       .^^ .:.:.   .J  :~!@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@Y^^  5!    :??.  7!!?7!7J7!?.  ??^    ^5. :!!@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@#.!  Y5.   :J:^:  ..~P75!..  :^:?^   .YY  ~:G@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@?:. .YY7^. ~^^^^    ...    :^^^!  .!5Y: .: P@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@...  J557 .7:.     .:..    .:7. !5Y~  .^  .@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@5  ^7.~55.... ^B5:!?YY57!^J#! ....5. .77 .. Y@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@P :~ .7Y55.  . !@&:!!^.^!!:#@? .  ~Y7JJ^  :Y. #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@J .YJ   .^7:    .^G?5YJ^?J5?G~.    ~~^.     ^5!.?@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@! :Y!             .~~!YYJYY7~~.         .     J5Y.^@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@7 ^5~  :~         .JG!^~:.:~~~GY.         7!:^?5555 .@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@5  Y5  .P~        .5!!: ^~:~^ .!~Y.         ~J555555^ ~@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@   Y5!:?57         ?^  .::.::.  :J.            .:!55^  B@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@G   .?5555~          :!^.      .~:        J:       :5^  7@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@Y    .555^      ..     .^~~~~^:.          :~~:.     ~7  !@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@#      !P7     .!J^                            :?^    :. .@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@.       ~?    .Y^                         ....  :^        !@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@P     .   ..   ::                      ^~::....::^^.        .&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@~     ~J        !                  .:::^.           ^^.       .&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@&.      ~57.     !7        .....::::::.           .:             ?@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@.         .^~^   :.     .!?#^ .:...                              .@@@@@@@@@@@@@@@@@@@@@@@@@@#J7P@
@@!             :J:        :~G^ .?#~   .:..         :...             @@@@@@@@@@@@@@@@@@@@&G5J~.    P
@&               :5.        .. .7#!  .^^~   .:.    ^^                @@@@@@@@@@@@@@@@#7.           G
@Y              .757            !    .?&#..:.    .~     ..           &@@@@@@@@@@@@@#:            .P@
@J              ....!J?^             ^G:  ~GG  .::      .:^:.        &@@@@@@@@@@@@5         .^75#@@@
@@:..                :~?!::.         .    PJ^..            ...      Y@@@@@@@@@@@@&        :#@@@@@@@@
@@@^ .                :   ~~...          ..                      JG#@@@@@@@@@@@@@#        &@@@@@@@@@
@@@@?.                ..:.5&G.:                                  G@@@@@@@@@@@@@@@@:       &@@@@@@@@@
@@@@@&5~.         ::  .  :.:J?.                                 ^ .~P&@@@@@@@@@@@@&       7@@@@@@@@@
@@@@@@@@@&^       .  .~.                                        ^   .~J#@@@@@@@@@@@B    .  ?@@@@@@@@
@@@@@@@@@@B        : ^G#B! .                    5&.             ^     :^7&@@@@@@@@@@J   :.  P@@@@@@@
@@@@@@@@@@@Y   .^   :.  .7PP&B!                 @@J^.          ^        ::B@@@@@@@@@&   .   :@@@@@@@
@@@@@@@@@@@@&. :^  .    :&@@@@@P.               ^&P.~         ~~GY^.     ..P@@@@@@@@J    !. .@@@@@@@
@@@@@@@@@@@@@7     G&B! J@@@@@@@@?                : .^:.     ~~B@@@5.     . :JGBBBY:    ^P: J@@@@@@@
@@@@@@@@@@@@@P.  ~7: :5G5G@@@@@@@@@Y            .:    ~..    .:5@@@@&~    ..           .Y? ~@@@@@@@@
@@@@@@@@@@@@@@&? .YB?^G@@@@@@@@@@@@@&?           :    7        .@@@@@@G:   .^:.      .~J!.5@@@@@@@@@
@@@@@@@@@@@@@@@@&P7^?G5@@@@@@@@@@@@@@@&Y~:::~: .::    !         P@@@@@@@B~    :^^^^~!!~~5@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&5!:   .!         .&@@@@@@@@@#57~^^^~~7Y-#@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@#!  ~    .  .   !@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&7..        :! #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@!!:.  .: :^~ &@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&?.^?7~7YJ. !@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&. .^. ::  .7&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@# :.        :#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@P 7.    ..!~ ?@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@J.~         5@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@#!   ..:^~G@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@&BPYYG&@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                                            Made with ❤️
                                For the Community, By the Community

                                ###################################

                                        Made by ElNiak
                linkedin  - https://www.linkedin.com/in/christophe-crochet-5318a8182/
                                Github - https://github.com/elniak

"""
banner_terminal = terminal_banner.Banner(banner)
cprint(banner_terminal, "green", file=sys.stderr)


def main():
    app = PFVServer(SOURCE_DIR)
    app.run()
    sys.exit(app.exec_())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
    finally:
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
