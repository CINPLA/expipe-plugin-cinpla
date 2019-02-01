from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.scripts.utils import _get_data_path
from expipe_io_neuro.openephys.openephys import generate_tracking, generate_events
from . import utils
from pathlib import Path
import shutil
import time
import os
import tempfile
import stat


def register_openephys_recording(
    project, action_id, openephys_path, depth, overwrite, templates,
    entity_id, user, session, location, message, tag, delete_raw_data,
    correct_depth_answer, register_depth):
    user = user or PAR.USERNAME
    if user is None:
        print('Missing option "user".')
        return
    location = location or PAR.LOCATION
    if location is None:
        print('Missing option "location".')
        return
    openephys_path = pathlib.Path(openephys_path)
    openephys_dirname = openephys_path.stem
    openephys_file = pyopenephys.File(str(openephys_path))
    openephys_exp = openephys_file.experiments[0]
    openephys_rec = openephys_exp.recordings[0]
    entity_id = entity_id or str(openephys_dirname).split('_')[0]
    session = session or str(openephys_dirname).split('_')[-1]
    if session.isdigit():
        pass
    else:
        print('Missing option "session".')
        return
    if action_id is None:
        session_dtime = datetime.datetime.strftime(openephys_exp.datetime, '%d%m%y')
        action_id = entity_id + '-' + session_dtime + '-' + session
    print('Generating action', action_id)
    try:
        action = project.create_action(action_id)
    except KeyError as e:
        if overwrite:
            project.delete_action(action_id)
            action = project.create_action(action_id)
        else:
            print(str(e) + ' Use "overwrite"')
            return
    action.datetime = openephys_exp.datetime
    action.type = 'Recording'
    action.tags.extend(list(tag) + ['open-ephys'])
    print('Registering entity id ' + entity_id)
    action.entities = [entity_id]
    print('Registering user ' + user)
    action.users = [user]
    print('Registering location ' + location)
    action.location = location

    if register_depth:
        correct_depth = utils.register_depth(
            project=project, action=action, depth=depth,
            answer=correct_depth_answer)
        if not correct_depth:
            print('Aborting registration!')
            project.delete_action(action_id)
            return
    utils.register_templates(action, templates)
    if message:
        action.create_message(text=message, user=user, datetime=datetime.datetime.now())

    for idx, m in enumerate(openephys_rec.messages):
        print('OpenEphys message: ', m.text)
        secs = float(m.time.rescale('s').magnitude)
        dtime = openephys_rec.datetime + datetime.timedelta(seconds=secs)
        action.create_message(text=m.text, user=user, datetime=dtime)

    exdir_path = utils._make_data_path(action, overwrite)
    openephys_io.convert(
        openephys_rec, exdir_path=exdir_path, session=session)
    if utils.query_yes_no(
        'Delete raw data in {}? (yes/no)'.format(openephys_path),
        default='no', answer=delete_raw_data):
        shutil.rmtree(openephys_path)


def process_tracking(project, action_id, openephys_path):
        action = project.actions[action_id]
        # if exdir_path is None:
        exdir_path = _get_data_path(action)
        exdir_file = exdir.File(exdir_path, plugins=exdir.plugins.quantities)
        acquisition = exdir_file["acquisition"]
        if acquisition.attrs['acquisition_system'] is None:
            raise ValueError('No Open Ephys acquisition system ' +
                             'related to this action')
        session = acquisition.attrs["session"]


        # check for tracking
        oe_recording = pyopenephys.File(str(openephys_path)).experiments[0].recordings[0]
        if len(oe_recording.tracking) > 0:
            print('Saving ', len(oe_recording.tracking), ' Open Ephys tracking sources')
            generate_tracking(exdir_path, oe_recording)

        if len(oe_recording.events) > 0:
            print('Saving ', len(oe_recording.events), ' Open Ephys event sources')
            generate_events(exdir_path, oe_recording)

        openephys_io.convert_tracking(
            oe_recording, exdir_path=exdir_path, session=session)
