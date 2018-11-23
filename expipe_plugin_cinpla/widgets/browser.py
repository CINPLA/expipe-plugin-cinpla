import ipywidgets
import IPython.display as ipd
import pathlib
import traitlets
from tkinter import Tk, filedialog
from expipe_plugin_cinpla.tools import openephys


def op():
    openephys_path = SelectFilesButton()
    user = ipywidgets.Text(placeholder='User')
    more_depth = ipywidgets.Button(description='Add depth')
    depth = ipywidgets.HBox([
        more_depth,
        ipywidgets.Text(placeholder='Key'),
        ipywidgets.Text(placeholder='Probe'),
        ipywidgets.Text(placeholder='Depth'),
        ipywidgets.Text(placeholder='Unit')])
    location = ipywidgets.Text(placeholder='Location')
    session = ipywidgets.Text(placeholder='Session')
    action_id = ipywidgets.Text(placeholder='Action id')
    entity_id = ipywidgets.Text(placeholder='Entity id')
    message = ipywidgets.Text(placeholder='Message')
    tag = ipywidgets.Text(placeholder='Tags (; to separate)')

    no_modules = ipywidgets.Checkbox(description='No modules')
    overwrite = ipywidgets.Checkbox(description='Overwrite')
    delete_raw_data = ipywidgets.Checkbox(
        description='Delete raw data', value=False)
    register = ipywidgets.Button(description='Register')

    def on_register(change):
        fname = openephys_path.files
        tags = tag.value.split(';')
        depth = main_box.children[2]
        if isinstance(depth, ipywidgets.HBox):
            depths = (' '.join([a.value for a in depth.children[1:]]))
        elif isinstance(depth, ipywidgets.VBox):
            depths = []
            for ch in depth.children:
                depths.append(' '.join([a.value for a in ch.children[1:]]))
        else:
            raise AssertionError()
        openephys.generate_openephys_action(
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

    main_box = ipywidgets.VBox([
        ipywidgets.HBox([openephys_path, no_modules, overwrite, delete_raw_data]),
        user,
        depth,
        location,
        session,
        action_id,
        entity_id,
        message,
        tag,
        register
    ])

    def on_more_depth(change):
        new_depth = ipywidgets.VBox([
            main_box.children[2],
            ipywidgets.HBox([
                ipywidgets.Output(layout={'width': '165px'}),
                ipywidgets.Text(placeholder='Key'),
                ipywidgets.Text(placeholder='Probe'),
                ipywidgets.Text(placeholder='Depth'),
                ipywidgets.Text(placeholder='Unit')])
            ])
        children = list(main_box.children)
        children[2] = new_depth
        main_box.children = children
        depth = new_depth


    register.on_click(on_register)
    more_depth.on_click(on_more_depth)


    ipd.display(main_box)


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
