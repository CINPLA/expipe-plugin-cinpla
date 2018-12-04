from expipe_plugin_cinpla.scripts import entity
from expipe_plugin_cinpla.imports import *
from .utils import DatePicker, Templates, required_values_filled


def entity_view(project):
    entity_id = ipywidgets.Text(placeholder='*Entity id')
    user = ipywidgets.Text(placeholder='*User', value=PAR.USERNAME)
    message = ipywidgets.Text(placeholder='Message')
    location = ipywidgets.Text(placeholder='*Location')
    tag = ipywidgets.Text(placeholder='Tags (; to separate)')
    birthday = DatePicker(description='*Birthday', disabled=False)
    templates = Templates(project)

    overwrite = ipywidgets.Checkbox(description='Overwrite', value=False)

    register = ipywidgets.Button(description='Register')

    fields = ipywidgets.VBox([
        entity_id,
        user,
        location,
        birthday,
        message,
        tag,
        register])

    main_box = ipywidgets.VBox([
            overwrite,
            ipywidgets.HBox([fields, templates])

        ])

    def on_register(change):
        tags = tag.value.split(';')
        if not required_values_filled(entity_id, user, location, birthday):
            return
        entity.register_entity(
            project=project,
            entity_id=entity_id.value,
            user=user.value,
            message=message.value,
            birthday=birthday.datetime,
            overwrite=overwrite,
            location=location.value,
            tag=tags,
            templates=templates.value)

    register.on_click(on_register)
    return main_box
