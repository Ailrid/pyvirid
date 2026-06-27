"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from .app import ViridApp
from .core import *
from .decorators import *
from .util import register_base_handlers, ViridLogger
from .app import ViridApp


def create_virid(
    max_depth: int = 1000,
    enable_logging: bool = True,
) -> ViridApp:
    virid_app = ViridApp(max_depth)
    # 注册基础处理system和logger
    register_base_handlers(virid_app)
    virid_app.get(ViridLogger).enable_logging = enable_logging
    # 动态把自己给注册到controller上
    self_app = virid_app
    virid_app.spawn(self_app)

    return virid_app
