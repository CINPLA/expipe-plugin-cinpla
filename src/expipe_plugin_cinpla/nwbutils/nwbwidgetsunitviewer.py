# -*- coding: utf-8 -*-
from functools import partial

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from ipywidgets import Layout, interactive_output

from spatial_maps import SpatialMap

color_wheel = plt.rcParams["axes.prop_cycle"].by_key()["color"]


class UnitWaveformsWidget(widgets.VBox):
    def __init__(
        self,
        units: "pynwb.misc.Units",
    ):
        super().__init__()

        self.units = units

        self.progress_bar = widgets.HBox()
        unit_indices = units.id.data[:]
        self.unit_list = widgets.Dropdown(
            options=unit_indices,
            default=unit_indices[0],
            description="",
            layout=dict(width="200px", display="flex", justify_content="flex-start"),
        )

        self.unit_name_text = widgets.Label("Unit:    ", layout=dict(width="200px"))
        unit_info_text = "Group:     "
        if "original_cluster_id" in self.units.colnames:
            unit_info_text += " - Phy ID:      "
        self.unit_info_text = widgets.Label(unit_info_text, layout=dict(width="90%"))

        unit_controls = widgets.HBox([self.unit_list, self.unit_name_text, self.unit_info_text])
        self.controls = dict(unit_index=self.unit_list)

        plot_func = partial(show_unit_waveforms, units=self.units)

        out_fig = interactive_output(plot_func, self.controls)

        self.children = [unit_controls, out_fig]

        self.layout = Layout(width="100%")

        self.unit_list.observe(self.on_unit_change, names="value")
        self.on_unit_change(None)

    def on_unit_change(self, change):
        unit_name = self.units["unit_name"][self.unit_list.value]
        unit_group = self.units["group"][self.unit_list.value]

        self.unit_name_text.value = f"Unit: {unit_name}"
        unit_info_text = f"Group: {unit_group}"
        if "original_cluster_id" in self.units.colnames:
            unit_info_text += f" - Phy ID: {int(self.units['original_cluster_id'][self.unit_list.value])}"
        self.unit_info_text.value = unit_info_text


def show_unit_waveforms(units: "pynwb.mis.Units", unit_index=None, ax=None):
    """
    TODO: add docstring

    Returns
    -------
    matplotlib.pyplot.Figure

    """
    if "waveform_mean" not in units.colnames:
        return ax

    if unit_index is None:
        return

    legend_kwargs = dict()
    figsize = (10, 7)
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
        if hasattr(fig, "canvas"):
            fig.canvas.header_visible = False
        else:
            legend_kwargs.update(bbox_to_anchor=(1.01, 1))
    color = color_wheel[unit_index % len(color_wheel)]
    waveform = units.waveform_mean[unit_index]
    if "waveform_sd" in units.colnames:
        waveform_sd = units.waveform_sd[unit_index]
    else:
        waveform_sd = None
    ptp = 2 * np.ptp(waveform)

    for i, wf in enumerate(waveform.T):
        offset = i * ptp
        ax.plot(wf + offset, color=color)
        if waveform_sd is not None:
            wf_sd = waveform_sd[:, i]
            ax.fill_between(
                np.arange(len(wf)),
                wf - wf_sd + offset,
                wf + wf_sd + offset,
                alpha=0.2,
                color=color,
            )

    return ax


# TODO: use SpatialMaps instead
class UnitRateMapWidget(widgets.VBox):
    def __init__(
        self,
        units: "pynwb.mis.Units",
        spatial_series: "SpatialSeries" = None,
    ):
        super().__init__()

        self.units = units

        if spatial_series is None:
            self.spatial_series = self.get_spatial_series()
            if len(self.spatial_series) == 0:
                self.children = [widgets.HTML("No sparial series present")]
                return
            elif len(self.spatial_series) > 1:
                self.spatial_series_selector = widgets.Dropdown(
                    options=list(self.spatial_series.keys()),
                    description="Spatial Series:",
                    layout=dict(width="200px", display="flex", justify_content="flex-start"),
                )
            else:
                self.spatial_series_selector = widgets.Text(
                    value=list(self.spatial_series.keys())[0],
                    description="Spatial Series:",
                    layout=dict(width="200px", display="flex", justify_content="flex-start"),
                    disabled=True,
                )
        self.units = units

        self.progress_bar = widgets.HBox()
        unit_indices = units.id.data[:]
        self.unit_list = widgets.Dropdown(
            options=unit_indices,
            default=unit_indices[0],
            description="",
            layout=dict(width="200px", display="flex", justify_content="flex-start"),
        )

        self.unit_name_text = widgets.Label("Unit:    ", layout=dict(width="200px"))
        unit_info_text = "Group:     "
        if "original_cluster_id" in self.units.colnames:
            unit_info_text += " - Phy ID:      "
        self.unit_info_text = widgets.Label(unit_info_text, layout=dict(width="90%"))
        self.bin_size_slider = widgets.FloatSlider(
            value=0.02,
            min=0,
            max=1,
            step=0.01,
            description="Bin size:",
        )
        self.smoothing_slider = widgets.FloatSlider(
            value=0.05,
            min=0,
            max=1,
            step=0.01,
            description="Smoothing:",
        )
        top_panel = widgets.VBox(
            [
                self.unit_list,
                self.unit_name_text,
                self.unit_info_text,
                self.spatial_series_selector,
                self.bin_size_slider,
                self.smoothing_slider,
            ]
        )
        self.controls = dict(
            unit_index=self.unit_list
        )
        self.instantiate_spatial_map()
        self.rate_maps = None
        self.compute_rate_maps()

        out_fig = interactive_output(self.show_unit_rate_maps, self.controls)

        self.children = [top_panel, out_fig]

        self.layout = Layout(width="100%")

        self.unit_list.observe(self.on_unit_change, names="value")
        self.spatial_series_selector.observe(self.on_spatial_series_change, names="value")
        self.bin_size_slider.observe(self.on_bin_size_change, names="value")
        self.smoothing_slider.observe(self.on_smoothing_change, names="value")
        self.on_unit_change(None)

    def compute_rate_maps(self):
        print("Computing rate maps")
        self.spatial_map = SpatialMap(
            smoothing=self.smoothing_slider.value,
            bin_size=self.bin_size_slider.value,
        )
        rate_maps = []
        spatial_series = self.spatial_series[self.spatial_series_selector.value]
        x, y = spatial_series.data[:].T
        t = spatial_series.timestamps[:]
        for unit_index in range(len(self.units.id.data)):
            spike_times = self.units[unit_index]["spike_times"][:][0]

            ratemap = spatial_map.rate_map(x, y, t, spike_train)
            rate_maps.append(ratemap)
        self.rate_maps = rate_maps

    def on_unit_change(self, change):
        unit_name = self.units["unit_name"][self.unit_list.value]
        unit_group = self.units["group"][self.unit_list.value]

        self.unit_name_text.value = f"Unit: {unit_name}"
        unit_info_text = f"Group: {unit_group}"
        if "original_cluster_id" in self.units.colnames:
            unit_info_text += f" - Phy ID: {int(self.units['original_cluster_id'][self.unit_list.value])}"
        self.unit_info_text.value = unit_info_text

    def get_spatial_series(self):
        from pynwb.behavior import SpatialSeries

        spatial_series = dict()
        nwbfile = self.units.get_ancestor("NWBFile")
        for item in nwbfile.all_children():
            if isinstance(item, SpatialSeries):
                spatial_series[item.name] = item
        return spatial_series

    def on_spatial_series_change(self, change):
        self.compute_rate_maps()
        self.show_unit_rate_maps(self.unit_list.value)

    def on_bin_size_change(self, change):
        self.compute_rate_maps()
        self.show_unit_rate_maps(self.unit_list.value)

    def on_smoothing_change(self, change):
        self.compute_rate_maps()
        self.show_unit_rate_maps(self.unit_list.value)

    def show_unit_rate_maps(self, unit_index=None, axs=None):
        """
        Shows unit rate maps.

        Returns
        -------
        matplotlib.pyplot.Figure

        """
        if unit_index is None:
            return
        if self.rate_maps is None:
            return

        legend_kwargs = dict()
        figsize = (10, 7)
        if axs is None:
            fig, axs = plt.subplots(figsize=figsize, ncols=2)
            if hasattr(fig, "canvas"):
                fig.canvas.header_visible = False
            else:
                legend_kwargs.update(bbox_to_anchor=(1.01, 1))
        axs[0].imshow(self.rate_maps[unit_index], cmap="viridis", origin="lower", aspect="auto")
        axs[0].set_xlabel("x")
        axs[0].set_ylabel("y")
        axs[1] = spike_track(x, y, t, spike_train, axs[1], spines=False)
        fig.tight_layout()

        return axs


def get_custom_spec():
    from nwbwidgets.view import default_neurodata_vis_spec
    from pynwb.misc import Units

    custom_neurodata_vis_spec = default_neurodata_vis_spec.copy()

    # remove irrelevant widgets
    units_view = custom_neurodata_vis_spec[Units].copy()
    if "Grouped PSTH" in units_view:
        units_view.pop("Grouped PSTH")
    if "Raster Grid" in units_view:
        units_view.pop("Raster Grid")
    if "Tuning Curves" in units_view:
        units_view.pop("Tuning Curves")
    if "Combined" in units_view:
        units_view.pop("Combined")

    # add custom widgets
    units_view["Waveforms"] = UnitWaveformsWidget
    units_view["Rate Maps"] = UnitRateMapWidget
    units_view.move_to_end("table")

    custom_neurodata_vis_spec[Units] = units_view

    return custom_neurodata_vis_spec
