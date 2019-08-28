from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.scripts import curation
import spiketoolkit as st
from . import utils


def attach_to_process(cli):
    @cli.command('phy2exdir',
                 short_help='Save curation output to exdir.')
    @click.argument('action-id', type=click.STRING)
    @click.option('--sorter',
                  default='kilosort2',
                  type=click.Choice([s.sorter_name for s in st.sorters.sorter_full_list]),
                  help='Spike sorter software to be used.',
                  )
    def _phy_to_exdir(action_id, sorter):
        curation.process_save_phy(project, action_id, sorter)
