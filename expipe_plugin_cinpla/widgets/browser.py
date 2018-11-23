import ipywidgets
import IPython.display as ipd
import pathlib
import traitlets
from tkinter import Tk, filedialog
from expipe_plugin_cinpla.tools import openephys


def op():
    openephys_path = SelectFilesButton()
    user = ipywidgets.Text(placeholder='User')
    depth = ipywidgets.HBox([
        ipywidgets.Text(placeholder='Key'),
        ipywidgets.Text(placeholder='Probe'),
        ipywidgets.Text(placeholder='Depth'),
        ipywidgets.Text(placeholder='Unit')])
    location = ipywidgets.Text(placeholder='Location')
    session = ipywidgets.Text(placeholder='Session')
    entity_id = ipywidgets.Text(placeholder='Entity id')
    message = ipywidgets.Text(placeholder='Message')
    tag = ipywidgets.Text(placeholder='Tags (; to separate)')

    no_modules = ipywidgets.Checkbox(description='No modules')
    overwrite = ipywidgets.Checkbox(description='Overwrite')
    register = ipywidgets.Button(description='Register')

    def on_register(change):
        fname = openephys_path.files
        print(fname)
        tags = tag.value.split(';')
        depth_str = ' '.join([a.value for a in depth.children])
        openephys.generate_openephys_action(
            action_id=None,
            openephys_path=fname[0],
            depth=depth_str,
            overwrite=overwrite.value,
            no_modules=no_modules.value,
            entity_id=entity_id.value,
            user=user.value,
            session=session.value,
            location=location.value,
            message=message.value,
            tag=tags)
    register.on_click(on_register)

    ipd.display(ipywidgets.VBox([
        openephys_path,
        user,
        depth,
        location,
        session,
        entity_id,
        message,
        tag,
        no_modules,
        overwrite,
        register
    ]))


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
