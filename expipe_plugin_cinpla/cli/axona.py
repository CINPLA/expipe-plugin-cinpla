from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.scripts import axona
from . import utils


def attach_to_cli(cli):
    @cli.command('axona', short_help='Register an axona recording-action to database.')
    @click.argument('axona-filename', type=click.Path(exists=True))
    @click.option('-u', '--user',
                  type=click.STRING,
                  help='The experimenter performing the recording.',
                  )
    @click.option('-d', '--depth',
                  multiple=True,
                  callback=utils.validate_depth,
                  help=('The depth given as <key num depth unit> e.g. ' +
                        '<mecl 0 10 um> (omit <>).'),
                  )
    @click.option('-c', '--cluster-group',
                  multiple=True,
                  callback=utils.validate_cluster_group,
                  help=('The depth given as <key num depth unit> e.g. ' +
                        '<"channel_group cluster_id good|noise|unsorted"> (omit <>).'),
                  )
    @click.option('-l', '--location',
                  type=click.STRING,
                  required=True,
                  callback=utils.optional_choice,
                  envvar=PAR.POSSIBLE_LOCATIONS,
                  help='The location of the recording, i.e. "room1".'
                  )
    @click.option('--action-id',
                  type=click.STRING,
                  help=('Desired action id for this action, if none' +
                        ', it is generated from axona-path.'),
                  )
    @click.option('--no-files',
                  is_flag=True,
                  help='Generate action without storing files.',
                  )
    @click.option('--no-modules',
                  is_flag=True,
                  help='Generate action without storing modules.',
                  )
    @click.option('--entity-id',
                  type=click.STRING,
                  help='The id number of the entity.',
                  )
    @click.option('--overwrite',
                  is_flag=True,
                  help='Overwrite modules or not.',
                  )
    @click.option('-m', '--message',
                  multiple=True,
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
    @click.option('--get-inp',
                  is_flag=True,
                  help='Use Axona input ".inp.',
                  )
    @click.option('--no-cut',
                  is_flag=True,
                  help='Do not load ".cut" files',
                  )
    @click.option('--set-noise',
                  is_flag=True,
                  help='All units not defined in cluster-group are noise.',
                  )
    @click.option('-y', '--yes',
                  is_flag=True,
                  help='Yes to depth registering query.',
                  )
    def _generate_axona_action(action_id, axona_filename, depth, user,
                              overwrite, no_files, no_modules,
                              entity_id, location, message, tag,
                              get_inp, yes, no_cut, cluster_group,
                              set_noise):
        generate_axona_action(action_id, axona_filename, depth, user,
                                  overwrite, no_files, no_modules,
                                  entity_id, location, message, tag,
                                  get_inp, yes, no_cut, cluster_group,
                                  set_noise)
