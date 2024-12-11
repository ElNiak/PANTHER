from flask import Blueprint, render_template, request

from config.config_global_schema import GlobalConfig
from webapp.web_app import dataclass_to_form

exp_manager = Blueprint("experiment-manager", __name__)


@exp_manager.route("/index", methods=["GET", "POST"])
def create_experiment():
    """
    It creates a folder for the project, and then calls the upload function
    :return: the upload function.
    """
    form_class = dataclass_to_form(GlobalConfig)
    form = form_class()
    if request.method == "POST" and form.validate():
        # Process submitted data
        return f"Configuration submitted: {request.form}"
    return render_template("index.html", form=form)
