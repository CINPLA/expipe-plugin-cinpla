from pathlib import Path

import expipe_plugin_cinpla

old_project_path = Path("path-to-old-expipe-project")
new_project_path = Path("path-to-new-expipe-project")

probe_path = Path("path-to-probe-JSON-file")

expipe_plugin_cinpla.convert_old_project(old_project_path, new_project_path, probe_path=probe_path, overwrite=True)
