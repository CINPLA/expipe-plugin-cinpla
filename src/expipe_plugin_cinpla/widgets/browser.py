# -*- coding: utf-8 -*-
import expipe
import IPython.display as ipd

from .curation import CurationView
from .process import process_ecephys_view
from .register import (
    register_adjustment_view,
    register_annotate_view,
    register_entity_view,
    register_openephys_view,
    register_perfuse_view,
    register_surgery_view,
)
from .unittracking import DailyUnitTrackViewer
from .viewer import NwbViewer


def display_browser(project_path):
    import ipywidgets

    project = expipe.get_project(project_path)
    # register tab
    register_tab_tab_titles = [
        "OpenEphys",
        "Adjustment",
        "Entity",
        "Surgery",
        "Perfusion",
        "Annotate",
    ]
    register_tab = ipywidgets.Tab()
    register_tab.children = [
        register_openephys_view(project),
        register_adjustment_view(project),
        register_entity_view(project),
        register_surgery_view(project),
        register_perfuse_view(project),
        register_annotate_view(project),
    ]
    for i, title in enumerate(register_tab_tab_titles):
        register_tab.set_title(i, title)

    process_tab_tab_titles = ["OpenEphys"]  # , 'Intan', 'Tracking', 'Psychopy', 'Curation']
    process_tab = ipywidgets.Tab()
    process_tab.children = [
        process_ecephys_view(project),
    ]
    for i, title in enumerate(process_tab_tab_titles):
        process_tab.set_title(i, title)

    curation_tab = CurationView(project)
    nwb_viewer_tab = NwbViewer(project)
    track_units_tab = DailyUnitTrackViewer(project)

    tab_titles = ["Register", "Process", "Curation", "View", "Track Units"]
    tab = ipywidgets.Tab()
    tab.children = [register_tab, process_tab, curation_tab, nwb_viewer_tab, track_units_tab]
    for i, title in enumerate(tab_titles):
        tab.set_title(i, title)
    ipd.display(tab)

    def on_tab_change(change):
        # refresh
        project = expipe.get_project(project_path)
        process_tab.children = [process_ecephys_view(project)]
        nwb_viewer_tab.close()
        nwb_viewer_tab.refresh(project)
        curation_tab.close()

    tab.observe(on_tab_change)
