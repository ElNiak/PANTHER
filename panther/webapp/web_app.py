#!/usr/bin/env python3.9

import os
from flask import (
    Flask,
    redirect,
)
from flask_cors import CORS
from omegaconf import OmegaConf

from panther.config.config_global_schema import GlobalConfig
from panther.config.config_manager import ConfigLoader
from panther.core.experiment_manager import ExperimentManager


def create_app(config_loader: ConfigLoader, global_config: GlobalConfig, args):
    app = Flask(
        "panther_webapp",
        static_folder="panther/webapp/static/",
        template_folder="panther/webapp/templates/",
    )
    # # app.logger.setLevel(logging.DEBUG)
    print(f"Flask app template - {app.template_folder} - {os.getcwd()}")
    app.secret_key = "ElNiakDummyKey"
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    app.config["APPLICATION_ROOT"] = "panther/webapp/templates/"
    CORS(app, resources={r"/*": {"origins": "*"}})

    app.config["config_loader"] = config_loader
    app.config["global_config"] = global_config
    experiment_manager = ExperimentManager(
        global_config=global_config, experiment_name=args.experiment_name
    )
    experiment_manager.test_cases
    app.config["experiment_manager"] = experiment_manager

    experiment_config = config_loader.load_and_validate_experiment_config()
    print(f"Experiment Config: {OmegaConf.to_yaml(experiment_config)}")
    app.config["experiment_config"] = experiment_config
    # Once we have the experiments configurations, we can initialize the experiment
    experiment_manager.initialize_experiments(experiment_config)

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
        return redirect("index", code=302)

    return app


def run(config_loader: ConfigLoader, global_config: GlobalConfig, args):
    print("Running webapp")
    app = create_app(
        config_loader=config_loader, global_config=global_config, args=args
    )
    app.run(host="0.0.0.0", port=8080, use_reloader=True, threaded=True, debug=True)
