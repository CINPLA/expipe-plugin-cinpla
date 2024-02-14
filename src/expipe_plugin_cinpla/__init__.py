from .cli import CinplaPlugin
from .widgets import display
from .scripts import convert_old_project

import importlib.metadata

__version__ = importlib.metadata.version("expipe_plugin_cinpla")
