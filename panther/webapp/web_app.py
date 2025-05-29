import os
import logging
from flask import (
    Flask,
    redirect,
    request,
    jsonify,
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

    # Add Jinja helper functions
    from panther.core.utils.jinja_manager import JinjaManager

    jinja_manager = JinjaManager(app.template_folder)
    app.jinja_env.globals["has_attr"] = jinja_manager.has_attr
    app.jinja_env.globals["safe_getattr"] = jinja_manager.safe_getattr

    # Also add as filters
    app.jinja_env.filters["has_attr"] = jinja_manager.has_attr
    app.jinja_env.filters["safe_getattr"] = jinja_manager.safe_getattr
    app.jinja_env.filters["safe_length"] = jinja_manager.safe_length
    app.jinja_env.filters["length"] = jinja_manager.safe_length

    # API endpoints for the dynamic UI
    @app.route("/api/plugins", methods=["GET"])
    def get_plugins():
        """Return all available plugins"""
        plugins = config_loader.load_all_plugins()
        return jsonify(plugins)

    @app.route("/api/experiments", methods=["GET"])
    def get_experiments():
        """Return all experiments"""
        return jsonify(OmegaConf.to_container(experiment_config))

    @app.route("/api/run-experiment", methods=["POST"])
    def run_experiment():
        """Run an experiment"""
        try:
            test_name = request.json.get("test_name")
            if test_name:
                # Run specific test
                for test in experiment_manager.test_cases:
                    if test.name == test_name:
                        result = experiment_manager.run_test(test)
                        return jsonify({"status": "success", "result": result})
                return jsonify(
                    {"status": "error", "message": f"Test {test_name} not found"}
                )
            else:
                # Run all tests
                results = experiment_manager.run_tests()
                return jsonify({"status": "success", "results": results})
        except Exception as e:
            logging.error(f"Error running experiment: {e}")
            return jsonify({"status": "error", "message": str(e)})

    @app.route("/api/protocols", methods=["GET"])
    def get_protocols():
        """Return all available protocols"""
        protocols = config_loader.get_all_protocol_classes()
        return jsonify(protocols)

    @app.route("/api/environments", methods=["GET"])
    def get_environments():
        """Return all available network and execution environments"""
        net_envs = config_loader.get_all_net_env_classes()
        exec_envs = config_loader.get_all_exec_env_classes()
        return jsonify(
            {"network_environments": net_envs, "execution_environments": exec_envs}
        )

    @app.route("/api/implementations", methods=["GET"])
    def get_implementations():
        """Return all available implementations"""
        iuts = config_loader.get_all_iut_classes()
        testers = config_loader.get_all_tester_classes()
        return jsonify({"iuts": iuts, "testers": testers})

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
