import click
from pathlib import Path
from datetime import datetime

import expipe

from expipe_plugin_cinpla.scripts import register
from expipe_plugin_cinpla.cli.utils import validate_depth, validate_position, validate_angle, validate_adjustment


import spikeinterface.sorters as ss


def attach_to_register(cli):
    ### OpenEphys ###
    @cli.command("openephys", short_help="Register an open-ephys recording-action to database.")
    @click.argument("openephys-path", type=click.Path(exists=True))
    @click.argument("probe-path", type=click.Path(exists=True))
    @click.option(
        "-p",
        "--project-path",
        type=click.STRING,
        default=".",
        help="The project path. Default is current directory.",
    )
    @click.option(
        "-u",
        "--user",
        type=click.STRING,
        help="The experimenter performing the recording.",
    )
    @click.option(
        "-d",
        "--depth",
        multiple=True,
        callback=validate_depth,
        help=(
            'Alternative "find" to find from surgery or adjustment'
            + " or given as <key num depth unit> e.g. "
            + "<mecl 0 10 um> (omit <>)."
        ),
    )
    @click.option(
        "--include-events",
        is_flag=True,
        help="Include events in NWB file.",
    )
    @click.option(
        "-l",
        "--location",
        type=click.STRING,
        help='The location of the recording, i.e. "room-1-ibv".',
    )
    @click.option(
        "--session",
        type=click.STRING,
        help="Session number, assumed to be in end of filename by default",
    )
    @click.option(
        "--action-id",
        type=click.STRING,
        help=("Desired action id for this action, if none" + ", it is generated from open-ephys-path."),
    )
    @click.option(
        "--entity-id",
        type=click.STRING,
        help="The id number of the entity.",
    )
    @click.option(
        "-m",
        "--message",
        type=click.STRING,
        help='Add message, use "text here" for sentences.',
    )
    @click.option(
        "-t",
        "--tags",
        multiple=True,
        type=click.STRING,
        help="Add tags to action.",
    )
    @click.option(
        "--overwrite",
        is_flag=True,
        help="Overwrite files and expipe action.",
    )
    @click.option(
        "--register-depth",
        is_flag=True,
        help="Overwrite files and expipe action.",
    )
    @click.option(
        "--templates",
        multiple=True,
        type=click.STRING,
        help="Which templates to add",
    )
    def _register_openephys_recording(
        action_id,
        openephys_path,
        probe_path,
        project_path,
        depth,
        overwrite,
        templates,
        entity_id,
        include_events,
        user,
        session,
        location,
        message,
        tags,
        register_depth,
    ):
        project = expipe.get_project(path=Path(project_path))
        register.register_openephys_recording(
            project=project,
            action_id=action_id,
            openephys_path=openephys_path,
            probe_path=probe_path,
            depth=depth,
            overwrite=overwrite,
            include_events=include_events,
            entity_id=entity_id,
            user=user,
            session=session,
            location=location,
            message=message,
            tags=tags,
            delete_raw_data=None,
            correct_depth_answer=None,
            register_depth=register_depth,
        )

    ### Surgery ###
    @cli.command("surgery", short_help="Register a surgery action.")
    @click.argument("entity-id")
    @click.option(
        "-p",
        "--project-path",
        type=click.STRING,
        default=".",
        help="The project path. Default is current directory.",
    )
    @click.option(
        "--date",
        "-d",
        required=True,
        type=click.STRING,
        help='The date of the surgery format: "dd.mm.yyyyTHH:MM".',
    )
    @click.option(
        "-t",
        "--tags",
        multiple=True,
        type=click.STRING,
        help="Add tags to action.",
    )
    @click.option(
        "--procedure",
        required=True,
        type=click.Choice(["implantation", "injection"]),
        help='The type of surgery "implantation" or "injection".',
    )
    @click.option(
        "--overwrite",
        is_flag=True,
        help="Overwrite modules or not.",
    )
    @click.option(
        "-u",
        "--user",
        type=click.STRING,
        help="The experimenter performing the surgery.",
    )
    @click.option(
        "-w",
        "--weight",
        nargs=2,
        type=(click.FLOAT, click.STRING),
        default=(None, None),
        help="The weight of the entity with unit i.e. <200 g> (ommit <>).",
    )
    @click.option(
        "-p",
        "--position",
        required=True,
        multiple=True,
        callback=validate_position,
        help='The position e.g. <"mecl 30 deg"> (omit <>).',
    )
    @click.option(
        "-a",
        "--angle",
        required=True,
        multiple=True,
        callback=validate_angle,
        help='The angle of implantation/injection e.g. <"mecl 0 x y z mm"> (omit <>)',
    )
    @click.option(
        "--message",
        "-m",
        type=click.STRING,
        help='Add message, use "text here" for sentences.',
    )
    @click.option(
        "-l",
        "--location",
        type=click.STRING,
        required=True,
        help='The location of the surgery, i.e. "room-1-ibv".',
    )
    @click.option(
        "--templates",
        multiple=True,
        type=click.STRING,
        help="Which templates to add",
    )
    def _register_surgery(
        project_path,
        entity_id,
        procedure,
        date,
        user,
        weight,
        location,
        overwrite,
        position,
        angle,
        message,
        tags,
        templates,
    ):
        project = expipe.get_project(path=Path(project_path))
        date = datetime.strptime(date, "%d.%m.%YT%H:%M")
        register.register_surgery(
            project,
            entity_id,
            procedure,
            date,
            user,
            weight,
            location,
            overwrite,
            position,
            angle,
            message,
            tags,
            templates,
        )

    ### Perfusion ###
    @cli.command(
        "perfusion", short_help=("Register a perfusion action. " + "Also tags the entity as perfused and euthanised.")
    )
    @click.argument("entity-id")
    @click.option(
        "-p",
        "--project-path",
        type=click.STRING,
        default=".",
        help="The project path. Default is current directory.",
    )
    @click.option(
        "--date",
        "-d",
        required=True,
        type=click.STRING,
        help='The date of the surgery format: "dd.mm.yyyyTHH:MM".',
    )
    @click.option(
        "-u",
        "--user",
        type=click.STRING,
        help="The experimenter performing the surgery.",
    )
    @click.option(
        "--weight",
        nargs=2,
        type=(click.FLOAT, click.STRING),
        default=(None, None),
        help="The weight of the animal.",
    )
    @click.option(
        "-l",
        "--location",
        type=click.STRING,
        help='The location of the recording, i.e. "room-1-ibv".',
    )
    @click.option(
        "--overwrite",
        is_flag=True,
        help="Overwrite files and expipe action.",
    )
    @click.option(
        "--message",
        "-m",
        type=click.STRING,
        help='Add message, use "text here" for sentences.',
    )
    @click.option(
        "--templates",
        multiple=True,
        type=click.STRING,
        help="Which templates to add",
    )
    def _register_perfusion(entity_id, project_path, date, user, weight, overwrite, message, templates, location):
        project = expipe.get_project(path=Path(project_path))
        register.register_perfusion(project, entity_id, date, user, weight, overwrite, message, templates, location)

    ### Entity ###
    @cli.command("entity", short_help=("Register a entity."))
    @click.argument("entity-id")
    @click.option(
        "-p",
        "--project-path",
        type=click.STRING,
        default=".",
        help="The project path. Default is current directory.",
    )
    @click.option(
        "-u",
        "--user",
        type=click.STRING,
        help="The experimenter performing the registration.",
    )
    @click.option(
        "--location",
        required=True,
        type=click.STRING,
        help="The location of the animal.",
    )
    @click.option(
        "--birthday",
        required=True,
        type=click.STRING,
        help='The birthday of the entity, format: "dd.mm.yyyy".',
    )
    @click.option(
        "--cell_line",
        type=click.STRING,
        help="Add cell line to entity.",
    )
    @click.option(
        "--developmental-stage",
        type=click.STRING,
        help="The developemtal stage of the entity. E.g. 'embroyonal', 'adult', 'larval' etc.",
    )
    @click.option(
        "--gender",
        type=click.STRING,
        required=True,
        help="Male or female?",
    )
    @click.option(
        "--genus",
        type=click.STRING,
        help='The Genus of the studied entity. E.g "rattus"',
    )
    @click.option(
        "--health_status",
        type=click.STRING,
        help="Information about the health status of this entity.",
    )
    @click.option(
        "--label",
        type=click.STRING,
        help="If the entity has been labled in a specific way. The lable can be described here.",
    )
    @click.option(
        "--population",
        type=click.STRING,
        help="The population this entity is offspring of. This may be the bee hive, the ant colony, etc.",
    )
    @click.option(
        "--species",
        type=click.STRING,
        required=True,
        help="The scientific name of the species e.g. Apis mellifera, Homo sapiens.",
    )
    @click.option(
        "--strain",
        type=click.STRING,
        help="The strain the entity was taken from. E.g. a specific genetic variation etc.",
    )
    @click.option(
        "--trivial_name",
        type=click.STRING,
        help="The trivial name of the species like Honeybee, Human.",
    )
    @click.option(
        "--weight",
        nargs=2,
        type=(click.FLOAT, click.STRING),
        default=(None, None),
        help="The weight of the animal.",
    )
    @click.option(
        "--message",
        "-m",
        type=click.STRING,
        help='Add message, use "text here" for sentences.',
    )
    @click.option(
        "-t",
        "--tags",
        multiple=True,
        type=click.STRING,
        help="Add tags to entity.",
    )
    @click.option(
        "--overwrite",
        is_flag=True,
        help="Overwrite existing module",
    )
    @click.option(
        "--templates",
        multiple=True,
        type=click.STRING,
        help="Which templates to add",
    )
    def _register_entity(
        entity_id,
        project_path,
        user,
        species,
        gender,
        message,
        location,
        tags,
        overwrite,
        birthday,
        templates,
        **kwargs,
    ):
        project = expipe.get_project(path=Path(project_path))
        register.register_entity(
            project, entity_id, user, species, gender, message, location, tags, overwrite, birthday, templates, **kwargs
        )

    ### Adjustment ###
    @cli.command("adjustment", short_help="Parse info about drive depth adjustment")
    @click.argument("entity-id", type=click.STRING)
    @click.option(
        "-p",
        "--project-path",
        type=click.STRING,
        default=".",
        help="The project path. Default is current directory.",
    )
    @click.option(
        "--date",
        type=click.STRING,
        help=('The date of the surgery format: "dd.mm.yyyyTHH:MM" ' + 'or "now".'),
    )
    @click.option(
        "-a",
        "--adjustment",
        multiple=True,
        callback=validate_adjustment,
        help=("The adjustment amount on given anatomical location " + "given as <key num value unit>"),
    )
    @click.option(
        "-d",
        "--depth",
        multiple=True,
        callback=validate_depth,
        help=("The depth given as <key num depth unit> e.g. " + "<mecl 0 10 um> (omit <>)."),
    )
    @click.option(
        "-u",
        "--user",
        type=click.STRING,
        help="The experimenter performing the adjustment.",
    )
    @click.option(
        "-y",
        "--yes",
        is_flag=True,
        help="No query for correct adjustment.",
    )
    def _register_adjustment(entity_id, project_path, date, adjustment, user, depth, yes):
        project = expipe.get_project(path=Path(project_path))
        register.register_adjustment(project, entity_id, date, adjustment, user, depth, yes)

    ### Annotation ###
    @cli.command("annotation", short_help="Parse info about recorded units")
    @click.argument("action-id", type=click.STRING)
    @click.option(
        "-p",
        "--project-path",
        type=click.STRING,
        default=".",
        help="The project path. Default is current directory.",
    )
    @click.option(
        "-t",
        "--tags",
        multiple=True,
        type=click.STRING,
        help="Add tags to action.",
    )
    @click.option(
        "--message",
        "-m",
        type=click.STRING,
        help='Add message, use "text here" for sentences.',
    )
    @click.option(
        "-u",
        "--user",
        type=click.STRING,
        help="The experimenter performing the annotation.",
    )
    def annotate(action_id, project_path, tags, message, user):
        from datetime import datetime

        project = expipe.get_project(path=Path(project_path))
        action = project.actions[action_id]
        user = user or project.config.get("username")
        if user is None:
            raise ValueError("Please add user name")
        users = list(set(action.users))
        if user not in users:
            users.append(user)
        action.users = users
        if message:
            action.create_message(text=message, user=user, datetime=datetime.now())
        if tags:
            action.tags.extend(tags)
