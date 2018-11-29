from . import utils


def generate_axona_action(action_id, axona_filename, depth, user,
                          overwrite, no_files, no_modules,
                          entity_id, location, message, tag,
                          get_inp, yes, no_cut, cluster_group,
                          set_noise):
    if not axona_filename.endswith('.set'):
        raise ValueError("Sorry, we need an Axona .set file not " +
              "'{}'.".format(axona_filename))
    if len(cluster_group) == 0:
        cluster_group = None # TODO set proper default via callback
    project = expipe.get_project(PAR.PROJECT_ROOT)
    entity_id = entity_id or axona_filename.split(os.sep)[-2]
    axona_file = pyxona.File(axona_filename)
    if action_id is None:
        session_dtime = datetime.strftime(axona_file._start_datetime,
                                          '%d%m%y')
        basename, _ = os.path.splitext(axona_filename)
        session = basename[-2:]
        action_id = entity_id + '-' + session_dtime + '-' + session
    try:
        action = project.create_action(action_id)
    except NameError as e:
        if overwrite:
            project.delete_action(action_id)
            action = project.create_action(action_id)
        else:
            raise NameError(str(e) + '. Use "overwrite"')
    if not no_modules:
        utils.generate_templates(action, 'axona')
    action.datetime = axona_file._start_datetime
    action.tags = list(tag) + ['axona']
    print('Registering action id ' + action_id)
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
    action.type = 'Recording'
    for m in message:
        action.create_message(text=m, user=user, datetime=datetime.now())
    if not no_modules:
        try:
            correct = utils.register_depth(
                project, action, depth=depth, answer=yes)
        except (NameError, ValueError):
            raise
        except Exception as e:
            raise Exception(str(e) + ' Note, you may also use ' +
                            '"--no-modules"')
        if not correct:
            print('Aborting')
            return
    if not no_files:
        exdir_path = utils._make_data_path(action, overwrite)
        axona.convert(axona_file, exdir_path)
        axona.generate_tracking(exdir_path, axona_file)
        axona.generate_analog_signals(exdir_path, axona_file)
        axona.generate_spike_trains(exdir_path, axona_file)
        if not no_cut:
            axona.generate_units(exdir_path, axona_file,
                                 cluster_group=cluster_group,
                                 set_noise=set_noise)
            axona.generate_clusters(exdir_path, axona_file)
        if get_inp:
            axona.generate_inp(exdir_path, axona_file)
        else:
            print('WARNING: Not registering Axona ".inp".')
    time_string = exdir.File(exdir_path).attrs['session_start_time']
    dtime = datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%S')
    action.datetime = dtime
