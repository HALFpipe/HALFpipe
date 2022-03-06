# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
import time
from threading import Thread, main_thread

from pympler import muppy, summary
from stackprinter import format_thread

logger = logging.getLogger("halfpipe.watchdog")


def init_watchdog(interval=60):
    def loop(interval):
        mainthread = main_thread()

        while True:
            time.sleep(interval)

            try:
                stacktrace = "".join(format_thread(mainthread))

                rows = summary.summarize(muppy.get_objects())
                memtrace = "\n".join(summary.format_(rows))

                logger.info("Watchdog traceback:\n" f"{stacktrace}\n" f"{memtrace}")
            except Exception as e:
                logger.error("Error in watchdog", exc_info=e)

    thread = Thread(target=loop, args=(interval,), daemon=True, name="watchdog")
    thread.start()
