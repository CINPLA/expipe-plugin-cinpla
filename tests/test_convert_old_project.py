from pathlib import Path
from pynwb import NWBHDF5IO

import expipe
from expipe_plugin_cinpla.scripts.utils import _get_data_path
from expipe_plugin_cinpla import convert_old_project

test_folder = Path(__file__).parent
old_project_path = test_folder / "test_data" / "old_project"


def test_convert_old_project(tmp_path):
    new_project_path = tmp_path / "new_project"
    probe_path = test_folder / "test_data" / "tetrode_32_openephys.json"

    convert_old_project(old_project_path, new_project_path, probe_path)

    old_project = expipe.get_project(old_project_path)
    new_project = expipe.get_project(new_project_path)

    for action in old_project.actions:
        assert action in new_project.actions
        action = new_project.actions[action]
        data_path = _get_data_path(action)

        assert data_path.name == "main.nwb"
        assert (data_path.parent / "spikeinterface").is_dir()

        with NWBHDF5IO(data_path, mode="r") as io:
            nwbfile = io.read()
            assert nwbfile.units is not None
