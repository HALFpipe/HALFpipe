# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import json
import os
import inspect

from logging import Handler, StreamHandler, Formatter
from .utils import transpose


def init_logging(workdir, jsonfile):
    """
    Add new logging handler to nipype to output to log directory

    :param workdir: Log directory

    """
    fp = os.path.join(workdir, jsonfile)

    with open(fp, "r") as f:
        data = json.load(f)

    images = transpose(data["images"])

    real_output_dir = os.path.join(workdir, "log")

    hdlr = WfHandler(real_output_dir, images)

    from nipype import logging as nlogging
    from nipype import config

    formatter = Formatter(fmt=nlogging.fmt, datefmt=nlogging.datefmt)
    hdlr.setFormatter(formatter)

    config.set("logging", "interface_level", "DEBUG")
    nlogging.update_logging(config)

    nlogging._iflogger.handlers = []
    nlogging._iflogger.propagate = False
    nlogging._iflogger.addHandler(hdlr)

    nlogging._logger.handlers = []
    nlogging._logger.propagate = True
    nlogging._logger.addHandler(hdlr)


class WfHandler(StreamHandler):
    """ Needs rewrite """

    def __init__(self, output_dir, images):
        self.output_dir = output_dir
        self.images = images

        self.files = {k: os.path.join(output_dir, "%s.txt" % k) for k in images.keys()}
        self.handles = {k: None for k in images.keys()}

        os.makedirs(self.output_dir, exist_ok=True)
        self.catch_all = open(os.path.join(output_dir, "log.txt"), "a")

        Handler.__init__(self)

    def emit(self, record):
        """

        :param record: 

        """
        stack = inspect.stack()
        try:
            if stack is not None:
                for s in stack:
                    if "self" in s.frame.f_locals:
                        obj = s.frame.f_locals["self"]
                        if hasattr(obj, "_hierarchy"):
                            hierarchy = obj._hierarchy
                            for k, stream in self.handles.items():
                                if k in hierarchy:
                                    if stream is None:
                                        self.handles[k] = open(self.files[k], "a")
                                        stream = self.handles[k]
                                    self.stream = stream
                                    StreamHandler.emit(self, record)
                                    return
        except Exception as e:
            pass

        self.stream = self.catch_all
        StreamHandler.emit(self, record)
        # print(record)

#     def acquire(self):
#         """ Acquire thread and file locks. Also re-opening log file when running
#         in "degraded" mode. """
#         # handle thread lock
#         Handler.acquire(self)
#         lock(self.stream_lock, LOCK_EX)
#         if self.stream.closed:
#             self._openFile(self.mode)
# 
#     def release(self):
#         """ Release file and thread locks. Flush stream and take care of closing
#         stream in "degraded" mode. """
#         try:
#             if not self.stream.closed:
#                 self.stream.flush()
#                 if self._rotateFailed:
#                     self.stream.close()
#         except IOError:
#             if self._rotateFailed:
#                 self.stream.close()
#         finally:
#             try:
#                 unlock(self.stream_lock)
#             finally:
#                 # release thread lock
#                 Handler.release(self)
# 
#     def close(self):
#         """
#         Closes the stream.
#         """
#         if not self.stream.closed:
#             self.stream.flush()
#             self.stream.close()
#         Handler.close(self)
# 
#     def flush(self):
#         """ flush():  Do nothing.
#         Since a flush is issued in release(), we don"t do it here. To do a flush
#         here, it would be necessary to re-lock everything, and it is just easier
#         and cleaner to do it all in release(), rather than requiring two lock
#         ops per handle() call.
#         Doing a flush() here would also introduces a window of opportunity for
#         another process to write to the log file in between calling
#         stream.write() and stream.flush(), which seems like a bad thing. """
# pass
