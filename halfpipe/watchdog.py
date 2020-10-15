# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import sys
import time
import logging
from traceback import format_stack
from threading import main_thread, Thread

logger = logging.getLogger("halfpipe.watchdog")


class Watchdog:

    def __init__(self, interval=60):
        self.interval = interval

        thread = Thread(target=self.loop, daemon=True, name="watchdog")
        thread.start()

    def loop(self):
        mainthread = main_thread()

        while True:
            time.sleep(self.interval)
            frame = sys._current_frames()[mainthread.ident]
            stacktrace = "".join(format_stack(frame))
            logger.info(f"Watchdog traceback: \n {stacktrace}")
