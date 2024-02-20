from pathlib import Path
from expipe_plugin_cinpla.scripts import register
from .utils import BaseViewWithLog
from ..utils import dump_project_config


### Open Ephys recording ###
def register_openephys_view(project):
    import ipywidgets
    from .utils import (
        MultiInput,
        required_values_filled,
        none_if_empty,
        split_tags,
    )

    # left column
    layout_auto = ipywidgets.Layout(width="300px")
    openephys_path = ipywidgets.Text(placeholder="Path to Open Ephys folder", layout=layout_auto)
    default_probe = project.config.get("probe_path", None)
    probe_path = ipywidgets.Text(placeholder="Path to probe JSON file", layout=layout_auto)
    if default_probe is not None:
        probe_path.value = default_probe
    user = ipywidgets.Text(placeholder="*User", value=project.config.get("username"), layout=layout_auto)
    session = ipywidgets.Text(placeholder="Session", layout=layout_auto)
    location = ipywidgets.Text(placeholder="*Location", value=project.config.get("location"), layout=layout_auto)
    action_id = ipywidgets.Text(placeholder="Action id", layout=layout_auto)
    entity_id = ipywidgets.Text(placeholder="Entity id", layout=layout_auto)
    message = ipywidgets.Text(placeholder="Message", layout=layout_auto)
    tag = ipywidgets.Text(placeholder="Tags (; to separate)", layout=layout_auto)
    # buttons
    depth = MultiInput(["Key", "Probe", "Depth", "Unit"], "Add depth")
    register_depth = ipywidgets.Checkbox(description="Register depth", value=False)
    include_events = ipywidgets.Checkbox(description="Include events", value=False)
    register_depth_from_adjustment = ipywidgets.Checkbox(description="Find adjustments", value=True)
    register_depth_from_adjustment.layout.visibility = "hidden"

    overwrite = ipywidgets.Checkbox(description="Overwrite", value=False)
    delete_raw_data = ipywidgets.Checkbox(description="Delete raw data", value=False)
    set_default_probe = ipywidgets.Button(description="Set default probe", layout={"width": "200px"})
    register_action = ipywidgets.Button(
        description="Register", layout=dict(height="50px", width="300px"), style={"button_color": "pink"}
    )

    fields = ipywidgets.VBox(
        [
            openephys_path,
            probe_path,
            set_default_probe,
            user,
            location,
            session,
            action_id,
            entity_id,
            message,
            tag,
            register_action,
        ]
    )
    checks = ipywidgets.VBox(
        [overwrite, delete_raw_data, include_events, register_depth, register_depth_from_adjustment]
    )
    main_box = ipywidgets.VBox([ipywidgets.HBox([fields, checks])])

    view = BaseViewWithLog(main_box=main_box, project=project)

    def on_register_depth(change):
        if change["name"] == "value":
            if change["owner"].value:
                register_depth_from_adjustment.layout.visibility = "visible"
            else:
                register_depth_from_adjustment.layout.visibility = "hidden"

    def on_register_depth_from_adjustment(change):
        if change["name"] == "value":
            if not change["owner"].value:
                children = list(fields.children)
                children = children[:5] + [depth] + children[5:]
                fields.children = children
            else:
                children = list(fields.children)
                del children[5]
                fields.children = children

    register_depth.observe(on_register_depth)
    register_depth_from_adjustment.observe(on_register_depth_from_adjustment)

    @view.output.capture()
    def on_set_default_probe(change):
        required_values_filled(probe_path)
        default_path = str(Path(probe_path.value).absolute())
        print(f"Setting default probe path to {default_path}")
        project.config["probe_path"] = default_path
        dump_project_config(project)

    set_default_probe.on_click(on_set_default_probe)

    @view.output.capture()
    def on_register(change):
        print("Registering action")
        if not required_values_filled(user, location, openephys_path):
            return
        tags = split_tags(tag)
        register.register_openephys_recording(
            project=project,
            action_id=none_if_empty(action_id.value),
            openephys_path=openephys_path.value,
            probe_path=probe_path.value,
            include_events=include_events.value,
            depth=depth.value,
            overwrite=overwrite.value,
            register_depth=register_depth.value,
            entity_id=none_if_empty(entity_id.value),
            user=user.value,
            session=session.value,
            location=location.value,
            message=none_if_empty(message.value),
            tags=tags,
            delete_raw_data=delete_raw_data.value,
            correct_depth_answer=True,
        )

    register_action.on_click(on_register)
    return view


### Adjustment ###
def register_adjustment_view(project):
    import ipywidgets
    from .utils import (
        DateTimePicker,
        MultiInput,
        required_values_filled,
        SearchSelect,
    )

    entity_id = SearchSelect(options=project.entities, description="*Entities")
    user = ipywidgets.Text(placeholder="*User", value=project.config.get("username"))
    date = DateTimePicker()
    adjustment = MultiInput(["*Key", "*Probe", "*Adjustment", "*Unit"], "Add adjustment")
    depth = MultiInput(["Key", "Probe", "Depth", "Unit"], "Add depth")
    depth_from_surgery = ipywidgets.Checkbox(description="Get depth from surgery", value=True)
    register = ipywidgets.Button(description="Register")

    fields = ipywidgets.VBox([user, date, adjustment, register])
    main_box = ipywidgets.VBox([depth_from_surgery, ipywidgets.HBox([fields, entity_id])])

    def on_manual_depth(change):
        if change["name"] == "value":
            if not change["owner"].value:
                children = list(main_box.children)
                children = children[:5] + [depth] + children[5:]
                main_box.children = children
            else:
                children = list(main_box.children)
                del children[5]
                main_box.children = children

    depth_from_surgery.observe(on_manual_depth, names="value")

    def on_register(change):
        if not required_values_filled(entity_id, user, adjustment):
            return
        register.register_adjustment(
            project=project,
            entity_id=entity_id.value,
            date=date.value,
            adjustment=adjustment.value,
            user=user.value,
            depth=depth.value,
            yes=True,
        )

    register.on_click(on_register)
    return main_box


### Annotation ###
def register_annotate_view(project):
    import ipywidgets
    from .utils import (
        DateTimePicker,
        MultiInput,
        required_values_filled,
        SearchSelectMultiple,
        split_tags,
    )

    action_id = SearchSelectMultiple(options=project.actions, description="*Actions")
    user = ipywidgets.Text(placeholder="*User", value=project.config.get("username"))
    date = DateTimePicker()
    depth = MultiInput(["Key", "Probe", "Depth", "Unit"], "Add depth")
    location = ipywidgets.Text(placeholder="Location", value=project.config.get("location"))
    entity_id = ipywidgets.Text(placeholder="Entity id")
    action_type = ipywidgets.Text(placeholder="Type (e.g. recording)")
    message = ipywidgets.Text(placeholder="Message")
    tag = ipywidgets.Text(placeholder="Tags (; to separate)")
    templates = SearchSelectMultiple(project.templates, description="Templates")
    register = ipywidgets.Button(description="Register")

    fields = ipywidgets.VBox([user, date, location, message, action_type, tag, depth, entity_id, register])
    main_box = ipywidgets.VBox([ipywidgets.HBox([fields, action_id, templates])])

    def on_register(change):
        if not required_values_filled(action_id, user):
            return
        tags = split_tags(tag)
        for a in action_id.value:
            register.register_annotation(
                project=project,
                action_id=a,
                user=user.value,
                action_type=action_type.value,
                date=date.value,
                location=location.value,
                message=message.value,
                tags=tags,
                depth=depth.value,
                entity_id=entity_id.value,
                templates=templates.value,
                correct_depth_answer=True,
            )

    register.on_click(on_register)
    return main_box


### Entity ###
def register_entity_view(project):
    import ipywidgets
    from .utils import (
        DatePicker,
        SearchSelectMultiple,
        required_values_filled,
        none_if_empty,
        split_tags,
        make_output_and_show,
    )

    entity_id = ipywidgets.Text(placeholder="*Entity id")
    user = ipywidgets.Text(placeholder="*User", value=project.config.get("username"))
    species = ipywidgets.Text(placeholder="Species", value="Rattus norvegicus")
    sex = ipywidgets.Text(placeholder="Sex", value="F")
    message = ipywidgets.Text(placeholder="Message")
    location = ipywidgets.Text(placeholder="*Location")
    tag = ipywidgets.Text(placeholder="Tags (; to separate)")
    birthday = DatePicker(description="*Birthday", disabled=False)
    templates = SearchSelectMultiple(project.templates, description="Templates")

    overwrite = ipywidgets.Checkbox(description="Overwrite", value=False)
    register = ipywidgets.Button(description="Register")
    fields = ipywidgets.VBox([entity_id, user, species, sex, location, birthday, message, tag, register])

    main_box = ipywidgets.VBox([overwrite, ipywidgets.HBox([fields, templates])])
    view = BaseViewWithLog(main_box=main_box, project=project)

    @view.output.capture()
    def on_register(change):
        tags = split_tags(tag)
        if not required_values_filled(entity_id, user, location, birthday):
            return
        register.register_entity(
            project=project,
            entity_id=entity_id.value,
            user=user.value,
            species=species.value,
            sex=sex.value,
            message=none_if_empty(message.value),
            birthday=birthday.datetime,
            overwrite=overwrite,
            location=location.value,
            tags=tags,
            templates=templates.value,
        )

    register.on_click(on_register)
    return view


### Surgery ###
def register_surgery_view(project):
    import ipywidgets
    from .utils import (
        DatePicker,
        MultiInput,
        SearchSelectMultiple,
        required_values_filled,
        none_if_empty,
        split_tags,
        SearchSelect,
    )

    entity_id = SearchSelect(options=project.entities, description="*Entities")
    procedure = ipywidgets.Dropdown(description="*Procedure", options=["implantation", "injection"])
    date = DatePicker(description="*Date", disabled=False)
    user = ipywidgets.Text(placeholder="*User", value=project.config.get("username"))
    weight = ipywidgets.HBox(
        [
            ipywidgets.Text(placeholder="*Weight", layout={"width": "60px"}),
            ipywidgets.Text(placeholder="*Unit", layout={"width": "60px"}),
        ]
    )
    location = ipywidgets.Text(placeholder="*Location", value=project.config.get("location"))
    message = ipywidgets.Text(placeholder="Message", value=None)
    tag = ipywidgets.Text(placeholder="Tags (; to separate)")
    position = MultiInput(["*Key", "*Probe", "*x", "*y", "*z", "*Unit"], "Add position")
    angle = MultiInput(["*Key", "*Probe", "*Angle", "*Unit"], "Add angle")
    templates = SearchSelectMultiple(project.templates, description="Templates")
    overwrite = ipywidgets.Checkbox(description="Overwrite", value=False)
    register = ipywidgets.Button(description="Register")

    fields = ipywidgets.VBox([user, location, date, weight, position, angle, message, procedure, tag, register])
    main_box = ipywidgets.VBox([overwrite, ipywidgets.HBox([fields, ipywidgets.VBox([entity_id, templates])])])

    view = BaseViewWithLog(main_box=main_box, project=project)

    @view.output.capture()
    def on_register(change):
        if not required_values_filled(entity_id, user, location, procedure, date, *weight.children, position, angle):
            return
        tags = split_tags(tag)
        weight_val = (weight.children[0].value, weight.children[1].value)
        register.register_surgery(
            project=project,
            overwrite=overwrite.value,
            entity_id=entity_id.value,
            user=user.value,
            procedure=procedure.value,
            location=location.value,
            weight=weight_val,
            date=date.datetime,
            templates=templates.value,
            position=position.value,
            angle=angle.value,
            message=none_if_empty(message.value),
            tags=tags,
        )

    register.on_click(on_register)
    return view


### PERFUSION ###
def register_perfuse_view(project):
    import ipywidgets
    from .utils import (
        DatePicker,
        MultiInput,
        SearchSelectMultiple,
        required_values_filled,
        none_if_empty,
        split_tags,
        SearchSelect,
    )

    entity_id = SearchSelect(options=project.entities, description="*Entities")
    date = DatePicker(disabled=False)
    user = ipywidgets.Text(placeholder="*User", value=project.config.get("username"))
    location = ipywidgets.Text(placeholder="*Location")
    message = ipywidgets.Text(placeholder="Message")
    weight = ipywidgets.HBox(
        [
            ipywidgets.Text(placeholder="*Weight", layout={"width": "60px"}),
            ipywidgets.Text(placeholder="*Unit", layout={"width": "60px"}),
        ]
    )
    templates = SearchSelectMultiple(project.templates, description="Templates")
    overwrite = ipywidgets.Checkbox(description="Overwrite", value=False)

    register = ipywidgets.Button(description="Register")
    fields = ipywidgets.VBox([user, location, date, weight, message, register])
    main_box = ipywidgets.VBox([overwrite, ipywidgets.HBox([fields, entity_id, templates])])
    view = BaseViewWithLog(main_box=main_box, project=project)

    @view.output.capture()
    def on_register(change):
        if not required_values_filled(user, entity_id, *weight.children):
            return
        weight_val = (weight.children[0].value, weight.children[1].value)
        register.register_perfusion(
            project=project,
            entity_id=entity_id.value,
            location=location.value,
            user=user.value,
            overwrite=overwrite.value,
            templates=templates.value,
            date=date.datetime,
            weight=weight_val,
            message=none_if_empty(message.value),
        )

    register.on_click(on_register)
    return view
