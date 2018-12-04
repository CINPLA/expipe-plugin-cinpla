from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.scripts import openephys
from .utils import SelectDirectoryButton, MultiInput, Templates, SelectFileButton, required_values_filled, none_if_empty, split_tags


def openephys_view(project):
    openephys_path = SelectDirectoryButton()
    user = ipywidgets.Text(placeholder='*User', value=PAR.USERNAME)
    session = ipywidgets.Text(placeholder='Session')
    location = ipywidgets.Text(placeholder='*Location', value=PAR.LOCATION)
    action_id = ipywidgets.Text(placeholder='Action id')
    entity_id = ipywidgets.Text(placeholder='Entity id')
    message = ipywidgets.Text(placeholder='Message')
    tag = ipywidgets.Text(placeholder='Tags (; to separate)')
    templates = Templates(project)
    depth = MultiInput(['Key', 'Probe', 'Depth', 'Unit'], 'Add depth')
    register_depth = ipywidgets.Checkbox(description='Register depth', value=False)
    register_depth_from_adjustment = ipywidgets.Checkbox(
        description='Find adjustments', value=True)

    overwrite = ipywidgets.Checkbox(description='Overwrite', value=False)
    delete_raw_data = ipywidgets.Checkbox(
        description='Delete raw data', value=False)
    register = ipywidgets.Button(description='Register')

    fields = ipywidgets.VBox([
        user,
        location,
        session,
        action_id,
        entity_id,
        message,
        tag,
        register
    ])
    checks = ipywidgets.HBox([openephys_path, register_depth, overwrite, delete_raw_data])
    main_box = ipywidgets.VBox([
            checks,
            ipywidgets.HBox([fields, templates])
        ])


    def on_register_depth(change):
         if change['name'] == 'value':
             if change['owner'].value:
                 children = list(checks.children)
                 children = children[:2] + [register_depth_from_adjustment] + children[2:]
                 checks.children = children
             else:
                children = list(checks.children)
                del(children[2])
                checks.children = children


    def on_register_depth_from_adjustment(change):
         if change['name'] == 'value':
             if not change['owner'].value:
                 children = list(fields.children)
                 children = children[:5] + [depth] + children[5:]
                 fields.children = children
             else:
                 children = list(fields.children)
                 del(children[5])
                 fields.children = children

    register_depth.observe(on_register_depth)
    register_depth_from_adjustment.observe(on_register_depth_from_adjustment)


    def on_register(change):
        if not required_values_filled(user, location):
            return
        tags = split_tags(tag)
        openephys.register_openephys_recording(
            templates=templates.value,
            project=project,
            action_id=none_if_empty(action_id.value),
            openephys_path=openephys_path.directory,
            depth=depth.value,
            overwrite=overwrite.value,
            register_depth=register_depth.value,
            entity_id=none_if_empty(entity_id.value),
            user=user.value,
            session=session.value,
            location=location.value,
            message=none_if_empty(message.value),
            tag=tags,
            delete_raw_data=delete_raw_data.value,
            correct_depth_answer=True)

    register.on_click(on_register)
    return main_box

#TODO add spike sorter specific params
def process_view(project):
    probe_path = SelectFileButton('.prb')
    action_id = ipywidgets.Text(placeholder='Action id')
    templates = Templates(project)
    sorter = ipywidgets.Dropdown(
        description='*Sorter', options=['klusta', 'mountain', 'kilosort', 'spyking-circus', 'ironclust'])

    run = ipywidgets.Button(description='Process')

    fields = ipywidgets.VBox([
        action_id,
        sorter,
        run
    ])
    main_box = ipywidgets.VBox([
            probe_path,
            fields
        ])

    def on_run(change):
        openephys.process_openephys(
            project=project,
            action_id=action_id.value,
            probe_path=probe_path.files[0],
            sorter=sorter.value)

    run.on_click(on_run)
    return main_box
