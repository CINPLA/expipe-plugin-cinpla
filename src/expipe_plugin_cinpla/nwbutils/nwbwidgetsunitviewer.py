from functools import partial
import numpy as np
import ipywidgets as widgets
from ipywidgets import Layout, interactive_output
from pynwb.misc import Units
from pynwb.behavior import SpatialSeries

import matplotlib.pyplot as plt

from nwbwidgets.view import default_neurodata_vis_spec


color_wheel = plt.rcParams["axes.prop_cycle"].by_key()["color"]


class UnitWaveformsWidget(widgets.VBox):
    def __init__(
        self,
        units: Units,
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
        self.unit_group_text = widgets.Label("Group:     ", layout=dict(width="200px"))
        unit_controls = widgets.HBox([self.unit_list, self.unit_name_text, self.unit_group_text])
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
        self.unit_group_text.value = f"Group: {unit_group}"


def show_unit_waveforms(units: Units, unit_index=None, ax=None):
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


class UnitRateMapWidget(widgets.VBox):
    def __init__(
        self,
        units: Units,
        spatial_series: SpatialSeries = None,
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
        self.unit_group_text = widgets.Label("Group:     ", layout=dict(width="200px"))
        self.num_bins_slider = widgets.IntSlider(
            value=30,
            min=5,
            max=100,
            step=1,
            description="Bins:",
        )
        top_panel = widgets.VBox(
            [
                self.unit_list,
                self.unit_name_text,
                self.unit_group_text,
                self.spatial_series_selector,
                self.num_bins_slider,
            ]
        )
        self.controls = dict(
            unit_index=self.unit_list,
            spatial_series_selector=self.spatial_series_selector,
            num_bins_slider=self.num_bins_slider,
        )
        self.rate_maps, self.binsxy, self.extent = None, None, None
        self.compute_rate_maps()

        out_fig = interactive_output(self.show_unit_rate_maps, self.controls)

        self.children = [top_panel, out_fig]

        self.layout = Layout(width="100%")

        self.unit_list.observe(self.on_unit_change, names="value")
        self.spatial_series_selector.observe(self.on_spatial_series_change, names="value")
        self.num_bins_slider.observe(self.on_num_bins_change, names="value")
        self.on_unit_change(None)

    def on_unit_change(self, change):
        unit_name = self.units["unit_name"][self.unit_list.value]
        unit_group = self.units["group"][self.unit_list.value]

        self.unit_name_text.value = f"Unit: {unit_name}"
        self.unit_group_text.value = f"Group: {unit_group}"

    def get_spatial_series(self):
        spatial_series = dict()
        nwbfile = self.units.get_ancestor("NWBFile")
        for item in nwbfile.all_children():
            if isinstance(item, SpatialSeries):
                spatial_series[item.name] = item
        return spatial_series

    def compute_rate_maps(self):
        import pynapple as nap

        spatial_series = self.spatial_series[self.spatial_series_selector.value]

        # Remove NaNs
        mask = np.logical_not(np.isnan(spatial_series.data)).T
        mask_and = np.logical_and(mask[0], mask[1])

        nap_position = nap.TsdFrame(
            d=spatial_series.data[mask_and],
            t=spatial_series.timestamps[mask_and],
            columns=["x", "y"],
        )
        self.extent = (
            np.min(nap_position["x"]),
            np.max(nap_position["x"]),
            np.min(nap_position["y"]),
            np.max(nap_position["y"]),
        )

        # Load the unit spike times into a pynapple TsGroup
        unit_names = self.units["unit_name"][:]
        unit_spike_times = self.units["spike_times"][:]
        nap_units = nap.TsGroup({i: unit_spike_times[i] for i in range(len(unit_names))})
        self.rate_maps, self.binsxy = nap.compute_2d_tuning_curves(nap_units, nap_position, self.num_bins_slider.value)
        self.nap_position = nap_position
        self.nap_units = nap_units

    def on_spatial_series_change(self, change):
        self.compute_rate_maps()

    def on_num_bins_change(self, change):
        self.compute_rate_maps()

    def show_unit_rate_maps(self, unit_index=None, spatial_series_selector=None, num_bins_slider=None, axs=None):
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
        axs[0].imshow(self.rate_maps[unit_index], cmap="viridis", origin="lower", aspect="auto", extent=self.extent)
        axs[0].set_xlabel("x")
        axs[0].set_ylabel("y")

        axs[1].plot(self.nap_position["y"], self.nap_position["x"], color="grey")
        spk_pos = self.nap_units[unit_index].value_from(self.nap_position)
        axs[1].plot(spk_pos["y"], spk_pos["x"], "o", color="red", markersize=5, alpha=0.5)
        axs[1].set_xlabel("x")
        axs[1].set_ylabel("y")
        fig.tight_layout()

        return axs


def get_custom_spec():
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

    # TODO: add Place Fields widget

    return custom_neurodata_vis_spec
