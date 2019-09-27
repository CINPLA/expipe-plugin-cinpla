from expipe_plugin_cinpla.imports import *
from .utils import _get_data_path, read_python, write_python
from pathlib import Path
import shutil
import time
from pathlib import Path, PureWindowsPath
import shlex
from subprocess import Popen, PIPE
import spikeextractors as se
import spiketoolkit as st
import spikecomparison as sc
import os


def process_phy(project, action_id, sorter, restore=False):
    action = project.actions[action_id]
    # if exdir_path is None:
    exdir_path = _get_data_path(action)
    exdir_file = exdir.File(exdir_path, plugins=exdir.plugins.quantities)

    phy_dir = exdir_file['processing']['electrophysiology']['spikesorting'][sorter]['phy'].directory
    phy_params = exdir_file['processing']['electrophysiology']['spikesorting'][sorter]['phy'].directory / 'params.py'

    if restore:
        groups_file = [p for p in phy_dir.iterdir() if 'cluster_group' in p.name]
        if len(groups_file) == 1:
            print('Removing cluster file')
            os.remove(str(groups_file[0]))

    sorting_phy = se.PhySortingExtractor(phy_dir)
    if not Path(sorting_phy.params['dat_path']).is_file():
        datfile = [x for x in phy_dir.iterdir() if x.suffix == '.dat'][0]
        new_params = sorting_phy.params
        datfile = Path(PureWindowsPath(datfile))
        new_params['dat_path'] = str(datfile.absolute())
        write_python(str(phy_dir / 'params.py'), new_params)
        sorting_phy = se.PhySortingExtractor(phy_dir)
        print("Changed absolute dat path to:", str(datfile.absolute()))

    if len(sorting_phy.get_unit_ids()) > 1:
        print('Running phy')
        cmd = 'phy template-gui ' + str(phy_params)
        _run_command_and_print_output(cmd)
    else:
        print('Only one unit found. Phy needs more than one unit.')


def process_consensus(project, action_id, sorters, min_agreement=None):
    action = project.actions[action_id]
    # if exdir_path is None:
    exdir_path = _get_data_path(action)
    exdir_file = exdir.File(exdir_path, plugins=[exdir.plugins.quantities])

    sorting_list = []
    sorter_names = []
    for sorter in sorters:
        phy_dir = str(exdir_file['processing']['electrophysiology']['spikesorting'][sorter]['phy'].directory)
        phy_params = str(
            exdir_file['processing']['electrophysiology']['spikesorting'][sorter]['phy'].directory / 'params.py')

        sorting_phy = se.PhySortingExtractor(phy_dir)
        sorting_list.append(sorting_phy)
        sorter_names.append(sorter)
        recording = se.PhyRecordingExtractor(phy_dir)

    mcmp = sc.compare_multiple_sorters(sorting_list=sorting_list, name_list=sorter_names, verbose=True)
    if min_agreement is None:
        min_agreement = len(sorter_names) - 1

    agr = mcmp.get_agreement_sorting(minimum_matching=min_agreement)
    print(agr.get_unit_ids())
    for u in agr.get_unit_ids():
        print(agr.get_unit_property(u, 'sorter_unit_ids'))
        agr.get_unit_property_names(u)

    consensus_dir = exdir_file['processing']['electrophysiology']['spikesorting'].require_group('consensus').require_raw('phy').directory
    st.postprocessing.export_to_phy(recording, agr, output_folder=consensus_dir,
                                    ms_before=0.5, ms_after=2, verbose=True,
                                    grouping_property='group')

def process_save_phy(project, action_id, sorter):
    action = project.actions[action_id]
    # if exdir_path is None:
    exdir_path = _get_data_path(action)
    exdir_file = exdir.File(exdir_path, plugins=exdir.plugins.quantities)

    print(exdir_file['processing']['electrophysiology']['spikesorting'][sorter]['phy'].directory)

    phy_folder = exdir_file['processing']['electrophysiology']['spikesorting'][sorter]['phy'].directory
    sorting = se.PhySortingExtractor(phy_folder, exclude_cluster_groups=['noise'], load_waveforms=True, verbose=True)
    se.ExdirSortingExtractor.write_sorting(sorting, exdir_path, sampling_frequency=sorting.params['sample_rate'],
                                           save_waveforms=True, verbose=True)


def _run_command_and_print_output(command):
    command_list = shlex.split(command, posix="win" not in sys.platform)
    with Popen(command_list, stdout=PIPE, stderr=PIPE) as process:
        while True:
            output_stdout = process.stdout.readline()
            output_stderr = process.stderr.readline()
            if (not output_stdout) and (not output_stderr) and (process.poll() is not None):
                break
            if output_stdout:
                print(output_stdout.decode())
            if output_stderr:
                print(output_stderr.decode())
        rc = process.poll()
        return rc
