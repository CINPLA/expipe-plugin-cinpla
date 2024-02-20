import pytest
from datetime import datetime
from expipe_plugin_cinpla.scripts.register import register_entity, register_openephys_recording
from expipe_plugin_cinpla.scripts.process import process_ecephys
from expipe_plugin_cinpla.scripts.curation import SortingCurator


@pytest.mark.dependency()
def test_register_entity():
    project = pytest.PROJECT
    rat_id = "008"
    user = "pytest"
    sex = "M"
    species = "Rattus norvegicus"
    message = None
    location = "animal-facility"
    tag = []
    overwrite = False
    birthday = datetime(2022, 10, 8)
    templates = []

    register_entity(project, rat_id, user, species, sex, message, location, tag, overwrite, birthday, templates)

    assert rat_id in project.entities


@pytest.mark.dependency(depends=["test_register_entity"])
def test_register_openephys():
    project = pytest.PROJECT
    openephys_path = pytest.TEST_DATA_PATH / "openephys" / "008_2022-12-08_17-23-24_2"
    probe_path = pytest.TEST_DATA_PATH / "tetrode_32_openephys.json"
    rat_id = "008"
    action_id = None
    depth = None
    overwrite = False
    include_events = True
    user = "pytest"
    session = None
    location = "recording-room1"
    message = (None,)
    tags = (None,)
    delete_raw_data = (False,)
    correct_depth_answer = ("y",)
    register_depth = (False,)

    register_openephys_recording(
        project,
        action_id,
        openephys_path,
        probe_path,
        depth,
        overwrite,
        include_events,
        rat_id,
        user,
        session,
        location,
        message=None,
        tags=None,
        delete_raw_data=False,
        correct_depth_answer="y",
        register_depth=False,
    )
    assert "008-081222-2" in project.actions


@pytest.mark.dependency(depends=["test_register_openephys"])
def test_process():
    import pynwb

    project = pytest.PROJECT
    action_id = "008-081222-2"
    sorter = "mountainsort5"
    spikesort = True
    compute_lfp = True
    compute_mua = True
    spikesorter_params = None
    bad_channel_ids = None
    reference = "cmr"
    split = "half"
    spikesort_by_group = True
    bad_threshold = 2
    ms_before = 1
    ms_after = 2
    metric_names = ["firing_rate", "presence_ratio", "isi_violation"]
    overwrite = False

    process_ecephys(
        project,
        action_id,
        sorter,
        spikesort=spikesort,
        compute_lfp=compute_lfp,
        compute_mua=compute_mua,
        spikesorter_params=spikesorter_params,
        bad_channel_ids=bad_channel_ids,
        reference=reference,
        split=split,
        spikesort_by_group=spikesort_by_group,
        bad_threshold=bad_threshold,
        ms_before=ms_before,
        ms_after=ms_after,
        metric_names=metric_names,
        overwrite=overwrite,
        plot_sortingview=False,
        n_components=2,  # this is needed because there are very few waveforms!
    )

    nwbfile_path = project.actions[action_id].path / "data" / "main.nwb"
    assert nwbfile_path.is_file()

    with pynwb.NWBHDF5IO(str(nwbfile_path), "r") as io:
        nwbfile = io.read()
        assert f"RawUnits-{sorter}" in nwbfile.processing["ecephys"].data_interfaces


@pytest.mark.dependency(depends=["test_process"])
def test_curate():
    import spikeinterface.extractors as se

    project = pytest.PROJECT
    sorter = "mountainsort5"
    curator = SortingCurator(project)
    action_id = "008-081222-2"
    curator.set_action(action_id)
    sorting_raw = curator.load_raw_sorting(sorter)
    curator.apply_qc_curator(sorter, query="firing_rate > 2")
    curator.save_to_nwb()
    sorting_curated = se.read_nwb_sorting(
        project.actions[action_id].path / "data" / "main.nwb",
        unit_table_path="units",
        electrical_series_path="acquisition/ElectricalSeries",
    )
    assert len(sorting_curated.unit_ids) <= len(sorting_raw.unit_ids)


if __name__ == "__main__":
    from conftest import pytest_configure

    pytest_configure()

    test_register_entity()
    test_register_openephys()
    test_process()
    test_curate()
