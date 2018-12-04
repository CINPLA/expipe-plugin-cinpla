from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.scripts import surgery
from .utils import DatePicker, MultiInput, Templates, required_values_filled


def surgery_view(project):
    entity_id = ipywidgets.Text(placeholder='*Entity id')
    procedure = ipywidgets.Dropdown(
        description='*Procedure', options=['implantation', 'injection'])
    date = DatePicker(description='*Date', disabled=False)
    user = ipywidgets.Text(placeholder='*User', value=PAR.USERNAME)
    weight = ipywidgets.HBox([
        ipywidgets.Text(placeholder='*Weight', layout={'width': '60px'}),
        ipywidgets.Text(placeholder='*Unit', layout={'width': '60px'})])
    location = ipywidgets.Text(placeholder='*Location', value=PAR.LOCATION)
    message = ipywidgets.Text(placeholder='Message')
    tag = ipywidgets.Text(placeholder='Tags (; to separate)')
    position = MultiInput(['*Key', '*Probe', '*x', '*y', '*z', '*Unit'], 'Add position')
    angle = MultiInput(['*Key', '*Probe', '*Angle', '*Unit'], 'Add angle')
    templates = Templates(project)
    overwrite = ipywidgets.Checkbox(description='Overwrite', value=False)
    register = ipywidgets.Button(description='Register')

    fields = ipywidgets.VBox([
        entity_id,
        user,
        location,
        date,
        weight,
        position,
        angle,
        message,
        procedure,
        tag,
        register
    ])
    main_box = ipywidgets.VBox([
            overwrite,
            ipywidgets.HBox([fields, templates])
        ])



    def on_register(change):
        if not required_values_filled(
            entity_id, user, location, procedure, date, *weight.children, *fields.children[5:7]):
            return
        tags = tag.value.split(';')
        weight_val = (weight.children[0].value, weight.children[1].value)
        surgery.register_surgery(
            project=project,
            overwrite=overwrite.value,
            entity_id=entity_id.value,
            user=user.value,
            procedure=procedure.value,
            location=location.value,
            weight=weight_val,
            date=date.datetime,
            position=position.value,
            angle=angle.value,
            message=message.value,
            tag=tags)

    register.on_click(on_register)
    return main_box


def perfuse_view(project):
    entity_id = ipywidgets.Text(placeholder='Entity id')
    date = DatePicker(disabled=False)
    user = ipywidgets.Text(placeholder='User', value=PAR.USERNAME)
    message = ipywidgets.Text(placeholder='Message')
    weight = ipywidgets.HBox([
        ipywidgets.Text(placeholder='*Weight', layout={'width': '60px'}),
        ipywidgets.Text(placeholder='*Unit', layout={'width': '60px'})])
    templates = Templates(project)
    overwrite = ipywidgets.Checkbox(description='Overwrite', value=False)

    register = ipywidgets.Button(description='Register')
    fields = ipywidgets.VBox([
        entity_id,
        date,
        user,
        weight,
        message,
        register
    ])
    main_box = ipywidgets.VBox([
        overwrite,
        ipywidgets.HBox([fields, templates])
    ])

    def on_register(change):
        weight_val = (weight.children[0].value, weight.children[1].value)
        surgery.register_perfusion(
            project=project,
            entity_id=entity_id.value,
            user=user.value,
            overwrite=overwrite.value,
            date=date.datetime,
            weight=weight_val,
            message=message.value)

    register.on_click(on_register)
    return main_box
