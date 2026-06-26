"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from .app import ViridApp
from .core import *
from .decorators import *
from .util import register_base_handlers, toggle_log
from .app import ViridApp


def create_virid(
    max_depth: int = 1000,
    enable_logging: bool = True,
) -> ViridApp:
    virid_app = ViridApp(max_depth)
    register_base_handlers(virid_app)
    toggle_log(enable_logging)
    return virid_app
