# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Optional

import logging
from pathlib import Path
import re

from .base import Writer
from ....io import AdaptiveLock

logger = logging.getLogger("halfpipe")

escape_codes_regex = re.compile(r"\x1b\[.*?(m|K)")


class FileWriter(Writer, AdaptiveLock):
    def __init__(self, **kwargs):
        Writer.__init__(self, **kwargs)
        AdaptiveLock.__init__(self)

        self.filename: Optional[Path] = None

        self.stream = None

    def check(self) -> bool:
        if self.filename is None or not isinstance(self.filename, Path):
            return False

        return True

    def acquire(self):
        assert self.filename is not None

        lock_file = str(self.filename.parent / f".{self.filename.name}.lock")  # hidden lock file
        self.lock(lock_file)

        self.stream = open(self.filename, mode="a", encoding="utf-8")

    def emit(self, msg: str, levelno: int):
        msg = escape_codes_regex.sub("", msg)
        self.stream.write(msg + self.terminator)

    def release(self):
        self.stream.close()

        self.unlock()
