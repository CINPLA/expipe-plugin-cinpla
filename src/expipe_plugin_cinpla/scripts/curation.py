import shutil
import json
from pathlib import Path
import numpy as np
from pynwb import NWBHDF5IO
from pynwb.testing.mock.file import mock_NWBFile
import warnings

import spikeinterface.full as si
import spikeinterface.extractors as se
import spikeinterface.postprocessing as spost
import spikeinterface.qualitymetrics as sqm
import spikeinterface.curation as sc

from spikeinterface.extractors.nwbextractors import _retrieve_unit_table_pynwb

from .utils import _get_data_path, add_units_from_waveform_extractor, compute_and_set_unit_groups

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
        self.curated_we = None
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
        raw_units_path = f"processing/ecephys/RawUnits-{sorter}"
        try:
            sorting_raw = se.read_nwb_sorting(
                self.nwb_path_main,
                unit_table_path=raw_units_path,
                electrical_series_path="acquisition/ElectricalSeries",
            )
        except Exception as e:
            print(f"Could not load raw sorting for {sorter}. Using None: {e}")
            sorting_raw = None
        return sorting_raw

    def load_raw_units(self, sorter):
        raw_units_path = f"processing/ecephys/RawUnits-{sorter}"
        self.io = NWBHDF5IO(self.nwb_path_main, "r")
        nwbfile = self.io.read()
        try:
            units = _retrieve_unit_table_pynwb(nwbfile, raw_units_path)
        except:
            units = None
        return units

    def load_main_units(self):
        self.io = NWBHDF5IO(self.nwb_path_main, "r")
        nwbfile = self.io.read()
        return nwbfile.units

    def construct_curated_units(self):
        if len(self.curated_we.unit_ids) == 0:
            print("No units left after curation.")
            return
        self.io = NWBHDF5IO(self.nwb_path_main, "r")
        nwbfile = self.io.read()
        add_units_from_waveform_extractor(
            self.curated_we,
            nwbfile,
            unit_table_name="curated units",
            unit_table_description=self.curation_description,
            write_in_processing_module=True,
            write_electrodes_column=False,
        )
        return nwbfile.units

    def load_processed_recording(self, sorter):
        preprocessed_json = self.si_path / sorter / "preprocessed.json"
        recording = si.load_extractor(preprocessed_json)
        return recording

    def load_raw_waveforms(self, sorter):
        raw_waveforms_path = self.si_path / sorter / "waveforms"
        raw_we = si.load_waveforms(raw_waveforms_path, with_recording=False)
        recording = self.load_processed_recording(sorter)
        raw_we.set_recording(recording)
        return raw_we

    def apply_curation(self, sorter, curated_sorting):
        sorting_raw = self.load_raw_sorting(sorter)
        if sorting_raw is not None and self.check_sortings_equal(sorting_raw, curated_sorting):
            print(f"No curation was performed for {sorter}. Using raw sorting")
            self.curated_we = None
        else:
            recording = self.load_processed_recording(sorter)

            # if not sort by group, extract dense and estimate group
            if "group" not in curated_sorting.get_property_keys():
                compute_and_set_unit_groups(curated_sorting, recording)

            print("Extracting waveforms on curated sorting")
            self.curated_we = si.extract_waveforms(
                recording,
                curated_sorting,
                folder=None,
                mode="memory",
                max_spikes_per_unit=100,
                sparse=True,
                method="by_property",
                by_property="group",
                n_jobs=-1,
                progress_bar=False,
            )
            # recompute PC, template and quality metrics
            print("Recomputing PC, template and quality metrics")
            _ = spost.compute_principal_components(self.curated_we, progress_bar=False)
            _ = spost.compute_template_metrics(self.curated_we)
            metric_names = []
            for property_name in curated_sorting.get_property_keys():
                for metric_str in metric_metric_str_to_si_metric_name:
                    if metric_str in property_name:
                        new_metric = metric_metric_str_to_si_metric_name[metric_str]
                        if new_metric not in metric_names:
                            metric_names.append(new_metric)
            _ = sqm.compute_quality_metrics(self.curated_we, metric_names=metric_names, n_jobs=-1, progress_bar=False)
            _ = sqm.compute_quality_metrics(self.curated_we, metric_names=metric_names, n_jobs=-1, progress_bar=False)
            print("Done applying curation")

    def load_from_phy(self, sorter):
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

    def get_sortingview_link(self, sorter):
        visualization_json = self.si_path / sorter / "sortingview_links.json"
        if not visualization_json.is_file():
            return "Sorting view link not found."
        with open(visualization_json, "r") as f:
            sortingview_links = json.load(f)
        return sortingview_links["raw"]

    def apply_sortingview_curation(self, sorter, curated_link):
        sorting_raw = self.load_raw_sorting(sorter)
        assert sorting_raw is not None, f"Could not load raw sorting for {sorter}."
        sorting_raw = sorting_raw.save(format="memory")

        # delete NWB-specific properties: id, waveform_mean, and waveform_sd properties
        sorting_raw.delete_property("id")
        sorting_raw.delete_property("waveform_mean")
        sorting_raw.delete_property("waveform_sd")
        sorting_raw.delete_property("electrodes")

        curated_link_ = curated_link.replace("%22", '"')
        curation_str = curated_link_[curated_link_.find("sortingCuration") :]
        uri = curation_str[curation_str.find("sha1://") : -2]
        sorting_curated = sc.apply_sortingview_curation(sorting_raw, uri_or_json=uri)
        # exclude noise
        good_units = sorting_curated.unit_ids[sorting_curated.get_property("noise") == False]
        # create single property for SUA and MUA
        sorting_curated = sorting_curated.select_units(good_units)
        self.apply_curation(sorter, sorting_curated)
        self.curation_description = f"Curation manually performed in Sortingview\nLink: {curated_link}"

    def apply_qc_curator(self, sorter, query):
        raw_we = self.load_raw_waveforms(sorter)
        qm_table = raw_we.load_extension("quality_metrics").get_data()
        units_good = qm_table.query(query).index.values
        # in this case, no split/merge is performed, so we can just select the units
        self.curated_we = raw_we.select_units(units_good, new_folder=None)
        print(f'Applied QM-based curation with query "{query}" for {sorter}:\n{self.curated_we.sorting}')
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
        if self.curated_we is None:
            print("No curation was performed.")
            return

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
            add_units_from_waveform_extractor(
                we=self.curated_we,
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
