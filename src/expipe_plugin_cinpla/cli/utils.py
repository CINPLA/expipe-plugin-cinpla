# -*- coding: utf-8 -*-
import collections
import copy

import click

from expipe_plugin_cinpla.tools.imports import *


def deep_update(d, other):
    for k, v in other.items():
        d_v = d.get(k)
        if isinstance(v, collections.Mapping) and isinstance(d_v, collections.Mapping):
            deep_update(d_v, v)
        else:
            d[k] = copy.deepcopy(v)


def validate_cluster_group(ctx, param, cluster_group):
    try:
        tmp = []
        for cl in cluster_group:
            group, cluster, sorting = cl.split(" ", 3)
            tmp.append((int(group), int(cluster), sorting))
        out = {cl[0]: dict() for cl in tmp}
        for cl in tmp:
            out[cl[0]].update({cl[1]: cl[2]})
        return out
    except ValueError:
        raise click.BadParameter(
            'cluster-group needs to be contained in "" and '
            + "separated with white space i.e "
            + "<channel_group cluster_id good|noise|unsorted> (ommit <>)."
        )


def validate_depth(ctx, param, depth):
    if depth == "find":
        return depth
    try:
        out = []
        for pos in depth:
            key, num, z, unit = pos.split(" ", 4)
            out.append((key, int(num), float(z), unit))
        return tuple(out)
    except ValueError:
        raise click.BadParameter(
            'Depth need to be contained in "" and '
            + "separated with white space i.e "
            + '<"key num depth physical_unit"> (ommit <>).'
        )


def validate_position(ctx, param, position):
    try:
        out = []
        for pos in position:
            key, num, x, y, z, unit = pos.split(" ", 6)
            out.append((key, int(num), float(x), float(y), float(z), unit))
        return tuple(out)
    except ValueError:
        raise click.BadParameter(
            'Position need to be contained in "" and '
            + "separated with white space i.e "
            + '<"key num x y z physical_unit"> (ommit <>).'
        )


def validate_angle(ctx, param, position):
    try:
        out = []
        for pos in position:
            key, num, angle, unit = pos.split(" ", 4)
            out.append((key, int(num), float(angle), unit))
        return tuple(out)
    except ValueError:
        raise click.BadParameter(
            'Angle need to be contained in "" and '
            + "separated with white space i.e "
            + '<"key probe angle physical_unit"> (ommit <>).'
        )


def validate_adjustment(ctx, param, position):
    try:
        out = []
        for pos in position:
            key, num, z, unit = pos.split(" ", 4)
            out.append((key, int(num), float(z), unit))
        return tuple(out)
    except ValueError:
        raise click.BadParameter(
            'Position need to be contained in "" and '
            + "separated with white space i.e "
            + '<"key num z physical_unit"> (ommit <>).'
        )


def optional_choice(ctx, param, value):
    options = param.envvar
    assert isinstance(options, list)
    if value is None:
        if param.required:
            raise ValueError(f'Missing option "{param.opts}"')
        return value
    if param.multiple:
        if len(value) == 0:
            if param.required:
                raise ValueError(f'Missing option "{param.opts}"')
            return value
    if len(options) == 0:
        return value
    else:
        if isinstance(value, (str, int, float)):
            value = [
                value,
            ]
        for val in value:
            if val not in options:
                raise ValueError(f'Value "{val}" not in "{options}".')
            else:
                if param.multiple:
                    return value
                else:
                    return value[0]
