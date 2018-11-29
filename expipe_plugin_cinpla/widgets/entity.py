from expipe_plugin_cinpla.scripts import entity
from expipe_plugin_cinpla.imports import *
from .utils import DatePicker


def entity_view(project_path):
    entity_id = ipywidgets.Text(placeholder='*Entity id')
    user = ipywidgets.Text(placeholder='*User', value=PAR.USERNAME)
    message = ipywidgets.Text(placeholder='Message')
    location = ipywidgets.Text(placeholder='*Location')
    tag = ipywidgets.Text(placeholder='Tags (; to separate)')
    birthday = DatePicker(description='*Birthday', disabled=False)


    overwrite = ipywidgets.Checkbox(description='Overwrite', value=False)

    register = ipywidgets.Button(description='Register')

    main_box = ipywidgets.VBox([
            overwrite,
            entity_id,
            user,
            location,
            birthday,
            message,
            tag,
            register
        ])

    def on_register(change):
        tags = tag.value.split(';')
        if not required_values_filled(entity_id, user, location, birthday):
            return
        entity.register_entity(
            project_path=project_path,
            entity_id=entity_id.value,
            user=user.value,
            message=message.value,
            birthday=birthday.datetime,
            overwrite=overwrite,
            location=location.value,
            tag=tags)

    register.on_click(on_register)
    return main_box
