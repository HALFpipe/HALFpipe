# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from pathlib import Path
import re

from flufl.lock import Lock as FluflLock
from fasteners import InterProcessLock as FcntlLock

from .base import Writer

logger = logging.getLogger("halfpipe")

escapeCodesRegex = re.compile(r"\x1b\[.*?(m|K)")


class AdaptiveLock:
    timeout = 600

    def __init__(self):
        self.method = "hard_links"

        self.lock_instance = None

    def lock(self, lock_file):
        if self.method == "hard_links":
            self.lock_instance = FluflLock(lock_file, lifetime=60)  # seconds after which the lock is broken

            try:
                self.lock_instance.lock(timeout=self.timeout)  # try for a long time
                return
            except TimeoutError:
                pass
            except OSError:
                pass
            except PermissionError:
                pass

            logger.warning(
                "Unable to use hard link-based file locks. "
                "Trying fcntl-based file locks",
                exc_info=True
            )

            self.method = "fcntl"

        if self.method == "fcntl":
            self.lock_instance = FcntlLock(lock_file)

            acquired = self.lock_instance.acquire(timeout=self.timeout)

            if acquired:
                return

            logger.warning(
                "Unable to use fcntl-based file locks. "
                "Disabling file locks",
                exc_info=True
            )

            self.method = None
            self.delay = 10.0  # use a large delay to make write collisions unlikely

    def unlock(self):
        if self.method == "hard_links":
            self.lock_instance.unlock(unconditionally=True)  # do not raise errors in unlock
            self.lock_instance = None
        elif self.method == "fcntl":
            self.lock_instance.release()


class FileWriter(Writer, AdaptiveLock):
    def __init__(self, **kwargs):
        Writer.__init__(self, **kwargs)
        AdaptiveLock.__init__(self)

        self.filename = None

        self.stream = None

    def check(self) -> bool:
        if self.filename is None or not isinstance(self.filename, Path):
            return False

        return True

    def acquire(self):
        lock_file = str(self.filename.parent / f".{self.filename.name}.lock")  # hidden lock file
        self.lock(lock_file)

        self.stream = open(self.filename, mode="a", encoding="utf-8")

    def emit(self, msg: str, levelno: int):
        msg = escapeCodesRegex.sub("", msg)
        self.stream.write(msg + self.terminator)

    def release(self):
        self.stream.close()

        self.unlock()
