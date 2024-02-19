import pytest
import time
import click
from pathlib import Path
from click.testing import CliRunner
import quantities as pq
import numpy as np

from expipe_plugin_cinpla.cli import CinplaPlugin

import spikeinterface.extractors as se


@click.group()
@click.pass_context
def cli(ctx):
    pass


CinplaPlugin().attach_to_cli(cli)


def run_command(command_list, inp=None):
    runner = CliRunner()
    command_list = [str(c) for c in command_list]
    # print(" ".join(command_list))
    result = runner.invoke(cli, command_list, input=inp)
    if result.exit_code != 0:
        print(result.output)
        raise result.exception


def test_annotate():
    project = pytest.PROJECT
    action = project.require_action(pytest.ACTION_ID)

    run_command(
        [
            "register",
            "annotation",
            pytest.ACTION_ID,
            "--project-path",
            pytest.PROJECT_PATH,
            "--tags",
            pytest.POSSIBLE_TAGS[0],
            "-t",
            pytest.POSSIBLE_TAGS[1],
            "--message",
            "first message",
        ],
    )
    assert all(tag in pytest.POSSIBLE_TAGS for tag in action.tags)
    message_keys = list(action.messages.keys())
    message = action.messages[message_keys[0]]
    assert message.text == "first message"
    assert message.user == pytest.USERNAME

    time.sleep(1)
    run_command(
        [
            "register",
            "annotation",
            "--project-path",
            pytest.PROJECT_PATH,
            pytest.ACTION_ID,
            "--user",
            "test_user",
            "-m",
            "second message",
        ]
    )
    message_keys = sorted(list(action.messages.keys()))
    message = action.messages[message_keys[1]]
    assert message.text == "second message"
    assert message.user == "test_user"


def test_entity_surgery_adjustment():
    # project, _ = teardown_setup_project
    project = pytest.PROJECT
    action = project.require_action(pytest.ACTION_ID)

    # make rat entity
    run_command(
        [
            "register",
            "entity",
            pytest.RAT_ID,
            "--project-path",
            pytest.PROJECT_PATH,
            "--location",
            "animal-facility",
            "--species",
            "rattus norvegicus",
            "--gender",
            "F",
            "--birthday",
            "09.02.2024",
            "--weight",
            "500",
            "g",
        ],
    )

    # make surgery action
    run_command(
        [
            "register",
            "surgery",
            pytest.RAT_ID,
            "--project-path",
            pytest.PROJECT_PATH,
            "--weight",
            "500",
            "g",
            "--procedure",
            "implantation",
            "--date",
            "21.01.2017T14:40",
            "--angle",
            "mecl 0 1.9 deg",
            "--position",
            "mecl 0 1 2 3 mm",
            "--angle",
            "mecr 1 1.8 deg",
            "--position",
            "mecr 1 3 2 1 mm",
            "--location",
            "room1",
        ]
    )

    # init
    run_command(
        [
            "register",
            "adjustment",
            pytest.RAT_ID,
            "--project-path",
            pytest.PROJECT_PATH,
            "-a",
            "mecl 0 50 um",
            "--adjustment",
            "mecr 1 100 um",
            "--date",
            "now",
            "-y",
        ]
    )

    # adjust more
    run_command(
        [
            "register",
            "adjustment",
            pytest.RAT_ID,
            "--project-path",
            pytest.PROJECT_PATH,
            "-a",
            "mecl 0 50 um",
            "--adjustment",
            "mecr 1 200 um",
            "--date",
            "now",
            "-y",
        ]
    )

    action = project.require_action(pytest.RAT_ID + "-adjustment")
    adj000 = action.modules["000_adjustment"].contents
    assert adj000["depth"]["mecl"]["probe_0"] == 3.05 * pq.mm
    assert adj000["depth"]["mecr"]["probe_1"] == 1.1 * pq.mm
    adj001 = action.modules["001_adjustment"].contents
    assert adj001["depth"]["mecl"]["probe_0"] == 3.1 * pq.mm
    assert adj001["depth"]["mecr"]["probe_1"] == 1.3 * pq.mm


def test_perfursion():
    project = pytest.PROJECT
    action = project.require_action(pytest.ACTION_ID)

    # make rat entity
    run_command(
        ["register", "perfusion", pytest.RAT_ID, "--project-path", pytest.PROJECT_PATH, "--date", "now"],
    )


def test_register_openephys():
    project = pytest.PROJECT
    openephys_path = pytest.TEST_DATA_PATH / "openephys" / "008_2022-12-08_17-01-48_1"
    probe_path = pytest.TEST_DATA_PATH / "tetrode_32_openephys.json"
    RAT_ID = "008"

    # make rat entity
    run_command(
        [
            "register",
            "entity",
            RAT_ID,
            "--project-path",
            pytest.PROJECT_PATH,
            "--location",
            "animal-facility",
            "--species",
            "Rattus norvegicus",
            "--gender",
            "M",
            "--birthday",
            "09.02.2024",
            "--weight",
            "500",
            "g",
        ],
    )

    # make rat entity
    run_command(
        [
            "register",
            "openephys",
            openephys_path,
            probe_path,
            "--project-path",
            pytest.PROJECT_PATH,
            "--location",
            "recording-room1",
        ],
    )

    action_id = "008-081222-1"
    assert action_id in project.actions
    action = project.actions[action_id]
    assert (action.path / "data" / "main.nwb").is_file()

    recording_openephys = se.read_openephys(openephys_path)
    recoring_nwb = se.read_nwb_recording(str(action.path / "data" / "main.nwb"))

    # data has been saved correctly
    np.testing.assert_array_equal(recording_openephys.get_traces(), recoring_nwb.get_traces())
