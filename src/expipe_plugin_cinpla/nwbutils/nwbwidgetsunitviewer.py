# -*- coding: utf-8 -*-
import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from ipywidgets import Layout, interactive_output

color_wheel = plt.rcParams["axes.prop_cycle"].by_key()["color"]


class UnitWaveformsWidget(widgets.VBox):
    def __init__(
        self,
        units: "pynwb.misc.Units",
    ):
        super().__init__()

        self.units = units

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

        out_fig = interactive_output(self.show_unit_waveforms, self.controls)

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

    def show_unit_waveforms(self, unit_index=None, ax=None):
        """
        Shows unit waveforms.

        Parameters
        ----------
        unit_index: int
            Index of the unit to show.
        ax: matplotlib.pyplot.Axes
            Axes to plot the waveforms on.

        Returns
        -------
        matplotlib.pyplot.Figure

        """
        units = self.units
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
        units: "pynwb.misc.Units",
        spatial_series: "pynwb.behavior.SpatialSeries" = None,
    ):
        super().__init__()

        self.units = units

        if spatial_series is None:
            self.spatial_series = get_spatial_series(self.units)
            if len(self.spatial_series) == 0:
                self.children = [widgets.HTML("No sparial series present")]
                return
            elif len(self.spatial_series) > 1:
                self.spatial_series_selector = widgets.Dropdown(
                    options=list(self.spatial_series.keys()),
                    description="",
                    layout=dict(width="200px", display="flex", justify_content="flex-start"),
                )
            else:
                self.spatial_series_selector = widgets.Text(
                    value=list(self.spatial_series.keys())[0],
                    description="",
                    layout=dict(width="200px", display="flex", justify_content="flex-start"),
                    disabled=True,
                )
        self.units = units

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
        self.smoothing_slider = widgets.FloatSlider(
            value=0.03,
            min=0,
            max=0.2,
            step=0.01,
            description="Smoothing:",
        )
        self.bin_size_slider = widgets.FloatSlider(
            value=0.02,
            min=0.01,
            max=0.2,
            step=0.01,
            description="Bin size:",
        )
        self.flip_y_axis = widgets.Checkbox(
            value=False,
            description="Flip y-axis",
        )
        spatial_series_label = widgets.Label("Spatial Series:")
        top_panel = widgets.VBox(
            [
                self.unit_list,
                self.unit_name_text,
                self.unit_info_text,
                widgets.HBox([spatial_series_label, self.spatial_series_selector]),
                widgets.HBox([self.smoothing_slider, self.bin_size_slider, self.flip_y_axis]),
            ]
        )
        self.controls = dict(
            unit_index=self.unit_list,
            spatial_series_selector=self.spatial_series_selector,
            smoothing_slider=self.smoothing_slider,
            bin_size_slider=self.bin_size_slider,
            flip_y_axis=self.flip_y_axis,
        )
        self.rate_maps, self.extent = None, None
        self.compute_rate_maps()

        out_fig = interactive_output(self.show_unit_rate_maps, self.controls)

        self.children = [top_panel, out_fig]

        self.layout = Layout(width="100%")

        self.unit_list.observe(self.on_unit_change, names="value")
        self.spatial_series_selector.observe(self.on_spatial_series_change, names="value")
        self.smoothing_slider.observe(self.on_smoothing_change, names="value")
        self.bin_size_slider.observe(self.on_bin_size_change, names="value")
        self.on_unit_change(None)

    def on_unit_change(self, change):
        unit_name = self.units["unit_name"][self.unit_list.value]
        unit_group = self.units["group"][self.unit_list.value]

        self.unit_name_text.value = f"Unit: {unit_name}"
        unit_info_text = f"Group: {unit_group}"
        if "original_cluster_id" in self.units.colnames:
            unit_info_text += f" - Phy ID: {int(self.units['original_cluster_id'][self.unit_list.value])}"
        self.unit_info_text.value = unit_info_text

    def compute_rate_maps(self):
        import pynapple as nap
        from spatial_maps import SpatialMap

        from ..tools.data_processing import process_tracking

        spatial_series = self.spatial_series[self.spatial_series_selector.value]
        x, y = spatial_series.data[:].T
        t = spatial_series.timestamps[:]

        # Remove NaNs and zeros
        x, y, t = process_tracking(x, y, t)

        nap_position = nap.TsdFrame(
            d=np.array([x, y]).T,
            t=t,
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
        nap_units = nap.TsGroup({i: np.array(unit_spike_times[i]) for i in range(len(unit_names))})
        self.nap_position = nap_position
        self.nap_units = nap_units

        sm = SpatialMap(
            bin_size=self.bin_size_slider.value,
            smoothing=self.smoothing_slider.value,
        )
        rate_maps = []
        for unit_index in self.units.id.data:
            rate_map = sm.rate_map(x, y, t, unit_spike_times[unit_index])
            rate_maps.append(rate_map.T)
        self.rate_maps = np.array(rate_maps)

    def on_spatial_series_change(self, change):
        self.compute_rate_maps()
        self.show_unit_rate_maps(self.unit_list.value)

    def on_bin_size_change(self, change):
        self.compute_rate_maps()
        self.show_unit_rate_maps(self.unit_list.value)

    def on_smoothing_change(self, change):
        self.compute_rate_maps()
        self.show_unit_rate_maps(self.unit_list.value)

    def show_unit_rate_maps(
        self,
        unit_index=None,
        spatial_series_selector=None,
        smoothing_slider=None,
        bin_size_slider=None,
        flip_y_axis=None,
        axs=None,
    ):
        """
        Shows unit rate maps.

        Parameters
        ----------
        unit_index: int
            Index of the unit to show.
        spatial_series_selector: widget
            Name of the spatial series to use.
        smoothing_slider: widget
            Smoothing factor for the rate map.
        bin_size_slider: widget
            Bin size for the rate map.
        flip_y_axis: widget
            Whether to flip the y-axis.
        axs: matplotlib.pyplot.Axes
            Axes to plot the rate maps on.

        Returns
        -------
        matplotlib axes
        """
        if unit_index is None:
            return

        legend_kwargs = dict()
        figsize = (10, 7)

        if axs is None:
            fig, axs = plt.subplots(figsize=figsize, ncols=2, sharex=True, sharey=True)
            if hasattr(fig, "canvas"):
                fig.canvas.header_visible = False
            else:
                legend_kwargs.update(bbox_to_anchor=(1.01, 1))
        origin = "lower" if not self.flip_y_axis.value else "upper"
        axs[0].imshow(self.rate_maps[unit_index], cmap="viridis", origin=origin, aspect="auto", extent=self.extent)
        axs[0].set_xlabel("x")
        axs[0].set_ylabel("y")

        tracking_x = self.nap_position["x"]
        tracking_y = self.nap_position["y"]
        spk_pos = self.nap_units[unit_index].value_from(self.nap_position)
        spike_pos_x = spk_pos["x"]
        spike_pos_y = spk_pos["y"]
        if self.flip_y_axis.value:
            tracking_y = 1 - tracking_y
            spike_pos_y = 1 - spike_pos_y
        axs[1].plot(tracking_x, tracking_y, color="grey")
        axs[1].plot(spike_pos_x, spike_pos_y, "o", color="red", markersize=5, alpha=0.5)
        axs[1].set_xlabel("x")
        axs[1].set_ylabel("y")
        fig.tight_layout()

        return axs


class UnitSummaryWidget(widgets.VBox):
    def __init__(
        self,
        units: "pynwb.misc.Units",
    ):
        super().__init__()

        self.units = units
        self.spatial_series = get_spatial_series(self.units)
        self.spatial_series_selector = widgets.SelectMultiple(
            options=sorted(list(self.spatial_series.keys())),
            disabled=False,
            layout=dict(width="200px", display="flex", justify_content="flex-start"),
        )
        if len(self.spatial_series) == 2:
            self.spatial_series_selector.value = list(self.spatial_series.keys())

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
        self.smoothing_slider = widgets.FloatSlider(
            value=0.03,
            min=0,
            max=0.2,
            step=0.01,
            description="Smoothing:",
        )
        self.bin_size_slider = widgets.FloatSlider(
            value=0.02,
            min=0.01,
            max=0.2,
            step=0.01,
            description="Bin size:",
        )

        spatial_series_label = widgets.Label("Spatial Series:")
        top_panel = widgets.VBox(
            [
                self.unit_list,
                self.unit_name_text,
                self.unit_info_text,
                widgets.HBox([spatial_series_label, self.spatial_series_selector]),
                widgets.HBox([self.smoothing_slider, self.bin_size_slider]),
            ]
        )
        self.controls = dict(
            unit_index=self.unit_list,
            spatial_series_selector=self.spatial_series_selector,
            smoothing_slider=self.smoothing_slider,
            bin_size_slider=self.bin_size_slider,
        )

        out_fig = interactive_output(self.show_unit_summary, self.controls)

        self.children = [top_panel, out_fig]

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

    def show_unit_summary(self, unit_index, spatial_series_selector=None, smoothing_slider=None, bin_size_slider=None):
        """
        Shows unit summary.

        Parameters
        ----------
        unit_index: int
            Index of the unit to show.
        spatial_series_selector: widget
            Name of the spatial series to use.
        smoothing_slider: widget
            Smoothing factor for the rate map.
        bin_size_slider: widget
            Bin size for the rate map.

        Returns
        -------
        matplotlib axes

        """
        from head_direction import head_direction, head_direction_rate
        from spatial_maps import SpatialMap

        from ..tools.data_processing import _cut_to_same_len, process_tracking
        from ..tools.plotting_utils import spike_track

        sm = SpatialMap(
            bin_size=self.bin_size_slider.value,
            smoothing=self.smoothing_slider.value,
        )

        fig, axs = plt.subplots(nrows=2, ncols=4)
        axs[0, 3].remove()
        axs[0, 3] = plt.subplot(244, projection="polar")

        spike_train = self.units["spike_times"][unit_index][:]
        group = self.units["group"][unit_index]
        if "original_cluster_id" in self.units.colnames:
            phy_id = int(self.units["original_cluster_id"][unit_index])
        else:
            phy_id = None
        unit_name = self.units["unit_name"][unit_index]

        # ratemap
        if len(self.spatial_series_selector.value) == 1:
            spatial_series1 = self.spatial_series[self.spatial_series_selector.value[0]]
            x1, y1 = spatial_series1.data[:].T
            t1 = spatial_series1.timestamps[:]
            x1, y1, t1 = process_tracking(x1, y1, t1)
            x, y, t = x1, y1, t1
        elif len(self.spatial_series_selector.value) == 2:
            spatial_series1 = self.spatial_series[self.spatial_series_selector.value[0]]
            x1, y1 = spatial_series1.data[:].T
            t1 = spatial_series1.timestamps[:]
            spatial_series2 = self.spatial_series[self.spatial_series_selector.value[1]]
            x2, y2 = spatial_series2.data[:].T
            t2 = spatial_series2.timestamps[:]
            x2, y2, t2 = process_tracking(x2, y2, t2)
            x1, y1, t1, x2, y2, t2 = _cut_to_same_len(x1, y1, t1, x2, y2, t2)
            x = np.mean([x1, x2], axis=0)
            y = np.mean([y1, y2], axis=0)
            t = t1

        ratemap = sm.rate_map(x, y, t, spike_train)
        axs[0, 0].imshow(ratemap.T, origin="lower")
        title = f"grp={group}, unit={unit_name}"
        if phy_id is not None:
            title += f", phy_id={phy_id}"
        title += f", #spikes={spike_train.shape[0]}"

        # spikes and tracking
        axs[0, 1] = spike_track(x, y, t, spike_train, axs[0, 1], spines=False)
        axs[0, 1].axis("equal")

        # occupancy
        occupancymap = sm.occupancy_map(x, y, t)
        axs[0, 2].imshow(occupancymap.T, origin="lower")
        axs[0, 2].set_title("occupancy")

        if len(self.spatial_series_selector.value) != 2:
            axs[0, 3].set_title("Select 2 spatial series for head direction")
        else:
            ang, ang_t = head_direction(x1, y1, x2, y2, t1)
            ang_bin, ang_rate = head_direction_rate(spike_train, ang, ang_t)
            axs[0, 3].plot(ang_bin, ang_rate)
            axs[0, 3].set_title("Head direction")

        waveform = self.units.waveform_mean[unit_index]
        if "waveform_sd" in self.units.colnames:
            waveform_sd = self.units.waveform_sd[unit_index]
        else:
            waveform_sd = None
        min_max = np.min(waveform), np.max(waveform)
        for i, wf in enumerate(waveform.T):
            axs[1, i].plot(waveform[:, i], color="C0")
            axs[1, i].set_ylim(*min_max)
            if waveform_sd is not None:
                wf_sd = waveform_sd[:, i]
                axs[1, i].fill_between(np.arange(len(wf)), wf - wf_sd, wf + wf_sd, alpha=0.2, color="C0")
        axs[1, 0].set_ylabel("Mean waveform")

        fig.suptitle(title)

        return axs


def get_spatial_series(units):
    from pynwb.behavior import SpatialSeries

    spatial_series = dict()
    nwbfile = units.get_ancestor("NWBFile")
    for item in nwbfile.all_children():
        if isinstance(item, SpatialSeries):
            spatial_series[item.name] = item
    return spatial_series


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
    units_view["Unit Summary"] = UnitSummaryWidget
    units_view.move_to_end("table")

    custom_neurodata_vis_spec[Units] = units_view

    return custom_neurodata_vis_spec
