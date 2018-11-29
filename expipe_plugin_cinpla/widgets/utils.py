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


def extract_multi_input(multi_input):
    if isinstance(multi_input, ipywidgets.HBox):
        multi_inputs = [[a.value for a in multi_input.children[1:]]]
    elif isinstance(multi_input, ipywidgets.VBox):
        multi_inputs = []
        for ch in multi_input.children:
            multi_inputs.append([a.value for a in ch.children[1:]])
    else:
        raise AssertionError(multi_input.description)
    return multi_inputs


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


class DateTimePicker(ipywidgets.HBox):
    def __init__(self, *args, **kwargs):
        super(DateTimePicker, self).__init__(*args, **kwargs)
        self.d = ipywidgets.DatePicker(disabled=False)
        self.h = ipywidgets.Text(placeholder='HH')
        self.m = ipywidgets.Text(placeholder='MM')
        self.s = ipywidgets.Text(placeholder='SS')
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
        self.add_traits(files=traitlets.traitlets.Unicode())
        # Create the button.
        self.description = "Select Files"
        self.icon = "square-o"
        self.style.button_color = "orange"
        # Set on click behavior.
        self.on_click(self.select_files)

    @staticmethod
    def select_files(b):
        from tkinter import Tk, filedialog
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
