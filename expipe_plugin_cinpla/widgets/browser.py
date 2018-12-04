from expipe_plugin_cinpla.imports import *
import IPython.display as ipd
from .openephys import openephys_view, process_view
from .entity import entity_view
from .adjust import adjustment_view
from .surgery import perfuse_view, surgery_view
from .axona import axona_view
import expipe

# TODO: how to make templates
# TODO: convert templates to yaml
# TODO: transfer to db for processing
# TODO: processing
# TODO: fix old data

def display(project_path=None):
    project_path = project_path or PAR.PROJECT_ROOT
    assert project_path is not None
    project = expipe.get_project(project_path)
    # register tab
    register_tab_tab_titles = [
        'OpenEphys',
        'Axona',
        'Adjustment',
        'Entity',
        'Surgery',
        'Perfusion']
    register_tab = ipywidgets.Tab()
    register_tab.children = [
        openephys_view(project),
        axona_view(project),
        adjustment_view(project),
        entity_view(project),
        surgery_view(project),
        perfuse_view(project),
    ]
    for i, title in enumerate(register_tab_tab_titles):
        register_tab.set_title(i, title)

    process_tab_tab_titles = [
        'OpenEphys',]
    process_tab = ipywidgets.Tab()
    process_tab.children = [
        process_view(project)
    ]
    for i, title in enumerate(process_tab_tab_titles):
        process_tab.set_title(i, title)

    tab_titles = ['Register', 'Process']
    tab = ipywidgets.Tab()
    tab.children = [
        register_tab,
        process_tab
    ]
    for i, title in enumerate(tab_titles):
        tab.set_title(i, title)
    ipd.display(tab)
