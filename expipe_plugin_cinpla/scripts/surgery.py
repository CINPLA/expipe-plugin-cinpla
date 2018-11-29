from expipe_plugin_cinpla.imports import *
from .utils import generate_templates, query_yes_no


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
    surgery_key = 'surgery-' + procedure + '-' + date.strftime(expipe.core.datetime_key_format)
    if surgery_key not in entity.modules:
        entity.modules[surgery_key] = {}
    entity.modules[surgery_key]['weight'] = weight
    entity.tags.extend([surgery_key, PAR.PROJECT_ID])
    entity.users.append(user)

    # generate_templates(action, 'surgery_' + procedure)
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
    for key, probe, x, y, z, unit in position:
        action.modules[key] = {}
        probe_key = 'probe_{}'.format(probe)
        action.modules[key][probe_key] = {}
        print('Registering position ' +
              '{} {}: x={}, y={}, z={} {}'.format(key, probe, x, y, z, unit))
        action.modules[key][probe_key]['position'] = pq.Quantity([x, y, z], unit)
    for key, probe, ang, unit in angle:
        probe_key = 'probe_{}'.format(probe)
        if probe_key not in action.modules[key]:
            action.modules[key][probe_key] = {}
        print('Registering angle ' +
              '{} {}: angle={} {}'.format(key, probe, ang, unit))
        action.modules[key][probe_key]['angle'] = pq.Quantity(ang, unit)


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
        action.create_module(
            'perfusion', contents={'weight': pq.Quantity(weight[0], weight[1])})
    entity = project.entities[entity_id]
    entity.tags.extend(['perfused', 'euthanised'])
