from expipe_plugin_cinpla.scripts import openephys
from expipe_plugin_cinpla.imports import *
from .utils import SelectFilesButton, add_multi_input, extract_multi_input


def openephys_view(project_path):
    openephys_path = SelectFilesButton()
    user = ipywidgets.Text(placeholder='User', value=PAR.USERNAME)
    session = ipywidgets.Text(placeholder='Session')
    location = ipywidgets.Text(placeholder='Location', value=PAR.LOCATION)
    action_id = ipywidgets.Text(placeholder='Action id')
    entity_id = ipywidgets.Text(placeholder='Entity id')
    message = ipywidgets.Text(placeholder='Message')
    tag = ipywidgets.Text(placeholder='Tags (; to separate)')

    no_modules = ipywidgets.Checkbox(description='No modules', value=False)
    overwrite = ipywidgets.Checkbox(description='Overwrite', value=False)
    delete_raw_data = ipywidgets.Checkbox(
        description='Delete raw data', value=False)
    register = ipywidgets.Button(description='Register')

    main_box = ipywidgets.VBox([
            ipywidgets.HBox([openephys_path, no_modules, overwrite, delete_raw_data]),
            user,
            location,
            session,
            action_id,
            entity_id,
            message,
            tag,
            register
        ])

    add_multi_input(main_box, 6, ['Key', 'Probe', 'Depth', 'Unit'], 'Add depth')

    def on_register(change):
        fname = openephys_path.files
        tags = tag.value.split(';')
        depths = extract_multi_input(main_box, 6)
        openephys.register_openephys_recording(
            project_path=project_path,
            action_id=action_id.value,
            openephys_path=fname,
            depth=depths,
            overwrite=overwrite.value,
            no_modules=no_modules.value,
            entity_id=entity_id.value,
            user=user.value,
            session=session.value,
            location=location.value,
            message=message.value,
            tag=tags,
            delete_raw_data=delete_raw_data.value,
            query_depth_answer=True)

    register.on_click(on_register)
    return main_box
