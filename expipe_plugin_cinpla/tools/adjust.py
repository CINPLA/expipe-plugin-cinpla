from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.tools import action as action_tools
from expipe_plugin_cinpla.tools import config
from datetime import datetime as dt


def register_adjustment(project_path, entity_id, date, adjustment, user, index,
                        init, depth, yes, overwrite):
    user = user or PAR.USERNAME
    if user is None:
        print('Missing option "user".')
        return
    if not init:
        if len(depth) != 0:
            print('"depth" is only valid if "init"')
            return
        if len(adjustment) == 0:
            print('Missing option "adjustment".')
            return
        if date is None:
            print('Missing option "date".')
            return
    DTIME_FORMAT = expipe.core.datetime_format
    if date == 'now':
        date = dt.now()
    else:
        dt.strptime(date, '%d.%m.%YT%H:%M')

    if isinstance(date, str):
        datestring = dt.strftime(date, DTIME_FORMAT)
    project = expipe.get_project(project_path)
    action_id = entity_id + '-adjustment'
    try:
        if init:
            try:
                action = project.create_action(action_id)
            except KeyError as e:
                if overwrite:
                    project.delete_action(action_id)
                    action = project.create_action(action_id)
                else:
                    print(str(e) + '. Use "overwrite"')
                    return
        else:
            action = project.actions[action_id]
    except KeyError as e:
        print(str(e) + '. Use "init"')
        return
    if index is None and not init:
        deltas = []
        for name in action.modules.keys():
            if name.endswith('adjustment'):
                deltas.append(int(name.split('_')[0]))
        index = max(deltas) + 1
    if init:
        if len(depth) > 0:
            prev_depth = action_tools.position_to_dict(depth)
        else:
            prev_depth = action_tools.get_position_from_surgery(
                project=project, entity_id=entity_id)
        index = 0
    else:
        prev_depth = action.modules[
            '{:03d}_adjustment'.format(index - 1)].contents['depth']
    name = '{:03d}_adjustment'.format(index)
    if not isinstance(prev_depth, dict):
        print('Unable to retrieve previous depth.')
        return
    adjustment_dict = {key: dict() for key in prev_depth}
    for key, num, val, unit in adjustment:
        pos_key = 'position_{}'.format(num)
        adjustment_dict[key][pos_key] = pq.Quantity(val, unit)
    adjustment = {key: {pos_key: adjustment_dict[key].get(pos_key) or 0 * pq.mm
                        for pos_key in prev_depth[key]}
                  for key in prev_depth}
    curr_depth = {key: {pos_key: round(prev_depth[key][pos_key] + val[pos_key], 3)
                        for pos_key in val}
                  for key, val in adjustment.items()} # round to um

    def last_num(x):
        return '%.3d' % int(x.split('_')[-1])
    correct = action_tools.query_yes_no(
        'Correct adjustment?: \n' +
        ' '.join('{} {} = {}\n'.format(key, pos_key, val[pos_key])
                 for key, val in adjustment.items()
                 for pos_key in sorted(val, key=lambda x: last_num(x))) +
        'New depth: \n' +
        ' '.join('{} {} = {}\n'.format(key, pos_key, val[pos_key])
                 for key, val in curr_depth.items()
                 for pos_key in sorted(val, key=lambda x: last_num(x))),
        answer=yes
    )
    if not correct:
        print('Aborting adjustment.')
        return
    print(
        'Registering adjustment: \n' +
        ' '.join('{} {} = {}\n'.format(key, pos_key, val[pos_key])
                 for key, val in adjustment.items()
                 for pos_key in sorted(val, key=lambda x: last_num(x))) +
        ' New depth: \n' +
        ' '.join('{} {} = {}\n'.format(key, pos_key, val[pos_key])
                 for key, val in curr_depth.items()
                 for pos_key in sorted(val, key=lambda x: last_num(x)))
    )
    template_name = PAR.TEMPLATES['adjustment']
    template = project.templates[template_name].contents
    template['depth'] = curr_depth
    template['adjustment'] = adjustment
    template['experimenter'] = user
    template['date'] = datestring
    action.create_module(name=name, contents=template)

    action.type = 'Adjustment'
    action.entities = [entity_id]
    action.users.append(user)
