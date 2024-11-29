# -*- coding: utf-8 -*-
import uuid
from pathlib import Path

import matplotlib.pylab as plt
import networkx as nx
import numpy as np
import yaml
from matplotlib import gridspec
from tqdm import tqdm

from expipe_plugin_cinpla.tools.data_loader import (
    get_channel_groups,
    get_data_path,
    load_spiketrains,
)
from expipe_plugin_cinpla.tools.track_units_tools import plot_template
from expipe_plugin_cinpla.tools.trackunitcomparison import TrackingSession


class TrackMultipleSessions:
    """
    Class to compare multiple sessions and identify units across sessions.

    Parameters
    ----------
    actions: expipe.Actions
        List of expipe actions.
    action_list: list
        List of action ids to compare.
    channel_groups: list | None, default: None
        List of channel groups to compare. If None, all channel groups are compared.
    verbose: bool, default: False
        If True, output is printed during the comparison.
    progress_bar: callable, default: None
        Progress bar to use. If None, tqdm is used.
    data_path: str | None, default: None
        Path to save the data. If None, the current working directory is used.

    Examples
    --------
    >>> from expipe_plugin_cinpla import TrackMultipleSessions
    >>> # at instantiation, all pairwise comparisons are performed
    >>> track_sessions = TrackMultipleSessions(actions)
    >>> # make graphs from the matches
    >>> track_sessions.make_graphs_from_matches()
    >>> track_sessions.compute_depth_delta_edges()
    >>> track_sessions.compute_time_delta_edges()
    >>> # filter graph
    >>> track_sessions.remove_edges_above_threshold(key="weight", threshold=0.05)
    >>> track_sessions.remove_edges_with_duplicate_actions()
    >>> track_sessions.identify_units()
    >>> print(track_sessions.identified_units)
    >>> track_sessions.plot_matches()
    """

    def __init__(
        self,
        actions,
        action_list=None,
        channel_groups=None,
        verbose=False,
        progress_bar=None,
        data_path=None,
    ):
        self.data_path = Path.cwd() if data_path is None else Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.action_list = [a for a in actions] if action_list is None else action_list
        self._actions = actions
        self.channel_groups = channel_groups
        self._verbose = verbose
        self._pbar = tqdm if progress_bar is None else progress_bar
        self._templates = {}
        if self.channel_groups is None:
            dp = get_data_path(self._actions[self.action_list[0]])
            self.channel_groups = get_channel_groups(dp)
            if len(self.channel_groups) == 0:
                print("Unable to locate channel groups, please provide a working action_list")

    def do_matching(self):
        """
        Perform the pairwise matching based on dissimilarity
        """
        # do pairwise matching
        if self._verbose:
            print("Multicomaprison step1: pairwise comparison")

        self.comparisons = []
        N = len(self.action_list)
        if self._pbar is not None:
            pbar = self._pbar(total=int((N**2 - N) / 2))
        for i in range(N):
            for j in range(i + 1, N):
                if self._verbose:
                    print("  Comparing: ", self.action_list[i], " and ", self.action_list[j])
                comp = TrackingSession(
                    self.action_list[i],
                    self.action_list[j],
                    actions=self._actions,
                    max_dissimilarity=np.inf,
                    channel_groups=self.channel_groups,
                    verbose=self._verbose,
                )
                # comp.save_dissimilarity_matrix()
                self.comparisons.append(comp)
                if pbar is not None:
                    pbar.update(1)
        if pbar is not None:
            pbar.close()

    def make_graphs_from_matches(self):
        """
        Create graphs from the matches
        """
        if self._verbose:
            print("Multicomaprison step2: make graph")

        self.graphs = {}

        for ch in self.channel_groups:
            if self._verbose:
                print("Processing channel", ch)
            self.graphs[ch] = nx.Graph()

            # nodes
            for comp in self.comparisons:
                # if same node is added twice it's only created once
                for i, action_id in enumerate(comp.action_ids):
                    for u in comp.unit_ids[ch][i]:
                        node_name = action_id + "_" + str(int(u))
                        self.graphs[ch].add_node(node_name, action_id=action_id, unit_id=int(u))

            # edges
            for comp in self.comparisons:
                if "hungarian_match_01" not in comp.matches[ch]:
                    continue
                for u1 in comp.unit_ids[ch][0]:
                    u2 = comp.matches[ch]["hungarian_match_01"][u1]
                    if u2 != -1:
                        score = comp.matches[ch]["dissimilarity_scores"].loc[u1, u2]
                        node1_name = comp.action_id_0 + "_" + str(int(u1))
                        node2_name = comp.action_id_1 + "_" + str(int(u2))
                        self.graphs[ch].add_edge(node1_name, node2_name, weight=float(score))

            # the graph is symmetrical
            self.graphs[ch] = self.graphs[ch].to_undirected()

        self.remove_edges_with_duplicate_actions()

    def compute_time_delta_edges(self):
        """
        Adds a timedelta to each of the edges
        """
        for graph in self.graphs.values():
            for n0, n1 in graph.edges():
                action_id_0 = graph.nodes[n0]["action_id"]
                action_id_1 = graph.nodes[n1]["action_id"]
                time_delta = abs(self._actions[action_id_0].datetime - self._actions[action_id_1].datetime)
                graph.add_edge(n0, n1, time_delta=time_delta)

    def compute_depth_delta_edges(self):
        """
        Adds a depthdelta to each of the edges
        """
        for ch, graph in self.graphs.items():
            ch_num = int(ch[-1])
            for n0, n1 in graph.edges():
                action_id_0 = graph.nodes[n0]["action_id"]
                action_id_1 = graph.nodes[n1]["action_id"]
                loc_0 = self._actions[action_id_0].modules["channel_group_location"][ch_num]
                loc_1 = self._actions[action_id_1].modules["channel_group_location"][ch_num]
                assert loc_0 == loc_1
                depth_0 = self._actions[action_id_0].modules["depth"][loc_0]["probe_0"]
                depth_1 = self._actions[action_id_0].modules["depth"][loc_1]["probe_0"]
                depth_0 = float(depth_0.rescale("um"))
                depth_1 = float(depth_1.rescale("um"))
                depth_delta = abs(depth_0 - depth_1)
                graph.add_edge(n0, n1, depth_delta=depth_delta)

    def remove_edges_above_threshold(self, key="weight", threshold=0.05):
        """
        Remove edges above a certain threshold for a given
        key: weight, depth_delta, time_delta

        Parameters
        ----------
        key: str
            The key to remove edges based on
        threshold: float
            The threshold to remove edges above
        """
        for ch in self.graphs:
            graph = self.graphs[ch]
            edges_to_remove = []
            for sub_graph in nx.connected_components(graph):
                for node_id in sub_graph:
                    for n1, n2, d in graph.edges(node_id, data=True):
                        if d[key] > threshold and n2 in sub_graph:  # remove all edges from the subgraph
                            edge = set((n1, n2))
                            if edge not in edges_to_remove:
                                edges_to_remove.append(edge)
            for n1, n2 in edges_to_remove:
                graph.remove_edge(n1, n2)
            self.graphs[ch] = graph

    def remove_edges_with_duplicate_actions(self):
        """
        Removes edges between nodes that have the same action_id
        """
        for graph in self.graphs.values():
            edges_to_remove = []
            for sub_graph in nx.connected_components(graph):
                sub_graph_action_ids = {node: graph.nodes[node]["action_id"] for node in sub_graph}
                action_ids = np.array(list(sub_graph_action_ids.values()))
                node_ids = np.array(list(sub_graph_action_ids.keys()))
                unique_action_ids, action_id_counts = np.unique(action_ids, return_counts=True)
                if len(unique_action_ids) != len(action_ids):
                    duplicates = unique_action_ids[action_id_counts > 1]

                    for duplicate in duplicates:
                        (idxs,) = np.where(action_ids == duplicate)
                        weights = {}
                        for node_id in node_ids[idxs]:
                            weights[node_id] = np.mean(
                                [
                                    d["weight"]
                                    for n1, n2, d in graph.edges(node_id, data=True)
                                    if n2 in sub_graph_action_ids
                                ]
                            )
                        min_weight = np.min(list(weights.values()))
                        for node_id, weight in weights.items():
                            if weight > min_weight:  # remove all edges from the subgraph
                                for n1, n2 in graph.edges(node_id):
                                    if n2 in sub_graph_action_ids:
                                        edge = set((n1, n2))
                                        if edge not in edges_to_remove:
                                            edges_to_remove.append(edge)
            for n1, n2 in edges_to_remove:
                graph.remove_edge(n1, n2)

    def save_graphs(self):
        """
        Save the graphs to the data_path
        """
        for ch, graph in self.graphs.items():
            with open(self.data_path / f"graph-group-{ch}.yaml", "w") as f:
                yaml.dump(graph, f)

    def load_graphs(self):
        """
        Load the graphs from the data_path
        """
        self.graphs = {}
        for path in self.data_path.iterdir():
            if path.name.startswith("graph-group") and path.suffix == ".yaml":
                ch = path.stem.split("-")[-1]
                with open(path) as f:
                    self.graphs[ch] = yaml.load(f, Loader=yaml.Loader)

    def identify_units(self):
        """
        Identify units across sessions from the graphs
        """
        if self._verbose:
            print("Multicomaprison step3: extract agreement from graph")
        self.identified_units = {}
        for ch, graph in self.graphs.items():
            # extract agrrement from graph
            self._new_units = {}
            for node_set in nx.connected_components(graph):
                unit_id = str(uuid.uuid4())
                edges = graph.edges(node_set, data=True)

                if len(node_set) < 2:
                    continue

                average_dissimilarity = np.mean([d["weight"] for _, _, d in edges])

                original_ids = dict()
                for node in node_set:
                    original_ids[graph.nodes[node]["action_id"]] = graph.nodes[node]["unit_id"]

                self._new_units[unit_id] = {
                    "average_dissimilarity": average_dissimilarity,
                    "original_unit_ids": original_ids,
                }

            self.identified_units[ch] = self._new_units

    def load_template(self, action_id, channel_group, unit_id):
        """
        Load the template for a given action_id, channel_group and unit_id

        Parameters
        ----------
        action_id: str
            The action id
        channel_group: int or str
            The channel group
        unit_id: int or str
            The unit id

        Returns
        -------
        template: np.ndarray
            The template
        """
        group_unit_hash = str(channel_group) + "_" + str(unit_id)
        if action_id in self._templates:
            return self._templates[action_id][group_unit_hash]

        action = self._actions[action_id]

        data_path = get_data_path(action)

        spike_trains = load_spiketrains(data_path)

        self._templates[action_id] = {}
        for sptr in spike_trains:
            group_unit_hash_ = sptr.annotations["group"] + "_" + str(int(sptr.annotations["name"]))
            self._templates[action_id][group_unit_hash_] = sptr.annotations["waveform_mean"]

        return self._templates[action_id][group_unit_hash]

    def plot_matches(self, channel_group=None, figsize=(10, 3)):
        """
        Plot the matched units across sessions

        Parameters
        ----------
        channel_group: int or str
            The channel group to plot. If None, all channel groups are plotted
        figsize: tuple
            The figure size
        """
        if channel_group is None:
            ch_groups = sorted(self.identified_units.keys())
        else:
            ch_groups = [channel_group]
        for ch_group in ch_groups:
            identified_units = self.identified_units[ch_group]
            units = [
                (unit["original_unit_ids"], unit["average_dissimilarity"])
                for unit in identified_units.values()
                if len(unit["original_unit_ids"]) > 1
            ]
            num_units = sum([len(u) for u in units])
            if num_units == 0:
                print(f"Zero units found on channel group {ch_group}")
                continue
            fig = plt.figure(figsize=(figsize[0], figsize[1] * num_units))
            gs = gridspec.GridSpec(num_units, 1)
            id_ax = 0
            for unit, avg_dsim in units:
                axs = None
                for action_id, unit_id in unit.items():
                    label = f"{action_id} Unit {unit_id} {avg_dsim:.2f}"
                    template = self.load_template(action_id, ch_group, unit_id)
                    if template is None:
                        print(f'Unable to plot "{unit_id}" from action "{action_id}" ch group "{ch_group}"')
                        continue
                    # print(f'plotting {action_id}, {ch_group}, {unit_id}')
                    axs = plot_template(template, fig=fig, gs=gs[id_ax], axs=axs, label=label)
                id_ax += 1
                plt.legend(loc="center left", bbox_to_anchor=(1, 0.5))
            fig.suptitle("Channel group " + str(ch_group))
            plt.tight_layout(rect=[0, 0.03, 1, 0.98])
