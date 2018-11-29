from expipe_plugin_cinpla.scripts import adjust
from expipe_plugin_cinpla.imports import *
from .utils import DateTimePicker, add_multi_input, extract_multi_input

def adjustment_view(project_path):
    entity_id = ipywidgets.Text(placeholder='*Entity id')
    date = DateTimePicker()
    user = ipywidgets.Text(placeholder='*User', value=PAR.USERNAME)

    depth_from_surgery = ipywidgets.Checkbox(description='Get depth from surgery', value=True)
    register = ipywidgets.Button(description='Register')

    main_box = ipywidgets.VBox([
            depth_from_surgery,
            entity_id,
            user,
            date,
            register
        ])

    add_multi_input(main_box, 4, ['*Key', '*Probe', '*Adjustment', '*Unit'], 'Add adjustment')

    def on_manual_depth(change):
        if change['name'] == 'value':
            if not change['owner'].value:
                add_multi_input(
                    main_box, 5, ['Key', 'Probe', 'Depth', 'Unit'],
                    'Add depth')
            else:
                idxs = []
                for i, ch in enumerate(main_box.children):
                    if isinstance(ch, ipywidgets.HBox) and len(ch.children) == 5:
                        if ch.children[3].placeholder == 'Depth':
                            idxs.append(i)
                children = list(main_box.children)
                for i in idxs:
                    del(children[i])
                main_box.children = children

    depth_from_surgery.observe(on_manual_depth, names='value')

    def on_register(change):
        adjustment = extract_multi_input(main_box.children[4])
        if not depth_from_surgery.value:
            depth = extract_multi_input(main_box.children[5])
        else:
            depth = ()
        adjust.register_adjustment(
            project_path=project_path,
            entity_id=entity_id.value,
            date=date.value,
            adjustment=adjustment,
            user=user.value,
            depth=depth,
            yes=True)

    register.on_click(on_register)
    return main_box
