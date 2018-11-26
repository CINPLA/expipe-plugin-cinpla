from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.tools.action import generate_templates, query_yes_no


def register_entity(project_path, entity_id, user, message, location, tag, overwrite,
                    birthday, **kwargs):
    DTIME_FORMAT = expipe.core.datetime_format
    project = expipe.get_project(project_path)
    user = user or PAR.USERNAME
    if user is None:
        print('Missing option "user".')
        return
    if birthday is None:
        print('Missing option "birthday".')
        return
    try:
        entity = project.create_entity(entity_id)
    except KeyError as e:
        if overwrite:
            project.delete_entity(entity_id)
            entity = project.create_entity(entity_id)
        else:
            print(str(e) + '. Use "overwrite"')
            return
    if isinstance(birthday, str):
        birthday = datetime.strftime(
            datetime.strptime(birthday, '%d.%m.%Y'), DTIME_FORMAT)
    entity.datetime = datetime.now()
    entity.type = 'Subject'
    entity.tags.extend(list(tag))
    entity.location = location
    print('Registering user ' + user)
    entity.users = [user]
    for m in message:
        entity.create_message(text=m, user=user, datetime=datetime.now())
    template = project.templates[PAR.TEMPLATES['entity']].contents
    for key, val in kwargs.items():
        if isinstance(val, (str, float, int)):
            template[key]['value'] = val
        elif isinstance(val, tuple):
            if not None in val:
                template[key] = pq.Quantity(val[0], val[1])
        elif isinstance(val, type(None)):
            pass
        else:
            print('Not recognized type ' + str(type(val)))
            return
    not_reg_keys = []
    for key, val in template.items():
        if isinstance(val, dict):
            if val.get('value') is None:
                not_reg_keys.append(key)
            elif len(val.get('value')) == 0:
                not_reg_keys.append(key)
    if len(not_reg_keys) > 0:
        print('WARNING: No value registered for {}'.format(not_reg_keys))
    entity.create_module(name=PAR.TEMPLATES['entity'], contents=template)
