from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.scripts import openephys
from . import utils


def attach_to_register(cli):
    @cli.command('openephys',
                 short_help='Register an open-ephys recording-action to database.')
    @click.argument('openephys-path', type=click.Path(exists=True))
    @click.option('-u', '--user',
                  type=click.STRING,
                  help='The experimenter performing the recording.',
                  )
    @click.option('-d', '--depth',
                  multiple=True,
                  callback=utils.validate_depth,
                  help=(
                    'Alternative "find" to find from surgery or adjustment' +
                    ' or given as <key num depth unit> e.g. ' +
                    '<mecl 0 10 um> (omit <>).'),
                  )
    @click.option('-l', '--location',
                  type=click.STRING,
                  callback=utils.optional_choice,
                  envvar=PAR.POSSIBLE_LOCATIONS,
                  help='The location of the recording, i.e. "room-1-ibv".'
                  )
    @click.option('--session',
                  type=click.STRING,
                  help='Session number, assumed to be in end of filename by default',
                  )
    @click.option('--action-id',
                  type=click.STRING,
                  help=('Desired action id for this action, if none' +
                        ', it is generated from open-ephys-path.'),
                  )
    @click.option('--entity-id',
                  type=click.STRING,
                  help='The id number of the entity.',
                  )
    @click.option('-m', '--message',
                  type=click.STRING,
                  help='Add message, use "text here" for sentences.',
                  )
    @click.option('-t', '--tag',
                  multiple=True,
                  type=click.STRING,
                  callback=utils.optional_choice,
                  envvar=PAR.POSSIBLE_TAGS,
                  help='Add tags to action.',
                  )
    @click.option('--overwrite',
                  is_flag=True,
                  help='Overwrite files and expipe action.',
                  )
    @click.option('--register-depth',
                  is_flag=True,
                  help='Overwrite files and expipe action.',
                  )
    @click.option('--templates',
                  multiple=True,
                  type=click.STRING,
                  help='Which templates to add',
                  )
    def _register_openephys_recording(
        action_id, openephys_path, depth, overwrite, templates,
        entity_id, user, session, location, message, tag, register_depth):
        openephys.register_openephys_recording(
            project=PAR.PROJECT,
            action_id=action_id,
            openephys_path=openephys_path,
            depth=depth,
            overwrite=overwrite,
            templates=templates,
            entity_id=entity_id,
            user=user,
            session=session,
            location=location,
            message=message,
            tag=tag,
            delete_raw_data=None,
            correct_depth_answer=None,
            register_depth=register_depth)


def attach_to_process(cli):
    @cli.command('openephys',
                 short_help='Process open ephys recordings.')
    @click.argument('action-id', type=click.STRING)
    @click.option('--probe-path',
                  type=click.STRING,
                  help='Path to probefile, assumed to be in expipe config directory by default.',
                  )
    @click.option('--sorter',
                  default='klusta',
                  type=click.Choice(['klusta', 'mountain', 'kilosort', 'spyking-circus', 'ironclust']),
                  help='Spike sorter software to be used.',
                  )
    @click.option('--acquisition',
                  default=None,
                  type=click.STRING,
                  help='(optional) Open ephys cquisition folder.',
                  )
    @click.option('--exdir-path',
                  default=None,
                  type=click.STRING,
                  help='(optional) Exdir file path.',
                  )
    @click.option('--no-sorting',
                  is_flag=True,
                  help='if True spikesorting is not performed.',
                  )
    @click.option('--no-lfp',
                  is_flag=True,
                  help='if True LFP are not extracted.',
                  )
    @click.option('--no-mua',
                  is_flag=True,
                  help='if True MUA are not extracted.',
                  )
    @click.option('--spike-params',
                  type=click.STRING,
                  default=None,
                  help='Path to spike sorting params yml file.',
                  )
    @click.option('--server',
                  type=click.STRING,
                  default=None,
                  help="'local' or name of expipe server.",
                  )
    @click.option('--ground', '-g',
                  type=click.INT,
                  multiple=True,
                  default=None,
                  help="bad channels to ground.",
                  )
    @click.option('--ref',
                  default='cmr',
                  type=click.Choice(['cmr', 'car', 'none']),
                  help='Reference to be used.',
                  )
    @click.option('--split-channels',
                  default='all',
                  type=click.STRING,
                  help="It can be 'all', 'half', or list of channels used for custom split e.g. [[0,1,2,3,4], [5,6,7,8,9]]"
                  )
    def _process_openephys(action_id, probe_path, sorter, no_sorting, no_mua, no_lfp,
                           spike_params, server, acquisition, exdir_path, ground, ref, split_channels):
        if no_sorting:
            spikesort = False
        else:
            spikesort = True
        if no_lfp:
            compute_lfp = False
        else:
            compute_lfp = True
        if no_mua:
            compute_mua = False
        else:
            compute_mua = True
        if spike_params is not None:
            spike_params = pathlib.Path(spike_params)
            if spike_params.is_file():
                with spike_params.open() as f:
                    params = yaml.load(f)
            else:
                params = None
        else:
            params = None
        if split_channels == 'custom':
            import ast
            split_channels = ast.literal_eval(split_channels)
            assert isinstance(split_channels, list), 'With custom reference the list of channels has to be provided ' \
                                                     'with the --split-channels argument'
        openephys.process_openephys(project=PAR.PROJECT, action_id=action_id, probe_path=probe_path, sorter=sorter,
                                    spikesort=spikesort, compute_lfp=compute_lfp, compute_mua=compute_mua,
                                    spikesorter_params=params, server=server, acquisition_folder=acquisition,
                                    exdir_file_path=exdir_path, ground=ground, ref=ref, split=split_channels)
