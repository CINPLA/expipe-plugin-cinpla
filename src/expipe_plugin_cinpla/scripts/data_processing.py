"""Utils for loading data from NWB files"""
import numpy as np

import quantities as pq
import neo
import spikeinterface as si
import spikeinterface.extractors as se

from pynwb import NWBHDF5IO
from .utils import _get_data_path


def get_data_path(action):
    """Returns the path to the main.nwb file"""
    return str(_get_data_path(action))


def get_sample_rate(data_path):
    """
    Return the sampling rate of the recording

    Parameters
    ----------
    data_path: Path
        The action data path

    Returns
    -------
    sr: pq.Quantity
        The sampling rate of the recording
    """
    recording = se.read_nwb_recording(str(data_path), electrical_series_path="acquisition/ElectricalSeries")
    sr = recording.get_sampling_frequency() * pq.Hz
    return sr


def get_duration(data_path):
    """
    Return the duration of the recording in s

    Parameters
    ----------
    data_path: Path
        The action data path

    Returns
    -------
    duration: pq.Quantity
        The duration of the recording
    """
    recording = se.read_nwb_recording(str(data_path), electrical_series_path="acquisition/ElectricalSeries")
    duration = recording.get_total_duration() * pq.s
    return duration


def view_active_channels(action, sorter):
    """
    Returns the active channels for a given action and sorter

    Parameters
    ----------
    action: Action
        The action
    sorter: str
        The sorter name

    Returns
    -------
    active_channels: list
        The active channels
    """
    path = _get_data_path(action)
    sorter_path = path.parent / "spikeinterface" / sorter
    if not sorter_path.is_dir():
        raise ValueError(f"Action {action.id} has not been sorted with {sorter}")
    waveforms_folder = sorter_path / "waveforms"
    we = si.load_waveforms(waveforms_folder, with_recording=False)
    return we.channel_ids


def load_leds(data_path):
    """
    Returns the positions of the LEDs (red + green)

    Parameters
    ----------
    data_path: Path
        The action data path

    Returns
    -------
    x1, y1, t1, x2, y2, t2, stop_time: tuple
        The x and y positions of the red and green LEDs, the timestamps and the stop time
    """
    io = NWBHDF5IO(str(data_path), "r")
    nwbfile = io.read()

    behavior = nwbfile.processing["behavior"]

    # tracking data
    open_field_position = behavior["Open Field Position"]
    red_spatial_series = open_field_position["LedRed"]
    green_spatial_series = open_field_position["LedGreen"]
    red_data = red_spatial_series.data
    green_data = green_spatial_series.data
    x1, y1 = red_data[:, 0], red_data[:, 1]
    x2, y2 = green_data[:, 0], green_data[:, 1]
    t1 = red_spatial_series.timestamps
    t2 = green_spatial_series.timestamps
    stop_time = np.max([t1[-1], t2[-1]])

    return x1, y1, t1, x2, y2, t2, stop_time


def load_lfp(data_path, channel_group=None, lim=None):
    """
    Returns the LFP signal

    Parameters
    ----------
    data_path: Path
        The action data path
    channel_group: str, optional
        The channel group to load. If None, all channel groups are loaded
    lim: list, optional
        The time limits to load the LFP signal. If None, the entire signal is loaded

    Returns
    -------
    LFP: neo.AnalogSignal
        The LFP signal
    """
    recording_lfp = se.read_nwb_recording(
        str(data_path), electrical_series_path="processing/ecephys/LFP/ElectricalSeriesLFP"
    )
    # LFP
    units = pq.uV
    sampling_rate = recording_lfp.sampling_frequency * pq.Hz

    if channel_group is not None:
        available_channel_groups = np.unique(recording_lfp.get_channel_groups())
        assert (
            channel_group in recording_lfp.get_channel_groups()
        ), f"Channel group {channel_group} not found in available channel groups: {available_channel_groups}"
        # this returns a sub-extractor with the requested channel group
        recording_lfp_group = recording_lfp.split_by("group")[channel_group]
        (electrode_idx,) = np.nonzero(np.isin(recording_lfp.channel_ids, recording_lfp_group.channel_ids))
    else:
        recording_lfp_group = recording_lfp
        electrode_idx = np.arange(recording_lfp.get_num_channels())

    if lim is None:
        lfp_traces = recording_lfp_group.get_traces(return_scaled=True)
        t_start = recording_lfp.get_times()[0] * pq.s
        t_stop = recording_lfp.get_times()[-1] * pq.s
    else:
        assert len(lim) == 2, "lim must be a list of two elements with t_start and t_stop"
        times_all = recording_lfp_group.get_times()
        start_frame, end_frame = np.searchsorted(times_all, lim)
        times = times_all[start_frame:end_frame]
        t_start = times[0] * pq.s
        t_stop = times[-1] * pq.s
        lfp_traces = recording_lfp_group.get_traces(start_frame=start_frame, end_frame=end_frame, return_scaled=True)

    LFP = neo.AnalogSignal(
        lfp_traces,
        units=units,
        t_start=t_start,
        t_stop=t_stop,
        sampling_rate=sampling_rate,
        **{"electrode_idx": electrode_idx},
    )
    LFP = LFP.rescale("mV")
    return LFP


def load_epochs(data_path, label_column=None):
    """
    Returns the trials as NEO epochs

    Parameters
    ----------
    data_path: Path
        The action data path
    label_column: str, optional
        The column name to use as labels

    Returns
    -------
    epochs: neo.Epoch
        The trials as NEO epochs
    """
    with NWBHDF5IO(str(data_path), "r") as io:
        nwbfile = io.read()
        trials = nwbfile.trials.to_dataframe()

        start_times = trials["start_time"].values * pq.s
        stop_times = trials["stop_time"].values * pq.s
        durations = stop_times - start_times

        if label_column is not None and label_column in trials.columns:
            labels = trials[label_column].values
        else:
            labels = None

        epochs = neo.Epoch(
            times=start_times,
            durations=durations,
            labels=labels,
        )
    return epochs


def get_channel_groups(data_path):
    """
    Returns channel groups of session

    Parameters
    ----------
    data_path: Path
        The action data path

    Returns
    -------
    channel groups: list
        The channel groups
    """
    recording = se.read_nwb_recording(str(data_path), electrical_series_path="acquisition/ElectricalSeries")
    channel_groups = list(np.unique(recording.get_channel_groups()))
    return channel_groups


def load_spiketrains(data_path, channel_group=None, lim=None):
    """
    Returns the spike trains as a list of NEO spike trains

    Parameters
    ----------
    data_path: str / Path
        The action data path
    channel_group: str, optional
        The channel group to load. If None, all channel groups are loaded
    lim: list, optional
        The time limits to load the spike trains. If None, the entire spike train is loaded

    Returns
    -------
    spiketrains: list of NEO spike trains
        The spike trains
    """
    recording = se.read_nwb_recording(str(data_path), electrical_series_path="acquisition/ElectricalSeries")
    sorting = se.read_nwb_sorting(str(data_path), electrical_series_path="acquisition/ElectricalSeries")

    if channel_group is None:
        unit_ids = sorting.unit_ids
    else:
        assert "group" in sorting.get_property_keys(), "group property not found in sorting"
        groups = sorting.get_property("group")
        unit_ids = [
            unit_id for unit_index, unit_id in enumerate(sorting.unit_ids) if groups[unit_index] == channel_group
        ]
    sptr = []
    # build neo pbjects
    for unit in unit_ids:
        times = sorting.get_unit_spike_train(unit, return_times=True) * pq.s
        if lim is None:
            times = recording.get_times() * pq.s
            t_start = times[0]
            t_stop = times[-1]
        else:
            t_start = pq.Quantity(lim[0], "s")
            t_stop = pq.Quantity(lim[1], "s")
        mask = (times >= t_start) & (times <= t_stop)
        times = times[mask]

        st = neo.SpikeTrain(
            times=times, t_start=t_start, t_stop=t_stop, sampling_rate=sorting.sampling_frequency * pq.Hz
        )
        for p in sorting.get_property_keys():
            st.annotations.update({p: sorting.get_unit_property(unit, p)})
        sptr.append(st)

    return sptr


def load_unit_annotations(data_path, channel_group=None):
    """
    Returns the annotations of the units

    Parameters
    ----------
    data_path: str/Path
        The action data path
    channel_group: str, optional
        The channel group to load. If None, all channel groups are loaded

    Returns
    -------
    annotations: list of dicts
        The annotations of the units
    """
    sorting = se.read_nwb_sorting(str(data_path), electrical_series_path="acquisition/ElectricalSeries")

    units = []

    if channel_group is None:
        unit_ids = sorting.unit_ids
    else:
        assert "group" in sorting.get_property_keys(), "group property not found in sorting"
        groups = sorting.get_property("group")
        unit_ids = [
            unit_id for unit_index, unit_id in enumerate(sorting.unit_ids) if groups[unit_index] == channel_group
        ]

    for unit in unit_ids:
        annotations = {}
        for p in sorting.get_property_keys():
            annotations.update({p: sorting.get_unit_property(unit, p)})
        units.append(annotations)
    return units


# These functions are not relevant anymore
# def get_unit_id(unit):
#     try:
#         uid = int(unit.annotations['name'].split('#')[-1])
#     except AttributeError:
#         uid = int(unit['name'].split('#')[-1])
#     return uid

# def sort_by_cluster_id(spike_trains):
#     if len(spike_trains) == 0:
#         return spike_trains
#     if "name" not in spike_trains[0].annotations:
#         print("Unable to get cluster_id, save with phy to create")
#     sorted_sptrs = sorted(spike_trains, key=lambda x: int(x.annotations["name"].lower().replace("unit #", "")))
#     return sorted_sptrs
