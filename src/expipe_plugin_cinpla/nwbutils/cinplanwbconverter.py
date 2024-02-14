from probeinterface import ProbeGroup
from neuroconv import NWBConverter
from neuroconv.datainterfaces import OpenEphysRecordingInterface

from .interfaces.openephystrackinginterface import OpenEphysTrackingInterface


class CinplaNWBConverter(NWBConverter):
    data_interface_classes = dict(
        OpenEphysRecording=OpenEphysRecordingInterface, OpenEphysTracking=OpenEphysTrackingInterface
    )

    def set_probegroup(self, probegroup: ProbeGroup):
        """
        Sets probe group to OpenEphysRecordingInterface and sets group_name property
        """
        self.data_interface_objects["OpenEphysRecording"].recording_extractor.set_probegroup(
            probegroup, group_mode="by_probe", in_place=True
        )
        channel_groups = self.data_interface_objects["OpenEphysRecording"].recording_extractor.get_channel_groups()
        self.data_interface_objects["OpenEphysRecording"].recording_extractor.set_property(
            "group_name", [f"tetrode{ch}" for ch in channel_groups]
        )

    def enable_events(self):
        """
        Enables writing of Open Ephys events
        """
        self.data_interface_objects["OpenEphysTracking"].include_events = True

    def disable_events(self):
        """
        Disables writing of Open Ephys events
        """
        self.data_interface_objects["OpenEphysTracking"].include_events = False
