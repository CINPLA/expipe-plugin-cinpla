# -*- coding: utf-8 -*-
import ipywidgets
import matplotlib.pyplot as plt
import numpy as np

from expipe_plugin_cinpla.scripts.unittracking import (
    plot_rate_maps,
    plot_unit_templates,
    save_to_nwb,
    track_units,
)
from expipe_plugin_cinpla.tools.project_loader import ProjectLoader
from expipe_plugin_cinpla.widgets.utils import BaseViewWithLog


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

        output_waveforms = ipywidgets.Output()
        with output_waveforms:
            self.figure_waveforms = plt.figure(figsize=(7, 10))
            plt.show()

        output_ratemaps = ipywidgets.Output()
        with output_ratemaps:
            self.figure_ratemaps = plt.figure(figsize=(7, 10))
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
                output_waveforms,
                output_ratemaps,
            ]
        )

        view_plot = BaseViewWithLog(main_box=main_box_plot, project=project)

        # this is shared across tabs
        self.unit_matching = {}

        @view_compute.output.capture()
        def on_track_units(change):
            print("Tracking daily units")
            track_units_label.description = "Status: Processing"
            track_units_label.style.button_color = "yellow"
            self.unit_matching = track_units(
                project_loader,
                entity_selector_compute.value,
                date_selector_compute.value,
                dissimilarity.value,
            )
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
                for action_id in unit_matching.actions_list:
                    save_to_nwb(
                        project_loader,
                        action_id,
                        unit_matching,
                    )

        @view_plot.output.capture()
        def save_selected_to_nwb():
            for _, unit_matching in self.unit_matching.items():
                for action_id in unit_matching.actions_list:
                    entity, date, _ = action_id.split("-")
                    if entity in entity_selector_view.value and date in date_selector_view.value:
                        save_to_nwb(
                            project_loader,
                            action_id,
                            unit_matching,
                        )

        def plot_matched_units(change):
            entity = entity_selector_view.value
            date = date_selector_view.value
            unit_matching = self.unit_matching.get((entity, date))
            if unit_matching is None:
                print(f"No matching found for {entity} on {date}")
            else:
                unit_id = matched_units.value
                plot_unit_templates(self.project, unit_matching, unit_id, fig=self.figure_waveforms)
                plot_rate_maps(self.project, unit_matching, unit_id, fig=self.figure_ratemaps)

        entity_selector_view.observe(on_entity_view_change, names="value")
        date_selector_view.observe(on_date_view_change, names="value")
        matched_units.observe(plot_matched_units, names="value")
        track_units_button.on_click(on_track_units)
        save_selected_nwb_button.on_click(save_selected_to_nwb)
        save_all_nwb_button.on_click(save_all_to_nwb)

        super().__init__(children=(view_compute, view_plot))
        self.titles = ["Compute", "Plot"]
