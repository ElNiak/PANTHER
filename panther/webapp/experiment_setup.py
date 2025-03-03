from dataclasses import fields
from flask import Blueprint, redirect, render_template, request, current_app
from flask_wtf import FlaskForm
from wtforms import (
    FieldList,
    FormField,
    StringField,
    IntegerField,
    BooleanField,
    SelectField,
    SubmitField,
)
from wtforms.validators import DataRequired, NumberRange, Optional
from dataclasses import MISSING, is_dataclass
from enum import Enum
from panther.config.config_global_schema import GlobalConfig
import typing
from panther.core.utils.jinja_manager import JinjaManager #Import JinjaManager
from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify
import logging
from omegaconf import OmegaConf


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


def generate_form(dataclass):
    print(f"Generating form for dataclass: {dataclass.__name__}")
    if not is_dataclass(dataclass):
        raise ValueError("Provided class is not a dataclass")

    class DynamicForm(FlaskForm):
        pass

    for field in fields(dataclass):
        print(f"Processing dataclass: {dataclass}")
        field_type = field.type
        default_value = field.default if field.default != MISSING else None

        print(
            f"Processing field: {field.name}, Type: {field_type}, Default: {default_value}"
        )

        if is_dataclass(field_type):
            print(f"Field {field.name} is a nested dataclass. Generating nested form.")
            nested_form = generate_form(field_type)
            setattr(DynamicForm, field.name, FormField(nested_form))
        elif field.name == "type":
            choices = []
            all_choice = current_app.config["config_loader"].load_all_plugins()
            print(f"Field {field.name} is a type field with choices: {all_choice}")
            # plugin_loader = current_app.config["config_loader"].load_all_plugins()
            setattr(
                DynamicForm,
                field.name,
                SelectField(
                    field.name.capitalize(),
                    choices=[choice[0] for choice in choices],
                    validators=[DataRequired()],
                ),
            )
        elif field_type is str:
            setattr(
                DynamicForm,
                field.name,
                StringField(
                    field.name.capitalize(),
                    default=default_value,
                    validators=[Optional()],
                ),
            )
        elif field_type is int:
            setattr(
                DynamicForm,
                field.name,
                IntegerField(
                    field.name.capitalize(),
                    default=default_value,
                    validators=[Optional()],
                ),
            )
        elif field_type is bool:
            setattr(
                DynamicForm,
                field.name,
                BooleanField(field.name.capitalize(), default=default_value),
            )
        elif isinstance(field_type, type(Enum)):
            choices = [(e.name, e.value) for e in field_type]
            print(f"Field {field.name} is an Enum with choices: {choices}")
            setattr(
                DynamicForm,
                field.name,
                SelectField(
                    field.name.capitalize(),
                    choices=[choice[0] for choice in choices],
                    validators=[Optional()],
                ),
            )
        elif hasattr(field_type, "__origin__") and field_type.__origin__ is list:
            # Handle List of dataclasses or primitives
            print(f"Field {field.name} is a List. Generating FieldList.")
            inner_type = field_type.__args__[0]
            if is_dataclass(inner_type):
                nested_form = generate_form(inner_type)
                setattr(
                    DynamicForm,
                    field.name.capitalize(),
                    FieldList(FormField(nested_form), min_entries=1),
                )
            else:
                setattr(
                    DynamicForm,
                    field.name.capitalize(),
                    FieldList(StringField(field.name), min_entries=1),
                )
            # Add a button to extend the list
            setattr(
                DynamicForm,
                f"add_{field.name}_button",
                SubmitField(f"Add {field.name.capitalize()}"),
            )

            def add_to_list(self):
                getattr(self, field.name.capitalize()).append_entry()

            setattr(DynamicForm, f"add_{field.name}_to_list", add_to_list)
        elif hasattr(field_type, "__origin__") and field_type.__origin__ is dict:
            # Handle Dict of dataclasses or primitives
            print(
                f"Field {field.name} is a Dict. Generating FieldList for keys and values."
            )
            key_type, value_type = field_type.__args__
            if is_dataclass(value_type):
                nested_form = generate_form(value_type)
                setattr(
                    DynamicForm,
                    field.name.capitalize(),
                    FieldList(FormField(nested_form), min_entries=1),
                )
            else:
                setattr(
                    DynamicForm,
                    field.name.capitalize(),
                    FieldList(StringField(field.name), min_entries=1),
                )
        elif (
            hasattr(field_type, "__origin__")
            and field_type.__origin__ is typing.Optional
        ):
            # Handle Optional types
            print(f"Field {field.name} is an Optional. Generating Optional Field.")
            inner_type = field_type.__args__[0]
            if hasattr(inner_type, "__origin__") and inner_type.__origin__ is list:
                print(f"Field {field.name} is an Optional List. Generating FieldList.")
                list_inner_type = inner_type.__args__[0]
                if is_dataclass(list_inner_type):
                    nested_form = generate_form(list_inner_type)
                    setattr(
                        DynamicForm,
                        field.name,
                        FieldList(FormField(nested_form), min_entries=0),
                    )
                else:
                    setattr(
                        DynamicForm,
                        field.name,
                        FieldList(StringField(field.name), min_entries=0),
                    )
            elif is_dataclass(inner_type):
                print(
                    f"Field {field.name} is an Optional dataclass. Generating FormField."
                )
                nested_form = generate_form(inner_type)
                setattr(DynamicForm, field.name.capitalize(), FormField(nested_form))
            elif inner_type is str:
                setattr(
                    DynamicForm,
                    field.name.capitalize(),
                    StringField(field.name, validators=[Optional()]),
                )
            elif inner_type is int:
                setattr(
                    DynamicForm,
                    field.name.capitalize(),
                    IntegerField(field.name, validators=[Optional()]),
                )
            elif inner_type is bool:
                setattr(DynamicForm, field.name.capitalize(), BooleanField(field.name))
            elif isinstance(inner_type, type(Enum)):
                choices = [(e.name, e.value) for e in inner_type]
                print(f"Field {field.name} is an Optional Enum with choices: {choices}")
                setattr(
                    DynamicForm,
                    field.name.capitalize(),
                    SelectField(field.name, choices=choices, validators=[Optional()]),
                )
            else:
                print(
                    f"Field {field.name} is an Optional unhandled type {inner_type}, defaulting to StringField."
                )
                setattr(
                    DynamicForm,
                    field.name.capitalize(),
                    StringField(field.name, validators=[Optional()]),
                )
        else:
            print(
                f"Field {field.name} is of unhandled type {field_type}, defaulting to StringField."
            )
            setattr(
                DynamicForm,
                field.name.capitalize(),
                StringField(field.name, default=default_value, validators=[Optional()]),
            )

    # setattr(DynamicForm, 'submit', SubmitField('Submit'))
    print(f"Form generation complete for dataclass: {dataclass.__name__}")
    return DynamicForm


exp_manager = Blueprint("experiment-manager", __name__)


@exp_manager.route("/index", methods=["GET", "POST"])
def create_experiment():
    form_class = generate_form(GlobalConfig)
    form = form_class()

    current_app.logger.info(f"Flask app template - {current_app.template_folder}")

    exp_form_class = generate_form(current_app.config["experiment_config"])
    exp_form = exp_form_class()
    if request.method == "POST" and form.validate():
        updated_data = {
            field.name: form.data[field.name] for field in fields(GlobalConfig)
        }
        updated_instance = GlobalConfig(**updated_data)
        print("Updated Dataclass Instance:", updated_instance)
        return redirect("/index")

    return render_template("index.html", form=form, exp_form=exp_form)



# Create a blueprint
exp_manager = Blueprint('exp_manager', __name__)

@exp_manager.route('/index')
def index():
    experiment_manager = current_app.config.get('experiment_manager')
    test_cases = experiment_manager.test_cases

    # Count unique protocols and implementations
    protocols = set()
    implementations = set()
    services_count = 0

    for test in test_cases:
        services_count += len(test.services)
        for service_name, service in test.services.items():
            protocols.add(service.protocol.name)
            implementations.add(service.implementation.name)

    return render_template(
        'index.html',
        active_page='dashboard',
        tests=test_cases,
        protocols_count=len(protocols),
        implementations_count=len(implementations),
        services_count=services_count
    )

@exp_manager.route('/experiments')
def experiments():
    experiment_manager = current_app.config.get('experiment_manager')
    test_cases = experiment_manager.test_cases

    return render_template(
        'experiments.html',
        active_page='experiments',
        tests=test_cases
    )

@exp_manager.route('/plugins')
def plugins():
    config_loader = current_app.config.get('config_loader')
    plugins = config_loader.load_all_plugins()

    return render_template(
        'plugins.html',
        active_page='plugins',
        plugins=plugins
    )

@exp_manager.route('/configuration')
def configuration():
    global_config = current_app.config.get('global_config')
    experiment_config = current_app.config.get('experiment_config')

    return render_template(
        'configuration.html',
        active_page='configuration',
        global_config=global_config,
        experiment_config=experiment_config
    )

@exp_manager.route('/logs')
def logs():
    global_config = current_app.config.get('global_config')
    log_dir = global_config.paths.log_dir

    # This is a placeholder - you would need to implement actual log fetching
    recent_logs = []

    return render_template(
        'logs.html',
        active_page='logs',
        log_dir=log_dir,
        recent_logs=recent_logs
    )

# API Endpoints

@exp_manager.route('/api/global-config')
def global_config_api():
    global_config = current_app.config.get('global_config')
    return jsonify(OmegaConf.to_container(global_config))

@exp_manager.route('/api/test-cases')
def test_cases_api():
    experiment_manager = current_app.config.get('experiment_manager')
    test_cases = experiment_manager.test_cases

    test_cases_dict = []
    for test in test_cases:
        test_cases_dict.append({
            'name': test.name,
            'description': test.description,
            'network_environment': test.network_environment,
            'iterations': test.iterations,
            'service_count': len(test.services) if hasattr(test, 'services') else 0
        })

    return jsonify(test_cases_dict)

@exp_manager.route('/api/test/<test_name>')
def get_test(test_name):
    experiment_manager = current_app.config.get('experiment_manager')

    for test in experiment_manager.test_cases:
        if test.name == test_name:
            return jsonify(OmegaConf.to_container(test))

    return jsonify({'error': 'Test not found'}), 404

@exp_manager.route('/api/run-experiment', methods=['POST'])
def run_experiment():
    try:
        test_name = request.json.get('test_name')
        experiment_manager = current_app.config.get('experiment_manager')

        if test_name:
            for test in experiment_manager.test_cases:
                if test.name == test_name:
                    result = experiment_manager.run_test(test)
                    return jsonify({"status": "success", "result": "Test executed successfully"})

            return jsonify({"status": "error", "message": f"Test {test_name} not found"})
        else:
            results = experiment_manager.run_tests()
            return jsonify({"status": "success", "results": "All tests executed successfully"})
    except Exception as e:
        logging.error(f"Error running experiment: {e}")
        return jsonify({"status": "error", "message": str(e)})