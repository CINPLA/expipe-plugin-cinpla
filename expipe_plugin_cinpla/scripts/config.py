from expipe_plugin_cinpla.imports import *


def give_attrs_val(obj, value, *attrs):
    for attr in attrs:
        if not hasattr(obj, attr):
            setattr(obj, attr, value)


def set_empty_if_no_value(PAR=None):
    if PAR is None:
        class Parameters:
            pass
        PAR = Parameters()
    give_attrs_val(
        PAR, list(),
        'POSSIBLE_TAGS',
        'POSSIBLE_LOCATIONS',
        'POSSIBLE_CELL_LINES')
    give_attrs_val(
        PAR, None,
        'PROJECT_ID',
        'PROJECT_ROOT',
        'PROJECT',
        'USERNAME',
        'LOCATION',
        'CONFIG')
    return PAR


def load_parameters(): # load global and merge
    PAR = set_empty_if_no_value()
    local_root, _ = expipe.config._load_local_config(pathlib.Path.cwd())
    try:
        project = expipe.get_project(path=local_root)
        config = project.config
    except:
        return PAR
    PAR.PROJECT_ID = config['project']
    PAR.PROJECT_ROOT = local_root
    PAR.PROJECT = project
    PAR.USERNAME = config.get('username')
    PAR.LOCATION = config.get('location')
    PAR.CONFIG = config
    try:
        PAR.__dict__.update(project.modules['settings'].contents)
    except KeyError:
        pass
    return PAR
