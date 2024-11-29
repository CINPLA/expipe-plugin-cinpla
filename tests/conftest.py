# -*- coding: utf-8 -*-
import shutil
from pathlib import Path

import expipe
import pytest

from expipe_plugin_cinpla.tools.utils import dump_project_config

TEST_DATA_PATH = Path(__file__).parent / "test_data"

PROJECT_NAME = "pytest-project"
ACTION_ID = "action-plugin-test"
MODULE_ID = "module-plugin-test"
RAT_ID = "test-rat"
USER_NAME = "John Doe"
POSSIBLE_TAGS = ["good", "place cells", "grid cells", "bad"]


def pytest_configure():
    project_path = Path(PROJECT_NAME).absolute()
    if project_path.is_dir():
        shutil.rmtree(project_path)
    project = expipe.create_project(path=project_path, name=PROJECT_NAME)
    project.config["username"] = USER_NAME
    project.config["possible_tags"] = POSSIBLE_TAGS
    dump_project_config(project)
    project.require_action(ACTION_ID)

    pytest.PROJECT = project
    pytest.PROJECT_PATH = project_path
    pytest.ACTION_ID = ACTION_ID
    pytest.MODULE_ID = MODULE_ID
    pytest.RAT_ID = RAT_ID
    pytest.USERNAME = project.config.get("username")
    pytest.POSSIBLE_TAGS = project.config.get("possible_tags")
    pytest.TEST_DATA_PATH = TEST_DATA_PATH


def pytest_unconfigure():
    shutil.rmtree(PROJECT_NAME)
