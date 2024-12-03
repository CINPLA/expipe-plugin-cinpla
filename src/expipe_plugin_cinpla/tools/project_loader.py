#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
import re
from collections import defaultdict

import expipe
import pandas as pd


class ProjectLoader:
    """
    Class for loading an expipe project.

    Attributes:
    ----------
    _project : expipe.Project
        The loaded project instance.
    path : str
        The path to the project.
    actions : list
        List of expipe actions associated with the project.
    action_ids : list
        List of action IDs associated with the project.
    entities : list
        Sorted list of entities in the project.
    metadata : pandas.DataFrame
        Dataframe of metadata for actions.
    info : dict
        Dictionary containing project-specific information.
    """

    def __init__(self, project_path):
        """
        Initializes the ProjectLoader with the given project path.

        Parameters:
        ----------
        project_path : str
            The path to the expipe project to be loaded.
        """

        # Load the project from the specified path
        self._project = expipe.get_project(project_path)
        self._config = self._project.config
        self._project_path = self._project.path
        self._actions = self._project.actions
        self._entities = sorted(list(self._project.entities))
        self._metadata_path = self._project.path / "actions_metadata.parquet"

        # Check if the metadata file exists, and process it if it doesn't
        # if not self._metadata_path.is_file():
        # This is relatively fast, so it's better to always process the metadata
        # to ensure it's up-to-date
        self.process_metadata()

        # Initialize the project information dictionary
        self._info = defaultdict(str)
        self._info["project"] = self._config["project"]
        self._info["project_path"] = self._project_path
        self._info["metadata_path"] = self._metadata_path
        self._info["probe_path"] = self._config["probe_path"]

    def _ipython_display_(self):
        """
        Custom display method for IPython environments. Displays project
        information as HTML in Jupyter notebooks.
        """
        expipe.widgets.display.display_dict_html(self.info)

    @property
    def path(self):
        """
        Returns the path of the loaded project.

        Returns:
        -------
        str
            The project path.
        """
        return self._project_path

    @property
    def info(self):
        """
        Returns project-specific information.

        Returns:
        -------
        dict
            Dictionary containing project information.
        """
        return self._info

    @property
    def actions(self):
        """
        Returns the list of actions associated with the project.

        Returns:
        -------
        list
            List of actions.
        """
        return self._actions

    @property
    def action_ids(self):
        """
        Returns the list of action IDs.

        Returns:
        -------
        list
            List of action IDs.
        """
        return [action.id for action in self._actions]

    @property
    def entities(self):
        """
        Returns the sorted list of entities in the project.

        Returns:
        -------
        list
            Sorted list of entities.
        """
        return self._entities

    @property
    def metadata(self):
        """
        Returns the metadata of the actions as a pandas DataFrame.

        Returns:
        -------
        pandas.DataFrame
            DataFrame containing the actions metadata.
        """
        return pd.read_parquet(self._metadata_path, dtype_backend="numpy_nullable")

    def select_metadata(self, action_ids):
        """
        Selects metadata for specific action IDs.

        Parameters:
        ----------
        action_ids : list or str
            List of action IDs or a single action ID.

        Returns:
        -------
        pandas.DataFrame
            DataFrame containing the selected actions metadata.
        """
        action_ids = [action_ids] if isinstance(action_ids, (str, bytes)) else action_ids
        mask = self.metadata["action_id"].isin(action_ids)
        return self.metadata[mask]

    def get_actions(self, action_ids):
        """
        Retrieve actions based on provided action IDs.

        Parameters:
        ----------
        action_ids : list or str
            List of action IDs or a single action ID.

        Returns:
        -------
        list
            List of actions corresponding to the given action IDs.
        """
        action_ids_lst = [action_ids] if isinstance(action_ids, (str, bytes)) else action_ids
        return [self._actions[action_id] for action_id in action_ids_lst]

    def get_action_ids(self, actions):
        """
        Retrieve action IDs based on provided actions.

        Parameters:
        ----------
        action_ids : list or str
            List of actions or a single action.

        Returns:
        -------
        list
            List of actions IDs corresponding to the given actions.
        """
        action_lst = [actions] if isinstance(actions, expipe.core.Action) else actions
        return [action.id for action in action_lst]

    def get_recording_actions(self):
        """
        Retrieves recording actions from the project.

        Returns:
        -------
        list
            List of recording actions.
        """
        recording_action_ids = [action.id for action in self._actions.values() if action.type == "Recording"]
        recording_action_ids = sorted(recording_action_ids)
        return self.get_actions(recording_action_ids)

    def require_action(self, action_name):
        """
        Create an action on the project or return an existing action if it already exists.

        Parameters:
        ----------
        action_name : str
            The name of the action to create or fetch.

        Returns:
        -------
        expipe.core.Action
            The required action object.
        """
        return self._project.require_action(action_name)

    def filter_actions(self, entity="*", date="*", recording_id="*"):
        """
        Filters actions based on provided entity, date, and recording ID.

        Parameters:
        ----------
        entity : str | list of str, optional
            Filter by entity. A single entity or a list of entities can
            be provided. Default is "*".
        date : str | list of str, optional
            Filter by date. A single date or a list of dates can be provided.
            Default is "*".
        recording_id : str | list of str, optional
            Filter by recording ID. A single recording ID or a list of
            recording IDs can be provided. Default is "*".

        Returns:
        -------
        list
            Filtered list of actions.

        Notes:
        -----
        - Uses regular expressions for filtering actions.
        - "*" is treated as a wildcard that matches any value.
        """

        entity_iter = [entity] if isinstance(entity, (str, bytes)) else entity
        date_iter = [date] if isinstance(date, (str, bytes)) else date
        recording_id_iter = [recording_id] if isinstance(recording_id, (str, bytes)) else recording_id

        selected_ids = []

        for entity in entity_iter:
            for date in date_iter:
                for recording_id in recording_id_iter:

                    # Handle wildcard patterns
                    if entity is None or entity == "*":
                        entity = "(\d+)"
                    if date is None or date == "*":
                        date = "(\d+)"
                    if recording_id is None or recording_id == "*":
                        recording_id = "(\d+)"

                    # Compile a regex pattern for matching actions based on entity-date-recording_id format
                    pattern = re.compile(f"^{entity}-{date}-{recording_id}$")

                    # Filter actions using the compiled pattern
                    selected_ids.append(list(filter(pattern.match, self._actions)))

        # Flatten list
        selected_ids = list(itertools.chain(*selected_ids))

        # Convert to list and sort action ids
        selected_ids = sorted(selected_ids)

        if len(selected_ids) < 1:
            raise ValueError("No action matching the filter pattern was found")

        # Convert to a list of expipe.core.Action objects
        selected_actions = (
            [self._actions[id] for id in selected_ids] if len(selected_ids) > 1 else self._actions[selected_ids[0]]
        )

        return selected_actions

    def process_metadata(self):
        """
        Processes metadata for the actions in the project and save it to a parquet file.
        """

        recording_actions = self.get_recording_actions()
        recording_action_ids = self.get_action_ids(recording_actions)

        # Extract entity, date and recording_id from action ID
        pattern = r"(\d+)-(\d+)-(\d+)"
        prog = re.compile(pattern)
        result = [m for m in (prog.match(action_id) for action_id in recording_action_ids) if m]
        entities = [m.group(1) for m in result]
        dates = [m.group(2) for m in result]
        recording_ids = [m.group(3) for m in result]

        datetimes = [action.datetime for action in recording_actions]

        metadata = {
            "action_id": recording_action_ids,
            "entity": entities,
            "date": dates,
            "recording_id": recording_ids,
            "datetime": datetimes,
        }

        meta_df = pd.DataFrame(metadata)

        meta_df.to_parquet(self._metadata_path, index=False)
