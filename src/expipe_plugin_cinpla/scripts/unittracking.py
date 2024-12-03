# -*- coding: utf-8 -*-
import shutil
import warnings

import numpy as np
from pynwb import NWBHDF5IO
from tqdm.auto import tqdm

from expipe_plugin_cinpla.scripts.utils import _get_data_path
from expipe_plugin_cinpla.tools.data_loader import load_spiketrains

warnings.filterwarnings("ignore")


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
    for g_name in tqdm(g_by_entity_date.groups, desc="Tracking daily units"):
        g_df = g_by_entity_date.get_group(g_name)
        action_list = [
            action for action in g_df["action_id"].tolist() if check_action_has_main_units(project_loader, action)
        ]
        actions_without_main_units = [a for a in g_df["action_id"].tolist() if a not in action_list]
        if len(actions_without_main_units) > 0:
            print(f"Some actions don't have main units. Perform curation first!\n{actions_without_main_units}")
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
        unit_matching.remove_edges_above_threshold("weight", dissimilarity)
        unit_matching.identify_units()
        unit_matching_dict[g_name] = unit_matching

    for g_name, unit_matching in unit_matching_dict.items():
        num_matches = sum([len(matches) for g, matches in unit_matching.identified_units.items()])
        print(f"Number of identified units for {g_name}: {num_matches}")
    return unit_matching_dict


def save_to_nwb(project_loader, action_id, unit_matching):
    action = project_loader.actions[action_id]
    nwb_path = _get_data_path(action)
    nwb_path_tmp = nwb_path.parent / "main_tmp.nwb"
    shutil.copy(nwb_path, nwb_path_tmp)

    spike_trains = load_spiketrains(nwb_path_tmp)
    unit_ids = [u.annotations["name"] for u in spike_trains]

    daily_ids = np.zeros(len(unit_ids), dtype="U38")
    for group in unit_matching.identified_units:
        identified_units_in_group = unit_matching.identified_units[group]
        for unique_unit, unit_dict in identified_units_in_group.items():
            original_unit_id = unit_dict["original_unit_ids"].get(action_id)
            if original_unit_id is not None:
                unit_index = unit_ids.index(str(original_unit_id))
                daily_ids[unit_index] = unique_unit

    try:
        with NWBHDF5IO(str(nwb_path_tmp), mode="a") as io:
            nwbfile = io.read()
            if "daily_unit_id" in nwbfile.units.colnames:
                print("Overwriting existing daily_unit_id column")
                daily_units_vector = nwbfile.units["daily_unit_id"]
                daily_units_vector.data[:] = daily_ids
                daily_units_vector.set_modified(True)
            else:
                nwbfile.add_unit_column(
                    name="daily_unit_id", description="Unique unid ID over same day", data=daily_ids
                )
            io.write(nwbfile)
        nwb_path.unlink()
        shutil.copy(nwb_path_tmp, nwb_path)
    except Exception as e:
        print(f"Failed saving {action_id} to NWB:\n{e}")
        nwb_path_tmp.unlink()


def plot_unit_templates(unit_matching, fig):
    fig.clear()
    identified_units = unit_matching.identified_units
    num_matches = sum([len(matches) for g, matches in identified_units.items()])
    fig.set_size_inches(10, 3 * num_matches)

    ax_idx = 0
    axs = None

    for ch_group in identified_units:
        units = identified_units[ch_group]
        for unique_unit_id, unit_dict in units.items():
            actions_in_match = sorted(list(unit_dict["original_unit_ids"].keys()))
            for i, action_id in enumerate(actions_in_match):
                original_unit_id = unit_dict["original_unit_ids"][action_id]
                template = unit_matching.load_template(action_id, ch_group, original_unit_id)
                num_channels = template.shape[1]
                if np.mod(num_channels, 2) == 0:
                    center_ax = num_channels // 2 - 1
                    title_x = 0.5
                else:
                    center_ax = num_channels // 2
                    title_x = -0.3
                if i == 0 and ax_idx == 0:
                    axs = fig.subplots(nrows=num_matches, ncols=num_channels)
                for ch in range(num_channels):
                    ax = axs[ax_idx, ch]
                    if ch == num_channels - 1:
                        label = f"{action_id} - {original_unit_id}"
                    else:
                        label = None
                    ax.plot(template[:, ch], label=label, color=f"C{i}")
                    if ch == 0:
                        ax.spines[["top", "right", "bottom"]].set_visible(False)
                        ax.set_xticklabels([])
                        ax.set_xticks([])
                    else:
                        ax.axis("off")
                    if ch == num_channels - 1:
                        ax.legend(loc="upper left", bbox_to_anchor=(0.9, 0.8))
                    if ch == center_ax:
                        ax.text(title_x, 1.1, f"{unique_unit_id} ({ch_group})", transform=ax.transAxes)
            ax_idx += 1
    fig.subplots_adjust(hspace=0.3, wspace=0.3, right=0.9)


def plot_rate_maps(project_loader, unit_matching, fig):
    from spatial_maps import SpatialMap

    from ..tools.data_processing import load_spiketrains, load_tracking

    identified_units = unit_matching.identified_units
    fig.clear()
    num_matches = sum([len(matches) for g, matches in identified_units.items()])
    fig.set_size_inches(10, 4 * num_matches)
    num_actions = len(unit_matching.action_list)
    axs = fig.subplots(nrows=num_matches, ncols=num_actions)

    if np.mod(num_actions, 2) == 0:
        center_ax = num_actions // 2 - 1
        title_x = 0.5
    else:
        center_ax = num_actions // 2
        title_x = -0.3
    ax_idx = 0
    for ch_group in identified_units:
        units = identified_units[ch_group]
        for unique_unit_id, unit_dict in units.items():
            original_unit_ids = unit_dict["original_unit_ids"]
            sm = SpatialMap()

            for i, action_id in enumerate(sorted(unit_matching.action_list)):
                ax = axs[ax_idx, i]
                original_unit_id = original_unit_ids.get(action_id)
                if original_unit_id is not None:
                    action = project_loader.actions[action_id]
                    nwb_path = _get_data_path(action)
                    x, y, t, _ = load_tracking(nwb_path)
                    spike_trains = load_spiketrains(nwb_path)
                    unit_names = [st.annotations["name"] for st in spike_trains]
                    if str(original_unit_id) in unit_names:
                        spike_train = spike_trains[unit_names.index(str(original_unit_id))]
                        ratemap = sm.rate_map(x, y, t, spike_train)
                        ax.imshow(ratemap.T, origin="lower")
                else:
                    ax.imshow(np.zeros((10, 10)) * np.nan)
                ax.set_title(action_id, fontsize=10)
                ax.axis("off")
                if i == center_ax:
                    ax.text(title_x, 1.3, f"{unique_unit_id} ({ch_group})", transform=ax.transAxes, fontsize=12)
            ax_idx += 1
    fig.subplots_adjust(hspace=0.5, wspace=0.3, top=0.9)
