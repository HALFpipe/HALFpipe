# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from types import MethodType

import logging
import warnings

warnings.filterwarnings("ignore")  # catch all warnings while loading modules

from .context import Context  # noqa: E402
from .handler import QueueHandler  # noqa: E402
from .formatter import ColorFormatter  # noqa: E402
from .filter import DTypeWarningsFilter, PyWarningsFilter  # noqa: E402

warn = warnings.warn

loggernames = [
    "halfpipe",
    "halfpipe.ui",
    "halfpipe.watchdog",
    "nipype",
    "nipype.workflow",
    "nipype.utils",
    "nipype.filemanip",
    "nipype.interface",
    "py.warnings",
    "calamities",
]


def showwarning(message, category, filename, lineno, file=None, line=None):
    s = warnings.formatwarning(message, category, filename, lineno, line)
    logger = logging.getLogger("py.warnings")
    logger.warning(f"{s}", stack_info=True)


def setupcontext():
    queue = Context.queue()
    setup(queue)


def setup(queue, levelno=logging.INFO):
    queuehandler = QueueHandler(queue)
    queuehandler.setFormatter(ColorFormatter())
    queuehandler.setLevel(levelno)

    warnings.resetwarnings()

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

        # monkey patch warnings module to overwrite mriqc monkey patching
        warnings.warn = warn
        warnings.showwarning = showwarning

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
