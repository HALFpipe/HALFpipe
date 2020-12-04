# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import time
import logging
from stackprinter import format_thread
from threading import main_thread, Thread

from pympler import muppy, summary

logger = logging.getLogger("halfpipe.watchdog")


def init_watchdog(interval=60):
    def loop(interval):
        mainthread = main_thread()

        while True:
            time.sleep(interval)

            stacktrace = "".join(format_thread(mainthread))

            rows = summary.summarize(muppy.get_objects())
            memtrace = "\n".join(summary.format_(rows))

            logger.info(
                "Watchdog traceback:\n"
                f"{stacktrace}\n"
                f"{memtrace}"
            )

    thread = Thread(target=loop, args=(interval,), daemon=True, name="watchdog")
    thread.start()
