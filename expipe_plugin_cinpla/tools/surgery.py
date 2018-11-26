from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.tools.action import generate_templates, query_yes_no


def register_surgery(
    project_path, entity_id, procedure, date, user, weight, location,
    overwrite, position, angle, message, tag):
    # TODO tag sucject as active
    if weight == (None, None):
        print('Missing option "weight".')
        return
    user = user or PAR.USERNAME
    if user is None:
        print('Missing option "user".')
        return
    location = location or PAR.LOCATION
    if location is None:
        print('Missing option "location".')
        return
    weight = pq.Quantity(weight[0], weight[1])
    project = expipe.get_project(project_path)
    action_id = entity_id + '-surgery-' + procedure
    try:
        action = project.create_action(action_id)
    except KeyError as e:
        if overwrite:
            project.delete_action(action_id)
            action = project.create_action(action_id)
        else:
            print(str(e) + ' Use "overwrite"')
            return
    entity = project.entities[entity_id]
    entity_module = entity.modules[PAR.TEMPLATES['entity']]
    entity_module['surgery_weight'] = weight
    entity.tags.extend(['surgery', PAR.PROJECT_ID])
    entity.users.append(user)

    generate_templates(action, 'surgery_' + procedure)
    if date == 'now':
        date = datetime.now()
    if isinstance(date, str):
        date = datetime.strftime(date, DTIME_FORMAT)
    action.datetime = date
    print('Registering location', location)
    action.location = location
    action.type = 'Surgery'
    action.tags = [procedure] + list(tag)
    action.entities = [entity_id]
    print('Registering user', user)
    action.users.append(user)
    for m in message:
        action.create_message(text=m, user=user, datetime=datetime.now())
    modules_dict = action.modules.contents
    keys = list(set([pos[0] for pos in position]))
    modules = {
        key: project.templates[PAR.TEMPLATES[procedure][key]].contents
        for key in keys}
    for key, num, x, y, z, unit in position:
        mod = modules[key]
        if 'position' in mod:
            del(mod['position']) # delete position template
        print('Registering position ' +
              '{} {}: x={}, y={}, z={} {}'.format(key, num, x, y, z, unit))
        mod['position_{}'.format(num)] = pq.Quantity([x, y, z], unit)
    for key, ang, unit in angle:
        mod = modules[key]
        if 'angle' in mod:
            del(mod['angle']) # delete position template
        print('Registering angle ' +
              '{}: angle={} {}'.format(key, ang, unit))
        mod['angle'] = pq.Quantity(ang, unit)
    for key in keys:
        action.modules[PAR.TEMPLATES[procedure][key]] = modules[key]


def register_perfusion(project_path, entity_id, date, user, weight, overwrite,
                       message):
    project = expipe.get_project(project_path)
    action_id = entity_id + '-perfusion'
    user = user or PAR.USERNAME
    if user is None:
        print('Missing option "user".')
        return
    try:
        action = project.create_action(action_id)
    except KeyError as e:
        if overwrite:
            project.delete_action(action_id)
            action = project.create_action(action_id)
        else:
            print(str(e) + '. Use "overwrite"')
            return
    generate_templates(action, 'perfusion')
    if date == 'now':
        date = datetime.now()
    if isinstance(date, str):
        date = datetime.strftime(date, DTIME_FORMAT)
    for m in message:
        action.messages.create_message(
            text=m, user=user, datetime= datetime.now())
    action.datetime = date
    action.location = 'Sterile surgery station'
    action.type = 'Surgery'
    action.tags = ['perfusion']
    action.entities = [entity_id]
    print('Registering user ' + user)
    action.users = [user]
    if weight != (None, None):
        action.modules[PAR.TEMPLATES['entity']]['weight'] = pq.Quantity(weight[0], weight[1])
    entity = project.entities[entity_id]
    entity.tags.extend(['perfused', 'euthanised'])
