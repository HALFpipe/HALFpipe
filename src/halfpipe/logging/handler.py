# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from copy import copy
from logging import Handler

from .worker.message import LogMessage


class QueueHandler(Handler):
    def __init__(self, queue):
        super(QueueHandler, self).__init__()
        self.queue = queue

    def emit(self, record):
        try:
            long_msg = self.format(record)

            short_record = copy(record)
            short_record.exc_info = None
            short_record.exc_text = None
            short_record.stack_info = None

            short_msg = self.format(short_record)

            obj = LogMessage(short_msg=short_msg, long_msg=long_msg, levelno=record.levelno)
            self.queue.put(obj)
        except Exception:
            self.handleError(record)
