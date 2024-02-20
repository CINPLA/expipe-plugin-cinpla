import ipywidgets
from pynwb import NWBHDF5IO

import expipe

from ..nwbutils.nwbwidgetsunitviewer import get_custom_spec
from ..scripts.utils import _get_data_path


class NwbViewer(ipywidgets.VBox):
    """View NWB files from actions in a project and handle refreshing and closing of files."""

    def __init__(self, project, **kwargs):
        super().__init__(**kwargs)
        self.project = project

        options = self.get_options()
        self.actions_list = ipywidgets.Select(
            options=options, value=None, rows=10, description="Actions: ", disabled=False, layout={"width": "80%"}
        )
        out = ipywidgets.Output(layout={"width": "75%"})
        self.children = [self.actions_list, out]
        self.actions_list.observe(self.on_change)
        self.ios = dict()
        self.nwbfile = None

    def get_options(self):
        options = []
        all_actions = self.project.actions
        for action_name in all_actions:
            action = all_actions[action_name]
            data_path = _get_data_path(action)
            if data_path is not None and data_path.name == "main.nwb":
                options.append(action_name)
        return options

    def on_change(self, change):
        if change["type"] == "change" and change["name"] == "value":
            from nwbwidgets import nwb2widget

            action_id = change["new"]
            if action_id is None:
                return
            action = self.project.actions[action_id]
            data_path = _get_data_path(action)
            if data_path not in self.ios:
                self.ios[data_path] = NWBHDF5IO(data_path, mode="r")
            io = self.ios[data_path]
            # close existing
            if self.nwbfile is not None:
                del self.nwbfile
                self.nwbfile = None
            self.nwbfile = io.read()
            w = nwb2widget(self.nwbfile, get_custom_spec())
            self.children = [self.actions_list, w]
            w.layout.width = "75%"

    def refresh(self, project):
        self.project = expipe.get_project(project.path)
        options = self.get_options()

        self.actions_list = ipywidgets.Select(
            options=options, value=None, rows=10, description="Actions: ", disabled=False, layout={"width": "80%"}
        )
        self.actions_list.observe(self.on_change)

    def close(self):
        del self.nwbfile
        self.nwbfile = None
        for data_path, io in self.ios.items():
            io.close()
