import ast
from expipe_plugin_cinpla.scripts import process
from .utils import BaseViewWithLog

metric_names = [
    "num_spikes",
    "firing_rate",
    "presence_ratio",
    "snr",
    "isi_violation",
    "rp_violation",
    "amplitude_cutoff",
    "amplitude_median",
    "amplitude_cv",
    "synchrony",
    "firing_range",
    "isolation_distance",
    "l_ratio",
    "d_prime",
    "nearest_neighbor",
    "silhouette",
]


def process_ecephys_view(project):
    import ipywidgets
    import spikeinterface.sorters as ss
    from .utils import SearchSelectMultiple, required_values_filled, ParameterSelectList
    from ..scripts.utils import _get_data_path

    all_actions = project.actions

    action_names = []
    for action_name in all_actions:
        # if exdir_path is None:
        action = all_actions[action_name]
        data_path = _get_data_path(action)
        if data_path is not None and data_path.name == "main.nwb":
            si_path = data_path.parent / "spikeinterface"
            if si_path.is_dir():
                action_names.append(f"{action_name} -- (P)")
            else:
                action_names.append(f"{action_name} -- (U)")

    action_ids = SearchSelectMultiple(action_names, description="*Actions")

    overwrite = ipywidgets.Checkbox(description="Overwrite", value=True)

    available_sorters = ss.available_sorters()
    # klusta and YASS are legacy
    available_sorters.remove("klusta")
    available_sorters.remove("yass")
    installed_sorters = ss.installed_sorters()

    sorters_string_to_name = dict()
    for sorter in available_sorters:
        if sorter in installed_sorters:
            sorters_string_to_name[f"{sorter} (I)"] = sorter
        else:
            sorters_string_to_name[f"{sorter} (U)"] = sorter
    options = list(sorters_string_to_name.keys())
    initial_value = [s for s in options if "mountainsort5" in s][0]
    sorter = ipywidgets.Dropdown(
        description="Sorter",
        options=options,
        value=initial_value,
        layout={"width": "initial"},
    )
    sorter_initial_params = ss.get_default_sorter_params(sorters_string_to_name[sorter.value])
    num_params = len(sorter_initial_params)
    sorter_param = ParameterSelectList(
        description="Spike sorting options",
        param_dict=sorter_initial_params,
        layout={"width": "initial", "height": f"{30 * num_params}px", "overflow": "scroll"},
    )
    sorter_param.layout.visibility = "hidden"

    spikesort_by_group = ipywidgets.ToggleButton(description="Sort by group", value=True, layout={"width": "initial"})
    use_singularity = ipywidgets.ToggleButton(description="Use singularity", value=False, layout={"width": "initial"})

    compute_lfp = ipywidgets.ToggleButton(
        value=True,
        description="Compute LFP",
        disabled=False,
        button_style="",  # 'success', 'info', 'warning', 'danger' or ''
        tooltip="Compute LFP",
        icon="check",
        layout={"width": "initial"},
    )
    compute_mua = ipywidgets.ToggleButton(
        value=False,
        description="Compute MUA",
        disabled=False,
        button_style="",  # 'success', 'info', 'warning', 'danger' or ''
        tooltip="Compute MUA",
        icon="check",
        layout={"width": "initial"},
    )
    spikesort = ipywidgets.ToggleButton(
        value=True,
        description="Spikesort",
        disabled=False,
        button_style="",  # 'success', 'info', 'warning', 'danger' or ''
        tooltip="Spike sort data",
        icon="check",
        layout={"width": "initial"},
    )

    show_params = ipywidgets.ToggleButton(
        value=False,
        description="Params",
        disabled=False,
        button_style="",  # 'success', 'info', 'warning', 'danger' or ''
        tooltip="Show spike sorting specific params",
        icon="edit",
        layout={"width": "initial"},
    )

    other_settings = ipywidgets.ToggleButton(
        value=False,
        description="Other setting",
        disabled=False,
        button_style="",  # 'success', 'info', 'warning', 'danger' or ''
        tooltip="Modify other processing settings",
        icon="edit",
        layout={"width": "initial"},
    )

    reference = ipywidgets.RadioButtons(
        options=["cmr", "car", "none"], description="Reference:", disabled=False, layout={"width": "initial"}
    )
    reference.layout.visibility = "hidden"

    split_group = ipywidgets.RadioButtons(
        options=["all", "half", "custom"],
        value="half",
        description="Ref channels:",
        disabled=False,
        layout={"width": "initial"},
    )
    split_group.layout.visibility = "hidden"

    custom_split = ipywidgets.Text(
        description="Split",
        value="",
        placeholder="(e.g. [[1,2,3,...], [4,5,6,...]])",
    )
    custom_split.layout.visibility = "hidden"

    bad_channel_ids = ipywidgets.Text(
        description="Bad channels",
        value="",
        placeholder="(e.g. 5, 8, 12 or auto)",
    )
    bad_channel_ids.layout.visibility = "hidden"

    bad_threshold = ipywidgets.FloatText(
        description="Auto threshold",
        value=2,
        tooltip="(e.g 2, default = 2 * std)",
    )
    bad_threshold.layout.visibility = "hidden"

    quality_metrics = ipywidgets.SelectMultiple(
        options=metric_names, value=metric_names, layout={"height": "200px"}, description="QM:"
    )
    quality_metrics.layout.visibility = "hidden"

    rightbox = ipywidgets.VBox(
        [
            ipywidgets.Label("Processing options", layout={"width": "initial"}),
            overwrite,
            spikesort,
            compute_lfp,
            compute_mua,
            other_settings,
            bad_channel_ids,
            bad_threshold,
            reference,
            split_group,
            custom_split,
        ],
        layout={"width": "initial"},
    )

    run_button = ipywidgets.Button(
        description="Process", layout={"height": "50px", "width": "50%"}, style={"button_color": "pink"}
    )
    run_status_label = ipywidgets.Button(
        description="Status: Ready",
        disabled=True,
        layout={"height": "50px", "width": "50%"},
        style={"button_color": "green"},
    )
    run_box = ipywidgets.HBox([run_button, run_status_label])

    left_box = ipywidgets.VBox([sorter, spikesort_by_group, use_singularity, show_params, sorter_param])

    middle_box = ipywidgets.VBox([action_ids, quality_metrics])

    main_box = ipywidgets.VBox([ipywidgets.HBox([left_box, middle_box, rightbox]), run_box], layout={"width": "100%"})
    main_box.layout.display = "flex"

    view = BaseViewWithLog(main_box=main_box, project=project)

    def on_change(change):
        if change["type"] == "change" and change["name"] == "value":
            for s in ss.sorter_full_list:
                if s.sorter_name == sorters_string_to_name[sorter.value]:
                    params = s.default_params()
            sorter_param.update_params(params)

    def on_show(change):
        if change["type"] == "change" and change["name"] == "value":
            for s in ss.sorter_full_list:
                if s.sorter_name == sorters_string_to_name[sorter.value]:
                    params = s.default_params()
            sorter_param.update_params(params)
            if show_params.value:
                sorter_param.layout.visibility = "visible"
            else:
                sorter_param.layout.visibility = "hidden"

    def on_other(change):
        if change["type"] == "change" and change["name"] == "value":
            if other_settings.value:
                bad_channel_ids.layout.visibility = "visible"
                bad_threshold.layout.visibility = "visible"
                reference.layout.visibility = "visible"
                split_group.layout.visibility = "visible"
                quality_metrics.layout.visibility = "visible"
            else:
                bad_threshold.layout.visibility = "hidden"
                bad_threshold.layout.visibility = "hidden"
                reference.layout.visibility = "hidden"
                split_group.layout.visibility = "hidden"
                quality_metrics.layout.visibility = "hidden"

    def on_split(change):
        if change["type"] == "change" and change["name"] == "value":
            if reference.value != "none":
                if split_group.value == "custom":
                    custom_split.layout.visibility = "visible"
                else:
                    custom_split.layout.visibility = "hidden"

    @view.output.capture()
    def on_run(change):
        if not required_values_filled(action_ids):
            return

        spikesorter_params = sorter_param.value
        for k, v in spikesorter_params.items():
            if v == "None":
                spikesorter_params[k] = None
            elif isinstance(v, str):
                if "[" in v and "]" in v:
                    # this is needed to properly parse lists
                    spikesorter_params[k] = eval(v)
                elif "(" in v and ")" in v:
                    # this is needed to properly parse tuples
                    spikesorter_params[k] = eval(v)

        sorter_name = sorters_string_to_name[sorter.value]
        if sorter_name not in installed_sorters and not use_singularity.value:
            raise ValueError(f"Sorter {sorter_name} not installed. Use singularity to run.")

        if bad_channel_ids.value not in ["", "auto"]:
            bad_chans = [str(b) for b in bad_channel_ids.value.split(",")]
        elif bad_channel_ids.value == "auto":
            bad_chans = ["auto"]
        else:
            bad_chans = []
        if reference.value != "none":
            ref = reference.value
        else:
            ref = None
        if split_group != "custom":
            split = split_group.value
        elif split_group == "custom":
            split = ast.literal_eval(split_group.value)
        else:
            split = "all"
        for action_id_ in action_ids.value:
            action_id, status = action_id_.split(" -- ")
            if status == "(P)" and not overwrite.value:
                run_status_label.description = "Status: Overwrite error"
                run_status_label.style.button_color = "red"
                raise ValueError(f"Action {action_id} already processed. Set overwrite to True to overwrite.")

            try:
                print(f"Processing {action_id}")
                run_status_label.description = "Status: Processing"
                run_status_label.style.button_color = "yellow"

                process.process_ecephys(
                    project=project,
                    action_id=action_id,
                    sorter=sorter_name,
                    spikesort=spikesort.value,
                    compute_lfp=compute_lfp.value,
                    compute_mua=compute_mua.value,
                    spikesorter_params=spikesorter_params,
                    bad_channel_ids=bad_chans,
                    reference=ref,
                    split=split,
                    spikesort_by_group=spikesort_by_group.value,
                    bad_threshold=bad_threshold.value,
                    metric_names=quality_metrics.value,
                    overwrite=overwrite.value,
                    singularity_image=use_singularity.value,
                    verbose=True,
                )

                run_status_label.description = "Status: Done"
                run_status_label.style.button_color = "green"
            except Exception as e:
                import traceback

                error = "".join(traceback.format_exception(e))
                run_status_label.description = "Status: Processing error"
                run_status_label.style.button_color = "red"
                print(f"ERROR: unable to process {action_id}")
                print(str(error))
                process.clean_up(project, action_id, sorters_string_to_name[sorter.value])

    sorter.observe(on_change)
    run_button.on_click(on_run)
    show_params.observe(on_show)
    other_settings.observe(on_other)
    split_group.observe(on_split)

    return view
