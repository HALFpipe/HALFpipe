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

    queuehandler = QueueHandler(queue)
    queuehandler.setFormatter(ColorFormatter())
    queuehandler.setLevel(levelno)

    def removeHandlers(logger):
        c = logger
        while c:
            for hdlr in c.handlers:
                c.removeHandler(hdlr)
            if not c.propagate:
                break
            else:
                c = c.parent

    def setupLoggers():
        for loggername in loggernames:
            logger = logging.getLogger(loggername)
            removeHandlers(logger)
            logger.propagate = False

            logger.filters = []

            logger.addHandler(queuehandler)

            logger.setLevel(levelno)

        logging.getLogger("nipype.interface").addFilter(DTypeWarningsFilter())
        logging.getLogger("py.warnings").addFilter(PyWarningsFilter())

    setupLoggers()

    from nipype.utils.logger import Logging as nipypelogging
    from fmriprep.config import loggers as fmripreploggers
    from mriqc.config import loggers as mriqcloggers

    setupLoggers()  # re-do setup

    # monkey patch nipype, fmriprep and mriqc
    # so that thhe logging config will not be overwritten

    def emptymethod(self, *args, **kwargs):
        pass

    def emptyinit(cls):
        pass

    nipypelogging.__init__ = emptymethod
    nipypelogging.enable_file_logging = emptymethod
    nipypelogging.disable_file_logging = emptymethod
    nipypelogging.update_logging = emptymethod
    fmripreploggers.init = MethodType(emptyinit, fmripreploggers)
    mriqcloggers.init = MethodType(emptyinit, mriqcloggers)


def teardown():
    Context.teardown()
