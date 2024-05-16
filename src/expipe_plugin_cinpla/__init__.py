# -*- coding: utf-8 -*-
import importlib.metadata

from .cli import CinplaPlugin  # noqa
from .scripts import convert_old_project  # noqa
from .widgets import display_browser  # noqa

__version__ = importlib.metadata.version("expipe_plugin_cinpla")
