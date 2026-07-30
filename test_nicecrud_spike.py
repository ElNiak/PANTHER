"""NiceCRUD spike: test with PANTHER config models."""
from nicegui import ui
from niceguicrud import NiceCRUD
from panther.config.core.models.global_config import LoggingConfig, DockerConfig
from panther.webapp.utils.form_models import strip_omega_config

@ui.page('/')
def main():
    ui.label("NiceCRUD Spike").classes('text-h4')

    # IMPORTANT: PANTHER models carry omega_config: Optional[DictConfig]
    # which breaks NiceCRUD's JSON Schema generation. strip_omega_config()
    # removes it recursively.

    # Test 1: Simple flat model
    ui.label("LoggingConfig:").classes('text-h6')
    try:
        FormModel = strip_omega_config(LoggingConfig)
        crud = NiceCRUD(FormModel, id_field='level')
        crud.show_table()
        ui.label("LoggingConfig: works!").classes('text-green')
    except Exception as e:
        ui.label(f"LoggingConfig FAILED: {e}").classes('text-red')

    # Test 2: Nested model (note: field is force_build_docker_image, NOT force_build)
    ui.label("DockerConfig:").classes('text-h6')
    try:
        FormModel2 = strip_omega_config(DockerConfig)
        crud2 = NiceCRUD(FormModel2, id_field='force_build_docker_image')
        crud2.show_table()
        ui.label("DockerConfig: works!").classes('text-green')
    except Exception as e:
        ui.label(f"DockerConfig FAILED: {e}").classes('text-red')

ui.run(port=9999)