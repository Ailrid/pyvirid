"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from .app import ViridApp
from .core import *
from .decorators import *
from .util import register_base_handlers, Logger
from .app import ViridApp


def create_virid(
    max_depth: int = 1000,
    enable_logging: bool = True,
) -> ViridApp:
    virid_app = ViridApp(max_depth)
    register_base_handlers(virid_app)
    virid_app.get(Logger).enable_logging = enable_logging
    return virid_app
