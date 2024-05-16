# -*- coding: utf-8 -*-
from pathlib import Path

import numpy as np
import pandas as pd

from expipe_plugin_cinpla.data_loader import (
    get_channel_groups,
    get_data_path,
    load_spiketrains,
)

from .track_units_tools import (
    dissimilarity_weighted,
    make_best_match,
    make_hungarian_match,
    make_possible_match,
)


class TrackingSession:
    """
    Base class shared by SortingComparison and GroundTruthComparison
    """

    def __init__(
        self,
        action_id_0,
        action_id_1,
        actions,
        channel_groups=None,
        max_dissimilarity=10,
        dissimilarity_function=None,
        verbose=False,
    ):
        data_path_0 = get_data_path(actions[action_id_0])
        data_path_1 = get_data_path(actions[action_id_1])

        self._actions = actions
        self.action_id_0 = action_id_0
        self.action_id_1 = action_id_1
        self.channel_groups = channel_groups
        self.action_ids = [action_id_0, action_id_1]
        self.max_dissimilarity = max_dissimilarity
        self.dissimilarity_function = dissimilarity_function
        self._verbose = verbose

        if self.channel_groups is None:
            self.channel_groups = get_channel_groups(data_path_0)
        self.matches = {}
        self.templates = {}
        self.unit_ids = {}
        for chan in self.channel_groups:
            self.matches[chan] = dict()
            self.templates[chan] = list()
            self.unit_ids[chan] = list()

        self.units_0 = load_spiketrains(data_path_0)
        self.units_1 = load_spiketrains(data_path_1)
        for channel_group in self.channel_groups:
            us_0 = [u for u in self.units_0 if u.annotations["group"] == channel_group]
            us_1 = [u for u in self.units_1 if u.annotations["group"] == channel_group]

            self.unit_ids[channel_group] = [
                [int(u.annotations["name"]) for u in us_0],
                [int(u.annotations["name"]) for u in us_1],
            ]
            self.templates[channel_group] = [
                [u.annotations["waveform_mean"] for u in us_0],
                [u.annotations["waveform_mean"] for u in us_1],
            ]
            if len(us_0) > 0 and len(us_1) > 0:
                self._do_dissimilarity(channel_group)
                self._do_matching(channel_group)
            elif self._verbose:
                print(f"Found no units in {channel_group}")

    def save_dissimilarity_matrix(self, path=None):
        path = path or Path.cwd()
        for channel_group in self.channel_groups:
            if "dissimilarity_scores" not in self.matches[channel_group]:
                continue
            filename = f"{self.action_id_0}_{self.action_id_1}_{channel_group}"
            self.matches[channel_group]["dissimilarity_scores"].to_csv(path / (filename + ".csv"))

    @property
    def session_0_name(self):
        return self.name_list[0]

    @property
    def session_1_name(self):
        return self.name_list[1]

    def make_dissimilary_matrix(self, channel_group):
        templates_0, templates_1 = self.templates[channel_group]
        diss_matrix = np.zeros((len(templates_0), len(templates_1)))

        unit_ids_0, unit_ids_1 = self.unit_ids[channel_group]

        for i, w0 in enumerate(templates_0):
            for j, w1 in enumerate(templates_1):
                diss_matrix[i, j] = dissimilarity_weighted(w0, w1)

        diss_matrix = pd.DataFrame(diss_matrix, index=unit_ids_0, columns=unit_ids_1)

        return diss_matrix

    def _do_dissimilarity(self, channel_group):
        if self._verbose:
            print("Agreement scores...")

        # agreement matrix score for each pair
        self.matches[channel_group]["dissimilarity_scores"] = self.make_dissimilary_matrix(channel_group)

    def _do_matching(self, channel_group):
        # must be implemented in subclass
        if self._verbose:
            print("Matching...")

        (
            self.matches[channel_group]["possible_match_01"],
            self.matches[channel_group]["possible_match_10"],
        ) = make_possible_match(self.matches[channel_group]["dissimilarity_scores"], self.max_dissimilarity)
        self.matches[channel_group]["best_match_01"], self.matches[channel_group]["best_match_10"] = make_best_match(
            self.matches[channel_group]["dissimilarity_scores"], self.max_dissimilarity
        )
        (
            self.matches[channel_group]["hungarian_match_01"],
            self.matches[channel_group]["hungarian_match_10"],
        ) = make_hungarian_match(self.matches[channel_group]["dissimilarity_scores"], self.max_dissimilarity)
