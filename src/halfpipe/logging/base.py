# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import logging
import warnings
from multiprocessing.queues import JoinableQueue
from types import MethodType

warnings.filterwarnings("ignore")  # catch all warnings while loading modules

from .context import Context as LoggingContext  # noqa: E402
from .filter import DTypeWarningsFilter, PyWarningsFilter  # noqa: E402
from .formatter import ColorFormatter  # noqa: E402
from .handler import QueueHandler  # noqa: E402

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
    "niworkflows",
    "py.warnings",
]


def showwarning(message, category, filename, lineno, _=None, line=None):
    s = warnings.formatwarning(message, category, filename, lineno, line)
    logger = logging.getLogger("py.warnings")
    logger.warning(f"{s}", stack_info=True)


def setup_context():
    LoggingContext.setup_worker()
    queue = LoggingContext.queue()
    assert isinstance(queue, JoinableQueue)
    setup(queue)


def setup(queue, levelno=logging.INFO):
    queue_handler = QueueHandler(queue)
    queue_handler.setFormatter(ColorFormatter())
    queue_handler.setLevel(levelno)

    warnings.resetwarnings()

    def remove_handlers(logger):
        c = logger
        while c:
            for hdlr in c.handlers:
                c.removeHandler(hdlr)
            if not c.propagate:
                break
            else:
                c = c.parent

    def setup_loggers():
        for loggername in loggernames:
            logger = logging.getLogger(loggername)
            remove_handlers(logger)
            logger.propagate = False

            logger.filters = []

            logger.addHandler(queue_handler)

            logger.setLevel(levelno)

        # monkey patch warnings module to overwrite dependencies monkey patching
        warnings.warn = warn
        warnings.showwarning = showwarning

        logging.getLogger("nipype.interface").addFilter(DTypeWarningsFilter())
        logging.getLogger("py.warnings").addFilter(PyWarningsFilter())

    setup_loggers()

    from fmriprep.config import loggers as fmriprep_loggers
    from nipype.utils.logger import Logging as NipypeLogging

    setup_loggers()  # re-do setup

    # monkey patch nipype and fmriprep
    # so that thhe logging config will not be overwritten

    def empty_method(self, *args, **kwargs):
        _, _, _ = self, args, kwargs
        pass

    def empty_init(_):
        pass

    NipypeLogging.__init__ = empty_method
    NipypeLogging.enable_file_logging = empty_method
    NipypeLogging.disable_file_logging = empty_method
    NipypeLogging.update_logging = empty_method
    fmriprep_loggers.init = MethodType(empty_init, fmriprep_loggers)


def teardown():
    LoggingContext.teardown_worker()
