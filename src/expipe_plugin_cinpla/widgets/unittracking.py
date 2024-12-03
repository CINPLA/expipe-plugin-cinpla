# -*- coding: utf-8 -*-
import ipywidgets
import matplotlib.pyplot as plt
import numpy as np
from ipywidgets.widgets.interaction import show_inline_matplotlib_plots

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
        self.project_loader = project_loader
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

        track_units_button = ipywidgets.Button(description="Track Units", layout={"height": "50px", "width": "100%"})

        main_box_compute = ipywidgets.VBox(
            [
                ipywidgets.HBox([entity_selector_compute, date_selector_compute]),
                dissimilarity_label,
                dissimilarity,
                track_units_button,
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
        )
        save_all_nwb_button = ipywidgets.Button(
            description="Save all matches to NWB",
            layout={"height": "50px", "width": "50%"},
        )
        plot_button = ipywidgets.Button(
            description="Plot templates and maps", layout={"height": "50px", "width": "100%"}
        )
        show_hide_plot_button = ipywidgets.Button(
            description="Show/Hide plots", layout={"height": "50px", "width": "100%"}
        )

        buttons_box = ipywidgets.HBox([plot_button, show_hide_plot_button])

        output_waveforms = ipywidgets.Output(layout={"height": "600px", "overflow": "scroll"})
        output_ratemaps = ipywidgets.Output(layout={"height": "600px", "overflow": "scroll"})

        matched_unit_labels = ipywidgets.Label("Number of matches")
        matched_units = ipywidgets.Text("", disabled=True)
        main_box_plot = ipywidgets.VBox(
            [
                ipywidgets.HBox([entity_selector_view, date_selector_view]),
                ipywidgets.HBox([matched_unit_labels, matched_units]),
                buttons_box,
                ipywidgets.HBox([save_selected_nwb_button, save_all_nwb_button]),
            ]
        )

        view_plot = BaseViewWithLog(main_box=main_box_plot, project=project)

        # this is shared across tabs
        self.unit_matching = {}

        @view_compute.output.capture()
        def on_track_units(change):
            original_color = track_units_button.style.button_color
            track_units_button.style.button_color = "yellow"
            self.unit_matching = track_units(
                project_loader,
                entity_selector_compute.value,
                date_selector_compute.value,
                dissimilarity.value,
            )
            track_units_button.style.button_color = original_color

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
                num_matches = sum([len(matches) for g, matches in unit_matching.identified_units.items()])
                matched_units.value = str(int(num_matches))

        @view_plot.output.capture()
        def on_plot_button(change):
            original_color = plot_button.style.button_color
            plot_button.style.button_color = "yellow"
            plot_matched_units()
            view_plot.children = (
                list(view_plot.children[:-2]) + [output_waveforms, output_ratemaps] + list(view_plot.children[-2:])
            )
            plot_button.style.button_color = original_color

        def on_show_hide_plot_button(change):
            main_box_plot.children = main_box_plot.children[:-2]

        @view_plot.output.capture()
        def save_all_to_nwb(change):
            print("Saving all matches to NWB")
            original_color = save_all_nwb_button.style.button_color
            save_all_nwb_button.style.button_color = "yellow"
            for _, unit_matching in self.unit_matching.items():
                for action_id in unit_matching.action_list:
                    print(f"Saving action id: {action_id}")
                    save_to_nwb(
                        project_loader,
                        action_id,
                        unit_matching,
                    )
            save_all_nwb_button.style.button_color = original_color
            print("Done!")

        @view_plot.output.capture()
        def save_selected_to_nwb(change):
            print("Saving selected entities/dates to NWB")
            original_color = save_selected_nwb_button.style.button_color
            save_selected_nwb_button.style.button_color = "yellow"
            for _, unit_matching in self.unit_matching.items():
                for action_id in unit_matching.action_list:
                    entity, date, _ = action_id.split("-")
                    if entity in entity_selector_view.value and date in date_selector_view.value:
                        save_to_nwb(
                            project_loader,
                            action_id,
                            unit_matching,
                        )
            print("Done!")
            save_selected_nwb_button.style.button_color = original_color

        def plot_matched_units():
            entity = entity_selector_view.value
            date = date_selector_view.value
            unit_matching = self.unit_matching.get((entity, date))
            if unit_matching is None:
                print(f"No matching found for {entity} on {date}")
            else:
                figure_waveforms, _ = plt.subplots(figsize=(10, 5))
                plot_unit_templates(unit_matching, fig=figure_waveforms)
                # unit_matching.plot_matches(fig=figure_waveforms)
                output_waveforms.clear_output()
                with output_waveforms:
                    figure_waveforms.show()
                    show_inline_matplotlib_plots()
                figure_ratemaps, _ = plt.subplots(figsize=(10, 3))
                plot_rate_maps(self.project_loader, unit_matching, fig=figure_ratemaps)
                output_ratemaps.clear_output()
                with output_ratemaps:
                    figure_ratemaps.show()
                    show_inline_matplotlib_plots()

        entity_selector_view.observe(on_entity_view_change, names="value")
        date_selector_view.observe(on_date_view_change, names="value")
        track_units_button.on_click(on_track_units)
        save_selected_nwb_button.on_click(save_selected_to_nwb)
        save_all_nwb_button.on_click(save_all_to_nwb)
        plot_button.on_click(on_plot_button)
        show_hide_plot_button.on_click(on_show_hide_plot_button)

        super().__init__(children=(view_compute, view_plot))
        self.titles = ["Compute", "Plot"]

        def on_tab_change(change):
            entity = entity_selector_view.value
            dates = df_meta[df_meta["entity"] == entity]["date"].unique()
            date_selector_view.options = dates

        self.observe(on_tab_change)
