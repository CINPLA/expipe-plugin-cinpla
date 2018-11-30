from expipe_plugin_cinpla.scripts import adjust
from expipe_plugin_cinpla.imports import *
from .utils import DateTimePicker, MultiInput


def adjustment_view(project):
    entity_id = ipywidgets.Text(placeholder='*Entity id')
    user = ipywidgets.Text(placeholder='*User', value=PAR.USERNAME)
    date = DateTimePicker()
    adjustment = MultiInput(['*Key', '*Probe', '*Adjustment', '*Unit'], 'Add adjustment')
    depth = MultiInput(['Key', 'Probe', 'Depth', 'Unit'], 'Add depth')
    depth_from_surgery = ipywidgets.Checkbox(description='Get depth from surgery', value=True)
    register = ipywidgets.Button(description='Register')

    main_box = ipywidgets.VBox([
            depth_from_surgery,
            entity_id,
            user,
            date,
            adjustment,
            register
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
