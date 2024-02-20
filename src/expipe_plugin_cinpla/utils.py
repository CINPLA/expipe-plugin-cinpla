from expipe.backends.filesystem import yaml_dump


def dump_project_config(project):
    expipe_file = project.path / "expipe.yaml"
    yaml_dump(expipe_file, project.config)
