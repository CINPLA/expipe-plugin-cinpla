import shutil
from pathlib import Path

import expipe

from .utils import _get_data_path
from .register import convert_to_nwb
from .process import process_ecephys
from .curation import SortingCurator


def convert_old_project(
    old_project_path: str | Path,
    new_project_path: str | Path,
    probe_path: str | Path,
    include_events: bool = True,
    process_ecephys_params: dict | None = None,
    preferred_sorter: str | None = None,
):
    """
    Convert an expipe CINPLA project from an old version to the current version.

    Parameters
    ----------
    old_project_path : str or Path
        Path to the old project
    new_project_path : str or Path
        Path to the new project
    probe_path : str or Path
        Path to the probe file
    include_events : bool, default: True
        Whether to include events in the NWB file
    process_ecephys_params : dict, optional
        Parameters for the process_ecephys function. If None, default parameters are used, including:
        * compute_lfp=True
        * compute_mua=False
        * bad_channel_ids=None
        * reference="cmr"
        * split="half"
        * bad_threshold=None
        * ms_before=1
        * ms_after=2
    preferred_sorter : str, optional
        Name of the preferred sorter to use for processing. Required if there are multiple sorters in the old project.
    """
    if process_ecephys_params is None:
        process_ecephys_params = dict(
            compute_lfp=True,
            compute_mua=False,
            bad_channel_ids=None,
            reference="cmr",
            split="half",
            bad_threshold=None,
            ms_before=1,
            ms_after=2,
        )

    old_project_path = Path(old_project_path)
    old_project_name = old_project_path.name
    new_project_path = Path(new_project_path)
    new_project_name = new_project_path.name

    # Instantiate project and retrieve actions
    old_project = expipe.get_project(old_project_path)
    old_actions = old_project.actions

    # copy everything, will prune later
    # TODO: remove later
    if new_project_path.is_dir():
        raise FileExistsError(f"Project {new_project_path} already exists!")
    else:
        print("Copying entire project")
        shutil.copytree(old_project_path, new_project_path, ignore=shutil.ignore_patterns("**/*main.exdir", ".git"))

    expipe_str = (new_project_path / "expipe.yaml").read_text()
    expipe_str = expipe_str.replace(old_project_name, new_project_name)
    (new_project_path / "expipe.yaml").write_text(expipe_str)
    new_project = expipe.get_project(new_project_path)

    print(f"Found {len(old_actions)} actions in {old_project_name}\n")

    # copy actions
    for action_id in old_actions:
        print(f"Processing action {action_id}")
        old_action = old_actions[action_id]
        new_action = new_project.actions[action_id]
        old_data_folder = _get_data_path(old_action).parent
        new_data_folder = _get_data_path(new_action).parent

        # main.exdir
        old_exdir_folder = old_data_folder / "main.exdir"

        # find open-ephys folder
        acquisition_folder = old_exdir_folder / "acquisition"
        openephys_folders = [p for p in acquisition_folder.iterdir() if p.is_dir()]
        if len(openephys_folders) != 1:
            print(f"Found {len(openephys_folders)} openephys folders in {acquisition_folder}!")
            continue
        openephys_path = openephys_folders[0]
        entity_id = action_id.split("-")[0]
        user = old_action.attributes["users"][0]

        print("\tConverting to NWB")
        convert_to_nwb(
            new_project, new_action, openephys_path, probe_path, entity_id, user, include_events, overwrite=True
        )

        # Copy Phy folder
        print("\tCopying Phy folder")
        old_spikesorting = old_exdir_folder / "processing" / "electrophysiology" / "spikesorting"
        new_si_folder = new_data_folder / "spikeinterface"
        new_si_folder.mkdir(exist_ok=True)
        old_sorters = [p for p in old_spikesorting.iterdir() if p.is_dir()]
        for sorter_folder in old_sorters:
            new_sorter_folder = new_si_folder / sorter_folder.name
            new_sorter_folder.mkdir(exist_ok=True)
            # copy phy folder
            old_phy_folder = sorter_folder / "phy"
            new_phy_folder = new_sorter_folder / "phy"
            shutil.copytree(old_phy_folder, new_phy_folder)

        # Run processing only (no spike sorting)
        if len(old_sorters) == 1:
            sorter_name = old_sorters[0].name
        else:
            assert preferred_sorter is not None
            sorter_name = preferred_sorter
        print("\tRunning processing")
        process_ecephys(new_project, action_id, sorter=sorter_name, spikesort=False, **process_ecephys_params)

        print("\tApplying Phy curation and set main units")
        # Generate new main unit table from Phy (with preprocessed data)
        sorting_curator = SortingCurator(new_project)
        sorting_curator.set_action(action_id)
        sorting_curator.load_from_phy(sorter=sorter_name)
        # save main units
        sorting_curator.save_to_nwb()
