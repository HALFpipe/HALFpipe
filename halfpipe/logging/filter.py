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


pywarnings_to_ignore: list[str] = [
    "ParserWarning",
    "FutureWarning",
    "DeprecationWarning",
    "DependencyWarning",
    # numpy
    "RuntimeWarning: Mean of empty slice",
    "`np.bool` is a deprecated alias for the builtin `bool`. To silence this warning, use `bool` by itself. Doing this will not modify any behavior and is safe. If you specifically wanted the numpy scalar type, use `np.bool_` here.",
    "`np.int` is a deprecated alias for the builtin `int`. To silence this warning, use `int` by itself. Doing this will not modify any behavior and is safe. When replacing `np.int`, you may wish to use e.g. `np.int64` or `np.int32` to specify the precision. If you wish to review your current use, check the release note link for additional information.",
    "`np.float` is a deprecated alias for the builtin `float`. To silence this warning, use `float` by itself. Doing this will not modify any behavior and is safe. If you specifically wanted the numpy scalar type, use `np.float64` here.",
    # nipype
    "cmp not installed",
    "The trackvis interface has been deprecated and will be removed in v4.0; please use the 'nibabel.streamlines' interface.",
    "This has not been fully tested. Please report any failures.",
]

pywarnings_to_hide: list[str] = [
    # numpy
    "invalid value encountered in",
    "divide by zero encountered in",
    # nitransforms
    "Reference space not set",
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
