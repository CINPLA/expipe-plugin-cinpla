from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.tools.action import generate_templates, query_yes_no
from expipe_plugin_cinpla.tools import config, surgery


def attach_to_cli(cli):
    @cli.command('surgery', short_help='Register a surgery action.')
    @click.argument('entity-id')
    @click.option('--date', '-d',
                  required=True,
                  type=click.STRING,
                  help='The date of the surgery format: "dd.mm.yyyyTHH:MM".',
                  )
    @click.option('-t', '--tag',
                  multiple=True,
                  type=click.STRING,
                  callback=config.optional_choice,
                  envvar=PAR.POSSIBLE_TAGS,
                  help='Add tags to action.',
                  )
    @click.option('--procedure',
                  required=True,
                  type=click.Choice(['implantation', 'injection']),
                  help='The type of surgery "implantation" or "injection".',
                  )
    @click.option('--overwrite',
                  is_flag=True,
                  help='Overwrite modules or not.',
                  )
    @click.option('-u', '--user',
                  type=click.STRING,
                  help='The experimenter performing the surgery.',
                  )
    @click.option('-w', '--weight',
                  nargs=2,
                  type=(click.FLOAT, click.STRING),
                  default=(None, None),
                  help='The weight of the entity with unit i.e. <200 g> (ommit <>).',
                  )
    @click.option('-p', '--position',
                  required=True,
                  multiple=True,
                  callback=config.validate_position,
                  help='The position e.g. <"mecl 0 x y z mm"> (ommit <>).',
                  )
    @click.option('-a', '--angle',
                  required=True,
                  multiple=True,
                  callback=config.validate_angle,
                  help='The angle of implantation/injection.',
                  )
    @click.option('--message', '-m',
                  multiple=True,
                  type=click.STRING,
                  help='Add message, use "text here" for sentences.',
                  )
    def _register_surgery(entity_id, procedure, date, user, weight,
                         overwrite, position, angle, message, tag):
        surgery.register_surgery(PAR.PROJECT_ROOT, entity_id, procedure, date, user, weight,
                             overwrite, position, angle, message, tag)


    @cli.command('perfusion',
                 short_help=('Register a perfusion action. ' +
                             'Also tags the entity as perfused and euthanised.'))
    @click.argument('entity-id')
    @click.option('--date', '-d',
                  required=True,
                  type=click.STRING,
                  help='The date of the surgery format: "dd.mm.yyyyTHH:MM".',
                  )
    @click.option('-u', '--user',
                  type=click.STRING,
                  help='The experimenter performing the surgery.',
                  )
    @click.option('--weight',
                  nargs=2,
                  type=(click.FLOAT, click.STRING),
                  default=(None, None),
                  help='The weight of the animal.',
                  )
    @click.option('--overwrite',
                  is_flag=True,
                  help='Overwrite files and expipe action.',
                  )
    @click.option('--message', '-m',
                  multiple=True,
                  type=click.STRING,
                  help='Add message, use "text here" for sentences.',
                  )
    def _register_perfusion(entity_id, date, user, weight, overwrite, message):
        surgery.register_perfusion(
            PAR.PROJECT_ROOT, entity_id, date, user, weight, overwrite, message)
