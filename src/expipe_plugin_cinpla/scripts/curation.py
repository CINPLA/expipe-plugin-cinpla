# -*- coding: utf-8 -*-
import shutil
import warnings

import numpy as np
import spikeinterface as si

from .utils import (
    _get_data_path,
    add_units_from_sorting_analyzer,
    compute_and_set_unit_groups,
)

warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)


metric_metric_str_to_si_metric_name = {
    "amplitude_cutoff": "amplitude_cutoff",
    "amplitude_median": "amplitude_median",
    "amplitude_cv": "amplitude_cv",
    "isi_violations": "isi_violation",
    "firing_range": "firing_range",
    "firing_rate": "firing_rate",
    "l_ratio": "l_ratio",
    "d_prime": "d_prime",
    "rp_violations": "rp_violation",
    "presence_ratio": "presence_ratio",
    "nn_": "nearest_neighbor",
    "silhouette": "silhouette",
    "snr": "snr",
    "sync_spike_": "synchrony",
}


class SortingCurator:
    def __init__(self, project) -> None:
        self.project = project
        self.action = None
        self.nwb_path_tmp = None
        self.nwb_path_main = None
        self.nwbfile = None
        self.io = None
        self.si_path = None
        self.curated_sorting = None
        self.curated_analyzer = None
        self.curation_description = ""

    def set_action(self, action_id):
        self.action = self.project.actions[action_id]
        self.remove_tmp_files()
        nwb_path = _get_data_path(self.action)
        nwb_path_tmp = nwb_path.parent / "main_tmp.nwb"
        if nwb_path_tmp.is_file():
            nwb_path_tmp.unlink()
        self.nwb_path_tmp = nwb_path_tmp
        self.nwb_path_main = nwb_path
        self.si_path = self.nwb_path_tmp.parent / "spikeinterface"

    def check_sortings_equal(self, sorting1, sorting2):
        if sorting1.get_num_units() != sorting2.get_num_units():
            return False

        if not np.array_equal(sorting1.unit_ids.astype(str), sorting2.unit_ids.astype(str)):
            return False

        if not np.array_equal(sorting1.to_spike_vector(), sorting2.to_spike_vector()):
            return False

        return True

    def load_raw_sorting(self, sorter):
        import spikeinterface.extractors as se

        raw_units_path = f"processing/ecephys/RawUnits-{sorter}"
        try:
            sorting_raw = se.read_nwb_sorting(
                self.nwb_path_main,
                unit_table_path=raw_units_path,
                electrical_series_path="acquisition/ElectricalSeries",
            )
            return sorting_raw
        except Exception as e:
            print(f"Could not load raw sorting for {sorter}. Using None.\nError: {e}")
            return None

    def load_raw_units(self, sorter):
        from pynwb import NWBHDF5IO
        from spikeinterface.extractors.nwbextractors import _retrieve_unit_table_pynwb

        raw_units_path = f"processing/ecephys/RawUnits-{sorter}"
        self.io = NWBHDF5IO(self.nwb_path_main, "r")
        nwbfile = self.io.read()
        try:
            units = _retrieve_unit_table_pynwb(nwbfile, raw_units_path)
            return units
        except Exception as e:
            print(f"Could not load raw units for {sorter}. Using None: {e}")
            return None

    def load_main_units(self):
        from pynwb import NWBHDF5IO

        self.io = NWBHDF5IO(self.nwb_path_main, "r")
        nwbfile = self.io.read()
        return nwbfile.units

    def construct_curated_units(self):
        if self.curated_analyzer is None:
            print("No units left after curation.")
            return
        from pynwb import NWBHDF5IO

        self.io = NWBHDF5IO(self.nwb_path_main, "r")
        nwbfile = self.io.read()
        add_units_from_sorting_analyzer(
            self.curated_analyzer,
            nwbfile,
            unit_table_name="CuratedUnits",
            unit_table_description=self.curation_description,
            write_in_processing_module=True,
            write_electrodes_column=False,
        )
        return nwbfile.processing["ecephys"].data_interfaces["CuratedUnits"]

    def load_processed_recording(self, sorter):
        preprocessed_json = self.si_path / sorter / "preprocessed.json"
        try:
            recording = si.load_extractor(preprocessed_json)
        except Exception:
            recording = si.load_extractor(preprocessed_json, base_folder=self.si_path / sorter / "recording_cmr")
        return recording

    def load_raw_analyzer(self, sorter):
        if (self.si_path / sorter / "waveforms").is_dir():
            waveforms_folder = self.si_path / sorter / "waveforms"
            raw_analyzer = si.load_waveforms(waveforms_folder, output="SortingAnalyzer")
        elif (self.si_path / sorter / "analyzer").is_dir():
            raw_analyzer = si.load_sorting_analyzer(self.si_path / sorter / "analyzer")
        else:
            return None
        recording = self.load_processed_recording(sorter)
        raw_analyzer.set_temporary_recording(recording)
        return raw_analyzer

    def apply_curation(self, sorter, curated_sorting):
        sorting_raw = self.load_raw_sorting(sorter)
        if sorting_raw is not None and self.check_sortings_equal(sorting_raw, curated_sorting):
            print(f"No curation was performed for {sorter}. Using raw sorting")
            self.curated_analyzer = None
        else:
            import spikeinterface.curation as sc
            import spikeinterface.qualitymetrics as sqm

            si.set_global_job_kwargs(n_jobs=-1, progress_bar=False)

            recording = self.load_processed_recording(sorter)

            # remove excess spikes
            print("Removing excess spikes from curated sorting")
            curated_sorting = sc.remove_excess_spikes(curated_sorting, recording=recording)

            # if "group" is not available or some missing groups, extract dense and estimate group
            compute_and_set_unit_groups(curated_sorting, recording)

            # sort by group and phy ID (if present)
            if "original_cluster_id" in curated_sorting.get_property_keys():
                sort_unit_indices = np.lexsort(
                    (curated_sorting.get_property("original_cluster_id"), curated_sorting.get_property("group"))
                )
            else:
                sort_unit_indices = np.argsort(curated_sorting.get_property("group"))
            curated_sorting = curated_sorting.select_units(curated_sorting.unit_ids[sort_unit_indices])

            # load extension params from previously computed raw analyzer
            raw_analyzer = self.load_raw_analyzer(sorter)
            if raw_analyzer is None:
                print("No raw analyzer found. Using default values.")
                ms_before = 1
                ms_after = 2
                n_components = 3
            else:
                ms_before = raw_analyzer.get_extension("waveforms").params["ms_before"]
                ms_after = raw_analyzer.get_extension("waveforms").params["ms_after"]
                n_components = raw_analyzer.get_extension("principal_components").params["n_components"]

            self.curated_analyzer = si.create_sorting_analyzer(
                curated_sorting,
                recording,
                sparse=True,
                method="by_property",
                by_property="group",
            )
            print("Recomputing all extensions")

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
            self.curated_analyzer.compute(extension_list)
            metric_names = []
            for property_name in curated_sorting.get_property_keys():
                for metric_str in metric_metric_str_to_si_metric_name:
                    if metric_str in property_name:
                        new_metric = metric_metric_str_to_si_metric_name[metric_str]
                        if new_metric not in metric_names:
                            metric_names.append(new_metric)
            _ = sqm.compute_quality_metrics(self.curated_analyzer, metric_names=metric_names)
            print("Done applying curation")

    def load_from_phy(self, sorter):
        import spikeinterface.extractors as se

        phy_path = self.si_path / sorter / "phy"

        sorting_phy = se.read_phy(phy_path, exclude_cluster_groups=["noise"])
        sorting_phy = sorting_phy.rename_units(sorting_phy.unit_ids.astype(str))
        print(f"Loaded Phy-curated sorting for {sorter}:\n{sorting_phy}")
        sorting_phy.set_property("group", sorting_phy.get_property("channel_group"))
        self.apply_curation(sorter, sorting_phy)
        self.curation_description = "Curation manually performed in Phy."

    def get_phy_run_command(self, sorter):
        phy_path = (self.si_path / sorter / "phy" / "params.py").absolute()
        phy_run_command = f"phy template-gui {phy_path}"
        return phy_run_command

    def apply_qc_curator(self, sorter, query):
        raw_analyzer = self.load_raw_analyzer(sorter)
        qm_table = raw_analyzer.get_extension("quality_metrics").get_data()
        units_good = qm_table.query(query).index.values
        # in this case, no split/merge is performed, so we can just select the units
        self.curated_analyzer = raw_analyzer.select_units(units_good)
        print(f'Applied QM-based curation with query "{query}" for {sorter}:\n{self.curated_analyzer.sorting}')
        self.curation_description = f"Automatic curation based on quality metrics.\nQuery: {query}"

    def restore_phy(self, sorter):
        phy_folder = self.si_path / sorter / "phy"
        phy_restore_folder = phy_folder.parent / "phy_restore"

        if (phy_folder / "spike_clusters.npy").is_file():
            print(f"Restoring phy curation for {sorter}.")
            (phy_folder / "spike_clusters.npy").unlink()
        # delete curated files
        tsv_files = [p for p in phy_folder.iterdir() if p.suffix == ".tsv"]
        for tsv_file in tsv_files:
            tsv_file.unlink()
        # restore original files
        restore_tsv_files = [p for p in phy_restore_folder.iterdir() if p.suffix == ".tsv"]
        for restore_tsv_file in restore_tsv_files:
            shutil.copy(restore_tsv_file, phy_folder)

    def save_to_nwb(self):
        if self.curated_analyzer is None:
            print("No curation was performed.")
            return
        from pynwb import NWBHDF5IO

        # trick to get rid of Units first
        with NWBHDF5IO(self.nwb_path_main, mode="r") as read_io:
            nwbfile_in = read_io.read()

            # delete main unit table
            if nwbfile_in.units is not None:
                print("Deleting main unit table")
                nwbfile_in.units.reset_parent()
                nwbfile_in.fields["units"] = None

            with NWBHDF5IO(self.nwb_path_tmp, mode="w") as export_io:
                export_io.export(src_io=read_io, nwbfile=nwbfile_in)

        # write new units
        with NWBHDF5IO(self.nwb_path_tmp, mode="a") as io:
            nwbfile_out = io.read()
            print("Adding curated units table")
            add_units_from_sorting_analyzer(
                sorting_analyzer=self.curated_analyzer,
                nwbfile=nwbfile_out,
                unit_table_name="units",
                unit_table_description=self.curation_description,
                write_in_processing_module=False,
            )
            io.write(nwbfile_out)

        self.nwb_path_main.unlink()
        self.nwb_path_tmp.rename(self.nwb_path_main)
        print("Done saving to NWB")

    def remove_tmp_files(self):
        if self.nwb_path_tmp is not None and self.nwb_path_tmp.is_file():
            self.nwb_path_tmp.unlink()
        if self.io is not None:
            self.io.close()
        if self.nwbfile is not None:
            del self.nwbfile
            self.nwbfile = None
