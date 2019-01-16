from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.scripts.utils import _get_data_path
from expipe_io_neuro.openephys.openephys import generate_tracking
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
    if message:
        action.create_message(text=message, user=user, datetime=datetime.now())

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


def process_openephys(project, action_id, probe_path, sorter, spikesort=True, compute_lfp=True, compute_mua=False,
                      spikesorter_params=None, server=None, **kwargs):
    import spikeextractors as se
    import spiketoolkit as st

    if server is None or server == 'local':
        action = project.actions[action_id]
        # if exdir_path is None:
        exdir_path = _get_data_path(action)
        exdir_file = exdir.File(exdir_path, plugins=exdir.plugins.quantities)
        acquisition = exdir_file["acquisition"]
        if acquisition.attrs['acquisition_system'] is None:
            raise ValueError('No Open Ephys aquisition system ' +
                             'related to this action')
        openephys_session = acquisition.attrs["openephys_session"]
        openephys_path = Path(acquisition.directory) / openephys_session
        probe_path = probe_path or project.config.get('probe')

        recording = se.OpenEphysRecordingExtractor(str(openephys_path))

        # apply filtering and cmr
        print('Writing filtered and common referenced data')
        recording_hp = st.preprocessing.bandpass_filter(recording, freq_min=300, freq_max=6000)
        recording_cmr = st.preprocessing.common_reference(recording_hp)
        recording_lfp = st.preprocessing.bandpass_filter(recording, freq_min=1, freq_max=300)
        recording_lfp = st.preprocessing.resample(recording_lfp, 1000)
        recording_mua = st.preprocessing.resample(st.preprocessing.rectify(recording_cmr), 1000)
        tmpdir = Path(tempfile.mkdtemp(dir=os.getcwd()))
        print(tmpdir)

        if spikesort:
            print('Bandpass filter')
            t_start = time.time()

            filt_filename = Path(tmpdir) / 'filt.dat'
            se.BinDatRecordingExtractor.writeRecording(recording_cmr, save_path=filt_filename)
            recording_cmr = se.BinDatRecordingExtractor(filt_filename, samplerate=recording_cmr.getSamplingFrequency(),
                                                     numchan=len(recording_cmr.getChannelIds()))
            print('Filter time: ', time.time() -t_start)
        if compute_lfp:
            print('Computing LFP')
            t_start = time.time()
            lfp_filename = Path(tmpdir) / 'lfp.dat'
            se.BinDatRecordingExtractor.writeRecording(recording_lfp, save_path=lfp_filename)
            recording_lfp = se.BinDatRecordingExtractor(lfp_filename, samplerate=recording_lfp.getSamplingFrequency(),
                                                     numchan=len(recording_lfp.getChannelIds()))
            print('Filter time: ', time.time() -t_start)

        if compute_mua:
            print('Computing MUA')
            t_start = time.time()
            mua_filename =  Path(tmpdir) / 'mua.dat'
            se.BinDatRecordingExtractor.writeRecording(recording_mua, save_path=mua_filename)
            recording_mua = se.BinDatRecordingExtractor(mua_filename, samplerate=recording_mua.getSamplingFrequency(),
                                                     numchan=len(recording_mua.getChannelIds()))
            print('Filter time: ', time.time() -t_start)

        recording_cmr = se.loadProbeFile(recording_cmr, probe_path)
        recording_lfp = se.loadProbeFile(recording_lfp, probe_path)
        recording_mua = se.loadProbeFile(recording_mua, probe_path)

        if spikesort:
            try:
                if sorter == 'klusta':
                    sorting = st.sorters.klusta(recording_cmr, by_property='group', **spikesorter_params)
                elif sorter == 'mountain':
                    sorting = st.sorters.mountainsort4(recording_cmr, by_property='group', **spikesorter_params)
                elif sorter == 'kilosort':
                    sorting = st.sorters.kilosort(recording_cmr, by_property='group', **spikesorter_params)
                elif sorter == 'spyking-circus':
                    sorting = st.sorters.spyking_circus(recording_cmr, by_property='group', **spikesorter_params)
                elif sorter == 'ironclust':
                    sorting = st.sorters.ironclust(recording_cmr, by_property='group', **spikesorter_params)
                else:
                    raise NotImplementedError("sorter is not implemented")
            except Exception as e:
                shutil.rmtree(tmpdir)
                print(e)
                raise Exception("Spike sorting failed")
            print('Found ', len(sorting.getUnitIds()), ' units!')

        # extract waveforms
        if spikesort:
            print('Computing waveforms')
            wf = st.postprocessing.getUnitWaveforms(recording_cmr, sorting, by_property='group', verbose=True, ms_before=1, ms_after=1)
            print('Saving sorting output to exdir format')
            se.ExdirSortingExtractor.writeSorting(sorting, exdir_path, recording=recording_cmr)
        if compute_lfp:
            print('Saving LFP to exdir format')
            se.ExdirRecordingExtractor.writeRecording(recording_lfp, exdir_path, lfp=True)
        if compute_mua:
            print('Saving MUA to exdir format')
            se.ExdirRecordingExtractor.writeRecording(recording_mua, exdir_path, mua=True)

        # check for tracking
        oe_recording = pyopenephys.File(str(openephys_path)).experiments[0].recordings[0]
        if len(oe_recording.tracking) > 0:
            print('Saving ', len(oe_recording.tracking), ' tracking sources')
            generate_tracking(exdir_path, oe_recording)

        print('Cleanup')
        if not os.access(str(tmpdir), os.W_OK):
            # Is the error an access error ?
            os.chmod(str(tmpdir), stat.S_IWUSR)
        shutil.rmtree(str(tmpdir))

        print('Saved to exdir: ', exdir_path)
    else:
        config = expipe.config._load_config_by_name(None)
        assert server in [s['host'] for s in config.get('servers')]
        server_dict = [s for s in config.get('servers') if s['host'] == server][0]
        host = server_dict['host']
        user = server_dict['user']
        password = server_dict['password']
        port = 22

        # host, user, pas, port = utils.get_login(
        #     hostname=hostname, username=username, port=port, password=password)
        ssh, scp_client, sftp_client, pbar = utils.login(
            hostname=host, username=user, password=password, port=port)

        #TODO find

        ########################## SEND  #######################################
        action = project.actions[action_id]
        exdir_path = str(_get_data_path(action))
        print('Initializing transfer of "' + exdir_path + '" to "' +
              host + '"')
        try:  # make directory for untaring
            sftp_client.mkdir('process')
        except IOError:
            pass
        print('Packing tar archive')
        filename = shutil.make_archive(exdir_path, 'tar', exdir_path)
        print(filename)
        scp_client.put(
            filename, os.path.join('process', action_id + '.tar'), recursive=False)

        try:
            pbar[0].close()
        except Exception:
            pass

        print('Unpacking tar archive')
        cmd = "tar -C" + os.path.join('process', 'main.exdir') + "-xf " + os.path.join('process', action_id + '.tar')
        utils.ssh_execute(ssh, cmd)

        # print('Deleting tar archives')
        # sftp_client.remove(action_dir + '.tar')
        # os.remove(local_data + '.tar')
        # ###################### PROCESS #######################################
        # print('Processing on server')
        # ssh_execute(ssh, "expipe openephys process {}".format(action_id), get_pty=True, timeout=None)
        # ####################### RETURN PROCESSED DATA #######################
        # print('Initializing transfer of "' + server_data + '" to "' +
        #       local_data + '"')
        # print('Packing tar archive')
        # exclude_statement = ""
        # ssh_execute(ssh, "tar --exclude=acquisition -cf " +
        #             server_data + '.tar ' + server_data)
        # scp_client.get(server_data + '.tar', local_data + '.tar',
        #                recursive=False)
        # try:
        #     pbar[0].close()
        # except Exception:
        #     pass
        # print('Unpacking tar archive')
        # untar(local_data + '.tar', server_data)  # TODO merge with existing
        # print('Deleting tar archives')
        # os.remove(local_data + '.tar')
        # sftp_client.remove(server_data + '.tar')
        ##################### CLOSE UP #############################
        ssh.close()
        sftp_client.close()
        scp_client.close()


