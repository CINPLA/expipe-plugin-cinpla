import sys
import shutil
from datetime import datetime
from pathlib import Path, PureWindowsPath
import numpy as np

import quantities as pq

import expipe

nwb_main_groups = ["acquisition", "analysis", "processing", "epochs", "general"]
tmp_phy_folders = [".klustakwik2", ".phy", ".spikedetect"]


def query_yes_no(question, default="yes", answer=None):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    if answer is not None:
        assert isinstance(answer, bool)
        return answer
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [[Y]/n] "
    elif default == "no":
        prompt = " [y/[N]] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")


def deltadate(adjustdate, regdate):
    delta = regdate - adjustdate if regdate > adjustdate else datetime.timedelta.max
    return delta


def position_to_dict(depth):
    position = {d[0]: dict() for d in depth}
    for key, num, val, unit in depth:
        probe_key = "probe_{}".format(num)
        position[key][probe_key] = pq.Quantity(val, unit)
    return position


def read_python(path):
    from six import exec_

    path = Path(path).absolute()
    assert path.is_file()
    with path.open("r") as f:
        contents = f.read()
    metadata = {}
    exec_(contents, {}, metadata)
    metadata = {k.lower(): v for (k, v) in metadata.items()}
    return metadata


def write_python(path, dict):
    with Path(path).open("w") as f:
        for k, v in dict.items():
            if isinstance(v, str) and not v.startswith("'"):
                if "path" in k and "win" in sys.platform:
                    f.write(str(k) + " = r'" + str(v) + "'\n")
                else:
                    f.write(str(k) + " = '" + str(v) + "'\n")
            else:
                f.write(str(k) + " = " + str(v) + "\n")


def get_depth_from_surgery(project, entity_id):
    index = 0
    surgery = project.actions[entity_id + "-surgery-implantation"]
    position = {}
    for key, module in surgery.modules.items():
        for probe_key, probe in module.items():
            if probe_key.startswith("probe_") and probe_key.split("_")[-1].isnumeric():
                if key not in position:
                    position[key] = {}
                position[key][probe_key] = probe["position"]
    for key, groups in position.items():
        for group, pos in groups.items():
            if not isinstance(pos, pq.Quantity):
                raise ValueError("Depth of implant " + '"{} {} = {}"'.format(key, group, pos) + " not recognized")
            position[key][group] = pos.astype(float)[2]  # index 2 = z
    return position


def get_depth_from_adjustment(project, action, entity_id):
    DTIME_FORMAT = expipe.core.datetime_format
    try:
        adjustments = project.actions[entity_id + "-adjustment"]
    except KeyError as e:
        return None, None
    adjusts = {}
    for adjust in adjustments.modules.values():
        values = adjust.contents
        adjusts[datetime.strptime(values["date"], DTIME_FORMAT)] = adjust

    regdate = action.datetime
    adjustdates = adjusts.keys()
    adjustdate = min(adjustdates, key=lambda x: deltadate(x, regdate))
    return adjusts[adjustdate]["depth"].contents, adjustdate


def register_depth(project, action, depth=None, answer=None, overwrite=False):
    if len(action.entities) != 1:
        print("Exactly 1 entity is required to register depth.")
        return False
    depth = depth or []
    curr_depth = None
    if len(depth) > 0:
        curr_depth = position_to_dict(depth)
        adjustdate = None
    else:
        curr_depth, adjustdate = get_depth_from_adjustment(project, action, action.entities[0])
        print("Adjust date time: {}\n".format(adjustdate))
    if curr_depth is None:
        print("Cannot find current depth from adjustments.")
        return False

    def last_num(x):
        return "{:03d}".format(int(x.split("_")[-1]))

    print(
        "".join(
            "Depth: {} {} = {}\n".format(key, probe_key, val[probe_key])
            for key, val in curr_depth.items()
            for probe_key in sorted(val, key=lambda x: last_num(x))
        )
    )
    correct = query_yes_no("Are the values correct?", answer=answer)
    if not correct:
        return False
    if "depth" in action.modules and overwrite:
        action.delete_module("depth")
    action.create_module(name="depth", contents=curr_depth)
    return True


def _make_data_path(action, overwrite, suffix=".nwb"):
    action_path = action._backend.path
    project_path = action_path.parent.parent
    data_path = action_path / "data"
    data_path.mkdir(exist_ok=True)
    data_path = data_path / f"main{suffix}"
    if data_path.exists():
        if overwrite:
            if data_path.is_dir():
                shutil.rmtree(data_path)
            else:
                data_path.unlink()
        else:
            raise FileExistsError(
                'The data path to this action "' + str(data_path) + '" exists, optionally use "--overwrite"'
            )
    relpath = data_path.relative_to(project_path)
    action.data["main"] = str(relpath)
    return data_path


def _get_data_path(action):
    if "main" not in action.data:
        return
    try:
        data_path = action.data_path("main")
    except:
        data_path = Path("None")
        pass
    if not data_path.is_dir():
        action_path = action._backend.path
        project_path = action_path.parent.parent
        # data_path = action.data['main']
        data_path = project_path / str(Path(PureWindowsPath(action.data["main"])))
    return data_path


def register_templates(action, templates, overwrite=False):
    """
    Parameters
    ----------
    action : expipe.Action
    templates : list
    """
    if templates is not None:
        for template in templates:
            try:
                action.create_module(template=template)
                print("Adding module " + template)
            except KeyError as e:
                if overwrite:
                    action.delete_module(template)
                    action.create_module(template=template)
                    print("Adding module " + template)
                else:
                    raise KeyError(str(e) + '. Optionally use "overwrite"')
            except Exception as e:
                print(template)
                raise e


def add_units_from_waveform_extractor(
    we, nwbfile, unit_table_name, unit_table_description, write_in_processing_module=False, write_electrodes_column=True
):
    from neuroconv.tools.spikeinterface import add_units_table

    sorting = we.sorting
    # Take care of uneven sparsity
    if "group" in we.sorting.get_property_keys():
        waveform_means, waveform_sds, unit_electrode_indices = [], [], []
        max_channel_in_group = np.max([rec.get_num_channels() for rec in we.recording.split_by("group").values()])
        for unit_id in we.unit_ids:
            wf_mean = we.get_template(unit_id, mode="median")
            wf_sd = we.get_template(unit_id, mode="std")
            channel_indices = we.sparsity.unit_id_to_channel_indices[unit_id]
            if len(channel_indices) < max_channel_in_group:
                num_missing_channels = max_channel_in_group - len(channel_indices)
                wf_mean = np.pad(wf_mean, ((0, 0), (0, num_missing_channels)), mode="constant", constant_values=0)
                wf_sd = np.pad(wf_sd, ((0, 0), (0, num_missing_channels)), mode="constant", constant_values=0)
                max_index = np.max(channel_indices)
                # add fake missing channel indices
                if max_index < len(we.channel_ids) - num_missing_channels:
                    channel_indices = list(channel_indices) + list(
                        range(max_index + 1, max_index + num_missing_channels + 1)
                    )
                else:
                    min_index = np.min(channel_indices)
                    channel_indices = list(channel_indices) + list(range(min_index - num_missing_channels, min_index))
            waveform_means.append(wf_mean)
            waveform_sds.append(wf_sd)
            unit_electrode_indices.append(list(channel_indices))
    else:
        waveform_means = we.get_all_templates()
        waveform_sds = we.get_all_templates(mode="std")
        channel_indices = np.array([list(we.channel_ids).index(ch) for ch in we.channel_ids])
        unit_electrode_indices = [channel_indices] * len(we.unit_ids)

    if not write_electrodes_column:
        unit_electrode_indices = None

    # Add QM and TM properties to add to NWB Units table
    if we.has_extension("quality_metrics"):
        qm = we.load_extension("quality_metrics").get_data()
        for metric in qm.columns:
            sorting.set_property(metric, qm[metric].values)
    if we.has_extension("template_metrics"):
        tm = we.load_extension("template_metrics").get_data()
        for metric in tm.columns:
            sorting.set_property(metric, tm[metric].values)

    add_units_table(
        sorting=sorting,
        nwbfile=nwbfile,
        write_in_processing_module=write_in_processing_module,
        units_table_name=unit_table_name,
        unit_table_description=unit_table_description,
        waveform_means=waveform_means,
        waveform_sds=waveform_sds,
        unit_electrode_indices=unit_electrode_indices,
    )


def generate_phy_restore_files(phy_folder):
    phy_folder = Path(phy_folder)
    phy_restore_folder = phy_folder.parent / f"{phy_folder.name}_restore"
    phy_restore_folder.mkdir(exist_ok=True)

    tsv_files = list(phy_folder.glob("*.tsv"))
    for tsv_file in tsv_files:
        shutil.copy(tsv_file, phy_restore_folder)


def compute_and_set_unit_groups(sorting, recording):
    import spikeinterface as si

    we_mem = si.extract_waveforms(recording, sorting, folder=None, mode="memory", sparse=False)
    extremum_channel_indices = si.get_template_extremum_channel(we_mem, outputs="index")
    unit_groups = recording.get_channel_groups()[np.array(list(extremum_channel_indices.values()))]
    sorting.set_property("group", unit_groups)
