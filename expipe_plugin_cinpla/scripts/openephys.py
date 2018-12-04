from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.scripts.utils import _get_data_path
from . import utils


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
    openephys_dirname = openephys_path.parent
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

    for m in message:
        action.create_message(text=m, user=user, datetime=datetime.now())

        # TODO update to messages
        # for idx, m in enumerate(openephys_rec.messages):
        #     secs = float(m['time'].rescale('s').magnitude)
        #     dtime = openephys_file.datetime + timedelta(secs)
        #     action.create_message(text=m['message'], user=user, datetime=dtime)

    exdir_path = utils._make_data_path(action, overwrite)
    # TODO change to alessio stuff
    openephys_io.convert(
        openephys_rec, exdir_path=exdir_path, session=session)
    if utils.query_yes_no(
        'Delete raw data in {}? (yes/no)'.format(openephys_path),
        default='no', answer=delete_raw_data):
        shutil.rmtree(openephys_path)


def process_openephys(project, action_id, probe_path, sorter):
    import spikeextractors as se
    import spiketoolkit as st
    action = project.actions[action_id]
    # if exdir_path is None:
    exdir_path = _get_data_path(action)
    exdir_file = exdir.File(exdir_path, plugins=exdir.plugins.quantities)
    acquisition = exdir_file["acquisition"]
    if acquisition.attrs['acquisition_system'] is None:
        raise ValueError('No Open Ephys aquisition system ' +
                         'related to this action')
    openephys_session = acquisition.attrs["openephys_session"]
    openephys_path = os.path.join(str(acquisition.directory), openephys_session)
    probe_path = probe_path or project.config.get('probe')

    print(probe_path)

    recording = se.OpenEphysRecordingExtractor(openephys_path)
    se.loadProbeFile(recording, probe_path)
    # apply cmr
    recording_cmr = st.preprocessing.common_reference(recording)
    recording_lfp = st.preprocessing.bandpass_filter(recording, freq_min=1, freq_max=300)
    recording_lfp = st.preprocessing.resample(recording, 1000)
    recording_hp = st.preprocessing.bandpass_filter(recording_cmr, freq_min=300, freq_max=6000)

    if sorter == 'klusta':
        sorting = st.sorters.klusta(recording_cmr, by_property='group')
    elif sorter == 'mountain':
        sorting = st.sorters.mountainsort4(recording_cmr, by_property='group',
                                           adjacency_radius=10, detect_sign=-1)
    elif sorter == 'kilosort':
        sorting = st.sorters.kilosort(recording_cmr, by_property='group',
                                      kilosort_path='/home/mikkel/apps/KiloSort',
                                      npy_matlab_path='/home/mikkel/apps/npy-matlab/npy-matlab')
    elif sorter == 'spyking-circus':
        sorting = st.sorters.spyking_circus(recording_cmr, by_property='group', merge_spikes=False)
    elif sorter == 'ironclust':
        sorting = st.sorters.ironclust(recording_cmr, by_property='group')
    else:
        raise NotImplementedError("sorter is not implemented")

    # extract waveforms
    print('Computing waveforms')
    wf = st.postprocessing.getUnitWaveforms(recording_hp, sorting, by_property='group', verbose=True)
    print('Saving to exdir format')
    # save spike times and waveforms to exdir
    se.ExdirSortingExtractor.writeSorting(sorting, exdir_path, recording=recording_cmr)
    # save LFP to exdir
    se.ExdirRecordingExtractor.writeRecording(recording_lfp, exdir_path, lfp=True)