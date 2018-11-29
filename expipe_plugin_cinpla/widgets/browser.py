from expipe_plugin_cinpla.imports import *
import IPython.display as ipd
from .openephys import openephys_view
from .entity import entity_view
from .adjust import adjustment_view
from .surgery import perfuse_view, surgery_view


def display(project_path=None):
    project_path = project_path or pathlib.Path.cwd()
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
