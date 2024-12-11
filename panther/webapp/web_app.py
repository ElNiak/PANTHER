#!/usr/bin/env python3.9
# -*- coding: utf-8 -*-

import json
import os
import socket
import subprocess
import time
import uuid
import threading
import requests
from flask import (
    Flask,
    request,
    redirect,
    send_from_directory, 
    render_template,
    jsonify,
)
from flask_socketio import SocketIO
from base64 import b64encode
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import datetime
from flask_cors import CORS
import pandas as pd
from npf_web_extension.app import export
import argparse
import sys
from termcolor import cprint
import terminal_banner
import logging

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SelectField, FormField, FieldList
from wtforms.validators import DataRequired, NumberRange
from dataclasses import fields, is_dataclass
from enum import Enum

from panther.config.config_global_schema import DockerConfig, GlobalConfig, LoggingConfig, PathsConfig
from panther.config.config_experiment_schema import ExperimentConfig, ServiceConfig, TestConfig
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.plugins.services.iut.config_schema import ImplementationConfig


# Utility: Convert Enum to SelectField choices
def enum_to_choices(enum_cls):
    return [(e.name, e.value) for e in enum_cls]

# Utility: Map Python types to WTForms fields
def type_to_field(field_type, metadata):
    if field_type is bool:
        return BooleanField()
    elif field_type is int:
        return IntegerField(validators=[
            NumberRange(min=metadata.get("min", None), max=metadata.get("max", None))
        ])
    elif field_type is str:
        return StringField(validators=[DataRequired()])
    elif isinstance(field_type, Enum):
        return SelectField(choices=enum_to_choices(field_type))
    return StringField()  # Fallback

# Utility: Dynamically generate WTForms from dataclasses
def dataclass_to_form(dataclass_type):
    class DynamicForm(FlaskForm):
        pass
    for field in fields(dataclass_type):
        field_name = field.name
        field_type = field.type
        metadata = field.metadata
        form_field = type_to_field(field_type, metadata)
        setattr(DynamicForm, field_name, form_field)
    return DynamicForm

app = Flask(__name__, static_folder="webapp/static/")
app.secret_key = "ElNiakDummyKey"  
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["APPLICATION_ROOT"] =  "webapp/templates/"
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app)

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

@app.route("/index.html", methods=["GET", "POST"])
def serve_index():
    """
    It creates a folder for the project, and then calls the upload function
    :return: the upload function.
    """
    form_class = dataclass_to_form(GlobalConfig)
    form = form_class()
    if request.method == 'POST' and form.validate():
        # Process submitted data
        return f"Configuration submitted: {request.form}"
    return render_template('index.html', form=form)

def run():
    app.run(
        host="0.0.0.0", port=8080, use_reloader=True, threaded=True, debug=True
    )


