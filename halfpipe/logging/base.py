# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
from types import MethodType

from .context import Context
from .handler import QueueHandler
from .formatter import ColorFormatter
from .filter import DTypeWarningsFilter, PyWarningsFilter

loggernames = [
    "halfpipe",
    "halfpipe.ui",
    "halfpipe.watchdog",
    "nipype",
    "nipype.workflow",
    "nipype.utils",
    "nipype.filemanip",
    "nipype.interface",
    "py.warnings"
]


def setupcontext():
    queue = Context.queue()
    setup(queue)


def setup(queue, levelno=logging.INFO):
    logging.captureWarnings(True)

    def removehandlers(logger):
        c = logger
        while c:
            for hdlr in c.handlers:
                c.removeHandler(hdlr)
            if not c.propagate:
                break
            else:
                c = c.parent

    for loggername in loggernames:
        logger = logging.getLogger(loggername)
        removehandlers(logger)
        logger.propagate = False

    queuehandler = QueueHandler(queue)
    queuehandler.setFormatter(ColorFormatter())

    for loggername in loggernames:
        logger = logging.getLogger(loggername)
        logger.addHandler(queuehandler)

    for loggername in loggernames:
        logger = logging.getLogger(loggername)
        logger.setLevel(levelno)

    logging.getLogger("nipype.interface").addFilter(DTypeWarningsFilter())
    logging.getLogger("py.warnings").addFilter(PyWarningsFilter())

    # monkey patch nipype

    from nipype.utils.logger import Logging as nipypelogging

    def emptymethod(self, *args, **kwargs):
        pass

    nipypelogging.__init__ = emptymethod
    nipypelogging.enable_file_logging = emptymethod
    nipypelogging.disable_file_logging = emptymethod
    nipypelogging.update_logging = emptymethod

    # monkey patch fmriprep

    from fmriprep.config import loggers as fmripreploggers

    def emptyinit(cls):
        pass

    fmripreploggers.init = MethodType(emptyinit, fmripreploggers)


def teardown():
    Context.teardown()
