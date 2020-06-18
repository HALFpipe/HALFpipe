# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import sys
import time
import logging
import threading
import traceback


def start_watchdog_daemon():
    def watchdog():
        logger = logging.getLogger("pipeline")
        mainthread = threading.main_thread()
        while True:
            time.sleep(60)
            frame = sys._current_frames()[mainthread.ident]
            msg = "".join(traceback.format_stack(frame))
            logger.info("Watchdog traceback: \n" + msg)

    watchdogthread = threading.Thread(target=watchdog, daemon=True, name="watchdog")
    watchdogthread.start()
