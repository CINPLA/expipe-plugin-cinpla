import shutil
from datetime import datetime, timedelta
from pathlib import Path
import time

import expipe

from .utils import _get_data_path
from .register import convert_to_nwb, register_entity
from .process import process_ecephys
from .curation import SortingCurator


def convert_old_project(
    old_project_path: str | Path,
    new_project_path: str | Path,
    probe_path: str | Path,
    include_events: bool = True,
    process_ecephys_params: dict | None = None,
    preferred_sorter: str | None = None,
    default_species="Rattus norvegicus",
    default_sex="M",
    default_age_days=60,
    default_location="IBV Animal Facility",
    debug_n_actions=None,
    overwrite=False,
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
    preferred_sorter : str, default: None
        Name of the preferred sorter to use for processing. Required if there are multiple sorters in the old project.
    default_species : str, default: "Rattus norvegicus"
        Default species for the entities (if entity is not registered in old project and needs to be registered in new project)
    default_sex : str, optional
    debug_n_actions : int, optional
        Number of actions to process for debugging.
    """
    t_start_all = time.perf_counter()
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

    # copy everything, except main and .git
    if new_project_path.is_dir():
        if not overwrite:
            raise FileExistsError(f"Project {new_project_path} already exists!")
        else:
            shutil.rmtree(new_project_path)

    print("Copying entire project")
    shutil.copytree(old_project_path, new_project_path, ignore=shutil.ignore_patterns("main.exdir", ".git"))

    expipe_str = (new_project_path / "expipe.yaml").read_text()
    expipe_str = expipe_str.replace(old_project_name, new_project_name)
    (new_project_path / "expipe.yaml").write_text(expipe_str)

    new_project = expipe.get_project(new_project_path)

    # find actions with main.exdir that needs conversion
    actions_to_convert = []
    for action_id in old_actions:
        old_data_folder = old_actions[action_id].path / "data"
        if (old_data_folder / "main.exdir").is_dir():
            actions_to_convert.append(action_id)

    print(f"Found {len(old_actions)} actions in {old_project_name}\n")
    print(f"Actions that need conversion: {len(actions_to_convert)}")

    if debug_n_actions:
        actions_to_convert = actions_to_convert[:debug_n_actions]
    print(f"Actions that will be converted: {len(actions_to_convert)}")

    # copy actions
    for action_id in actions_to_convert:
        t_start_action = time.perf_counter()
        print(f"\n*****************\nProcessing action {action_id}\n*****************\n")
        old_action = old_actions[action_id]
        new_action = new_project.actions[action_id]

        # replace file in attributes.yaml
        attributes_file = new_project.path / "actions" / action_id / "attributes.yaml"
        attributes_str = attributes_file.read_text()
        attributes_str = attributes_str.replace("main.exdir", "main.nwb")
        attributes_file.write_text(attributes_str)

        old_data_folder = old_project.path / "actions" / action_id / "data"
        new_data_folder = new_project.path / "actions" / action_id / "data"

        # main.exdir
        old_exdir_folder = old_data_folder / "main.exdir"

        # find open-ephys folder
        acquisition_folder = old_exdir_folder / "acquisition"
        openephys_folders = [p for p in acquisition_folder.iterdir() if p.is_dir()]
        if len(openephys_folders) != 1:
            print(f"Found {len(openephys_folders)} openephys folders in {acquisition_folder}!")
            continue
        openephys_path = openephys_folders[0]
        # here we assume the following action name: {entity_id}-{date}-{session}
        entity_id = action_id.split("-")[0]
        user = old_action.attributes["users"][0]

        if entity_id not in new_project.entities:
            print(f"\tRegistering missing entity: {entity_id}")
            action_date = datetime.strptime("200619", "%y%M%d")
            birthday = action_date - timedelta(days=default_age_days)
            register_entity(
                new_project,
                entity_id,
                user,
                species=default_species,
                sex=default_sex,
                message=None,
                location=default_location,
                tags=None,
                overwrite=False,
                birthday=birthday,
                templates=None,
            )

        print("\tConverting to NWB")
        convert_to_nwb(
            new_project, new_action, openephys_path, probe_path, entity_id, user, include_events, overwrite=True
        )

        # Process
        old_spikesorting = old_exdir_folder / "processing" / "electrophysiology" / "spikesorting"
        new_si_folder = new_data_folder / "spikeinterface"
        new_si_folder.mkdir(exist_ok=True)
        old_sorters = [p for p in old_spikesorting.iterdir() if p.is_dir()]

        # Run processing only (no spike sorting)
        if len(old_sorters) == 1:
            sorter_name = old_sorters[0].name
        else:
            assert preferred_sorter is not None
            sorter_name = preferred_sorter
        print("\tRunning processing")
        process_ecephys(new_project, action_id, sorter=sorter_name, spikesort=False, **process_ecephys_params)

        print("\tCopying Phy folders")
        for sorter_folder in old_sorters:
            new_sorter_folder = new_si_folder / sorter_folder.name
            new_sorter_folder.mkdir(exist_ok=True)
            # copy phy folder
            old_phy_folder = sorter_folder / "phy"
            new_phy_folder = new_sorter_folder / "phy"
            if new_phy_folder.is_dir():
                if overwrite:
                    shutil.rmtree(new_phy_folder)
                else:
                    raise FileExistsError(f"Phy folder {new_phy_folder} already exists!")
            print(f"\t\tCopying folder for {sorter_folder.name}: from {old_phy_folder} to {new_phy_folder}")
            shutil.copytree(old_phy_folder, new_phy_folder)

        print("\tApplying Phy curation and set main units")
        # Generate new main unit table from Phy (with preprocessed data)
        sorting_curator = SortingCurator(new_project)
        sorting_curator.set_action(action_id)
        sorting_curator.load_from_phy(sorter=sorter_name)
        # save main units
        sorting_curator.save_to_nwb()

        t_stop_action = time.perf_counter()
        print(f"Action {action_id} done in {t_stop_action - t_start_action:.2f} s")

    t_stop_all = time.perf_counter()
    print(f"Total time: {t_stop_all - t_start_all:.2f} s")
    print(f"*****************\nALL DONE!\n*****************")
