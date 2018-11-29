from expipe_plugin_cinpla.imports import *
from . import utils


def register_openephys_recording(
    project_path, action_id, openephys_path, depth, overwrite, no_modules,
    entity_id, user, session, location, message, tag, delete_raw_data,
    query_depth_answer):
    user = user or PAR.USERNAME
    if user is None:
        print('Missing option "user".')
        return
    location = location or PAR.LOCATION
    if location is None:
        print('Missing option "location".')
        return

    openephys_path = pathlib.Path(openephys_path)
    openephys_dirname = openephys_path.parent
    project = expipe.get_project(project_path)
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
        session_dtime = datetime.strftime(openephys_exp.datetime, '%d%m%y')
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

    if not no_modules:
        if 'openephys' not in PAR.TEMPLATES:
            print('Could not find "openephys" in PAR.TEMPLATES, ' + # TODO be more descriptive than TEMPLATES
                  'use option "no-modules"')
            project.delete_action(action_id)
            return
        if len(depth) > 0:
            correct_depth = utils.register_depth(
                project=project, action=action, depth=depth,
                answer=query_depth_answer)
            if not correct_depth:
                print('Aborting registration!')
                project.delete_action(action_id)
                return
        utils.generate_templates(action, 'openephys')

    action.datetime = openephys_exp.datetime
    action.type = 'Recording'
    action.tags.extend(list(tag) + ['open-ephys'])
    print('Registering entity id ' + entity_id)
    action.entities = [entity_id]
    print('Registering user ' + user)
    action.users = [user]
    print('Registering location ' + location)
    action.location = location

    for m in message:
        action.create_message(text=m, user=user, datetime=datetime.now())

        # TODO update to messages
        # for idx, m in enumerate(openephys_rec.messages):
        #     secs = float(m['time'].rescale('s').magnitude)
        #     dtime = openephys_file.datetime + timedelta(secs)
        #     action.create_message(text=m['message'], user=user, datetime=dtime)

    exdir_path = utils._make_data_path(action, overwrite)
    # TODO change to alessio stuff
    openephys.convert(
        openephys_rec, exdir_path=exdir_path, session=session)
    if utils.query_yes_no(
        'Delete raw data in {}? (yes/no)'.format(openephys_path),
        default='no', answer=delete_raw_data):
        shutil.rmtree(openephys_path)
