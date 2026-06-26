"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from virid.core.app import ViridApp

from .core.message import ErrorMessage, InfoMessage, WarnMessage
from logging import getLogger
import logging
from .decorators import system

toggle_key = True


def toggle_log(enable_logging: bool) -> None:
    global toggle_key
    toggle_key = not enable_logging


class ViridFormatter(logging.Formatter):
    # 颜色与样式转义码
    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    MAGENTA = "\x1b[35m"
    CYAN = "\x1b[36m"
    GRAY = "\x1b[90m"

    def format(self, record):
        if record.levelno == logging.INFO:
            header = f"{self.GREEN}{self.BOLD} ✔ [Virid Info] {self.RESET}"
            record.msg = (
                f"{header}{self.GRAY}Global Info Caught:{self.RESET}\n"
                f"  {self.GREEN}Details:{self.RESET} {record.msg}"
            )
        elif record.levelno == logging.WARNING:
            header = f"{self.YELLOW}{self.BOLD} ⚠ [Virid Warn] {self.RESET}"
            context = f"{self.CYAN}{record.msg}{self.RESET}"
            record.msg = (
                f"{header}{self.GRAY}Global Warn Caught:{self.RESET}\n"
                f"  {self.YELLOW}Context:{self.RESET} {context}"
            )
        elif record.levelno == logging.ERROR:
            header = f"{self.RED}{self.BOLD} ✖ [Virid Error] {self.RESET}"

            if "context" in getattr(record, "msg_type", ""):
                record.msg = f"  {self.RED}Context:{self.RESET} {self.MAGENTA}{record.msg}{self.RESET}"
            else:
                record.msg = (
                    f"{header}{self.GRAY}Global Error Caught:{self.RESET}\n"
                    f"  {self.RED}Details:{self.RESET} {record.msg}"
                )

        return super().format(record)


logging.basicConfig(level=logging.INFO)
handler = logging.root.handlers[0]
handler.setFormatter(ViridFormatter("%(message)s"))
logger = getLogger(__name__)


@system(priority=-9999)
def error(message: ErrorMessage) -> None:
    global toggle_key
    if not toggle_key:
        return
    logger.error(message.error, extra={"msg_type": "error"})
    logger.error(message.context, extra={"msg_type": "context"})


@system(priority=-9999)
def info(message: InfoMessage) -> None:
    global toggle_key
    if not toggle_key:
        return
    logger.info(message.context)


@system(priority=-9999)
def warn(message: WarnMessage) -> None:
    global toggle_key
    if not toggle_key:
        return
    logger.warning(message.context)


def register_base_handlers(virid: ViridApp) -> None:
    virid.register(error)
    virid.register(info)
    virid.register(warn)
