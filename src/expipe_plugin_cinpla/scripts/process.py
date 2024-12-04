# -*- coding: utf-8 -*-
import contextlib
import json
import os
import shutil
import time

import numpy as np

from expipe_plugin_cinpla.scripts import utils


def process_ecephys(
    project,
    action_id,
    sorter,
    spikesort=True,
    compute_lfp=True,
    compute_mua=False,
    spikesorter_params=None,
    bad_channel_ids=None,
    reference=None,
    split=None,
    spikesort_by_group=True,
    bad_threshold=2,
    ms_before=1,
    ms_after=2,
    metric_names=None,
    overwrite=False,
    singularity_image=None,
    n_components=3,
    verbose=True,
):
    import warnings

    import spikeinterface as si
    import spikeinterface.curation as sc
    import spikeinterface.exporters as sexp
    import spikeinterface.extractors as se
    import spikeinterface.preprocessing as spre
    import spikeinterface.qualitymetrics as sqm
    import spikeinterface.sorters as ss
    from neuroconv.tools.spikeinterface import add_recording
    from pynwb import NWBHDF5IO

    from .utils import add_units_from_sorting_analyzer, compute_and_set_unit_groups

    warnings.filterwarnings("ignore")

    t_start = time.time()

    action = project.actions[action_id]
    nwb_path = utils._get_data_path(action)
    nwb_path_tmp = nwb_path.parent / "main_tmp.nwb"

    # clean up tmp NWB file in case of crash
    if nwb_path_tmp.is_file():
        nwb_path_tmp.unlink()

    si.set_global_job_kwargs(n_jobs=-1, progress_bar=False)

    if overwrite:
        if verbose:
            print("\nCleaning up existing NWB file")
        # trick to get rid of open synchronous files issue
        nwb_path2 = nwb_path.parent / "main2_tmp.nwb"
        shutil.copy(nwb_path, nwb_path2)

        # export NWB file and skip: processed timeseries, units
        with NWBHDF5IO(nwb_path2, "r") as read_io:
            nwbfile = read_io.read()
            # delete main unit table
            if nwbfile.units is not None:
                if verbose:
                    print("Deleting main unit table")
                nwbfile.units.reset_parent()
                nwbfile.fields["units"] = None
            # remove processed timeseries
            if "ecephys" in nwbfile.processing:
                for data_interface in nwbfile.processing["ecephys"].data_interfaces.copy():
                    if compute_lfp and "LFP" in data_interface:
                        if verbose:
                            print(f"\tRemoving {data_interface}")
                        di = nwbfile.processing["ecephys"].data_interfaces.pop(data_interface)
                        di.reset_parent()
                        for child in di.children:
                            child.reset_parent()
                    if compute_mua and "Processed" in data_interface:
                        if verbose:
                            print(f"\tRemoving {data_interface}")
                        di = nwbfile.processing["ecephys"].data_interfaces.pop(data_interface)
                        di.reset_parent()
                        for child in di.children:
                            child.reset_parent()
                    if spikesort and sorter in data_interface:
                        if verbose:
                            print(f"\tRemoving {data_interface}")
                        di = nwbfile.processing["ecephys"].data_interfaces.pop(data_interface)
                        di.reset_parent()
                        for child in di.children:
                            child.reset_parent()

            with NWBHDF5IO(nwb_path_tmp, "w") as export_io:
                export_io.export(src_io=read_io, nwbfile=nwbfile)
        nwb_path2.unlink()
    else:
        shutil.copy(nwb_path, nwb_path_tmp)

    recording = se.read_nwb_recording(nwb_path_tmp, electrical_series_path="acquisition/ElectricalSeries")

    auto_detection = False
    if bad_channel_ids is not None:
        if "auto" not in bad_channel_ids and len(bad_channel_ids) > 0:
            recording_active = recording.remove_channels(bad_channel_ids)
        else:
            auto_detection = True
            recording_active = recording
    else:
        recording_active = recording

    # apply filtering and cmr
    if verbose:
        duration = np.round(recording.get_total_duration(), 2)
        print(f"\nPreprocessing recording:\n\tNum channels: {recording.get_num_channels()}\n\tDuration: {duration} s")
    si_folder = nwb_path.parent / "spikeinterface"
    output_base_folder = si_folder / sorter
    if output_base_folder.is_dir():
        shutil.rmtree(output_base_folder)

    freq_min_hp = 300
    freq_max_hp = 3000
    freq_min_lfp = 1
    freq_max_lfp = 300
    freq_resample_lfp = 1000
    freq_resample_mua = 1000
    order_hp = 5

    recording_bp = spre.bandpass_filter(
        recording_active, freq_min=freq_min_hp, freq_max=freq_max_hp, filter_order=order_hp
    )

    if reference is not None:
        if reference.lower() == "cmr":
            reference = "median"
        elif reference.lower() == "car":
            reference = "average"
        else:
            raise Exception("'reference' can be either 'cmr' or 'car'")
        if split == "all":
            recording_cmr = spre.common_reference(recording_bp, operator=reference)
        elif split == "half":
            num_half = recording.get_num_channels() // 2
            groups = [
                recording.channel_ids[:num_half],
                recording.channel_ids[num_half:],
            ]
            recording_cmr = spre.common_reference(recording_bp, groups=groups, operator=reference)
        else:
            if isinstance(split, list):
                recording_cmr = spre.common_reference(recording_bp, groups=split, operator=reference)
            else:
                raise Exception("'split' must be a list of lists")
    else:
        recording_cmr = recording

    if auto_detection:
        bad_channel_ids, _ = spre.detect_bad_channels(recording_cmr, method="std", std_mad_threshold=bad_threshold)
        if len(bad_channel_ids) > 0:
            if verbose:
                print(f"\tDetected bad channels: {bad_channel_ids}")
            recording_cmr = recording_cmr.remove_channels(bad_channel_ids)
            recording_active = recording.channel_slice(channel_ids=recording_cmr.channel_ids)

    if verbose:
        print(f"\tActive channels: {len(recording_active.channel_ids)}")

    if compute_lfp:
        recording_lfp = spre.bandpass_filter(recording_active, freq_min=freq_min_lfp, freq_max=freq_max_lfp)
        recording_lfp = spre.resample(recording_lfp, freq_resample_lfp)
        # make sure to not override the electrodes table
        recording_lfp.set_property("group_name", [f"tetrode{gr}" for gr in recording_lfp.get_channel_groups()])
    if compute_mua:
        recording_mua = spre.resample(spre.rectify(recording_active), freq_resample_mua)
        # make sure to not override the electrodes table
        recording_mua.set_property("group_name", [f"tetrode{gr}" for gr in recording_lfp.get_channel_groups()])

    if spikesort:
        if verbose:
            print("\tSaving preprocessed recording")
        recording_cmr = recording_cmr.save(folder=output_base_folder / "recording_cmr", overwrite=True, verbose=False)

        if spikesorter_params is None:
            spikesorter_params = {}
        output_folder = output_base_folder / "spikesorting"
        try:
            # save in data/processing
            if singularity_image:
                if verbose:
                    print(f"\nSpike sorting with {sorter} using Singularity")
                # the redirect stdout doesn't work nicely with singularity
                context = contextlib.nullcontext()
            else:
                if verbose:
                    print(f"\nSpike sorting with {sorter} using installed sorter")
                context = contextlib.redirect_stdout(None)

            with context:
                if spikesort_by_group:
                    sorting = ss.run_sorter_by_property(
                        sorter,
                        recording_cmr,
                        folder=output_folder,
                        grouping_property="group",
                        verbose=False,
                        delete_output_folder=True,
                        remove_existing_folder=True,
                        singularity_image=singularity_image,
                        **spikesorter_params,
                    )
                else:
                    sorting = ss.run_sorter(
                        sorter,
                        recording_cmr,
                        folder=output_folder,
                        verbose=False,
                        delete_output_folder=True,
                        remove_existing_folder=True,
                        singularity_image=singularity_image,
                        **spikesorter_params,
                    )
        except Exception as e:
            shutil.rmtree(output_folder)
            raise Exception(f"Spike sorting failed:\n\n{e}")
        if verbose:
            print(f"\tFound {len(sorting.get_unit_ids())} units!")

        # remove excess spikes from KS, which sometimes finds spikes beyond the recording duration
        sorting = sc.remove_excess_spikes(sorting, recording=recording_cmr)

        # remove units with less than n_components spikes
        num_spikes = sorting.count_num_spikes_per_unit()
        selected_units = sorting.unit_ids[np.array(list(num_spikes.values())) >= n_components]
        n_too_few_spikes = int(len(sorting.unit_ids) - len(selected_units))
        print(f"\tRemoved {n_too_few_spikes} units with less than {n_components} spikes")
        sorting = sorting.select_units(selected_units)

        # extract waveforms
        if verbose:
            print("\nPostprocessing")
        # if not sort by group, extract dense and estimate group
        if "group" not in sorting.get_property_keys():
            compute_and_set_unit_groups(sorting, recording_cmr)

        sparsity_temp_folder = si_folder / "tmp"
        if sparsity_temp_folder.is_dir():
            shutil.rmtree(sparsity_temp_folder)

        sorting_analyzer = si.create_sorting_analyzer(
            sorting,
            recording_cmr,
            format="binary_folder",
            folder=output_base_folder / "analyzer",
            overwrite=True,
            sparse=True,
            method="by_property",
            by_property="group",
        )

        if verbose:
            print("\tComputing extensions")
        extension_list = {
            "noise_levels": {},
            "random_spikes": {},
            "waveforms": {"ms_before": ms_before, "ms_after": ms_after},
            "templates": {"operators": ["average", "std", "median"]},
            "spike_amplitudes": {},
            "unit_locations": {},
            "correlograms": {},
            "template_similarity": {},
            "isi_histograms": {},
            "principal_components": {"n_components": n_components},
            "template_metrics": {},
        }
        sorting_analyzer.compute(extension_list, n_jobs=-1, progress_bar=False)
        if verbose:
            print("\tComputing QC metrics")
        _ = sqm.compute_quality_metrics(sorting_analyzer, metric_names=metric_names)

        if verbose:
            print("\tExporting to phy")
        phy_folder = output_base_folder / "phy"
        if phy_folder.is_dir():
            shutil.rmtree(phy_folder)
        sexp.export_to_phy(
            sorting_analyzer,
            output_folder=phy_folder,
            copy_binary=True,
            use_relative_path=True,
            verbose=False,
        )
        # generate files to be used with restore
        utils.generate_phy_restore_files(phy_folder)

    if verbose:
        print("\nWriting to NWB")
    nwb_path.unlink()
    try:
        with NWBHDF5IO(nwb_path_tmp, mode="r") as read_io:
            nwbfile_out = read_io.read()
            if spikesort:
                if verbose:
                    print("\tAdding units table")

                add_units_from_sorting_analyzer(
                    sorting_analyzer=sorting_analyzer,
                    nwbfile=nwbfile_out,
                    unit_table_name=f"RawUnits-{sorter}",
                    unit_table_description=f"Raw units from {sorter} output",
                    write_in_processing_module=True,
                )
            metadata_ecephys = {}
            # assign existing device
            device_name = nwbfile_out.devices[list(nwbfile_out.devices.keys())[0]].name
            metadata_ecephys["Ecephys"] = {
                "Device": [
                    {"name": device_name, "description": nwbfile_out.devices[device_name].description},
                ]
            }
            if compute_lfp:
                if verbose:
                    print("\tAdding LFP")
                recording_lfp.set_property("group_name", recording_lfp.get_channel_groups())
                add_recording(recording_lfp, nwbfile=nwbfile_out, write_as="lfp", metadata=metadata_ecephys)
            if compute_mua:
                if verbose:
                    print("\tAdding MUA")
                # Add metadata about new electrical series
                metadata_ecephys["Ecephys"]["ElectricalSeriesMUA"] = {
                    "name": "ElectricalSeriesMUA",
                    "description": "Rectified signal representing Multi-Unit Activity",
                }
                recording_mua.set_property("group_name", recording_mua.get_channel_groups())
                add_recording(
                    recording_mua,
                    nwbfile=nwbfile_out,
                    write_as="processed",
                    metadata=metadata_ecephys,
                    es_key="ElectricalSeriesMUA",
                )

            with NWBHDF5IO(nwb_path, mode="w") as export_io:
                export_io.export(src_io=read_io, nwbfile=nwbfile_out)
    except Exception as e:
        # restore NWB file
        if verbose:
            print(f"Error exporting to NWB: {e}")
        if nwb_path.is_file():
            nwb_path.unlink()
        shutil.copy(nwb_path_tmp, nwb_path)

    # clean up
    if verbose:
        print("Cleaning up")
    provenance_file = output_base_folder / "recording_cmr" / "provenance.json"
    if not provenance_file.is_file():
        (output_base_folder / "recording_cmr").mkdir(parents=True, exist_ok=True)
        recording_cmr.dump_to_json(output_base_folder / "recording_cmr" / "provenance.json")
    with open(output_base_folder / "recording_cmr" / "provenance.json") as f:
        provenance = json.load(f)
    provenance_str = json.dumps(provenance)
    provenance_str = provenance_str.replace("../../../main_tmp.nwb", str(nwb_path))
    provenance_str = provenance_str.replace('"relative_paths": true', '"relative_paths": false')
    preprocessed_file = output_base_folder / "preprocessed.json"
    preprocessed_file.write_text(provenance_str)

    if spikesort:
        # update analyzer path
        analyer_recording_str = provenance_str.replace(
            str(nwb_path), os.path.relpath(nwb_path, str(output_base_folder / "analyzer"))
        )
        analyzer_recording_json = output_base_folder / "analyzer" / "recording.json"
        analyzer_recording_json.write_text(analyer_recording_str)

    if (output_base_folder / "recording_cmr").is_dir():
        shutil.rmtree(output_base_folder / "recording_cmr")
    try:
        nwb_path_tmp.unlink()
    except Exception as e:
        print(f"Could not remove: {nwb_path_tmp}")
        raise e

    if verbose:
        print("\tSaved to NWB: ", nwb_path)
        print(f"Total processing time: {np.round(time.time() - t_start)}s")


def clean_up(project, action_id, sorter):
    action = project.actions[action_id]
    nwb_path = utils._get_data_path(action)
    si_folder = nwb_path.parent / "spikeinterface"
    sorter_folder = si_folder / sorter
    nwb_path_tmp = nwb_path.parent / "main_tmp.nwb"

    if nwb_path_tmp.is_file():
        nwb_path_tmp.unlink()
    if sorter_folder.is_dir():
        shutil.rmtree(sorter_folder)
    if len([p for p in si_folder.iterdir()]) == 0:
        shutil.rmtree(si_folder)
