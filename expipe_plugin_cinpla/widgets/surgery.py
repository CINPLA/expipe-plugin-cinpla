from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.scripts import surgery
from .utils import DatePicker, add_multi_input, extract_multi_input


def surgery_view(project_path):
    entity_id = ipywidgets.Text(placeholder='*Entity id')
    procedure = ipywidgets.Dropdown(
        description='*Procedure', options=['implantation', 'injection'])
    date = DatePicker(description='*Date', disabled=False)
    user = ipywidgets.Text(placeholder='*User', value=PAR.USERNAME)
    weight = ipywidgets.HBox([
        ipywidgets.Text(placeholder='*Weight'),
        ipywidgets.Text(placeholder='*Unit')])
    location = ipywidgets.Text(placeholder='*Location', value=PAR.LOCATION)
    message = ipywidgets.Text(placeholder='Message')
    tag = ipywidgets.Text(placeholder='Tags (; to separate)')

    overwrite = ipywidgets.Checkbox(description='Overwrite', value=False)
    register = ipywidgets.Button(description='Register')

    main_box = ipywidgets.VBox([
            overwrite,
            entity_id,
            user,
            location,
            date,
            weight,
            message,
            procedure,
            tag,
            register
        ])

    add_multi_input(main_box, 6, ['*Key', '*Probe', '*x', '*y', '*z', '*Unit'], 'Add position')
    add_multi_input(main_box, 7, ['*Key', '*Probe', '*Angle', '*Unit'], 'Add angle')

    def on_register(change):
        if not required_values_filled(
            entity_id, user, location, procedure, date, *weight.children, *main_box.children[6:8]):
            return
        tags = tag.value.split(';')
        positions = extract_multi_input(main_box, 6)
        angles = extract_multi_input(main_box, 7)
        weight_val = (weight.children[0].value, weight.children[1].value)
        surgery.register_surgery(
            project_path=project_path,
            overwrite=overwrite.value,
            entity_id=entity_id.value,
            user=user.value,
            procedure=procedure.value,
            location=location.value,
            weight=weight_val,
            date=date.datetime,
            position=positions,
            angle=angles,
            message=message.value,
            tag=tags)

    register.on_click(on_register)
    return main_box


def perfuse_view(project_path):
    entity_id = ipywidgets.Text(placeholder='Entity id')
    date = DatePicker(disabled=False)
    user = ipywidgets.Text(placeholder='User', value=PAR.USERNAME)
    message = ipywidgets.Text(placeholder='Message')
    weight = ipywidgets.Text(placeholder='Weight')

    overwrite = ipywidgets.Checkbox(description='Overwrite', value=False)

    register = ipywidgets.Button(description='Register')

    main_box = ipywidgets.VBox([
            overwrite,
            entity_id,
            date,
            user,
            weight,
            message,
            register
        ])

    def on_register(change):
        surgery.register_perfusion(
            project_path=project_path,
            entity_id=entity_id.value,
            user=user.value,
            overwrite=overwrite.value,
            date=date.datetime,
            weight=weight.value,
            message=message.value)

    register.on_click(on_register)
    return main_box
