# -*- coding: utf-8 -*-
import h5py
import ipywidgets
import matplotlib.pyplot as plt
import numpy as np
from pynwb import NWBHDF5IO
from tqdm.auto import tqdm

from expipe_plugin_cinpla.scripts.utils import _get_data_path
from expipe_plugin_cinpla.tools.project_loader import ProjectLoader

from .utils import BaseViewWithLog


class DailyUnitTrackViewer(ipywidgets.Tab):

    def __init__(self, project):
        project_loader = ProjectLoader(project.path)
        df_meta = project_loader.metadata
        entities = project_loader.entities
        entity_selector_compute = ipywidgets.SelectMultiple(
            options=entities,
            description="Entities",
        )
        entity_selector_compute.value = entity_selector_compute.options
        dates = list(np.unique(df_meta["date"]))
        # Create widgets for compute tab
        date_selector_compute = ipywidgets.SelectMultiple(
            options=dates,
            description="Dates",
        )
        date_selector_compute.value = date_selector_compute.options
        dissimilarity_label = ipywidgets.Label("Dissimilarity threshold", layout=dict(width="300px"))
        dissimilarity = ipywidgets.FloatText(value=0.1, description="", layout=dict(width="300px"))

        track_units_button = ipywidgets.Button(description="Track Units", layout={"height": "50px", "width": "50%"})
        track_units_label = ipywidgets.Button(
            description="Status: Ready",
            disabled=True,
            layout={"height": "50px", "width": "50%"},
            style={"button_color": "green"},
        )
        track_box = ipywidgets.HBox([track_units_button, track_units_label])

        main_box_compute = ipywidgets.VBox(
            [
                ipywidgets.HBox([entity_selector_compute, date_selector_compute]),
                dissimilarity_label,
                dissimilarity,
                track_box,
            ]
        )

        view_compute = BaseViewWithLog(main_box=main_box_compute, project=project)

        # Create widgets for plot tab
        entity_selector_view = ipywidgets.Dropdown(
            options=entities,
            description="Entities",
        )
        # Create widgets for compute tab
        date_selector_view = ipywidgets.Dropdown(
            options=(),
            description="Dates",
        )

        save_selected_nwb_button = ipywidgets.Button(
            description="Save selected matches to NWB",
            layout={"height": "50px", "width": "50%"},
            style={"button_color": "pink"},
        )
        save_all_nwb_button = ipywidgets.Button(
            description="Save all matches to NWB",
            layout={"height": "50px", "width": "50%"},
            style={"button_color": "pink"},
        )

        output = ipywidgets.Output()
        with output:
            self.figure = plt.figure(figsize=(10, 10))
            plt.show()

        matched_units = ipywidgets.Dropdown(
            options=[],
            description="Matched units",
        )
        main_box_plot = ipywidgets.VBox(
            [
                ipywidgets.HBox([entity_selector_view, date_selector_view]),
                ipywidgets.HBox([save_selected_nwb_button, save_all_nwb_button]),
                matched_units,
                output,
            ]
        )

        view_plot = BaseViewWithLog(main_box=main_box_plot, project=project)

        # this is shared across tabs
        self.unit_matching = {}

        @view_compute.output.capture()
        def on_track_units(change):
            from ..tools.trackunitmulticomparison import TrackMultipleSessions

            df_meta_selected = df_meta[
                df_meta["entity"].isin(entity_selector_compute.value)
                & df_meta["date"].isin(date_selector_compute.value)
            ]
            g_by_entity_date = df_meta_selected.groupby(["entity", "date"])
            print(f"Processing {len(g_by_entity_date.groups)} days")
            track_units_label.description = "Status: Processing"
            track_units_label.style.button_color = "yellow"

            for g_name in tqdm(g_by_entity_date.groups, desc="Identyfing units"):
                g_df = g_by_entity_date.get_group(g_name)
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

                self.unit_matching[g_name] = unit_matching

            track_units_label.description = "Status: Done"
            track_units_label.style.button_color = "green"

        def on_entity_view_change(change):
            entity = change["new"]
            dates = df_meta[df_meta["entity"] == entity]["date"].unique()
            date_selector_view.options = dates

        @view_plot.output.capture()
        def on_date_view_change(change):
            entity = entity_selector_view.value
            date = change["new"]
            unit_matching = self.unit_matching.get((entity, date))
            if unit_matching is None:
                print(f"No matching found for {entity} on {date}")
            else:
                matched_units_options = []
                for group in unit_matching.identified_units:
                    identified_units_in_group = unit_matching.identified_units[group]
                    matched_units_options.extend(list(identified_units_in_group.keys()))
                matched_units.options = matched_units_options

        @view_plot.output.capture()
        def save_all_to_nwb():
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

        @view_plot.output.capture()
        def save_selected_to_nwb():
            pass

        def plot_matched_units(change):
            entity = entity_selector_view.value
            date = date_selector_view.value
            unit_matching = self.unit_matching.get((entity, date))
            if unit_matching is None:
                print(f"No matching found for {entity} on {date}")
            else:
                unit_id = matched_units.value
                unit_dict = unit_matching.identified_units[unit_id]
                unit_matching.plot_unit(unit_dict)

        entity_selector_view.observe(on_entity_view_change, names="value")
        date_selector_view.observe(on_date_view_change, names="value")
        matched_units.observe(plot_matched_units, names="value")
        track_units_button.on_click(on_track_units)
        save_selected_nwb_button.on_click(save_selected_to_nwb)
        save_all_nwb_button.on_click(save_all_to_nwb)

        super().__init__(children=(view_compute, view_plot))
        self.titles = ["Compute", "Plot"]
