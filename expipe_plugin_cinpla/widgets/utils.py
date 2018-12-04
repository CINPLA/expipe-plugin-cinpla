from expipe_plugin_cinpla.imports import *


def required_values_filled(*widgets):
    filled = []
    for w in widgets:
        if isinstance(w, ipywidgets.Box):
            filled.append(required_values_filled(*w.children))
            continue
        if isinstance(w, (ipywidgets.Button, ipywidgets.Output)):
            continue
        if w.value is None or w.value == '':
            if isinstance(w, ipywidgets.Text):
                assert w.placeholder[0] == '*'
                print('Missing option ', w.placeholder[1:])
            else:
                assert w.description[0] == '*'
                print('Missing option ', w.description[1:])
            filled.append(False)
    return all(filled)


class Templates(ipywidgets.VBox):
    def __init__(self, project, *args, **kwargs):
        super(Templates, self).__init__(*args, **kwargs)
        self.templates = ipywidgets.SelectMultiple(
            options=project.templates,
            value=(),
            disabled=False,
            layout={'height': '200px', 'width': '300px'}
        )
        search_widget = ipywidgets.Text(
            placeholder='Templates', layout={'width': self.templates.layout.width})
        orig_list = list(self.templates.options)
        # Wire the search field to the checkboxes
        def on_text_change(change):
            search_input = change['new']
            if search_input == '':
                # Reset search field
                new_options = orig_list
            else:
                # Filter by search field.
                new_options = [a for a in orig_list if search_input in a]
            self.templates.options = new_options

        search_widget.observe(on_text_change, names='value')
        self.children = [search_widget, self.templates]
        # self.layout={'width': '310px'}

    @property
    def value(self):
        return self.templates.value


class MultiInput(ipywidgets.VBox):
    def __init__(self, placeholders, description, *args, **kwargs):
        super(MultiInput, self).__init__(*args, **kwargs)
        self.description = description
        more_input = ipywidgets.Button(
            description=description, layout={'width': '160px'})
        self.children = [ipywidgets.HBox(
            [more_input] +
            [ipywidgets.Text(placeholder=v, layout={'width': '60px'})
            for v in placeholders])]

        def on_more_input(change):
            children = list(self.children)
            children.append(
                ipywidgets.HBox(
                    [ipywidgets.Output(layout={'width': '165px'})] +
                    [ipywidgets.Text(placeholder=v, layout={'width': '60px'})
                     for v in placeholders])
            )
            self.children = children

        more_input.on_click(on_more_input)

    @property
    def value(self):
        multi_inputs = []
        for ch in self.children:
            val = [a.value for a in ch.children[1:]]
            if all([a!='' for a in val]):
                multi_inputs.append(val)

        return tuple(multi_inputs)

class DateTimePicker(ipywidgets.HBox):
    def __init__(self, *args, **kwargs):
        super(DateTimePicker, self).__init__(*args, **kwargs)
        self.d = ipywidgets.DatePicker(disabled=False)
        self.h = ipywidgets.Text(placeholder='HH', layout={'width': '60px'})
        self.m = ipywidgets.Text(placeholder='MM', layout={'width': '60px'})
        self.s = ipywidgets.Text(placeholder='SS', layout={'width': '60px'})
        self.children = [self.d, self.h, self.m, self.s]

    @property
    def value(self):
        d, h, m, s = self.d.value, self.h.value, self.m.value, self.s.value
        h = h if h != '' else 0
        m = m if m != '' else 0
        s = s if s != '' else 0
        t = dt.time(int(h), int(m), int(s))

        if d:
            return dt.datetime.combine(d, t)
        else:
            return None


class DatePicker(ipywidgets.DatePicker):
    def __init__(self, *args, **kwargs):
        super(DatePicker, self).__init__(*args, **kwargs)

    @property
    def datetime(self):
        if self.value:
            return dt.datetime.combine(self.value, dt.time(0, 0))
        else:
            return None


class SelectFilesButton(ipywidgets.Button):
    """A file widget that leverages tkinter.filedialog."""

    def __init__(self, *args, **kwargs):
        """Initialize the SelectFilesButton class."""
        super(SelectFilesButton, self).__init__(*args, **kwargs)
        # Add the selected_files trait
        import traitlets
        self.add_traits(files=traitlets.traitlets.List())
        # Create the button.
        self.description = "Select Files"
        self.icon = "square-o"
        self.style.button_color = "orange"
        # Set on click behavior.
        self.on_click(self.select_files)

    @staticmethod
    def select_files(self):
        from tkinter import Tk, filedialog
        """Generate instance of tkinter.filedialog.
        """
        # Create Tk root
        root = Tk()
        # Hide the main window
        root.withdraw()
        # Raise the root to the top of all windows.
        root.call('wm', 'attributes', '.', '-topmost', True)
        # List of selected fileswill be set to self.value
        self.files = filedialog.askopenfilenames()

        self.description = "Files Selected"
        self.icon = "check-square-o"
        self.style.button_color = "lightgreen"


class SelectDirectoryButton(ipywidgets.Button):
    """A file widget that leverages tkinter.filedialog."""

    def __init__(self, *args, **kwargs):
        """Initialize the SelectFilesButton class."""
        super(SelectDirectoryButton, self).__init__(*args, **kwargs)
        # Add the selected_files trait
        import traitlets
        self.add_traits(directory=traitlets.traitlets.Unicode())
        # Create the button.
        self.description = "Select Files"
        self.icon = "square-o"
        self.style.button_color = "orange"
        # Set on click behavior.
        self.on_click(self.select_directory)

    @staticmethod
    def select_directory(self):
        from tkinter import Tk, filedialog
        """Generate instance of tkinter.filedialog.
        """
        # Create Tk root
        root = Tk()
        # Hide the main window
        root.withdraw()
        # Raise the root to the top of all windows.
        root.call('wm', 'attributes', '.', '-topmost', True)
        # List of selected fileswill be set to self.value
        self.directory = filedialog.askdirectory()

        self.description = "Files Selected"
        self.icon = "check-square-o"
        self.style.button_color = "lightgreen"
