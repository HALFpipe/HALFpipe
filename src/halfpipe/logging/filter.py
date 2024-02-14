# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
import re
from logging import Filter


def set_level(record, levelno=logging.DEBUG):
    record.levelno = levelno
    record.levelname = logging.getLevelName(levelno)


dtype_pattern = re.compile(r"Changing (.+) dtype from (.+) to (.+)")


class DTypeWarningsFilter(Filter):
    def filter(self, record):
        message = record.getMessage()

        if dtype_pattern.search(message) is not None:
            set_level(record, levelno=logging.INFO)

        return True


pywarnings_to_ignore: list[str] = []

pywarnings_to_hide: list[str] = [
    # numpy
    "invalid value encountered in",
    "divide by zero encountered in",
    # nitransforms
    "Reference space not set",
    # statsmodels
    "overflow encountered in",
]


def compile_list(ww: list[str]) -> re.Pattern:
    escaped: list[str] = [str(re.escape(w)) for w in ww]
    regex_str = "|".join(escaped)
    return re.compile(f"(?:{regex_str})")


ignore_pattern = compile_list(pywarnings_to_ignore)
hide_pattern = compile_list(pywarnings_to_hide)


class PyWarningsFilter(Filter):
    def __init__(self, name: str = "pywarnings_filter") -> None:
        super().__init__(name=name)

    def filter(self, record):
        message = record.getMessage()

        if ignore_pattern.search(message):
            set_level(record, levelno=logging.DEBUG)

        if hide_pattern.search(message):
            set_level(record, levelno=logging.INFO)

        return True
