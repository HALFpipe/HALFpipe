# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from random import gauss
from time import sleep
from typing import List

from fasteners import InterProcessLock as FcntlLock
from flufl.lock._lockfile import Lock as FluflLock
from flufl.lock._lockfile import LockError as FluflLockError
from flufl.lock._lockfile import TimeOutError

from . import logger


class AdaptiveLock:
    def __init__(self, timeout: int = 180):
        self.timeout = timeout

        self.methods: List[str] = ["fcntl", "hard_links", "delay"]

        self.lock_instance = None

    def lock(self, lock_file):
        if self.methods[0] == "hard_links":
            self.lock_instance = FluflLock(
                lock_file, lifetime=self.timeout
            )  # seconds after which the lock is broken

            try:
                self.lock_instance.lock(timeout=self.timeout)  # try for a long time
                return
            except (FluflLockError, TimeOutError):  # timeouts etc.
                pass
            except OSError:  # such as PermissionError
                pass

            logger.warning("Unable to use hard link-based file locks", exc_info=True)

            self.methods.pop(0)
            self.lock(lock_file)

        elif self.methods[0] == "fcntl":
            self.lock_instance = FcntlLock(lock_file)

            acquired = self.lock_instance.acquire(timeout=self.timeout, delay=1)

            if acquired:
                return

            logger.warning("Unable to use fcntl-based file locks", exc_info=True)

            self.methods.pop(0)
            self.lock(lock_file)

        else:
            # use a random delay to make write collisions unlikely
            delay = gauss(20, 5)
            if delay > 0:
                sleep(delay)

    def unlock(self):
        if self.methods[0] == "hard_links":
            assert isinstance(self.lock_instance, FluflLock)

            self.lock_instance.unlock(
                unconditionally=True
            )  # do not raise errors in unlock
            self.lock_instance = None

        elif self.methods[0] == "fcntl":
            assert isinstance(self.lock_instance, FcntlLock)

            self.lock_instance.release()
