import warnings
import numpy as np
import pyopenephys

from pynwb.behavior import (
    Position,
    SpatialSeries,
)

from neuroconv import BaseDataInterface
from neuroconv.utils import FolderPathType


class OpenEphysTrackingInterface(BaseDataInterface):
    def __init__(self, folder_path: FolderPathType):
        """ """
        openephys_file = pyopenephys.File(str(folder_path))
        experiments = openephys_file.experiments
        if len(experiments) > 1:
            raise NotImplementedError("Only single experiments are currently supported")
        experiment = experiments[0]
        recordings = experiment.recordings
        if len(recordings) > 1:
            raise NotImplementedError("Only single recordings are currently supported")
        recording = recordings[0]
        self.tracking = recording.tracking
        self.events = recording.events
        self.sample_rate = recording.sample_rate
        self.include_events = False
        self.session_start_time = recording.start_time.rescale("s")

    def add_to_nwbfile(
        self,
        nwbfile,
        metadata,
    ):
        """ """
        behavior_module = nwbfile.create_processing_module(name="behavior", description="Processed behavioral data")
        spatial_series_list = []
        for i, tracking_data in enumerate(self.tracking):
            # Grab led color from metadata
            led_color = tracking_data.metadata[0][0].item().decode().capitalize()
            name = f"Led{led_color}"
            x, y, timestamps = tracking_data.x, tracking_data.y, tracking_data.times
            if self.session_start_time is not None:
                timestamps = timestamps.rescale("s") + self.session_start_time
            position_data = np.array([x, y]).T
            position_spatial_series = SpatialSeries(
                name=name,
                description="Position (x, y) in an open field.",
                data=position_data,
                timestamps=timestamps,
                reference_frame="(0,0) is bottom left corner",
            )
            spatial_series_list.append(position_spatial_series)
        position = Position(spatial_series=spatial_series_list, name="Open Field Position")
        behavior_module.add(position)

        if self.include_events:
            for event in self.events:
                for channel in np.unique(event.channels):
                    mask = event.channels == channel
                    times = event.times[mask]
                    states = event.channel_states[mask]

                    if self.session_start_time is not None:
                        times = times + self.session_start_time

                    rising = np.where(states > 0)[0]
                    falling = np.where(states < 0)[0]

                    # infer durations
                    if len(states) > 0:
                        # make sure first event is rising and last is falling
                        if states[0] < 0:
                            falling = falling[1:]
                        if states[-1] > 0:
                            rising = rising[:-1]

                        if len(rising) == len(falling):
                            nwbfile.add_trial_column(
                                name="channel",
                                description="Open Ephys channel",
                            )
                            nwbfile.add_trial_column(
                                name="processor",
                                description="Open Ephys processor that recorded the event",
                            )
                            start_times = times[rising].rescale("s").magnitude
                            stop_times = times[falling].rescale("s").magnitude
                            for start, stop in zip(start_times, stop_times):
                                nwbfile.add_trial(
                                    start_time=start,
                                    stop_time=stop,
                                    channel=channel,
                                    processor=event.processor,
                                )
                        else:
                            warnings.warn(f"Unequal number of rising and falling edges for channel {channel}.")
