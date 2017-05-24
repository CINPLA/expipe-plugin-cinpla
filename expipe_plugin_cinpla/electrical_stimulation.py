import expipe
import expipe.io
from expipecli.utils import IPlugin
import click
from expipe_io_neuro import pyopenephys, openephys, pyintan, intan, axona

from .action_tools import (generate_templates, _get_local_path, GIT_NOTE,
                           add_message, _get_probe_file)
from .opto_tools import (generate_epochs, generate_axona_opto, populate_modules,
                        extract_laser_pulse, read_pulse_pal_mat,
                        read_pulse_pal_xml, read_laser_intensity,
                        generate_openephys_opto)
import os
import os.path as op
import sys
sys.path.append(expipe.config.config_dir)
if not op.exists(op.join(expipe.config.config_dir, 'expipe_params.py')):
    print('No config params file found, use "expipe' +
          'copy-to-config expipe_params.py"')
else:
    from expipe_params import (user_params, templates, unit_info,
                               possible_brain_areas)

DTIME_FORMAT = expipe.io.core.datetime_format


class ElectricalStimulationPlugin(IPlugin):
    """Create the `expipe parse-axona` command for neuro recordings."""
    def attach_to_cli(self, cli):
        @cli.command('register-electrical-stimulation')
        @click.argument('action-id', type=click.STRING)
        @click.option('--intan-sync',
                      type=click.STRING,
                      help='Sync source of Intan. e.g. adc-1, dig-0',
                      default='adc-0'
                      )
        @click.option('--ephys-sync',
                      type=click.STRING,
                      help='Sync source of Open Ephys. e.g. dig-0, sync-0',
                      default='sync-0'
                      )
        @click.option('--prb-path',
                      type=click.STRING,
                      help='Path to probefile, assumed to be in expipe config directory by default.',
                      )
        @click.option('--stim-chan',
                      required=True,
                      type=click.STRING,
                      help='TTL source for stimulation triggers. e.g. intan-adc-0, ephys-dig-1',
                      default='intan-dig-0'
                      )
        @click.option('-t', '--tag',
                      type=click.Choice(['opto-inside', 'opto-outside', 'opto-train']),
                      help='The anatomical brain-area of the optogenetic stimulus.',
                      )
        @click.option('-m', '--message',
                      type=click.STRING,
                      help='Add message, use "text here" for sentences.',
                      )
        @click.option('--no-local',
                      is_flag=True,
                      help='Store temporary on local drive.',
                      )
        @click.option('--overwrite',
                      is_flag=True,
                      help='Overwrite modules or not.',
                      )
        @click.option('--nchan',
                      type=click.INT,
                      default=32,
                      help='Number of channels. Default = 32',
                      )
        def parse_electrical_stimulation(action_id, intan_sync, stim_chan, no_local, overwrite,
                                         prb_path, tag, message, ephys_sync, nchan):
            """Parse optogenetics info to an action.

            COMMAND: action-id: Provide action id to find exdir path"""
            import exdir
            from expipe_io_neuro import pyintan, pyopenephys
            # TODO deafault none
            project = expipe.io.get_project(user_params['project_id'])
            action = project.require_action(action_id)
            tags = action.tags or {}
            tags.update({t: 'true' for t in tag})
            action.tags = tags
            fr = action.require_filerecord()
            if not no_local:
                exdir_path = _get_local_path(fr)
            else:
                exdir_path = fr.server_path
            exdir_object = exdir.File(exdir_path)
            if exdir_object['acquisition'].attrs['acquisition_system'] != 'Intan':
                raise ValueError('Only Intan stimulation is currently supported')

            acquisition = exdir_object["acquisition"]
            if acquisition.attrs['acquisition_system'] != 'Intan':
                raise ValueError('No Open Ephys aquisition system ' +
                                 'related to this action')
            openephys_session = acquisition.attrs["openephys_session"]
            intan_ephys_path = op.join(acquisition.directory, openephys_session)
            intan_ephys_base = op.join(intan_ephys_path, openephys_session)
            rhs_file = [f for f in os.listdir(intan_ephys_path) if f.endswith('.rhs')][0]
            rhs_path = op.join(intan_ephys_path, rhs_file)
            klusta_prm = op.abspath(intan_ephys_base) + '_klusta.prm'

            prb_path = prb_path or _get_probe_file(system='intan', nchan=nchan,
                                                   spikesorter='klusta')
            if prb_path is None:
                raise IOError('No probefile found in expipe config directory,' +
                              ' please provide one')
            openephys_file = pyopenephys.File(intan_ephys_path)
            intan_file = pyintan.File(rhs_path, prb_path)

            # clip and sync
            print('Pre-clip durations: Intan - ', intan_file.duration, ' Open Ephys - ', openephys_file.duration)
            if intan_sync and intan_sync != 'none':
                intan_sync = intan_sync.split('-')
                assert len(intan_sync) == 2
                intan_chan = int(intan_sync[1])
                if intan_sync[0] == 'adc':
                    intan_clip_times = pyintan.extract_sync_times(intan_file.adc_signals[0].signal[intan_chan],
                                                                  intan_file.times)
                elif intan_sync[0] == 'dig':
                    intan_clip_times = intan_file.digital_in_signals[0].times[intan_chan]
                else:
                    intan_clip_times = None
                print('Intan clip times: ', intan_clip_times)
                intan_file.clip_recording(intan_clip_times)

            if ephys_sync and ephys_sync != 'none':
                ephys_sync = ephys_sync.split('-')
                assert len(ephys_sync) == 2
                ephys_chan = int(ephys_sync[1])
                if ephys_sync[0] == 'sync':
                    ephys_clip_times = openephys_file.sync_signals[0].times[ephys_chan]
                elif intan_sync[0] == 'dig':
                    ephys_clip_times = openephys_file.digital_in_signals[0].times[intan_chan]
                else:
                    ephys_clip_times = None
                print('Openephys clip times: ', ephys_clip_times)
                openephys_file.clip_recording(ephys_clip_times)

            # Check duration
            if round(openephys_file.duration, 1) != round(intan_file.duration, 1):
                if round(openephys_file.duration, 1) < round(intan_file.duration, 1):
                    intan_file.clip_recording([openephys_file.duration], start_end='end')
                else:
                    openephys_file.clip_recording([intan_file.duration], start_end='end')

            print('Post-clip durations: Intan - ', intan_file.duration, ' Open Ephys - ', openephys_file.duration)




            # generate_templates(action, templates['opto_' + aq_sys],
            #                    overwrite, git_note=None)
            # populate_modules(action, params)
            # laser_id = laser_id or user_params['laser_device'].get('id')
            # laser_name = user_params['laser_device'].get('name')
            # assert laser_id is not None
            # assert laser_name is not None
            # laser = action.require_module(name=laser_name).to_dict()
            # laser['device_id'] = {'value': laser_id}
            # action.require_module(name=laser_name, contents=laser,
            #                       overwrite=True)
            # add_message(action, message)

        @cli.command('register-opto-files')
        @click.argument('action-id', type=click.STRING)
        @click.option('--no-local',
                      is_flag=True,
                      help='Store temporary on local drive.',
                      )
        @click.option('--io-channel',
                      default=4,
                      type=click.INT,
                      help='TTL input channel.',
                      )
        def parse_optogenetics_files(action_id, no_local, io_channel):
            """Parse optogenetics info to an action.

            COMMAND: action-id: Provide action id to find exdir path"""
            import exdir
            project = expipe.io.get_project(user_params['project_id'])
            action = project.require_action(action_id)
            fr = action.require_filerecord()
            if not no_local:
                exdir_path = _get_local_path(fr)
            else:
                exdir_path = fr.server_path
            exdir_object = exdir.File(exdir_path)
            if exdir_object['acquisition'].attrs['acquisition_system'] == 'Axona':
                aq_sys = 'axona'
                params = generate_axona_opto(exdir_path, io_channel)
            elif exdir_object['acquisition'].attrs['acquisition_system'] == 'OpenEphys':
                aq_sys = 'openephys'
                params = generate_openephys_opto(exdir_path, io_channel)
            else:
                raise ValueError('Acquisition system not recognized')
