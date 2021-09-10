# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Union

from pathlib import Path
from dataclasses import dataclass
import logging


@dataclass
class EnableVerboseMessage:
    pass


@dataclass
class EnablePrintMessage:
    pass


@dataclass
class DisablePrintMessage:
    pass


@dataclass
class TeardownMessage:
    pass


@dataclass
class LogMessage:
    short_msg: str
    long_msg: str

    levelno: int = logging.DEBUG


@dataclass
class SetWorkdirMessage:
    workdir: Path


Message = Union[
    EnableVerboseMessage,
    EnablePrintMessage,
    DisablePrintMessage,
    TeardownMessage,
    LogMessage,
    SetWorkdirMessage,
]
