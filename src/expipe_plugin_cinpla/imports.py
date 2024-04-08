import expipe
from pathlib import Path


local_root, _ = expipe.config._load_local_config(Path.cwd())
if local_root is not None:
    project = expipe.get_project(path=local_root)
else:

    class P:
        config = {}

    project = P
