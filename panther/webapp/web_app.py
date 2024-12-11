#!/usr/bin/env python3.9

import os
from flask import (
    Flask,
    redirect,
)
from flask_cors import CORS
import logging

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SelectField
from wtforms.validators import DataRequired, NumberRange
from dataclasses import fields
from enum import Enum


# Utility: Convert Enum to SelectField choices
def enum_to_choices(enum_cls):
    return [(e.name, e.value) for e in enum_cls]


# Utility: Map Python types to WTForms fields
def type_to_field(field_type, metadata):
    if field_type is bool:
        return BooleanField()
    elif field_type is int:
        return IntegerField(
            validators=[
                NumberRange(
                    min=metadata.get("min", None), max=metadata.get("max", None)
                )
            ]
        )
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


def create_app():
    app = Flask(
        __name__,
        static_folder=os.path(os.getcwd, "/panther/webapp/static/"),
        template_folder=os.path(os.getcwd, "/panther/webapp/templates/"),
    )
    app.logger.setLevel(logging.DEBUG)
    app.secret_key = "ElNiakDummyKey"
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    app.config["APPLICATION_ROOT"] = os.path(os.getcwd, "/panther/webapp/templates/")
    CORS(app, resources={r"/*": {"origins": "*"}})

    from .experiment_setup import exp_manager

    app.register_blueprint(exp_manager, url_prefix="/")

    app.logger.info(f"Flask app template - {app.template_folder}")

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

    return app


def run():
    app = create_app()
    app.run(host="0.0.0.0", port=8080, use_reloader=True, threaded=True, debug=True)
