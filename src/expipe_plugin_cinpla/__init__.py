#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2024
#
# This file is part of expipe-plugin-cinpla
# SPDX-License-Identifier:    GPLv3

import importlib.metadata

from .cli import CinplaPlugin
from .scripts import convert_old_project
from .tools import DataProcessor
from .widgets import display_browser

__version__ = importlib.metadata.version(__package__)

__all__ = [
    "CinplaPlugin",
    "convert_old_project",
    "DataProcessor",
    "display_browser",
]
