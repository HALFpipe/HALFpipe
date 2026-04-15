# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from random import gauss
from time import sleep
from typing import List

from fasteners import InterProcessLock as FcntlLock
from flufl.lock._lockfile import Lock as FluflLock
from flufl.lock._lockfile import LockError as FluflLockError
from flufl.lock._lockfile import TimeOutError


class AdaptiveLock:
    def __init__(self, timeout: int = 180) -> None:
        self.timeout = timeout

        self.methods: List[str] = ["fcntl", "hard_links", "delay"]

        self.fcntl_lock: FcntlLock | None = None
        self.flufl_lock: FluflLock | None = None

    def lock(self, lock_file: str) -> None:
        if self.methods[0] == "hard_links":
            self.flufl_lock = FluflLock(lock_file, lifetime=self.timeout)  # seconds after which the lock is broken

            try:
                self.flufl_lock.lock(timeout=self.timeout)  # try for a long time
                return
            except (FluflLockError, TimeOutError):  # timeouts etc.
                pass
            except OSError:  # such as PermissionError
                pass

            logging.warning("Unable to use hard link-based file locks", exc_info=True)

            self.methods.pop(0)
            self.lock(lock_file)

        elif self.methods[0] == "fcntl":
            self.fcntl_lock = FcntlLock(lock_file)

            acquired = self.fcntl_lock.acquire(timeout=self.timeout, delay=1)

            if acquired:
                return

            logging.warning("Unable to use fcntl-based file locks", exc_info=True)

            self.methods.pop(0)
            self.lock(lock_file)

        else:
            # use a random delay to make write collisions unlikely
            delay = gauss(20, 5)
            if delay > 0:
                sleep(delay)

    def unlock(self) -> None:
        if self.flufl_lock is None and self.fcntl_lock is None:
            raise ValueError("Lock instance is None")
        if self.methods[0] == "hard_links":
            if not isinstance(self.flufl_lock, FluflLock):
                raise ValueError("Lock instance is not a FluflLock")
            self.flufl_lock.unlock(unconditionally=True)  # Do not raise errors in unlock
            self.flufl_lock = None
        elif self.methods[0] == "fcntl":
            if not isinstance(self.fcntl_lock, FcntlLock):
                raise ValueError("Lock instance is not an FcntlLock")
            self.fcntl_lock.release()  # type: ignore
            self.fcntl_lock = None
