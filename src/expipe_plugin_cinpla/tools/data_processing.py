# -*- coding: utf-8 -*-
# This is work in progress,
import pathlib
import warnings

import expipe
import numpy as np
import spatial_maps as sp

from expipe_plugin_cinpla.tools.data_loader import (
    get_channel_groups,
    get_duration,
    load_epochs,
    load_leds,
    load_lfp,
    load_spiketrains,
)


def view_active_channels(action, sorter):
    path = action.data_path()
    sorter_path = path / "spikeinterface" / sorter / "phy"
    return np.load(sorter_path / "channel_map_si.npy")


def _cut_to_same_len(*args):
    out = []
    lens = []
    for arg in args:
        lens.append(len(arg))
    minlen = min(lens)
    for arg in args:
        out.append(arg[:minlen])
    return out


def velocity_filter(x, y, t, threshold):
    """
    Removes values above threshold
    Parameters
    ----------
    x : quantities.Quantity array in m
        1d vector of x positions
    y : quantities.Quantity array in m
        1d vector of y positions
    t : quantities.Quantity array in s
        1d vector of times at x, y positions
    threshold : float
    """
    assert len(x) == len(y) == len(t), "x, y, t must have same length"
    vel = np.gradient([x, y], axis=1) / np.gradient(t)
    speed = np.linalg.norm(vel, axis=0)
    speed_mask = speed < threshold
    speed_mask = np.append(speed_mask, 0)
    x = x[np.where(speed_mask)]
    y = y[np.where(speed_mask)]
    t = t[np.where(speed_mask)]
    return x, y, t


def interp_filt_position(x, y, tm, fs=100, f_cut=10):
    """
    rapid head movements will contribute to velocity artifacts,
    these can be removed by low-pass filtering
    see http://www.ncbi.nlm.nih.gov/pmc/articles/PMC1876586/
    code addapted from Espen Hagen
    Parameters
    ----------
    x : quantities.Quantity array in m
        1d vector of x positions
    y : quantities.Quantity array in m
        1d vector of y positions
    tm : quantities.Quantity array in s
        1d vector of times at x, y positions
    fs : quantities scalar in Hz
        return radians
    Returns
    -------
    out : angles, resized t
    """
    import scipy.signal as ss

    assert len(x) == len(y) == len(tm), "x, y, t must have same length"
    t = np.arange(tm.min(), tm.max() + 1.0 / fs, 1.0 / fs)
    x = np.interp(t, tm, x)
    y = np.interp(t, tm, y)
    # rapid head movements will contribute to velocity artifacts,
    # these can be removed by low-pass filteringpar
    # see http://www.ncbi.nlm.nih.gov/pmc/articles/PMC1876586/
    # code addapted from Espen Hagen
    b, a = ss.butter(N=1, Wn=f_cut * 2 / fs)
    # zero phase shift filter
    x = ss.filtfilt(b, a, x)
    y = ss.filtfilt(b, a, y)
    # we tolerate small interpolation errors
    x[(x > -1e-3) & (x < 0.0)] = 0.0
    y[(y > -1e-3) & (y < 0.0)] = 0.0

    return x, y, t


def rm_nans(*args):
    """
    Removes nan from all corresponding arrays
    Parameters
    ----------
    args : arrays, lists or quantities which should have removed nans in
           all the same indices
    Returns
    -------
    out : args with removed nans
    """
    nan_indices = []
    for arg in args:
        nan_indices.extend(np.where(np.isnan(arg))[0].tolist())
    nan_indices = np.unique(nan_indices)
    out = []
    for arg in args:
        out.append(np.delete(arg, nan_indices))
    return out


def filter_xy_zero(x, y, t):
    (idxs,) = np.where((x == 0) & (y == 0))
    return [np.delete(a, idxs) for a in [x, y, t]]


def filter_xy_box_size(x, y, t, box_size):
    (idxs,) = np.where((x > box_size[0]) | (x < 0) | (y > box_size[1]) | (y < 0))
    return [np.delete(a, idxs) for a in [x, y, t]]


def filter_t_zero_duration(x, y, t, duration):
    (idxs,) = np.where((t < 0) | (t > duration))
    return [np.delete(a, idxs) for a in [x, y, t]]


def load_head_direction(data_path, low_pass_frequency, box_size):
    from head_direction.head import head_direction

    x1, y1, t1, x2, y2, t2, stop_time = load_leds(data_path)

    x1, y1, t1 = process_tracking(x1, y1, t1, stop_time, low_pass_frequency)
    x2, y2, t2 = process_tracking(x2, y2, t2, stop_time, low_pass_frequency)

    x1, y1, t1, x2, y2, t2 = _cut_to_same_len(x1, y1, t1, x2, y2, t2)

    check_valid_tracking(x1, y1, box_size)
    check_valid_tracking(x2, y2, box_size)

    angles, times = head_direction(x1, y1, x2, y2, t1)

    return angles, times


def process_tracking(x, y, t, stop_time=None, low_pass_frequency=6):
    xp, yp, tp = rm_nans(x, y, t)
    if stop_time is None:
        stop_time = tp[-1]

    xp, yp, tp = filter_t_zero_duration(xp, yp, tp, stop_time)

    # OE saves 0.0 when signal is lost, these can be removed
    xp, yp, tp = filter_xy_zero(xp, yp, tp)

    sampling_rate = 1 / np.median(np.diff(tp))

    if low_pass_frequency is not None:
        xp, yp, tp = interp_filt_position(xp, yp, tp, fs=sampling_rate, f_cut=low_pass_frequency)

    return xp, yp, tp


def check_valid_tracking(x, y, box_size):
    if np.isnan(x).any() and np.isnan(y).any():
        raise ValueError(
            "nans found in  position, " + "x nans = %i, y nans = %i" % (sum(np.isnan(x)), sum(np.isnan(y)))
        )

    if x.min() < 0 or x.max() > box_size[0] or y.min() < 0 or y.max() > box_size[1]:
        warnings.warn(
            "Invalid values found "
            + f"outside box: min [x, y] = [{x.min()}, {y.min()}], "
            + f"max [x, y] = [{x.max()}, {y.max()}]"
        )


def load_tracking(data_path, low_pass_frequency=6, box_size=[1, 1], velocity_threshold=5):
    x1, y1, t1, x2, y2, t2, stop_time = load_leds(data_path)
    x1, y1, t1 = rm_nans(x1, y1, t1)
    x2, y2, t2 = rm_nans(x2, y2, t2)

    x1, y1, t1 = filter_t_zero_duration(x1, y1, t1, stop_time)
    x2, y2, t2 = filter_t_zero_duration(x2, y2, t2, stop_time)

    # select data with least nan
    if len(x1) > len(x2):
        x, y, t = x1, y1, t1
    else:
        x, y, t = x2, y2, t2

    # OE saves 0.0 when signal is lost, these can be removed
    x, y, t = filter_xy_zero(x, y, t)

    # x, y, t = filter_xy_box_size(x, y, t, box_size)

    # remove velocity artifacts
    x, y, t = velocity_filter(x, y, t, velocity_threshold)

    sampling_rate = 1 / np.median(np.diff(t))
    x, y, t = interp_filt_position(x, y, t, fs=sampling_rate, f_cut=low_pass_frequency)

    check_valid_tracking(x, y, box_size)

    vel = np.gradient([x, y], axis=1) / np.gradient(t)
    speed = np.linalg.norm(vel, axis=0)
    x, y, t, speed = np.array(x), np.array(y), np.array(t), np.array(speed)
    return x, y, t, speed


def sort_by_cluster_id(spike_trains):
    if len(spike_trains) == 0:
        return spike_trains
    if "name" not in spike_trains[0].annotations:
        print("Unable to get cluster_id, save with phy to create")
    sorted_sptrs = sorted(spike_trains, key=lambda x: str(x.annotations["name"]))
    return sorted_sptrs


def get_unit_id(unit):
    return str(int(unit.annotations["name"]))


class Template:
    def __init__(self, sptr):
        self.data = np.array(sptr.annotations["waveform_mean"])
        self.sampling_rate = float(sptr.sampling_rate)


class DataProcessor:
    def __init__(self, project, stim_mask=False, baseline_duration=None, stim_channels=None, **kwargs):
        self._project_path = project.path
        self.params = kwargs  # TODO: remove this
        self._project = expipe.get_project(self.project_path)
        self._actions = self.project.actions
        self._entities = list(self.project.entities)
        self._spike_trains = {}
        self._templates = {}
        self._stim_times = {}
        self._unit_names = {}
        self._tracking = {}
        self._head_direction = {}
        self._lfp = {}
        self._occupancy = {}
        self._rate_maps = {}
        self._tracking_split = {}
        self._rate_maps_split = {}
        self._prob_dist = {}
        self._spatial_bins = None
        self.stim_mask = stim_mask
        self.baseline_duration = baseline_duration
        self._channel_groups = {}
        self.stim_channels = stim_channels

    @property
    def project(self):
        return self._project

    @property
    def project_path(self):
        return self._project_path

    @property
    def actions(self):
        return self._actions

    @property
    def entities(self):
        return self._entities

    def channel_groups(self, action_id):
        if action_id not in self._channel_groups:
            self._channel_groups[action_id] = get_channel_groups(self.data_path(action_id))
        return self._channel_groups[action_id]

    def data_path(self, action_id):
        return pathlib.Path(self.project_path) / "actions" / action_id / "data" / "main.nwb"

    def get_lim(self, action_id):
        stim_times = self.stim_times(action_id)
        if stim_times is None:
            if self.baseline_duration is None:
                return [0, float(get_duration(self.data_path(action_id)).magnitude)]
            else:
                return [0, float(self.baseline_duration)]
        stim_times = np.array(stim_times)
        return [stim_times.min(), stim_times.max()]

    def duration(self, action_id):
        return get_duration(self.data_path(action_id))

    def tracking(self, action_id):
        if action_id not in self._tracking:
            x, y, t, speed = load_tracking(
                self.data_path(action_id),
                low_pass_frequency=self.params["position_low_pass_frequency"],
                box_size=self.params["box_size"],
            )
            if self.stim_mask:
                t1, t2 = self.get_lim(action_id)
                mask = (t >= t1) & (t <= t2)
                x = x[mask]
                y = y[mask]
                t = t[mask]
                speed = speed[mask]
            self._tracking[action_id] = {"x": x, "y": y, "t": t, "v": speed}
        return self._tracking[action_id]

    @property
    def spatial_bins(self):
        if self._spatial_bins is None:
            box_size_, bin_size_ = sp.maps._adjust_bin_size(
                box_size=self.params["box_size"], bin_size=self.params["bin_size"]
            )
            xbins, ybins = sp.maps._make_bins(box_size_, bin_size_)
            self._spatial_bins = (xbins, ybins)
            self.box_size_, self.bin_size_ = box_size_, bin_size_
        return self._spatial_bins

    def occupancy(self, action_id):
        if action_id not in self._occupancy:
            xbins, ybins = self.spatial_bins

            occupancy_map = sp.maps._occupancy_map(
                self.tracking(action_id)["x"],
                self.tracking(action_id)["y"],
                self.tracking(action_id)["t"],
                xbins,
                ybins,
            )
            threshold = self.params.get("occupancy_threshold")
            if threshold is not None:
                occupancy_map[occupancy_map <= threshold] = 0
            self._occupancy[action_id] = occupancy_map
        return self._occupancy[action_id]

    def prob_dist(self, action_id):
        if action_id not in self._prob_dist:
            xbins, ybins = xbins, ybins = self.spatial_bins
            prob_dist = sp.stats.prob_dist(
                self.tracking(action_id)["x"], self.tracking(action_id)["y"], bins=(xbins, ybins)
            )
            self._prob_dist[action_id] = prob_dist
        return self._prob_dist[action_id]

    def tracking_split(self, action_id):
        if action_id not in self._tracking_split:
            x, y, t, v = map(self.tracking(action_id).get, ["x", "y", "t", "v"])

            t_split = t[-1] / 2
            mask_1 = t < t_split
            mask_2 = t >= t_split
            x1, y1, t1, v1 = x[mask_1], y[mask_1], t[mask_1], v[mask_1]
            x2, y2, t2, v2 = x[mask_2], y[mask_2], t[mask_2], v[mask_2]

            self._tracking_split[action_id] = {
                "x1": x1,
                "y1": y1,
                "t1": t1,
                "v1": v1,
                "x2": x2,
                "y2": y2,
                "t2": t2,
                "v2": v2,
            }
        return self._tracking_split[action_id]

    def spike_train_split(self, action_id, channel_group, unit_name):
        spikes = self.spike_train(action_id, channel_group, unit_name)
        t_split = self.duration(action_id) / 2
        spikes_1 = spikes[spikes < t_split]
        spikes_2 = spikes[spikes >= t_split]
        return spikes_1, spikes_2, t_split

    def rate_map_split(self, action_id, channel_group, unit_name, smoothing):
        make_rate_map = False
        if action_id not in self._rate_maps_split:
            self._rate_maps_split[action_id] = {}
        if channel_group not in self._rate_maps_split[action_id]:
            self._rate_maps_split[action_id][channel_group] = {}
        if unit_name not in self._rate_maps_split[action_id][channel_group]:
            self._rate_maps_split[action_id][channel_group][unit_name] = {}
        if smoothing not in self._rate_maps_split[action_id][channel_group][unit_name]:
            make_rate_map = True

        if make_rate_map:
            xbins, ybins = self.spatial_bins
            x, y, t = map(self.tracking(action_id).get, ["x", "y", "t"])
            spikes = self.spike_train(action_id, channel_group, unit_name)
            t_split = t[-1] / 2
            mask_1 = t < t_split
            mask_2 = t >= t_split
            x_1, y_1, t_1 = x[mask_1], y[mask_1], t[mask_1]
            x_2, y_2, t_2 = x[mask_2], y[mask_2], t[mask_2]
            spikes_1 = spikes[spikes < t_split]
            spikes_2 = spikes[spikes >= t_split]
            occupancy_map_1 = sp.maps._occupancy_map(x_1, y_1, t_1, xbins, ybins)
            occupancy_map_2 = sp.maps._occupancy_map(x_2, y_2, t_2, xbins, ybins)

            spike_map_1 = sp.maps._spike_map(x_1, y_1, t_1, spikes_1, xbins, ybins)
            spike_map_2 = sp.maps._spike_map(x_2, y_2, t_2, spikes_2, xbins, ybins)

            smooth_spike_map_1 = sp.maps.smooth_map(spike_map_1, bin_size=self.bin_size_, smoothing=smoothing)
            smooth_spike_map_2 = sp.maps.smooth_map(spike_map_2, bin_size=self.bin_size_, smoothing=smoothing)
            smooth_occupancy_map_1 = sp.maps.smooth_map(occupancy_map_1, bin_size=self.bin_size_, smoothing=smoothing)
            smooth_occupancy_map_2 = sp.maps.smooth_map(occupancy_map_2, bin_size=self.bin_size_, smoothing=smoothing)

            rate_map_1 = smooth_spike_map_1 / smooth_occupancy_map_1
            rate_map_2 = smooth_spike_map_2 / smooth_occupancy_map_2
            self._rate_maps_split[action_id][channel_group][unit_name][smoothing] = [rate_map_1, rate_map_2]

        return self._rate_maps_split[action_id][channel_group][unit_name][smoothing]

    def rate_map(self, action_id, channel_group, unit_name, smoothing):
        make_rate_map = False
        if action_id not in self._rate_maps:
            self._rate_maps[action_id] = {}
        if channel_group not in self._rate_maps[action_id]:
            self._rate_maps[action_id][channel_group] = {}
        if unit_name not in self._rate_maps[action_id][channel_group]:
            self._rate_maps[action_id][channel_group][unit_name] = {}
        if smoothing not in self._rate_maps[action_id][channel_group][unit_name]:
            make_rate_map = True

        if make_rate_map:
            xbins, ybins = self.spatial_bins

            spike_map = sp.maps._spike_map(
                self.tracking(action_id)["x"],
                self.tracking(action_id)["y"],
                self.tracking(action_id)["t"],
                self.spike_train(action_id, channel_group, unit_name),
                xbins,
                ybins,
            )

            smooth_spike_map = sp.maps.smooth_map(spike_map, bin_size=self.bin_size_, smoothing=smoothing)
            smooth_occupancy_map = sp.maps.smooth_map(
                self.occupancy(action_id), bin_size=self.bin_size_, smoothing=smoothing
            )
            rate_map = smooth_spike_map / smooth_occupancy_map
            self._rate_maps[action_id][channel_group][unit_name][smoothing] = rate_map

        return self._rate_maps[action_id][channel_group][unit_name][smoothing]

    def head_direction(self, action_id):
        if action_id not in self._head_direction:
            a, t = load_head_direction(
                self.data_path(action_id),
                sampling_rate=self.params["position_sampling_rate"],
                low_pass_frequency=self.params["position_low_pass_frequency"],
                box_size=self.params["box_size"],
            )
            if self.stim_mask:
                t1, t2 = self.get_lim(action_id)
                mask = (t >= t1) & (t <= t2)
                a = a[mask]
                t = t[mask]
            self._head_direction[action_id] = {"a": a, "t": t}
        return self._head_direction[action_id]

    def lfp(self, action_id, channel_group, clean_memory=False):
        lim = self.get_lim(action_id) if self.stim_mask else None
        if clean_memory:
            return load_lfp(self.data_path(action_id), channel_group, lim)
        if action_id not in self._lfp:
            self._lfp[action_id] = {}
        if channel_group not in self._lfp[action_id]:
            self._lfp[action_id][channel_group] = load_lfp(self.data_path(action_id), channel_group, lim)
        return self._lfp[action_id][channel_group]

    def template(self, action_id, channel_group, unit_id):
        self.spike_trains(action_id)
        return Template(self._spike_trains[action_id][channel_group][unit_id])

    def spike_train(self, action_id, channel_group, unit_id):
        self.spike_trains(action_id)
        return self._spike_trains[action_id][channel_group][unit_id]

    def spike_trains(self, action_id, channel_group=None):
        if action_id not in self._spike_trains:
            self._spike_trains[action_id] = {}
        lim = self.get_lim(action_id) if self.stim_mask else None

        sts = load_spiketrains(self.data_path(action_id), lim=lim)
        for st in sts:
            group = st.annotations["group"]
            if group not in self._spike_trains[action_id]:
                self._spike_trains[action_id][group] = {}
            self._spike_trains[action_id][group][int(get_unit_id(st))] = st
        if channel_group is None:
            return self._spike_trains[action_id]
        else:
            return self._spike_trains[action_id][channel_group]

    def unit_names(self, action_id, channel_group):
        # TODO
        # units = load_unit_annotations(self.data_path(action_id), channel_group=channel_group)
        units = None
        return [u["name"] for u in units]

    def stim_times(self, action_id):
        if action_id not in self._stim_times:
            try:
                trials = load_epochs(self.data_path(action_id), label_column="channel")
                if len(set(trials.labels)) > 1:
                    stim_times = trials.times[trials.labels == self.stim_channels[action_id]]
                else:
                    stim_times = trials.times
                stim_times = np.sort(np.abs(np.array(stim_times)))
                # there are some 0 times and inf times, remove those
                # stim_times = stim_times[stim_times >= 1e-20]
                self._stim_times[action_id] = stim_times
            except AttributeError as e:
                if str(e) == "'NoneType' object has no attribute 'to_dataframe'":
                    self._stim_times[action_id] = None
                else:
                    raise e

        return self._stim_times[action_id]
