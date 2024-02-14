import click
from pathlib import Path
import ruamel.yaml as yaml

from expipe_plugin_cinpla.imports import project
from expipe_plugin_cinpla.scripts import process


# TODO: update this
def attach_to_process(cli):
    @cli.command("ecephys", short_help="Process open ephys recordings.")
    @click.argument("action-id", type=click.STRING)
    @click.option(
        "--probe-path",
        type=click.STRING,
        help="Path to probefile, assumed to be in expipe config directory by default.",
    )
    @click.option(
        "--sorter",
        default="mountainsort5",
        type=click.STRING,
        help="Spike sorter software to be used.",
    )
    @click.option(
        "--acquisition",
        default=None,
        type=click.STRING,
        help="(optional) Open ephys acquisition folder.",
    )
    @click.option(
        "--exdir-path",
        default=None,
        type=click.STRING,
        help="(optional) Exdir file path.",
    )
    @click.option(
        "--no-sorting",
        is_flag=True,
        help="if True spikesorting is not performed.",
    )
    @click.option(
        "--no-lfp",
        is_flag=True,
        help="if True LFP are not extracted.",
    )
    @click.option(
        "--no-par",
        is_flag=True,
        help="if True groups are not sorted in parallel.",
    )
    @click.option(
        "--sort-by",
        type=click.STRING,
        default=None,
        help="sort by property (group).",
    )
    @click.option(
        "--no-mua",
        is_flag=True,
        help="if True MUA are not extracted.",
    )
    @click.option(
        "--spike-params",
        type=click.STRING,
        default=None,
        help="Path to spike sorting params yml file.",
    )
    @click.option(
        "--server",
        type=click.STRING,
        default=None,
        help="'local' or name of expipe server.",
    )
    @click.option(
        "--bad-channels",
        "-bc",
        type=click.STRING,
        multiple=True,
        default=None,
        help="Bad channels to ground.",
    )
    @click.option(
        "--bad-threshold",
        "-bt",
        type=click.FLOAT,
        default=None,
        help="Bad channels to ground.",
    )
    @click.option(
        "--min-fr",
        "-mfr",
        type=click.FLOAT,
        default=None,
        help="Minimum firing rate per unit to retain.",
    )
    @click.option(
        "--min-isi",
        "-mi",
        type=click.FLOAT,
        default=None,
        help="Maximum isi violation rate (if > 0).",
    )
    @click.option(
        "--ref",
        default="cmr",
        type=click.Choice(["cmr", "car", "none"]),
        help="Reference to be used.",
    )
    @click.option(
        "--split-channels",
        default="all",
        type=click.STRING,
        help="It can be 'all', 'half', or list of channels " "used for custom split e.g. [[0,1,2,3,4], [5,6,7,8,9]]",
    )
    @click.option("--ms-before-wf", default=1, type=click.FLOAT, help="ms to clip before waveform peak")
    @click.option("--ms-after-wf", default=2, type=click.FLOAT, help="ms to clip after waveform peak")
    def _process_openephys(
        action_id,
        probe_path,
        sorter,
        no_sorting,
        no_mua,
        no_lfp,
        ms_before_wf,
        ms_after_wf,
        spike_params,
        server,
        acquisition,
        exdir_path,
        bad_channels,
        ref,
        split_channels,
        no_par,
        sort_by,
        bad_threshold,
        min_fr,
        min_isi,
    ):
        if "auto" in bad_channels:
            bad_channels = ["auto"]
        else:
            bad_channels = [int(bc) for bc in bad_channels]
        if no_sorting:
            spikesort = False
        else:
            spikesort = True
        if no_lfp:
            compute_lfp = False
        else:
            compute_lfp = True
        if no_mua:
            compute_mua = False
        else:
            compute_mua = True
        if spike_params is not None:
            spike_params = Path(spike_params)
            if spike_params.is_file():
                with spike_params.open() as f:
                    yaml_ = yaml.YAML(typ="safe", pure=True)
                    params = yaml_.load(f)
            else:
                params = None
        else:
            params = None
        if no_par:
            parallel = False
        else:
            parallel = True

        if split_channels == "custom":
            import ast

            split_channels = ast.literal_eval(split_channels)
            assert isinstance(split_channels, list), (
                "With custom reference the list of channels has to be provided " "with the --split-channels argument"
            )
        process.process_openephys(
            project=project,
            action_id=action_id,
            probe_path=probe_path,
            sorter=sorter,
            spikesort=spikesort,
            compute_lfp=compute_lfp,
            compute_mua=compute_mua,
            spikesorter_params=params,
            server=server,
            acquisition_folder=acquisition,
            exdir_file_path=exdir_path,
            bad_channels=bad_channels,
            ref=ref,
            split=split_channels,
            ms_before_wf=ms_before_wf,
            ms_after_wf=ms_after_wf,
            parallel=parallel,
            sort_by=sort_by,
            bad_threshold=bad_threshold,
            firing_rate_threshold=min_fr,
            isi_viol_threshold=min_isi,
        )
