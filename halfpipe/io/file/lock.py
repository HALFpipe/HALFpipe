# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from flufl.lock import Lock as FluflLock
from fasteners import InterProcessLock as FcntlLock

from time import sleep
from random import gauss

from ...utils import logger


class AdaptiveLock:
    timeout = 600

    def __init__(self):
        self.method = "hard_links"

        self.lock_instance = None

    def lock(self, lock_file):
        if self.method == "hard_links":
            self.lock_instance = FluflLock(lock_file, lifetime=self.timeout)  # seconds after which the lock is broken

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

        if self.method is None:
            # use a random delay to make write collisions unlikely
            delay = gauss(20.0, 2.5)
            if delay > 0:
                sleep(delay)

    def unlock(self):
        if self.method == "hard_links":
            assert isinstance(self.lock_instance, FluflLock)

            self.lock_instance.unlock(unconditionally=True)  # do not raise errors in unlock
            self.lock_instance = None

        elif self.method == "fcntl":
            assert isinstance(self.lock_instance, FcntlLock)

            self.lock_instance.release()
