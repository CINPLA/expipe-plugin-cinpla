# -*- coding: utf-8 -*-
import h5py
import ipywidgets
import numpy as np
import tqdm.auto as tqdm
from pynwb import NWBHDF5IO

from expipe_plugin_cinpla.scripts.utils import _get_data_path
from expipe_plugin_cinpla.tools.project_loader import ProjectLoader

from .utils import BaseViewWithLog


# TODO: make 2 tabs, one for tracking and one for plotting
class DailyUnitTrackViewer(BaseViewWithLog):

    def __init__(self, project):
        project_loader = ProjectLoader(project.path)
        df_meta = project_loader.metadata
        entities = project_loader.entities
        entity_selector = ipywidgets.SelectMultiple(
            options=entities,
            values=entities,
            description="Entities",
        )
        dates = list(np.unique(df_meta["date"]))
        date_selector = ipywidgets.SelectMultiple(
            options=dates,
            values=dates,
            description="Dates",
        )
        dissimilarity = ipywidgets.FloatText(
            value=0.1,
            description="Dissimilarity threshold",
        )

        track_units_button = ipywidgets.Button(
            description="Track Units", layout={"height": "50px", "width": "50%"}, style={"button_color": "pink"}
        )
        track_units_label = ipywidgets.Button(
            description="Status: Ready",
            disabled=True,
            layout={"height": "50px", "width": "50%"},
            style={"button_color": "green"},
        )
        track_box = ipywidgets.HBox([track_units_button, track_units_label])
        save_to_nwb_button = ipywidgets.Button(
            description="Save to NWB", layout={"height": "50px", "width": "50%"}, style={"button_color": "pink"}
        )

        main_box = ipywidgets.VBox(
            [ipywidgets.HBox([entity_selector, date_selector]), dissimilarity, track_box, save_to_nwb_button]
        )

        BaseViewWithLog.__init__(self, main_box=main_box, project=project)

        self.unit_matching = {}

        @self.output.capture()
        def on_track_units(change):
            from ..tools.trackunitmulticomparison import TrackMultipleSessions

            df_meta_selected = df_meta[
                df_meta["entity"].isin(entity_selector.value) & df_meta["date"].isin(date_selector.value)
            ]
            g_by_entity_date = df_meta_selected.groupby(["entity", "date"])
            print(f"Processing {len(g_by_entity_date)} days")
            track_units_label.description = "Status: Processing"
            track_units_label.style.button_color = "yellow"

            for g_names, g_df in tqdm(g_by_entity_date, desc="Identyfing units"):
                unit_matching = TrackMultipleSessions(
                    project.actions,
                    action_list=g_df["action_id"].tolist(),
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

                self.unit_matching[g_names] = unit_matching

            track_units_label.description = "Status: Done"
            track_units_label.style.button_color = "green"

        @self.output.capture()
        def save_to_nwb():
            for _, unit_matching in self.unit_matching.items():
                for action in unit_matching.actions_list:
                    nwb_path = _get_data_path(self.action)
                    io = NWBHDF5IO(nwb_path, mode="r")
                    nwbfile = io.read()
                    unit_ids = list(nwbfile.units.id[:])
                    io.close()

                    daily_ids = np.zeros(len(unit_ids), dtype="U16")
                    for group in unit_matching.identified_units:
                        identified_units_in_group = unit_matching.identified_units[group]
                        for unique_unit, unit_dict in identified_units_in_group.items():
                            original_unit_id = unit_dict["original_unit_ids"].get(action)
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

        track_units_button.on_click(on_track_units)
        save_to_nwb_button.on_click(save_to_nwb)

        # daily_tabs = ipywidgets.Tab()
        # daily_tabs.children = [
        #     compute_view,
        #     plot_view,
        # ]
