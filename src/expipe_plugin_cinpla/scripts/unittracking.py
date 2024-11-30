# -*- coding: utf-8 -*-
import h5py
import numpy as np
from pynwb import NWBHDF5IO
from tqdm.auto import tqdm

from expipe_plugin_cinpla.scripts.utils import _get_data_path


def check_action_has_main_units(project_loader, action_id):
    action = project_loader.actions[action_id]
    nwb_path = _get_data_path(action)
    with NWBHDF5IO(nwb_path, mode="r") as io:
        nwbfile = io.read()
        units = nwbfile.units
        if units is not None:
            return True
    return False


def track_units(project_loader, actions, dates, dissimilarity):
    from ..tools.trackunitmulticomparison import TrackMultipleSessions

    df_meta = project_loader.metadata
    df_meta_selected = df_meta[df_meta["entity"].isin(actions) & df_meta["date"].isin(dates)]
    g_by_entity_date = df_meta_selected.groupby(["entity", "date"])

    unit_matching_dict = {}
    for g_name in tqdm(g_by_entity_date.groups, desc="Identyfing units"):
        g_df = g_by_entity_date.get_group(g_name)
        action_list = [
            action for action in g_df["action_id"].tolist() if check_action_has_main_units(project_loader, action)
        ]
        unit_matching = TrackMultipleSessions(
            project_loader.actions,
            action_list=action_list,
            progress_bar=None,
            verbose=False,
            data_path=None,
        )

        unit_matching.do_matching()
        unit_matching.make_graphs_from_matches()
        unit_matching.compute_time_delta_edges()
        unit_matching.compute_depth_delta_edges()
        unit_matching.remove_edges_with_duplicate_actions()
        unit_matching.remove_edges_above_threshold("weight", dissimilarity.value)
        unit_matching.identify_units()
        unit_matching_dict[g_name] = unit_matching
    return unit_matching_dict


def save_to_nwb(project_loader, action_id, unit_matching):
    action = project_loader.actions[action_id]
    nwb_path = _get_data_path(action)
    io = NWBHDF5IO(nwb_path, mode="r")
    nwbfile = io.read()
    unit_ids = list(nwbfile.units.id[:])
    io.close()

    daily_ids = np.zeros(len(unit_ids), dtype="U16")
    for group in unit_matching.identified_units:
        identified_units_in_group = unit_matching.identified_units[group]
        for unique_unit, unit_dict in identified_units_in_group.items():
            original_unit_id = unit_dict["original_unit_ids"].get(action_id)
            if action is not None:
                unit_index = unit_ids.index(original_unit_id)
                daily_ids[unit_index] = f"d_{unique_unit}"

    # add column to HDF5 directly
    f = h5py.File(nwb_path, "r+")
    units = f["units"]
    colnames = units.attrs["colnames"]
    if isinstance(colnames, np.ndarray):
        colnames = colnames.tolist()
    else:
        assert isinstance(colnames, list)

    # Remove if already exists
    if "daily_unique_id" in colnames:
        colnames.remove("daily_unique_id")
        del units["daily_unique_id"]

    colnames.append("daily_unique_id")
    units.create_dataset("daily_unique_id", data=daily_ids, dtype="U16")
    f.close()


def plot_unit_templates(project_loader, unit_matching, unit_id, fig):
    identified_units = unit_matching.identified_units
    unit_dict = None
    for ch_group in identified_units:
        units = identified_units[ch_group]
        if unit_id in units:
            unit_dict = units[unit_id]
            break
    if unit_dict is None:
        print(f"Unit {unit_id} not found in identified units")
    else:
        fig.clear()
        axs = fig.subplots(num_cols=len(unit_dict["original_unit_ids"]))
        for i, (action_id, original_unit_id) in enumerate(unit_dict["original_unit_ids"].items()):
            ax = axs[i]
            template = unit_matching.load_template(action_id, ch_group, original_unit_id)
            if template is None:
                print(f'Unable to plot "{unit_id}" from action "{action_id}" ch group "{ch_group}"')
                continue
            ax.plot(template, label=f"{original_unit_id}")
        ax.legend()
        fig.suptitle(f"Unit {unit_id} on channel group {ch_group}")
        fig.canvas.draw()


def plot_rate_maps(project_loader, unit_matching, unit_id, fig):
    from spatial_maps import SpatialMap

    from ..tools.data_processing import load_spiketrains, load_tracking

    identified_units = unit_matching.identified_units
    unit_dict = None
    for ch_group in identified_units:
        units = identified_units[ch_group]
        if unit_id in units:
            unit_dict = units[unit_id]
            break
    if unit_dict is None:
        print(f"Unit {unit_id} not found in identified units")
    else:
        fig.clear()
        axs = fig.subplots(num_cols=len(unit_dict["original_unit_ids"]))
        original_unit_ids = unit_dict["original_unit_ids"]
        action_ids = sorted(list(original_unit_ids.keys()))
        sm = SpatialMap()
        for i, action_id in enumerate(action_ids):
            ax = axs[i]
            original_unit_id = original_unit_ids[action_id]
            action = project_loader.actions[action_id]
            nwb_path = _get_data_path(action)
            x, y, t, _ = load_tracking(nwb_path)
            spike_trains = load_spiketrains(nwb_path)
            unit_names = [st.annotations["name"] for st in spike_trains]
            if original_unit_id in unit_names:
                spike_train = spike_trains[unit_names.index(original_unit_id)]
                ratemap = sm.rate_map(x, y, t, spike_train)
                ax.imshow(ratemap.T, origin="lower")
            ax.set_title(action_id)
            ax.axis("off")
