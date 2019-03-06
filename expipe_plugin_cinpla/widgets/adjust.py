from expipe_plugin_cinpla.scripts import adjust
from expipe_plugin_cinpla.imports import *
from .utils import DateTimePicker, MultiInput, required_values_filled, none_if_empty, SearchSelect


def adjustment_view(project):
    entity_id = SearchSelect(options=project.entities, description='*Entities')
    user = ipywidgets.Text(placeholder='*User', value=project.config.get('username'))
    date = DateTimePicker()
    adjustment = MultiInput(['*Key', '*Probe', '*Adjustment', '*Unit'], 'Add adjustment')
    depth = MultiInput(['Key', 'Probe', 'Depth', 'Unit'], 'Add depth')
    depth_from_surgery = ipywidgets.Checkbox(description='Get depth from surgery', value=True)
    register = ipywidgets.Button(description='Register')

    fields = ipywidgets.VBox([
        user,
        date,
        adjustment,
        register])
    main_box = ipywidgets.VBox([
            depth_from_surgery,
            ipywidgets.HBox([fields, entity_id])
        ])


    def on_manual_depth(change):
        if change['name'] == 'value':
            if not change['owner'].value:
                children = list(main_box.children)
                children = children[:5] + [depth] + children[5:]
                main_box.children = children
            else:
                children = list(main_box.children)
                del(children[5])
                main_box.children = children

    depth_from_surgery.observe(on_manual_depth, names='value')

    def on_register(change):
        if not required_values_filled(entity_id, user, adjustment):
            return
        adjust.register_adjustment(
            project=project,
            entity_id=entity_id.value,
            date=date.value,
            adjustment=adjustment.value,
            user=user.value,
            depth=depth.value,
            yes=True)

    register.on_click(on_register)
    return main_box
