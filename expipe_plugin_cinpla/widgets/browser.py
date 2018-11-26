import ipywidgets
import IPython.display as ipd
import pathlib
from expipe_plugin_cinpla.imports import *
import traitlets
from tkinter import Tk, filedialog
from expipe_plugin_cinpla.tools import openephys, surgery, adjust, entity


def extract_multi_input(main_box, i):
    position = main_box.children[i]
    if isinstance(position, ipywidgets.HBox):
        positions = (' '.join([a.value for a in position.children[1:]]))
    elif isinstance(position, ipywidgets.VBox):
        positions = []
        for ch in position.children:
            positions.append(' '.join([a.value for a in ch.children[1:]]))
    else:
        raise AssertionError()
    return positions


def add_multi_input(main_box, i, var, description):
    more_input = ipywidgets.Button(
        description=description, layout={'width': '160px'})
    inp = ipywidgets.HBox(
        [more_input] +
        [ipywidgets.Text(placeholder=v, layout={'width': '100px'}) for v in var])
    children = list(main_box.children)
    children = children[:i] + [inp] + children[i:]
    main_box.children = children

    def on_more_input(change):
        new_input = ipywidgets.VBox([
            main_box.children[i],
            ipywidgets.HBox(
                [ipywidgets.Output(layout={'width': '165px'})] +
                [ipywidgets.Text(placeholder=v, layout={'width': '100px'})
                 for v in var])
        ])
        children = list(main_box.children)
        children[i] = new_input
        main_box.children = children
        inp = new_input

    more_input.on_click(on_more_input)
    return inp


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
        openephys.generate_openephys_action(
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

def surgery_view(project_path):
    entity_id = ipywidgets.Text(placeholder='Entity id')
    procedure = ipywidgets.Dropdown(options=['implantation', 'injection'])
    date = ipywidgets.DatePicker(disabled=False)
    user = ipywidgets.Text(placeholder='User', value=PAR.USERNAME)
    weight = ipywidgets.HBox([
        ipywidgets.Text(placeholder='Weight'),
        ipywidgets.Text(placeholder='Unit')])
    location = ipywidgets.Text(placeholder='Location', value=PAR.LOCATION)
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

    add_multi_input(main_box, 6, ['Key', 'Probe', 'x', 'y', 'z', 'Unit'], 'Add position')
    add_multi_input(main_box, 7, ['Key', 'Probe', 'Angle', 'Unit'], 'Add angle')

    def on_register(change):
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
            date=date.value,
            position=positions,
            angle=angles,
            message=message.value,
            tag=tags)

    register.on_click(on_register)
    return main_box


def adjustment_view(project_path):
    entity_id = ipywidgets.Text(placeholder='Entity id')
    date = ipywidgets.DatePicker(disabled=False)
    user = ipywidgets.Text(placeholder='User', value=PAR.USERNAME)

    overwrite = ipywidgets.Checkbox(description='Overwrite', value=False)
    init = ipywidgets.Checkbox(description='Initialize', value=False)
    manual_depth = ipywidgets.Checkbox(description='Manual depth', value=False)
    register = ipywidgets.Button(description='Register')

    main_box = ipywidgets.VBox([
            ipywidgets.HBox([overwrite, init, manual_depth]),
            entity_id,
            user,
            date,
            register
        ])

    add_multi_input(main_box, 4, ['Key', 'Probe', 'Adjustment', 'Unit'], 'Add adjustment')

    def on_manual_depth(change):
        if change['name'] == 'value':
            if change['owner'].value:
                add_multi_input(
                    main_box, 5, ['Key', 'Probe', 'Depth', 'Unit'],
                    'Add depth')
            else:
                idxs = []
                for i, ch in enumerate(main_box.children):
                    if isinstance(ch, ipywidgets.HBox) and len(ch.children) == 5:
                        if ch.children[3].placeholder == 'Depth':
                            idxs.append(i)
                children = list(main_box.children)
                for i in idxs:
                    del(children[i])
                main_box.children = children

    manual_depth.observe(on_manual_depth, names='value')

    def on_register(change):
        adjustment = extract_multi_input(main_box, 4)
        if manual_depth.value:
            depth = extract_multi_input(main_box, 5)
        else:
            depth = None
        adjust.register_adjustment(
            project_path=project_path,
            entity_id=entity_id.value,
            date=date.value,
            adjustment=adjustment,
            user=user.value,
            index=None,
            init=init.value,
            depth=depth,
            yes=True,
            overwrite=overwrite.value)

    register.on_click(on_register)
    return main_box


def perfuse_view(project_path):
    entity_id = ipywidgets.Text(placeholder='Entity id')
    date = ipywidgets.DatePicker(disabled=False)
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
            date=date.value,
            weight=weight.value,
            message=message.value)

    register.on_click(on_register)
    return main_box


def entity_view(project_path):
    entity_id = ipywidgets.Text(placeholder='Entity id')
    user = ipywidgets.Text(placeholder='User', value=PAR.USERNAME)
    message = ipywidgets.Text(placeholder='Message')
    location = ipywidgets.Text(placeholder='Location')
    tag = ipywidgets.Text(placeholder='Tags (; to separate)')
    birthday = ipywidgets.DatePicker(description='Birthday', disabled=False)


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
        entity.register_entity(
            project_path=project_path,
            entity_id=entity_id.value,
            user=user.value,
            message=message.value,
            birthday=birthday.value,
            overwrite=overwrite,
            location=location.value,
            tag=tags)

    register.on_click(on_register)
    return main_box


def main_view(project_path):
    # register tab
    register_tab_tab_titles = ['OpenEphys', 'Adjustment', 'Entity', 'Surgery', 'Perfusion', ]
    register_tab = ipywidgets.Tab()
    register_tab.children = [
        openephys_view(project_path), adjustment_view(project_path),
        entity_view(project_path),
        surgery_view(project_path), perfuse_view(project_path),
    ]
    for i, title in enumerate(register_tab_tab_titles):
        register_tab.set_title(i, title)

    tab_titles = ['Register']
    tab = ipywidgets.Tab()
    tab.children = [
        register_tab
    ]
    for i, title in enumerate(tab_titles):
        tab.set_title(i, title)
    ipd.display(tab)


class SelectFilesButton(ipywidgets.Button):
    """A file widget that leverages tkinter.filedialog."""

    def __init__(self, *args, **kwargs):
        """Initialize the SelectFilesButton class."""
        super(SelectFilesButton, self).__init__(*args, **kwargs)
        # Add the selected_files trait
        self.add_traits(files=traitlets.traitlets.Unicode())
        # Create the button.
        self.description = "Select Files"
        self.icon = "square-o"
        self.style.button_color = "orange"
        # Set on click behavior.
        self.on_click(self.select_files)

    @staticmethod
    def select_files(b):
        """Generate instance of tkinter.filedialog.
        Parameters
        ----------
        b : obj:
            An instance of ipywidgets.ipywidgets.Button
        """
        # Create Tk root
        root = Tk()
        # Hide the main window
        root.withdraw()
        # Raise the root to the top of all windows.
        root.call('wm', 'attributes', '.', '-topmost', True)
        # List of selected fileswill be set to b.value
        b.files = filedialog.askdirectory()

        b.description = "Files Selected"
        b.icon = "check-square-o"
        b.style.button_color = "lightgreen"
