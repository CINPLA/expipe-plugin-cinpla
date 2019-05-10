from expipe_plugin_cinpla.imports import *
from .utils import _get_data_path
from pathlib import Path
import shutil
import time
import shlex
from subprocess import Popen, PIPE
import spikeextractors as se
import spiketoolkit as st


def process_phy(project, action_id, sorter):
    action = project.actions[action_id]
    # if exdir_path is None:
    exdir_path = _get_data_path(action)
    exdir_file = exdir.File(exdir_path, plugins=exdir.plugins.quantities)

    phy_params = str(exdir_file['processing']['electrophysiology']['spikesorting'][sorter]['phy'].directory / 'params.py')
    print(phy_params)
    print('Running phy')
    cmd = 'phy template-gui ' + phy_params

    _run_command_and_print_output(cmd)


def process_consensus(project, action_id, sorters, min_agreement):
    pass
    # print(action_id, sorters, min_agreement)
    # action = project.actions[action_id]
    # # if exdir_path is None:
    # exdir_path = _get_data_path(action)
    # exdir_file = exdir.File(exdir_path, plugins=exdir.plugins.quantities)
    #
    # print(exdir_file['processing']['electrophysiology']['spikesorting'][sorter]['phy'].directory)
    #
    # phy_params = str(exdir_file['processing']['electrophysiology']['spikesorting'][sorter]['phy'].directory / 'params.py')
    # print('Running phy')
    # cmd = ['phy', 'template-gui', phy_params]
    #
    # _run_command_and_print_output(cmd)


def process_save_phy(project, action_id, sorter):
    action = project.actions[action_id]
    # if exdir_path is None:
    exdir_path = _get_data_path(action)
    exdir_file = exdir.File(exdir_path, plugins=exdir.plugins.quantities)

    print(exdir_file['processing']['electrophysiology']['spikesorting'][sorter]['phy'].directory)

    phy_folder = exdir_file['processing']['electrophysiology']['spikesorting'][sorter]['phy'].directory
    sorting = se.PhySortingExtractor(phy_folder, exclude_groups=['noise'], verbose=True)
    se.ExdirSortingExtractor.write_sorting(sorting, exdir_path, sample_rate=sorting.params['sample_rate'],
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




