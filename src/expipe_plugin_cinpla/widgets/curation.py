# -*- coding: utf-8 -*-
from collections import OrderedDict

import ipywidgets

from expipe_plugin_cinpla.scripts import curation
from expipe_plugin_cinpla.scripts.utils import _get_data_path

from ..tools.utils import dump_project_config
from .utils import BaseViewWithLog, required_values_filled

default_qms = [
    dict(name="isi_violations_ratio", sign="<", threshold=0.5),
    dict(name="amplitude_cutoff", sign="<", threshold=0.1),
    dict(name="presence_ratio", sign=">", threshold=0.8),
]


class QualityThreshold(ipywidgets.HBox):
    def __init__(self, qm_names=None, name=None, threshold=None, sign=None, **kwargs):
        super().__init__(**kwargs)
        if name:
            if qm_names:
                assert name in qm_names, f"{name} not in {qm_names}"
            else:
                qm_names = [name]
        if sign:
            assert sign in ["<", ">", "<=", ">="], f"{sign} not in ['<', '>', '<=', '>=']"
        name_list = ipywidgets.Dropdown(
            options=qm_names, value=name if name is not None else qm_names[0], layout={"width": "200px"}
        )
        sign_list = ipywidgets.Dropdown(
            options=["<", ">", "<=", ">="], value=">" if sign is None else sign, layout={"width": "50px"}
        )
        threshold_value = ipywidgets.FloatText(
            value=threshold if threshold is not None else 0.0, layout={"width": "100px"}
        )
        self.children = [name_list, sign_list, threshold_value]

    def get_query(self):
        return f"{self.children[0].value} {self.children[1].value} {self.children[2].value}"


class CurationView(BaseViewWithLog):
    def __init__(self, project):
        from nwbwidgets import nwb2widget
        from pynwb.misc import Units

        from ..nwbutils.nwbwidgetsunitviewer import UnitSummaryWidget

        custom_raw_unit_vis = {
            Units: OrderedDict(
                {
                    "Raw Units": UnitSummaryWidget,
                }
            )
        }
        custom_main_unit_vis = {
            Units: OrderedDict(
                {
                    "Main Units": UnitSummaryWidget,
                }
            )
        }
        custom_curated_unit_vis = {
            Units: OrderedDict(
                {
                    "Curated Units": UnitSummaryWidget,
                }
            )
        }

        all_actions = project.actions

        actions_processed = []
        for action_name in all_actions:
            # if exdir_path is None:
            action = all_actions[action_name]
            data_path = _get_data_path(action)
            if data_path is not None and data_path.name == "main.nwb":
                si_path = data_path.parent / "spikeinterface"
                if si_path.is_dir():
                    actions_processed.append(action_name)
        actions_processed = sorted(actions_processed)
        actions_list = ipywidgets.Select(
            options=actions_processed, rows=10, description="Actions: ", disabled=False, layout={"width": "300px"}
        )
        sorter_list = ipywidgets.SelectMultiple(description="Spike sorters", options=[], layout={"width": "initial"})
        run_save = ipywidgets.Button(
            description="Save as NWB Units", layout={"width": "100%"}, tooltip="Save curated units to NWB file."
        )
        run_save.style.button_color = "pink"
        load_status = ipywidgets.Button(
            description="Status: Units not loaded",
            disabled=True,
            layout={"width": "100%"},
        )

        # curation strategies

        # 1. Load from Phy
        # 2. Use Quality metrics
        strategy = ipywidgets.RadioButtons(
            options=["Phy", "Quality Metrics"],
            description="Curation strategy:",
            disabled=False,
            value="Phy",
            layout={"width": "initial"},
        )

        # Phy
        run_phy_command = ipywidgets.Label(
            value="",
            layout={"width": "500px"},
        )
        load_from_phy = ipywidgets.Button(description="Load from Phy", layout={"width": "initial"})
        load_from_phy.style.button_color = "pink"

        self.restore_phy_clicked = False
        restore_phy = ipywidgets.Button(
            value=False,
            description="Restore (click twice to restore)",
            disabled=False,
            button_style="",  # 'success', 'info', 'warning', 'danger' or ''
            tooltip="Restore unsorted clusters",
            layout={"width": "initial"},
        )

        # Quality metrics
        qm_thresholds = []
        standard_qms = project.config.get("custom_qms") if project.config.get("custom_qms") is not None else default_qms

        for default_qm in standard_qms:
            qm_thresholds.append(
                QualityThreshold(name=default_qm["name"], sign=default_qm["sign"], threshold=default_qm["threshold"])
            )
        qc_metrics = ipywidgets.VBox(qm_thresholds)

        add_metric_button = ipywidgets.Button(description="+", layout={"width": "initial"})
        remove_metric_button = ipywidgets.Button(description="-", layout={"width": "initial"})
        set_default_qms = ipywidgets.Button(description="Set default", layout={"width": "200px"})
        apply_qm_curation = ipywidgets.Button(description="Apply", layout={"width": "200px"})
        apply_qm_curation.style.button_color = "pink"
        qc_controls = ipywidgets.HBox([add_metric_button, remove_metric_button, set_default_qms, apply_qm_curation])

        actions_panel = ipywidgets.VBox([actions_list, sorter_list])

        buttons_panel = ipywidgets.HBox([load_status, run_save])

        phy_panel = ipywidgets.VBox(
            [
                run_phy_command,
                load_from_phy,
                restore_phy,
            ]
        )

        qm_panel = ipywidgets.VBox(
            [
                qc_controls,
                qc_metrics,
            ]
        )

        curation_panel = ipywidgets.VBox([strategy, phy_panel])

        units_placeholder = ipywidgets.Output(layout={"width": "300px", "height": "500px"})
        units_viewers = dict(
            raw=None,
            main=None,
            curated=None,
        )
        sorting_not_found = ipywidgets.ToggleButton(
            value=False,
            description="Sorting not found",
            disabled=True,
            button_style="warning",  # 'success', 'info', 'warning', 'danger' or ''
            layout={"width": "100%"},
        )
        units_number = ipywidgets.Label(value="Number of units: ", layout={"width": "500px"})
        units_dropdown = ipywidgets.Dropdown(
            options=["Raw", "Main", "Curated"],
            description="Display:",
            disabled=False,
            layout={"width": "50%"},
            value="Raw",
        )
        units_col = ipywidgets.VBox([units_dropdown, units_number, units_placeholder])

        curation_box = ipywidgets.HBox([actions_panel, curation_panel], layout={"width": "100%"})
        main_box = ipywidgets.VBox([curation_box, buttons_panel, units_col])
        super().__init__(main_box=main_box, project=project)

        self.sorting_curator = curation.SortingCurator(project)

        def on_action(change):
            self.sorting_curator.set_action(actions_list.value)
            action = project.actions[actions_list.value]
            si_path = _get_data_path(action).parent / "spikeinterface"
            sorters = [p.name for p in si_path.iterdir() if p.is_dir()]
            sorter_list.options = sorters
            units_dropdown.value = "Raw"
            sorter_list.value = []
            units_number.value = "Number of units: "
            load_status.description = "Units not loaded"
            units_col.children = [units_dropdown, units_number, units_placeholder]
            units_main = self.sorting_curator.load_main_units()
            if units_main is not None:
                w = nwb2widget(units_main, custom_main_unit_vis)
                units_viewers["main"] = w
            units_viewers["curated"] = None

        def on_sorter(change):
            required_values_filled(actions_list)
            if len(sorter_list.value) > 1:
                print("Select one spike sorting output at a time")
            else:
                if len(sorter_list.value) == 1:
                    units_raw = self.sorting_curator.load_raw_units(sorter_list.value[0])
                    if units_raw is not None:
                        w = nwb2widget(units_raw, custom_raw_unit_vis)
                        units_viewers["raw"] = w
                    if strategy.value == "Phy":
                        run_phy_command.value = self.sorting_curator.get_phy_run_command(sorter_list.value[0])
                    units_dropdown.value = "Raw"
                    units_viewers["curated"] = None
                    on_choose_units(None)

        def on_change_strategy(change):
            if change["new"] == "Phy":
                curation_panel.children = [strategy, phy_panel]
                if len(sorter_list.value) == 1:
                    run_phy_command.value = self.sorting_curator.get_phy_run_command(sorter_list.value[0])
            elif change["new"] == "Quality Metrics":
                curation_panel.children = [strategy, qm_panel]
                # check if metrics apply
                if len(sorter_list.value) == 1:
                    check_metrics(project, actions_list, sorter_list.value[0], qc_metrics)

        def on_add_metric(change):
            selected_sorters = sorter_list.value
            assert len(selected_sorters) == 1, "Select one sorter"
            analyzer = self.sorting_curator.load_raw_analyzer(selected_sorters[0])
            selected_qm = analyzer.get_extension("quality_metrics").get_data()
            qc_metrics.children += (QualityThreshold(qm_names=list(selected_qm.columns)),)

        def on_remove_metric(change):
            if len(qc_metrics.children) > 1:
                qc_metrics.children = qc_metrics.children[:-1]

        @self.output.capture()
        def on_choose_units(change):
            original_color = load_status.style.button_color
            load_status.style.button_color = "yellow"
            load_status.description = "Loading..."
            units_widget = units_viewers[units_dropdown.value.lower()]
            if units_widget is not None:
                units_number.value = f"Number of units: {len(units_widget.children[0].units)}"
                units_col.children = [units_dropdown, units_number, units_widget]
                load_status.description = f"Units {units_dropdown.value} loaded"
            else:
                units_col.children = [units_dropdown, sorting_not_found]
                load_status.description = f"Units {units_dropdown.value} not found"
            load_status.style.button_color = original_color

        @self.output.capture()
        def on_set_default_qms(change):
            custom_qms = []
            for qm in qc_metrics.children:
                custom_qms.append(
                    dict(name=qm.children[0].value, sign=qm.children[1].value, threshold=qm.children[2].value)
                )
            print(f"Setting default quality metrics to {custom_qms}")
            project.config["custom_qms"] = custom_qms
            dump_project_config(project)

        @self.output.capture()
        def on_load_phy(change):
            required_values_filled(sorter_list, actions_list)
            if len(sorter_list.value) > 1:
                print("Select one spike sorting output at a time")
            else:
                load_from_phy.style.button_color = "yellow"

                self.sorting_curator.load_from_phy(sorter_list.value[0])
                units = self.sorting_curator.construct_curated_units()
                if units:
                    w = nwb2widget(units, custom_curated_unit_vis)
                    units_viewers["curated"] = w
                load_from_phy.style.button_color = "pink"

        @self.output.capture()
        def on_restore_phy(change):
            required_values_filled(sorter_list, actions_list)

            if len(sorter_list.value) > 1:
                print("Select one spike sorting output at a time")
            else:
                if self.restore_phy_clicked:
                    self.sorting_curator.restore_phy(sorter_list.value[0])
                    self.restore_phy_clicked = False
                    restore_phy.description = "Restore (click twice to restore)"
                    restore_phy.button_style = "primary"
                else:
                    self.restore_phy_clicked = True
                    restore_phy.description = "Restore (click again to confirm)"
                    restore_phy.button_style = "danger"

        @self.output.capture()
        def on_apply_qm_curation(change):
            required_values_filled(sorter_list, actions_list)
            if len(sorter_list.value) > 1:
                print("Select one spike sorting output at a time")
            else:
                apply_qm_curation.style.button_color = "yellow"

                query = " and ".join([qm.get_query() for qm in qc_metrics.children])
                self.sorting_curator.apply_qc_curator(sorter_list.value[0], query)
                units = self.sorting_curator.construct_curated_units()
                if units:
                    w = nwb2widget(units, custom_curated_unit_vis)
                    units_viewers["curated"] = w
                apply_qm_curation.style.button_color = "pink"

        @self.output.capture()
        def on_save_to_nwb(change):
            required_values_filled(sorter_list, actions_list)
            run_save.style.button_color = "yellow"
            self.sorting_curator.save_to_nwb()
            units_main = self.sorting_curator.load_main_units()
            if units_main is not None:
                w = nwb2widget(units_main, custom_main_unit_vis)
                units_viewers["main"] = w
            run_save.style.button_color = "pink"

        actions_list.observe(on_action)
        load_from_phy.on_click(on_load_phy)
        restore_phy.on_click(on_restore_phy)
        run_save.on_click(on_save_to_nwb)
        strategy.observe(on_change_strategy)
        sorter_list.observe(on_sorter)
        set_default_qms.on_click(on_set_default_qms)
        apply_qm_curation.on_click(on_apply_qm_curation)
        units_dropdown.observe(on_choose_units)

        add_metric_button.on_click(on_add_metric)
        remove_metric_button.on_click(on_remove_metric)

        on_action(actions_processed[0])

    def close(self):
        self.sorting_curator.remove_tmp_files()


def check_metrics(project, actions_list, sorter, qm_panel):
    sorting_curator = curation.SortingCurator(project)
    sorting_curator.set_action(actions_list.value)
    analyzer = sorting_curator.load_raw_analyzer(sorter)
    qm_table = analyzer.get_extension("quality_metrics").get_data()

    valid_children = []
    for qm in qm_panel.children:
        name = qm.children[0].value
        if name not in qm_table.columns:
            print(f"Quality metric {name} not available for {sorter}. Removing from list.")
        else:
            valid_children.append(qm)
    qm_panel.children = valid_children
