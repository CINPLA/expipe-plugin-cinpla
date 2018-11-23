from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.tools import action as action_tools
from expipe_plugin_cinpla.tools import config


def generate_openephys_action(action_id, openephys_path,
                              depth, overwrite, no_modules,
                              entity_id, user, session,
                              location, message, tag):
    openephys_path = os.path.abspath(openephys_path)
    openephys_dirname = openephys_path.split(os.sep)[-1]
    project = expipe.get_project(PAR.PROJECT_ROOT)
    openephys_file = pyopenephys.File(openephys_path)
    openephys_exp = openephys_file.experiments[0]
    openephys_rec = openephys_exp.recordings[0]
    entity_id = entity_id or openephys_dirname.split('_')[0]
    session = session or openephys_dirname.split('_')[-1]
    if session.isdigit():
        pass
    else:
        raise ValueError('Did not find valid session number "' +
                         session + '"')
    if action_id is None:
        session_dtime = datetime.strftime(openephys_exp.datetime, '%d%m%y')
        action_id = entity_id + '-' + session_dtime + '-' + session
    print('Generating action', action_id)
    try:
        action = project.create_action(action_id)
    except NameError as e:
        if overwrite:
            project.delete_action(action_id)
            action = project.create_action(action_id)
        else:
            raise NameError(str(e) + '. Use "overwrite"')
    action.datetime = openephys_exp.datetime
    action.type = 'Recording'
    action.tags.extend(list(tag) + ['open-ephys'])
    print('Registering entity id ' + entity_id)
    action.entities = [entity_id]
    user = user or PAR.USERNAME
    if user is None:
        raise click.ClickException('Missing option "-u" / "--user".')
    print('Registering user ' + user)
    action.users = [user]
    location = location or PAR.LOCATION
    if location is None:
        raise click.ClickException('Missing option "-l" / "--location".')
    print('Registering location ' + location)
    action.location = location


    if not no_modules:
        if 'openephys' not in PAR.TEMPLATES:
            raise ValueError(
                'Could not find "openephys" in PAR.TEMPLATES, ' +
                'optionally use "--no-modules"')
        if len(depth) > 0:
            correct_depth = action_tools.register_depth(
                project=project, action=action, depth=depth)
            if not correct_depth:
                print('Aborting registration!')
                return
        action_tools.generate_templates(action, 'openephys')

    for m in message:
        action.create_message(text=m, user=user, datetime=datetime.now())

        # TODO update to messages
        # for idx, m in enumerate(openephys_rec.messages):
        #     secs = float(m['time'].rescale('s').magnitude)
        #     dtime = openephys_file.datetime + timedelta(secs)
        #     action.create_message(text=m['message'], user=user, datetime=dtime)

    exdir_path = action_tools._make_data_path(action, overwrite)
    shutil.copy(prb_path, openephys_path)
    openephys.convert( # TODO why not main.exdir??
        openephys_rec, exdir_path=exdir_path, session=session)
    if action_tools.query_yes_no(
        'Delete raw data in {}? (yes/no)'.format(openephys_path),
        default='no'):
        shutil.rmtree(openephys_path)
